from typing import Any, Dict, List, Optional

import html
import random
import re
import time
from collections import namedtuple
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

from bs4 import BeautifulSoup
from integv import FileIntegrityVerifier
from requests import Response, Session
from requests.cookies import cookiejar_from_dict
from rich.console import Console

from . import constant as c

console = Console()
session = Session()
verifier = FileIntegrityVerifier()
Video = namedtuple("Video", "vid vname pname uname")


@dataclass
class Process:
    now: int = 1
    total: int = 1

    def status(self):
        if self.total > 1:
            return f"{self.now}/{self.total} ({self.now / self.total * 100:.0f}%)"
        return "⚓"


def retry(exceptions=Exception, tries=3, delay=1, backoff=2):
    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    console.print(f"[red]{e}, Retrying in {mdelay} seconds...[/]")
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry

    return deco_retry


@retry()
def session_request(method: str, url: str, **kwargs) -> Optional[Response]:
    resp = session.request(method, url, **kwargs)
    if resp.status_code == 404:
        console.print(f"[red]404 Client Error: Not Found for url: {url}[/]\n")
        return None
    resp.raise_for_status()
    return resp


def parse_cookies(cookie: str) -> Dict[str, str]:
    try:
        key_values = cookie.split("; ")
        return {kv.split("=")[0]: kv.split("=")[1] for kv in key_values}
    except IndexError:
        return {}


def save_cookie(cookie: str) -> None:
    cache_dir = Path.home() / f".{c.APP_NAME}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_dir / "cookie", "w") as f:
        f.write(cookie)


def read_cookie() -> str:
    cookie = "foo=bar"
    cache_file = Path.home() / f".{c.APP_NAME}/cookie"
    if cache_file.is_file():
        with open(cache_file) as f:
            cookie = f.read()
    return cookie


def find_from_string(pattern: str, string: str) -> str:
    find = re.search(pattern, string)
    if not find:
        raise ValueError(f"can't download video from URL: {string}")
    return find.group()


def parse_video_id(index: str) -> str:
    return find_from_string(r"(?<=video)\d+(?=/)", index.strip())


def parse_video_name(index: str) -> str:
    return find_from_string(r"(?<=\d/).+(?=[/])*", index.strip())


def parse_username(index: str) -> str:
    return find_from_string(r"(?<=profiles/|channels/)\w*(?=/*)", index.strip())


def parse_playlist_id(index: str) -> str:
    return find_from_string(r"(?<=/favorite/)\d+(?=/)", index.strip())


def safe_filename(filename: str) -> str:
    return "".join([char for char in filename if char not in r'\/:*?"<>|']).strip()


def get_video_full_name(index: str) -> str:
    resp = session_request("GET", index, timeout=c.TIMEOUT)
    title_tab = re.search(r'(?<=<meta property="og:title" content=").*?(?="\s*/>)', resp.text)
    if title_tab:
        return safe_filename(html.unescape(title_tab.group()))
    return ""


def request_with_cookie(method: str, url: str, return_when: str, reset_cookie: bool) -> Dict[str, Any]:
    cookie_raw = "k=v" if reset_cookie else read_cookie()
    cookies = parse_cookies(cookie_raw)

    while 1:
        session.cookies = cookiejar_from_dict(cookies)
        resp = session_request(method, url, timeout=c.TIMEOUT)
        data = resp.json()
        keys = return_when.split(".")
        value = data
        for key in keys:
            value = value.get(key, {})
        if value:
            save_cookie(cookie_raw)
            break
        error = data.get("ERROR")
        if error:
            raise ValueError(f"{error} {url}")
        cookie_raw = input(
            "The cookie has expired, please enter a new one:\n"
            "(Log in https://xvideos.com with your account via a browser, "
            "then open the developer mode, copy and paste the cookie here)\n"
        ).strip()
        cookies = parse_cookies(cookie_raw)

    return data


def get_video_url(vid: str, low: bool, reset_cookie: bool) -> str:
    video_api = c.VIDEO_API.format(vid=vid)
    data = request_with_cookie("GET", video_api, return_when="URL", reset_cookie=reset_cookie)

    url_field = "URL"
    if low:
        url_field = "URL_LOW"

    return data.get(url_field)


def get_videos_from_play_page(page_url: str) -> Video:
    vid = parse_video_id(page_url)
    vname = get_video_full_name(page_url) or parse_video_name(page_url)
    return Video(vid=vid, vname=vname, pname="", uname="")


def get_videos_from_user_page(page_url: str, aid: str, base_api: str, videos: List[Video]) -> List[Video]:
    username = parse_username(page_url)
    start_page = base_api.format(u=username, aid=aid)
    resp = session_request("POST", start_page, timeout=c.TIMEOUT)
    next_aid = find_from_string(r"\d+", resp.text.splitlines()[0])

    bs = BeautifulSoup(resp.text, "html.parser")
    blocks = bs.find_all("div", class_="thumb-block")
    for block in blocks:
        vid = block.attrs.get("data-id")
        vname = block.find("p", class_="title").find("a").attrs.get("title")
        videos.append(Video(vid=vid, vname=vname, pname="", uname=username))
    if int(next_aid) > 0:
        return get_videos_from_user_page(page_url, next_aid, base_api, videos)
    return videos


def get_videos_by_playlist_id(pid: str, reset_cookie: bool) -> List[Video]:
    playlist_api = c.PLAYLIST_API.format(pid=pid)
    data = request_with_cookie("POST", playlist_api, return_when="logged", reset_cookie=reset_cookie)
    playlist_name = data.get("list", {}).get("name")
    videos_info = data.get("list", {}).get("videos")
    if not any([playlist_name, videos_info]):
        raise Exception(f"No permission to access this playlist, {playlist_api}")

    videos = []
    for v in videos_info:
        videos.append(Video(vid=v.get("id"), vname=v.get("tf"), pname=playlist_name, uname=""))

    return videos


def remove_illegal_chars(string: str) -> str:
    illegal_chars: str = "\\/:*\"<>|;?!%^"

    ret_str = str(string)
    for ch in illegal_chars:
        ret_str = ret_str.replace(ch, '_')

    # remove non unicode characters
    ret_str = bytes(ret_str, 'utf-8').decode('utf-8', 'ignore')

    return ret_str


def download(video: Video, dest: str, low: bool, overwrite: bool, reset_cookie: bool) -> None:
    save_dir = Path(dest) / (video.pname or video.uname)
    save_dir.mkdir(parents=True, exist_ok=True)
    video_name = remove_illegal_chars(video.vname)
    save_name = save_dir / f"{video_name}(#{video.vid}).mp4"
    console.print(f"Video ID   : [white]{video.vid}[/]")
    console.print(f"Video Name : [yellow]{video_name}[/]")
    console.print(f"Destination: [white]{save_name.absolute()}[/]")

    done = 0
    if save_name.is_file():
        if overwrite:
            save_name.unlink()
        else:
            done = save_name.stat().st_size
            if verifier.verify(str(save_name)):
                console.print(f"Video Size : [white]{done / 1024 ** 2:.2f}[/] MB [green](skip downloaded)[/]\n")
                return None

    url = get_video_url(video.vid, low, reset_cookie)
    head = session_request("HEAD", url, stream=True)
    if not head:
        return None
    size = int(head.headers["Content-Length"].strip())
    console.print(f"Video Size : [white]{size / 1024 ** 2:.2f}[/] MB")
    console.print(f"Video Link : [underline]{url}[/]")

    show_process_bar = False
    if done < size:
        show_process_bar = True
        print()

    emoji = random.choice(c.SMILE_EMOJIS)
    while done < size:
        time_start = time.time()
        start = done
        done += c.FRAGMENT_SIZE
        if done > size:
            done = size
        end = done
        headers = {"Range": f"bytes={start}-{end - 1}"}
        resp = session_request("GET", url, stream=True, headers=headers, timeout=c.TIMEOUT)

        with open(save_name, "ab") as f:
            write = start
            for chunk in resp.iter_content(c.CHUNK_SIZE):
                f.write(chunk)

                write += c.CHUNK_SIZE
                percent_done = int(min(write, size) / size * 1000) / 10
                bar_done = int(percent_done * 0.6)
                console.print(
                    f"{emoji} |{'█' * bar_done}{' ' * (60 - bar_done)}| [green]{percent_done:5.1f}%[/]", end="\r"
                )
        # Download speed
        speed = (end - start) / (time.time() - time_start)
        if speed < 1024:  # 1KB
            speed_text = f"{speed:7.2f}B/s"
        elif speed < 1048576:  # 1MB
            speed_text = f"{speed / 1024:7.2f}KB/s"
        else:
            speed_text = f"{speed / 1048576:7.2f}MB/s"
        console.print(
            f"{emoji} |{'█' * bar_done}{' ' * (60 - bar_done)}| [green]{percent_done:5.1f}% {speed_text}[/]", end="\r"
        )

    if show_process_bar:
        print(end="\n\n")
