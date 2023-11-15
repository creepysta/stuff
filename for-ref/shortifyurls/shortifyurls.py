import logging
import re
from argparse import ArgumentParser
from functools import partial
from uuid import uuid4

import redis
from litehttp import (
    HTTP_201,
    HTTP_204,
    HTTP_400,
    HTTP_404,
    Loop,
    Request,
    Server,
    redirect_response,
    text_response,
)

logger = logging.getLogger("litehttp")


def get_url_from_path(path: str):
    return path.split("/")[-1].strip(" /")


def get(req: Request, store: redis.Redis):
    short_url = get_url_from_path(req.path)
    res = store.get(short_url)
    if res:
        return redirect_response(url=res)

    return HTTP_404 + "\r\n\r\n"


def post(req: Request, store: redis.Redis):
    short_url = uuid4().hex[-5:]
    for _ in range(5):
        if not store.get(short_url):
            break

        short_url = uuid4().hex[-6:]

    url = ""
    try:
        url = req.json()["url"]
    except Exception as e:
        logger.warning(f"Failed to parse request body with: {e=}")

    if url:
        store.set(short_url, url)
        return text_response(text=short_url, status=HTTP_201)

    return text_response(text="Url not found in body", status=HTTP_404)


def delete(req: Request, store: redis.Redis):
    short_url = get_url_from_path(req.path)
    if not store.get(short_url):
        return text_response(text="Url not found", status=HTTP_404)

    store.set(short_url, "")
    return text_response(status=HTTP_204)


def handle_root(req: Request, store: redis.Redis):
    match req.method:
        case "GET":
            return get(req, store)
        case "POST":
            return post(req, store)
        case "DELETE":
            return delete(req, store)
        case _:
            return text_response(
                "GET, POST, DELETE are the only methods", status=HTTP_400
            )


def main():
    parser = ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--redis-host", default="localhost")
    args = parser.parse_args()

    store = redis.Redis(host=args.redis_host, port=6379, decode_responses=True)
    fn = partial(handle_root, store=store)
    handlers = [
        (lambda x: re.search(r"/(\S+)?", x) is not None, fn),
    ]

    server = Server(loop=Loop(), handlers=handlers)
    server.run(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
