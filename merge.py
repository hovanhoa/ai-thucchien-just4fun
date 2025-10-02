#!/usr/bin/env python3
import argparse
import os
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime


SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
    ".ts",
    ".mts",
    ".m2ts",
    ".3gp",
}


def is_video_file(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    _, ext = os.path.splitext(path)
    return ext.lower() in SUPPORTED_EXTENSIONS


def natural_sort_key(s: str):
    # Basic natural sort: splits digits and non-digits to sort 1,2,10 correctly
    import re

    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


def which(cmd: str) -> str:
    from shutil import which as _which

    return _which(cmd)


def build_filelist_file(file_paths: list[str], directory: str) -> str:
    # Create a temporary file list compatible with ffmpeg concat demuxer
    tmp = tempfile.NamedTemporaryFile("w", delete=False, dir=directory, suffix="_ffconcat.txt")
    try:
        for p in file_paths:
            abs_path = os.path.abspath(p)
            # Use single quotes and escape existing single quotes by replacing ' with '\''
            escaped = abs_path.replace("'", "'\\''")
            tmp.write(f"file '{escaped}'\n")
        return tmp.name
    finally:
        tmp.close()


def run_ffmpeg_concat(list_file: str, output: str) -> tuple[bool, str]:
    # First try stream copy (fast, requires same codec/params)
    cmd_copy = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file,
        "-c",
        "copy",
        output,
    ]
    result = subprocess.run(cmd_copy, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(output) and os.path.getsize(output) > 0:
        return True, "Merged with stream copy."

    # Fallback: re-encode to a common format
    cmd_reencode = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        list_file,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        output,
    ]
    result2 = subprocess.run(cmd_reencode, capture_output=True, text=True)
    if result2.returncode == 0 and os.path.exists(output) and os.path.getsize(output) > 0:
        return True, "Merged with re-encode."

    return False, (result.stderr or result2.stderr or "Unknown error from ffmpeg")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge all video files in the current folder.")
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file name (e.g., merged.mp4). Defaults to merged_<timestamp>.mp4",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files (starting with a dot).",
    )
    return parser.parse_args()


def main() -> int:
    if which("ffmpeg") is None:
        print("Error: ffmpeg is not installed or not in PATH.", file=sys.stderr)
        print("Install via Homebrew: brew install ffmpeg", file=sys.stderr)
        return 1

    args = parse_args()
    cwd = os.getcwd()

    candidates = [f for f in os.listdir(cwd) if args.include_hidden or not f.startswith(".")]
    video_files = [f for f in candidates if is_video_file(os.path.join(cwd, f))]

    # Sort naturally by filename
    video_files.sort(key=natural_sort_key)

    if not video_files or len(video_files) < 2:
        print("Found fewer than 2 video files to merge. Nothing to do.")
        return 0

    # Determine output file
    if args.output:
        output_name = args.output
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_name = f"merged_{ts}.mp4"

    output_path = os.path.abspath(os.path.join(cwd, output_name))

    # Exclude output if it matches a candidate
    video_files = [f for f in video_files if os.path.abspath(os.path.join(cwd, f)) != output_path]

    if len(video_files) < 2:
        print("After filtering, fewer than 2 inputs remain. Nothing to do.")
        return 0

    print("Merging the following files in order:")
    for f in video_files:
        print(f" - {f}")

    list_file = build_filelist_file([os.path.join(cwd, f) for f in video_files], cwd)

    try:
        ok, msg = run_ffmpeg_concat(list_file, output_path)
        if ok:
            print(msg)
            print(f"Done: {output_path}")
            return 0
        else:
            print("Failed to merge videos.", file=sys.stderr)
            if msg:
                print(msg, file=sys.stderr)
            return 2
    finally:
        try:
            if os.path.exists(list_file):
                os.remove(list_file)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())


