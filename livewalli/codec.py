"""Check if a video file is playable (MPEG-4, HEVC, etc.) via AVFoundation."""
from __future__ import annotations

import os
from typing import Tuple, Optional

from Foundation import NSURL
from AVFoundation import AVURLAsset

# Allowed file extensions (MPEG-4, MOV, HEVC in .mov/.mp4)
ALLOWED_EXTENSIONS = (".mp4", ".mov")


def is_allowed_extension(path: str) -> bool:
    """Return True if path has an allowed video extension."""
    return path and path.lower().endswith(ALLOWED_EXTENSIONS)


def check_playable(path: str) -> Tuple[bool, Optional[str]]:
    """
    Return (True, None) if the file appears playable (exists, right extension).
    Optionally validates via AVFoundation when tracks are already loaded.
    Otherwise (False, error_message). Handles missing files and wrong extension.
    """
    if not path or not path.strip():
        return False, "No file selected."
    if not is_allowed_extension(path):
        return False, f"Unsupported format. Use {', '.join(ALLOWED_EXTENSIONS)} (MPEG-4 or HEVC)."
    try:
        if not os.path.isfile(path):
            return False, "File not found."
        url = NSURL.fileURLWithPath_(path)
        asset = AVURLAsset.assetWithURL_(url)
        # If tracks are already loaded (cached), validate; else accept and let playback reveal errors
        status, error = asset.statusOfValueForKey_error_("tracks", None)
        if status == 1:  # AVKeyValueStatusFailed
            if error is not None and hasattr(error, "localizedDescription"):
                msg = str(error.localizedDescription())
            else:
                msg = "Unsupported codec or corrupt file."
            return False, msg
        if status == 2:  # AVKeyValueStatusLoaded
            tracks = asset.tracksWithMediaType_("vide")
            if tracks is None or len(tracks) == 0:
                return False, "No video track (audio-only or unsupported)."
        return True, None
    except Exception as e:
        return False, f"Cannot open file: {e}"
