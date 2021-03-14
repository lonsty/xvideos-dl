from typing import Dict

import html
import re
from pathlib import Path

import requests
from rich.console import Console

from . import constant as c

console = Console()


def parse_cookies(cookie: str) -> Dict[str, str]:
    try:
        key_values = cookie.split("; ")
        return {kv.split("=")[0]: kv.split("=")[1] for kv in key_values}
    except IndexError:
        return {}


def save_cookie(cookie: str) -> None:
    cache_dir = Path.home() / f".{c.APP_NAME}"
    cache_dir.mkdir(exist_ok=True)
    with open(cache_dir / "cookie", "w") as f:
        f.write(cookie)


def read_cookie() -> str:
    cookie = "foo=bar"
    cache_file = Path.home() / f".{c.APP_NAME}/cookie"
    if cache_file.is_file():
        with open(cache_file) as f:
            cookie = f.read()
    return cookie


def parse_video_id(index: str) -> str:
    find = re.search(r"(?<=video)\d+(?=/)", index)
    if find:
        return find.group()
    return ""


def parse_video_name(index: str) -> str:
    find = re.search(r"(?<=\d/).+(?=[/])*", index)
    if find:
        return find.group()
    return ""


def safe_filename(filename: str) -> str:
    return "".join([char for char in filename if char not in r'\/:*?"<>|']).strip()


def get_video_full_name(index: str) -> str:
    resp = requests.get(index, timeout=c.TIMEOUT)
    resp.raise_for_status()
    title_tab = re.search(r'(?<=<meta property="og:title" content=").*?(?="\s*/>)', resp.text)
    if title_tab:
        return safe_filename(html.unescape(title_tab.group()))
    return ""


def get_video_url(vid: str, low: bool = False) -> str:
    video_api = c.VIDEO_API.format(vid=vid)
    cookie_raw = read_cookie()
    cookies = parse_cookies(cookie_raw)
    url = ""

    while 1:
        resp = requests.get(video_api, cookies=cookies, timeout=c.TIMEOUT)
        resp.raise_for_status()
        url_field = "URL"
        if low:
            url_field = "URL_LOW"
        url = resp.json().get(url_field)
        if url:
            save_cookie(cookie_raw)
            break
        cookie_raw = input("The cookie has expired, please enter a new one:\n").strip()
        cookies = parse_cookies(cookie_raw)

    return url


def download(page_url: str, dest: str, low: bool) -> None:
    vid = parse_video_id(page_url)
    name = get_video_full_name(page_url) or parse_video_name(page_url)
    if not any([vid, name]):
        raise ValueError(f"can't download video from URL: {page_url}")
    url = get_video_url(vid, low)

    save_dir = Path(dest)
    save_dir.mkdir(exist_ok=True)
    save_name = save_dir / f"{name}.mp4"

    head = requests.head(url, stream=True)
    size = int(head.headers["Content-Length"].strip())
    console.print(f"Video ID   : [cyan]{vid}[/]")
    console.print(f"Video Name : [yellow]{name}[/]")
    console.print(f"Video Link : [underline]{url}[/]")
    console.print(f"Video Size : [white]{size / 1024 ** 2:.2f}[/] MB")
    console.print(f"Destination: [white]{save_name.absolute()}[/]")

    done = 0
    if save_name.is_file():
        done = save_name.stat().st_size

    show_process_bar = False
    if done < size:
        show_process_bar = True
        print()

    while done < size:
        start = done
        done += c.FRAGMENT_SIZE
        if done > size:
            done = size
        end = done

        headers = {"Range": f"bytes={start}-{end - 1}"}
        resp = requests.get(url, stream=True, headers=headers, timeout=c.TIMEOUT)
        with open(save_name, "ab") as f:
            write = start
            for chunk in resp.iter_content(c.CHUNK_SIZE):
                f.write(chunk)
                write += c.CHUNK_SIZE
                percent_done = int(min(write, size) / size * 1000) / 10
                bar_done = int(percent_done * 0.7)
                console.print(f"|{'█' * bar_done}{' ' * (70 - bar_done)}| [green]{percent_done:5.1f}%[/]", end="\r")

    if show_process_bar:
        print(end="\n\n")
