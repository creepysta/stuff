import json
import re
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from uuid import uuid4

from litehttp import (
    HTTP_200,
    HTTP_204,
    HTTP_400,
    HTTP_404,
    Loop,
    Request,
    Server,
    file_response,
    json_response,
    text_response,
)
from redis import Redis

from .logger import logger
from .utils import download_from_urls, fetch_url_from_name, get_uid, submit_helper


def handle_root(_: Request):
    return text_response(text="Howdy!")


def search_get(req: Request, store: Redis):
    logger.debug(f"Processing get {req=} ...")
    try:
        name = req.query["name"]
    except Exception as e:
        logger.exception(f"Invalid query parameters in {req=}. Failed with error: {e}")
        return text_response(status=HTTP_400)

    logger.debug(f"Got query {name=} ...")
    url = fetch_url_from_name(name)
    # uid = get_uid()
    # with ProcessPoolExecutor(max_workers=1) as pool:
    #     future = pool.submit(fetch_url_from_name, name=name)
    #     future.add_done_callback(lambda x: store.set(uid, x.result()))

    payload = {"url": url}
    return json_response(payload, status=HTTP_200)


def search_post(req: Request, store: Redis):
    logger.debug(f"Processing post {req=} ...")
    names: list
    try:
        names = req.json()["names"]
        assert isinstance(names, list)
    except Exception as e:
        logger.exception(f"invalid request body: {req.body}. Failed with error: {e}")
        return text_response(status=HTTP_400)

    urls = list(map(fetch_url_from_name, names))
    payload = {"urls": urls}
    resp = json.dumps(payload)
    return text_response(text=resp, status=HTTP_200)


def handle_search(req: Request, store: Redis):
    match req.method:
        case "GET":
            return search_get(req, store)
        case "POST":
            return search_post(req, store)
        case _:
            return text_response(
                "GET, POST are the only methods defined", status=HTTP_404
            )


def search_path_match(path: str) -> bool:
    return re.search(r"/search$", path) is not None


def download_post(req: Request, store: Redis):
    url: str
    try:
        url = req.json()["url"]
    except Exception as e:
        logger.exception(f"Failed to parse request body {req=}, with error: {e}")
        return text_response(status=HTTP_400)

    # TODO:
    # 1) return the path for a tempdir and trigger a separate job to download the file
    # 2) make an endpoint where a client can poll if the job is finished
    # 3) use redis? check path once the client accesses it, remove dir
    # uid = get_uid()
    with download_from_urls([url]) as files:
        logger.debug(f"{files=}")
        if files:
            return file_response(file_path=files[0], f_type="binary")

    return text_response(status=HTTP_204)

    # store.set(uid, path)
    # with ProcessPoolExecutor(max_workers=1) as pool:
    #     future = pool.submit(download_from_urls, urls=[url])
    #     future.add_done_callback(lambda x: store.set(uid, x.result()))


def handle_download(req: Request, store: Redis):
    match req.method:
        case "POST":
            return download_post(req, store)
        case _:
            return text_response("POST is the only method defined", status=HTTP_404)


def download_path_match(path: str) -> bool:
    return re.search(r"/download$", path) is not None


def handle_result(req: Request, store: Redis):
    def get():
        logger.debug(f"Processing result get {req=} ...")
        try:
            uid = req.query["uid"]
        except Exception as e:
            logger.exception(
                f"Invalid query parameters in {req=}. Failed with error: {e}"
            )
            return text_response(status=HTTP_400)

        logger.debug(f"Got query {uid=} ...")
        res = store.get(uid)
        if not res:
            return text_response(
                "The result is either not yet available or has already been consumed",
                status=HTTP_404,
            )

        store.set(uid, "")
        return text_response(text=str(res), status=HTTP_200)

    match req.method:
        case "GET":
            return get()
        case _:
            return text_response("POST is the only method defined", status=HTTP_404)


def result_path_match(path: str) -> bool:
    return re.search(r"/result$", path) is not None


def run(args):
    host, port = args.host, args.port
    store = Redis(host=args.redis_host, port=6379)
    handlers = [
        (lambda x: x == "/", handle_root),
        (search_path_match, partial(handle_search, store=store)),
        (download_path_match, partial(handle_download, store=store)),
        (result_path_match, partial(handle_result, store=store)),
    ]

    logger.info(f"Trying to start server with {host}:{port}...")
    server = Server(loop=Loop(), handlers=handlers)
    server.run(host=host, port=port)
    return 0
