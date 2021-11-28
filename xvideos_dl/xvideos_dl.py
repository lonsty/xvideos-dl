from typing import Any, Dict, List, Optional

import html
import random
import re
import time
from collections import namedtuple
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

import ffmpeg
from bs4 import BeautifulSoup
from integv import FileIntegrityVerifier
from requests import Response, Session
from requests.cookies import cookiejar_from_dict
from rich.console import Console

from . import constant as c

console = Console()
session = Session()
verifier = FileIntegrityVerifier()
Video = namedtuple("Video", "vid vname pname uname vpage")
HLS = namedtuple("HLS", "name bandwidth resolution url")


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
    resp = session.request(method, url, timeout=c.TIMEOUT, **kwargs)
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
    return find_from_string(r"(?<=profiles/|channels/).+(?=/*)", index.strip())


def parse_playlist_id(index: str) -> str:
    return find_from_string(r"(?<=/favorite/)\d+(?=/)", index.strip())


def parse_video_hls(index: str) -> str:
    return find_from_string(r"(?<=setVideoHLS\(['\"]).+(?=['\"]\))", index.strip())


def parse_hls(index: str) -> List[HLS]:
    """
    #EXTM3U
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=423936,RESOLUTION=360x640,NAME="360p"
    hls-360p-045d9.m3u8
    #EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=155648,RESOLUTION=250x444,NAME="250p"
    hls-250p-639f7.m3u8
    """
    hls_list = []
    lines = index.strip().split("\n")
    for idx, line in enumerate(lines):
        if idx % 2 == 1:
            args_str = line.split(":")[-1]
            kwargs = {kv.split("=")[0]: kv.split("=")[1] for kv in args_str.split(",")}
            hls_list.append(
                HLS(
                    name=kwargs["NAME"].replace('"', ""),
                    bandwidth=kwargs["BANDWIDTH"],
                    resolution=kwargs["RESOLUTION"],
                    url=lines[idx + 1],
                )
            )

    # sort by bandwidth
    hls_list = sorted(hls_list, key=lambda x: int(x.bandwidth))

    return hls_list


def get_video_full_name(index: str) -> str:
    resp = session_request("GET", index)
    title_tab = re.search(r'(?<=<meta property="og:title" content=").*?(?="\s*/>)', resp.text)
    if title_tab:
        return str(html.unescape(title_tab.group()))
    return ""


def request_with_cookie(method: str, url: str, return_when: str, reset_cookie: bool) -> Dict[str, Any]:
    cookie_raw = "k=v" if reset_cookie else read_cookie()
    cookies = parse_cookies(cookie_raw)

    while 1:
        session.cookies = cookiejar_from_dict(cookies)
        resp = session_request(method, url)
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
    vpage = c.VIDEO_PAGE.format(vid=vid)
    return Video(vid=vid, vname=vname, pname="", uname="", vpage=vpage)


def get_videos_from_user_page(page_url: str, aid: str, base_api: str, videos: List[Video]) -> List[Video]:
    username = parse_username(page_url)
    start_page = base_api.format(u=username, aid=aid)
    resp = session_request("POST", start_page)
    next_aid = find_from_string(r"\d+", resp.text.splitlines()[0])

    bs = BeautifulSoup(resp.text, "html.parser")
    blocks = bs.find_all("div", class_="thumb-block")
    for block in blocks:
        vid = block.attrs.get("data-id")
        vname = block.find("p", class_="title").find("a").attrs.get("title")
        vpage = c.VIDEO_PAGE.format(vid=vid)
        videos.append(Video(vid=vid, vname=vname, pname="", uname=username, vpage=vpage))
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
        vid = v.get("id")
        vname = v.get("tf")
        vpage = c.VIDEO_PAGE.format(vid=vid)
        videos.append(Video(vid=vid, vname=vname, pname=playlist_name, uname="", vpage=vpage))

    return videos


def remove_illegal_chars(string: str) -> str:
    illegal_chars: str = r'\/:*?"<>|'

    ret_str = str(string)
    for ch in illegal_chars:
        ret_str = ret_str.replace(ch, "_")

    # remove non unicode characters
    ret_str = bytes(ret_str, "utf-8").decode("utf-8", "ignore")

    return ret_str


def get_hls_list(video: Video) -> List[HLS]:
    page_resp = session_request("GET", video.vpage)
    hls_url = parse_video_hls(page_resp.text)
    prefix = "/".join(hls_url.split("/")[:-1])

    hls_resp = session_request("GET", hls_url)
    hls_list = parse_hls(hls_resp.text)
    return [hls._replace(url=f"{prefix}/{hls.url}") for hls in hls_list]


def download_mp4_resource(video: Video, save_name: Path, overwrite: bool, low: bool, reset_cookie: bool) -> None:
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
        resp = session_request("GET", url, stream=True, headers=headers)

        with open(save_name, "ab") as f:
            write = start
            for chunk in resp.iter_content(c.CHUNK_SIZE):
                f.write(chunk)

                write += c.CHUNK_SIZE
                percent_done = int(min(write, size) / size * 1000) / 10
                bar_done = int(percent_done * 0.6)
                console.print(
                    f"{emoji} ╞{'█' * bar_done}{' ' * (60 - bar_done)} [green]{percent_done:5.1f}%[/]", end="\r"
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
            f"{emoji} ╞{'█' * bar_done}{' ' * (60 - bar_done)}╡ [green]{percent_done:5.1f}% {speed_text}[/]", end="\r"
        )

    if show_process_bar:
        print(end="\n\n")


def download_hls_stream(playlist: str, save_name: Path, overwrite: bool) -> None:
    console.print("⏳ Wait a mininute...", end="\r")
    ffnpeg_cmd = ffmpeg.input(playlist).output(str(save_name), codec="copy", loglevel="quiet")

    if save_name.is_file():
        if overwrite:
            # Cause got playlist.m3u8, we can download video by ffmpeg
            ffnpeg_cmd.run(overwrite_output=overwrite)
    else:
        ffnpeg_cmd.run()
    console.print(f"Video Size : [white]{save_name.stat().st_size / 1024 ** 2:.2f}[/] MB\n")


def download(video: Video, dest: str, quality: str, overwrite: bool, reset_cookie: bool) -> None:
    save_dir = Path(dest) / (video.pname or video.uname)
    save_dir.mkdir(parents=True, exist_ok=True)
    video_name = remove_illegal_chars(video.vname)
    save_name = save_dir / f"{video_name}(#{video.vid}).mp4"

    console.print(f"Video ID   : [white]{video.vid}[/]")
    console.print(f"Video Name : [yellow]{video_name}[/]")
    console.print(f"Video Page : [underline]{video.vpage}[/]")

    # Get all hls playlists
    hls_list = get_hls_list(video)

    # Choose video resolution
    if quality == "high":
        index = -1
    elif quality == "middle":
        index = int(len(hls_list) / 2)
    else:
        index = 0

    hls = hls_list[index]
    console.print(f"Quality    : [white]{hls.name}[/]")
    console.print(f"Destination: [white]{save_name.absolute()}[/]")

    if hls.name in c.HAS_MP4_RESOUCE:
        low = True if quality == "low" else False
        download_mp4_resource(video, save_name, overwrite, low, reset_cookie)
    else:
        download_hls_stream(hls.url, save_name, overwrite)
