#!/usr/bin/env python3
"""Download the PAGASA bulletin archive folder from GitHub.

The script uses only Python's standard library. Existing files are skipped by
 default, so it can be run again to resume an interrupted download.

Examples:
    python download_bulletin_archive.py
    python download_bulletin_archive.py -o bulletin-archive/archive
    python download_bulletin_archive.py --overwrite
"""

import argparse
import json
import sys
import time
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

OWNER = "pagasa-parser"
REPOSITORY = "bulletin-archive"
REF = "master"
ARCHIVE_PREFIX = "archive/"
SEASON_CODES = ("24", "25")
API_URL = (
    f"https://api.github.com/repos/{OWNER}/{REPOSITORY}/git/trees/{REF}"
    "?recursive=1"
)
RAW_URL = f"https://raw.githubusercontent.com/{OWNER}/{REPOSITORY}/{REF}/"
USER_AGENT = "pagasa-bulletin-archive-downloader/1.0"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "Typhoon and Coordinates"


def request_bytes(url, retries=3):
    request = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as error:
            if attempt == retries - 1:
                raise RuntimeError(f"download failed for {url}: {error}") from error
            time.sleep(2 ** attempt)
    raise RuntimeError(f"download failed for {url}")


def archive_files():
    tree = json.loads(request_bytes(API_URL).decode("utf-8"))
    if tree.get("truncated"):
        raise RuntimeError(
            "GitHub returned a truncated file tree; use the repository ZIP "
            "or authenticated GitHub API access instead."
        )

    files = []
    for entry in tree.get("tree", []):
        path = entry.get("path", "")
        relative_path = path.removeprefix(ARCHIVE_PREFIX)
        is_selected_season = relative_path.startswith(
            tuple(f"pagasa-{code}-" for code in SEASON_CODES)
        )
        if (
            entry.get("type") == "blob"
            and path.startswith(ARCHIVE_PREFIX)
            and is_selected_season
        ):
            files.append(path)
    return sorted(files)


def safe_destination(output_dir, repository_path):
    relative = PurePosixPath(repository_path).relative_to(ARCHIVE_PREFIX)
    if not relative.parts or any(part in ("", ".", "..") for part in relative.parts):
        raise RuntimeError(f"unsafe repository path: {repository_path}")
    destination = (output_dir / Path(*relative.parts)).resolve()
    output_root = output_dir.resolve()
    if destination != output_root and output_root not in destination.parents:
        raise RuntimeError(f"unsafe destination path: {repository_path}")
    return destination


def download(output_dir, overwrite=False):
    paths = archive_files()
    if not paths:
        raise RuntimeError("GitHub returned no files under archive/")

    downloaded = 0
    skipped = 0
    for index, repository_path in enumerate(paths, start=1):
        destination = safe_destination(output_dir, repository_path)
        if destination.exists() and not overwrite:
            skipped += 1
            print(f"[{index}/{len(paths)}] Skipped {destination}")
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        print(f"[{index}/{len(paths)}] Downloading {repository_path}")
        data = request_bytes(RAW_URL + quote(repository_path, safe="/"))
        destination.write_bytes(data)
        downloaded += 1
        print(f"[{index}/{len(paths)}] Downloaded {repository_path}")

    print(f"Finished: {downloaded} downloaded, {skipped} skipped, {len(paths)} total")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Local directory corresponding to the GitHub archive/ folder",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Redownload files that already exist",
    )
    args = parser.parse_args()

    try:
        download(args.output, overwrite=args.overwrite)
    except (RuntimeError, OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
