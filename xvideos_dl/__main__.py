# type: ignore[attr-defined]
from typing import List

import sys

import typer
from cursor import HiddenCursor
from rich.console import Console
from xvideos_dl import __version__
from xvideos_dl.xvideos_dl import download, get_videos_by_playlist_id, get_videos_from_play_page, parse_playlist_id

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


@app.command(name="")
def main(
    url: List[str] = typer.Argument(..., help="URL of the video web page."),
    playlist: bool = typer.Option(False, "-p", "--playlist", help="Download videos from playlist web page."),
    dest: str = typer.Option(
        "./xvideos",
        "-d",
        "--destination",
        help="Destination to save the downloaded videos.",
    ),
    low: bool = typer.Option(False, "-l", "--low-definition", help="Download low definition videos."),
    overwrite: bool = typer.Option(False, "-O", "--overwrite", help="Overwrite the exist video files."),
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
    videos = []
    if playlist:
        pids = [parse_playlist_id(u) for u in url]
        for pid in pids:
            vs = get_videos_by_playlist_id(pid)
            videos.extend(vs)
    else:
        for page_url in url:
            videos.append(get_videos_from_play_page(page_url))

    for video in videos:
        try:
            with HiddenCursor():
                download(video, dest, low, overwrite)
        except Exception as e:
            console.print(f"[red]{e}[/]")
            sys.exit(1)
