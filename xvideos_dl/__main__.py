# type: ignore[attr-defined]
from typing import List

import sys

import typer
from rich.console import Console
from xvideos_dl import __version__
from xvideos_dl.xvideos_dl import download

app = typer.Typer(
    name="xvideos-dl",
    help="CLI to download videos from https://xvideos.com",
    add_completion=False,
)
console = Console()


def version_callback(value: bool):
    """Prints the version of the package."""
    if value:
        console.print(
            f"[yellow]xvideos-dl[/] version: [bold blue]{__version__}[/]"
        )
        raise typer.Exit()


@app.command(name="")
def main(
    url: List[str] = typer.Argument(..., help="URL of the video web page."),
    dest: str = typer.Option(
        "./xvideos",
        "-d",
        "--destination",
        help="Destination to save the downloaded videos.",
    ),
    low: bool = typer.Option(
        False, "-l", "--low-definition", help="Download low definition videos."
    ),
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
    for one in url:
        try:
            download(one, dest, low)
        except Exception as e:
            console.print(f"[red]{e}[/]")
            sys.exit(1)
