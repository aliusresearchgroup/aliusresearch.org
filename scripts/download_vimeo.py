#!/usr/bin/env python3
"""Download Vimeo videos into the current user's Videos directory.

Requires yt-dlp:
    python -m pip install -U "yt-dlp[default]"

For best-quality merges, install the ffmpeg binary too:
    https://ffmpeg.org/download.html
"""

from __future__ import annotations

import argparse
import ctypes
import sys
from pathlib import Path
from typing import Iterable


DEFAULT_URLS = ("https://vimeo.com/252874735",)
DEFAULT_FORMAT = "bestvideo+bestaudio/best"


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def get_videos_dir() -> Path:
    """Return the user's Videos folder, using Windows known folders when available."""
    if sys.platform != "win32":
        return Path.home() / "Videos"

    # FOLDERID_Videos: https://learn.microsoft.com/windows/win32/shell/knownfolderid
    folderid_videos = GUID(
        0x18989B1D,
        0x99B5,
        0x455B,
        (ctypes.c_ubyte * 8)(0x84, 0x1C, 0xAB, 0x7C, 0x74, 0xE4, 0xDD, 0xFC),
    )
    path_ptr = ctypes.POINTER(ctypes.c_wchar)()

    try:
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folderid_videos), 0, None, ctypes.byref(path_ptr)
        )
        if result == 0 and path_ptr:
            return Path(ctypes.wstring_at(path_ptr))
    except Exception:
        pass
    finally:
        if path_ptr:
            try:
                ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            except Exception:
                pass

    return Path.home() / "Videos"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Vimeo videos into your Videos folder."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="One or more Vimeo video URLs. If omitted, the built-in default Vimeo URL is used.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=get_videos_dir(),
        help="Destination folder. Defaults to your Videos directory.",
    )
    parser.add_argument(
        "--cookies-from-browser",
        choices=("brave", "chrome", "chromium", "edge", "firefox", "opera", "safari", "vivaldi", "whale"),
        help="Use browser cookies for private videos you are authorized to access.",
    )
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="Allow playlist/channel/showcase downloads. By default only single videos are downloaded.",
    )
    parser.add_argument(
        "--format",
        default=DEFAULT_FORMAT,
        help="yt-dlp format selector. Default: best video plus best audio, falling back to best combined.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing download with the same output filename.",
    )
    return parser.parse_args(list(argv))


def prompt_for_urls() -> list[str]:
    print("Paste a Vimeo URL and press Enter.")
    print("For multiple URLs, separate them with spaces.")
    raw = input("Vimeo URL: ").strip()
    return raw.split()


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    try:
        from yt_dlp import YoutubeDL
    except ImportError:
        print("Missing dependency: yt-dlp", file=sys.stderr)
        print('Install it with: python -m pip install -U "yt-dlp[default]"', file=sys.stderr)
        return 1

    args = parse_args(argv)
    urls = args.urls or list(DEFAULT_URLS)
    if not urls:
        print("No URL provided.", file=sys.stderr)
        return 1

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    options = {
        "format": args.format,
        "merge_output_format": "mp4",
        "outtmpl": str(output_dir / "%(title).200B [%(id)s].%(ext)s"),
        "noplaylist": not args.playlist,
        "restrictfilenames": False,
        "windowsfilenames": True,
        "ignoreerrors": False,
        "overwrites": args.force,
        "continuedl": True,
        "noprogress": True,
    }

    if args.cookies_from_browser:
        options["cookiesfrombrowser"] = (args.cookies_from_browser,)

    print(f"Saving downloads to: {output_dir}")
    with YoutubeDL(options) as ydl:
        ydl.download(urls)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
