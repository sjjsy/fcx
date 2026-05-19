"""ffmpeg converters: audio → WAV (16 kHz mono)."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fcx.core import Converter, run

_AUDIO_FORMATS = (
    "mp3", "m4a", "ogg", "flac", "aac", "opus", "wma", "wav",
    "mp4", "mov", "mkv", "webm", "avi", "flv",
)


def _to_wav_16k(srcs: List[Path], dst: Path, params: Optional[str]) -> None:
    """Convert audio/video to 16 kHz mono WAV."""
    run(["ffmpeg", "-y", "-i", str(srcs[0]),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
         str(dst)])


CONVERTERS = [
    Converter(
        name="ffmpeg-16k",
        from_formats=_AUDIO_FORMATS,
        to_format="wav",
        deps=["ffmpeg"],
        params=None,
        fn=_to_wav_16k,
    ),
]
