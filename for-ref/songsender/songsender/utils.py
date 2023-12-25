import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from functools import wraps
from glob import glob
from logging import Logger
from pathlib import Path
from uuid import uuid4

import requests
import youtube_dl
from bs4 import BeautifulSoup
from redis import Redis

from .logger import logger


def get_uid(n=5):
    return uuid4().hex[:n]


def retry_with_exception(exception=Exception, retry_cnt: int = 1):
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            for i in range(retry_cnt):
                try:
                    rv = fn(*args, **kwargs)
                    return rv
                except exception:
                    pass
                except BaseException as e:
                    logger.exception(f"Retry failed with {e=}")
                    raise

        return inner

    return wrapper


def submit_helper(fn, *, uid: str, store: Redis, logger: Logger, **kwargs):
    logger.info(f"[submit_helper] {fn=}, {uid=}, {store=}, {kwargs=}")
    store.set(uid, fn(**kwargs))


def ytdl_hook(d):
    if d["status"] == "finished":
        logger.info(f"Done downloading, now converting {d=}...")


@contextmanager
def prepare_temp_dir():
    prev_path = Path()
    with tempfile.TemporaryDirectory() as f:
        download_dir = f

    path = Path(download_dir)
    path.mkdir(parents=True, exist_ok=True)
    logger.info(f"[prepare_temp_dir] Created {download_dir=}")
    os.chdir(path)
    logger.info(
        f"[prepare_temp_dir] Switching to {download_dir=} from {prev_path=} ..."
    )
    try:
        yield download_dir
    finally:
        # need to consider to keep the files around in case same files are called repeatedly
        logger.info(f"[prepare_temp_dir] Switching back to {prev_path=}...")
        os.chdir(prev_path)
        shutil.rmtree(download_dir)


def mp3_files(path: str):
    files = glob(f"{path}/*.mp3")
    return files


@retry_with_exception(Exception, retry_cnt=3)
@contextmanager
def download_from_urls(urls: list):
    ydl_opts = {
        "format": "bestaudio/best",
        "ignoreerrors": True,
        "verbose": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        # 'logger': MyLogger(),
        "progress_hooks": [ytdl_hook],
    }

    path: str
    print("URLS DOWNLOADING: ", urls)
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        with prepare_temp_dir() as path:
            ydl.download(urls)
            yield mp3_files(path)


def get_urls_from_path(path: str):
    url = ""
    if "youtube" in path:
        _, url = path.split("v=")
    elif "youtu.be" in path:
        url = path.split("/")[-1]

    if not url:
        return None

    return f"https://youtube.com/watch?v={url}"


def convert(src="videos", dst="audios"):
    logger.info("\n\nConverting...")
    logger.info(f"{src} -> {dst}")
    for index, f in enumerate(os.listdir(src)):
        src_path = os.path.join(src, f)
        # aud_name = Path(src_path).name.split('.')[0] + '.mp3'
        aud_name = Path(src_path).name[:-4] + ".mp3"
        dst_path = os.path.join(dst, aud_name)
        logger.info(f"{index+1}. {aud_name}:")
        subprocess.run(
            f'ffmpeg -n -v quiet -stats -i "{src_path}" -ab 128k "{dst_path}"',
            shell=True,
            check=True,
        )


@retry_with_exception(Exception, retry_cnt=1)
def fetch_url_from_name(name):
    query = "+".join(name.split(" "))
    base_url = f"https://www.youtube.com/results?search_query={query}"
    html = requests.get(base_url).text
    got_idx = html.index("/watch?v=")
    got = html[got_idx : got_idx + 20].split("=")[1]
    need = "https://youtu.be/" + got
    return need


def read_song_names():
    path = "songs"
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        path = input("Enter path: ")
    if not os.path.exists(path):
        return
    with open(path, "r") as song_file:
        urls = list(map(get_urls_from_path, song_file))
        download_from_urls(urls)


def retry():
    if not Path("log.txt").exists():
        return

    logger.info("Retrying...")
    test_path = "retry"
    if Path(test_path).exists():
        shutil.rmtree(test_path)

    Path(test_path).mkdir(parents=True, exist_ok=True)
    log = open("log.txt", "r").read().split("\n")
    logger.info(log)
    for index, line in enumerate(log):
        line = line.split(":")
        if len(line) == 2:
            if "title" in log[index + 1]:
                continue
            url = line[1]

    convert(src=test_path, dst="audios")
