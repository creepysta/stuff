import json
import re

from litehttp import (
    HTTP_200,
    HTTP_400,
    HTTP_404,
    Loop,
    Request,
    Server,
    file_response,
    text_response,
)

from .logger import logger
from .utils import download_from_urls, fetch_url_from_name


def handle_root(_: Request):
    return text_response(text="Howdy!")


def search_get(req: Request):
    logger.debug(f"Processing get {req=} ...")
    try:
        name = req.query["name"]
    except Exception as e:
        logger.exception(f"Invalid query parameters in {req=}. Failed with error: {e}")
        return text_response(status=HTTP_400)

    logger.debug(f"Got query {name=} ...")
    url = fetch_url_from_name(name)
    return text_response(text=url, status=HTTP_200)


def search_post(req: Request):
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


def handle_search(req: Request):
    match req.method:
        case "GET":
            return search_get(req)
        case "POST":
            return search_post(req)
        case _:
            return text_response(
                "GET, POST are the only methods defined", status=HTTP_404
            )


def search_path_match(path: str) -> bool:
    return re.search(r"/search$", path) is not None


def download_post(req: Request):
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
    path = download_from_urls([url])


def handle_download(req: Request):
    match req.method:
        case "POST":
            return download_post(req)
        case _:
            return text_response("POST is the only method defined", status=HTTP_404)


def download_path_match(path: str) -> bool:
    return re.search(r"/download$", path) is not None


def run(args):
    host, port = args.host, args.port
    handlers = [
        (lambda x: x == "/", handle_root),
        (search_path_match, handle_search),
        (download_path_match, handle_download),
    ]

    logger.info(f"Trying to start server with {host}:{port}...")
    server = Server(loop=Loop(), handlers=handlers)
    server.run(host=host, port=port)
    return 0
