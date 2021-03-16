# type: ignore[attr-defined]
from typing import List

import sys

import typer
from cursor import HiddenCursor
from rich.console import Console
from xvideos_dl import __version__
from xvideos_dl.xvideos_dl import (
    Process,
    download,
    get_videos_by_playlist_id,
    get_videos_from_play_page,
    get_videos_from_user_page,
    parse_playlist_id,
)

from . import constant as c

app = typer.Typer(
    name="xvideos-dl",
    help="CLI to download videos from https://xvideos.com",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    """Prints the version of the package."""
    if value:
        console.print(f"[yellow]xvideos-dl[/] version: [bold blue]{__version__}[/]")
        raise typer.Exit()


@app.command(name="CLI to download videos from https://xvideos.com")
def main(
    urls: List[str] = typer.Argument(..., help="URL of the video web page."),
    dest: str = typer.Option(
        "./xvideos",
        "-d",
        "--destination",
        help="Destination to save the downloaded videos.",
    ),
    max: int = typer.Option(None, "-n", "--maximum", help="Maximum videos to download."),
    reversed: bool = typer.Option(False, "-r", "--reversed", help="Download videos in reverse order."),
    low: bool = typer.Option(False, "-l", "--low-definition", help="Download low definition videos."),
    overwrite: bool = typer.Option(False, "-o", "--overwrite", help="Overwrite the exist video files."),
    version: bool = typer.Option(
        None,
        "-v",
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Prints the version of the xvideos-dl package.",
    ),
):
    """CLI to download videos from https://xvideos.com"""
    videos_to_download = []
    for url in urls:
        if "/profiles/" in url:
            videos = []
            videos = get_videos_from_user_page(url, "0", c.USER_UPLOAD_API, videos)
            videos_to_download.extend(videos)
        elif "/channels/" in url:
            videos = []
            videos = get_videos_from_user_page(url, "0", c.CHANNEL_API, videos)
            videos_to_download.extend(videos)
        elif "/favorite/" in url:
            pid = parse_playlist_id(url)
            videos = get_videos_by_playlist_id(pid)
            videos_to_download.extend(videos)
        else:
            video = get_videos_from_play_page(url)
            videos_to_download.append(video)

    if reversed:
        videos_to_download = videos_to_download[::-1]
    if max:
        videos_to_download = videos_to_download[:max]

    total = len(videos_to_download)
    for idx, video in enumerate(videos_to_download):
        try:
            with HiddenCursor():
                process = Process(idx + 1, total)
                console.print(f"Downloading: [cyan]{process.status()}[/]")
                download(video, dest, low, overwrite)
        except Exception as e:
            console.print(f"[red]{e}[/]")
            sys.exit(1)
