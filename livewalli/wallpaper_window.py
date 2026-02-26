"""Borderless NSWindow with AVPlayerLayer for live wallpaper (below desktop icons)."""
import objc
from AppKit import (
    NSWindow,
    NSView,
    NSWindowStyleMaskBorderless,
    NSColor,
    NSBackingStoreBuffered,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorStationary,
)
from Quartz import CGWindowLevelForKey, kCGDesktopWindowLevelKey
from AVFoundation import (
    AVPlayer,
    AVPlayerLayer,
    AVURLAsset,
    AVPlayerItem,
    AVLayerVideoGravityResizeAspectFill,
    AVLayerVideoGravityResizeAspect,
    AVLayerVideoGravityResize,
)
from Foundation import NSURL, NSNotificationCenter
from CoreMedia import CMTimeMakeWithSeconds

# Scale mode to AVLayerVideoGravity (center uses custom frame, not gravity)
GRAVITY_MAP = {
    "fill": AVLayerVideoGravityResizeAspectFill,
    "fit": AVLayerVideoGravityResizeAspect,
    "stretch": AVLayerVideoGravityResize,
    "center": AVLayerVideoGravityResizeAspect,  # frame set to centered native size
}


def _centerLayerFrame(asset, content_bounds, player_layer):
    """Set player_layer frame to video native size centered in content_bounds. No underscores in name for PyObjC."""
    try:
        tracks = asset.tracksWithMediaType_("vide")
        if tracks is None or len(tracks) == 0:
            player_layer.setFrame_(content_bounds)
            return
        track = tracks[0]
        size = track.naturalSize()
        w = size.width
        h = size.height
        if w <= 0 or h <= 0:
            player_layer.setFrame_(content_bounds)
            return
        transform = track.preferredTransform()
        if abs(transform.a) < 0.1 and abs(transform.b) > 0.9:
            w, h = h, w
        bw = content_bounds.size.width
        bh = content_bounds.size.height
        x = (bw - w) / 2 + content_bounds.origin.x
        y = (bh - h) / 2 + content_bounds.origin.y
        from Foundation import NSMakeRect
        player_layer.setFrame_(NSMakeRect(x, y, w, h))
    except Exception:
        if player_layer is not None and content_bounds is not None:
            player_layer.setFrame_(content_bounds)


class WallpaperWindow(NSWindow):
    """A borderless, transparent window that shows video below desktop icons."""

    def initWithScreen_videoPath_scaleMode_(self, screen, videoPath, scaleMode):
        frame = screen.frame()
        style = NSWindowStyleMaskBorderless
        backing = NSBackingStoreBuffered
        defer = False
        self = objc.super(WallpaperWindow, self).initWithContentRect_styleMask_backing_defer_(
            frame, style, backing, defer
        )
        if self is None:
            return None

        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.clearColor())
        self.setHasShadow_(False)

        level = CGWindowLevelForKey(kCGDesktopWindowLevelKey) - 1
        self.setLevel_(level)
        self.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorStationary
        )
        self.setIgnoresMouseEvents_(True)
        # Window is placed on the correct screen by using screen.frame(); no setScreen_ needed
        self._screen = screen
        self._scale_mode = scaleMode or "fill"
        self._video_path = videoPath
        self._player = None
        self._player_layer = None
        self._video_view = None
        self._endObserver = None

        if videoPath:
            self._setupVideo_(videoPath)
        return self

    def _setupVideo_(self, path):
        url = NSURL.fileURLWithPath_(path)
        asset = AVURLAsset.assetWithURL_(url)
        item = AVPlayerItem.playerItemWithAsset_(asset)
        player = AVPlayer.playerWithPlayerItem_(item)
        self._player = player

        # Loop: observe end and seek to start. Block must only touch player if still current.
        nc = NSNotificationCenter.defaultCenter()
        from AVFoundation import AVPlayerItemDidPlayToEndTimeNotification

        def on_end(_):
            if getattr(self, "_player", None) is player:
                player.seekToTime_(CMTimeMakeWithSeconds(0, 1))
                player.play()

        self._endObserver = nc.addObserverForName_object_queue_usingBlock_(
            AVPlayerItemDidPlayToEndTimeNotification,
            item,
            None,
            on_end,
        )

        layer = AVPlayerLayer.playerLayerWithPlayer_(player)
        gravity = GRAVITY_MAP.get(self._scale_mode, AVLayerVideoGravityResizeAspectFill)
        layer.setVideoGravity_(gravity)
        self._player_layer = layer

        content = self.contentView()
        if content is not None:
            view = NSView.alloc().initWithFrame_(content.bounds())
            view.setWantsLayer_(True)
            view.setLayer_(layer)
            view.setAutoresizingMask_(0x12)  # NSViewWidthSizable | NSViewHeightSizable
            content.addSubview_(view)
            self._video_view = view
            bounds = content.bounds()
            if self._scale_mode == "center":
                _centerLayerFrame(asset, bounds, layer)
            else:
                layer.setFrame_(bounds)
        player.play()

    def setScaleMode_(self, mode):
        self._scale_mode = mode
        if self._player_layer is not None:
            gravity = GRAVITY_MAP.get(mode, AVLayerVideoGravityResizeAspectFill)
            self._player_layer.setVideoGravity_(gravity)
            content = self.contentView()
            if mode == "center" and content is not None and self._player is not None:
                item = self._player.currentItem()
                if item is not None:
                    _centerLayerFrame(item.asset(), content.bounds(), self._player_layer)
                else:
                    self._player_layer.setFrame_(content.bounds())
            elif content is not None:
                self._player_layer.setFrame_(content.bounds())

    def setVideoPath_(self, path):
        if path == self._video_path:
            return
        # Tear down old video: pause, clear item (stops notifications), remove observer, then view
        old_player = self._player
        if old_player is not None:
            old_player.pause()
            try:
                old_player.replaceCurrentItemWithPlayerItem_(None)
            except Exception:
                pass
        if self._endObserver is not None:
            NSNotificationCenter.defaultCenter().removeObserver_(self._endObserver)
            self._endObserver = None
        content = self.contentView()
        if self._video_view is not None:
            self._video_view.removeFromSuperview()
            self._video_view = None
        self._player = None
        self._player_layer = None
        self._video_path = path
        if path:
            self._setupVideo_(path)

    def pause(self):
        if self._player is not None:
            self._player.pause()

    def play(self):
        if self._player is not None:
            self._player.play()

    def updateFrame(self):
        """Call when screen frame changes."""
        self.setFrame_display_(self._screen.frame(), True)
        if self._player_layer is not None and self.contentView() is not None:
            content = self.contentView()
            bounds = content.bounds()
            if self._scale_mode == "center" and self._player is not None:
                item = self._player.currentItem()
                if item is not None:
                    _centerLayerFrame(item.asset(), bounds, self._player_layer)
                    return
            self._player_layer.setFrame_(bounds)

    def is_visible(self) -> bool:
        """True if window is not fully occluded (for energy efficiency)."""
        try:
            state = self.occlusionState()
            return (state & 2) != 0  # NSWindowOcclusionStateVisible
        except Exception:
            return True
