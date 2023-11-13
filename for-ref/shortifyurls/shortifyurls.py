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


def get_url_from_path(path: str):
    return path.split("/")[-1].strip(" /")


def handle_root(req: Request, store: redis.Redis):
    resp = HTTP_400
    if req.method == "GET":
        short_url = get_url_from_path(req.path)
        res = store.get(short_url)
        if res:
            return redirect_response(url=res)

        return HTTP_404 + "\r\n\r\n"

    if req.method == "POST":
        short_url = uuid4().hex[-5:]
        for _ in range(5):
            if not store.get(short_url):
                break

            short_url = uuid4().hex[-6:]

        url = req.json()["url"]
        store.set(short_url, url)
        return text_response(text=short_url, status=HTTP_201)

    if req.method == "DELETE":
        short_url = get_url_from_path(req.path)
        if not store.get(short_url):
            return HTTP_404 + "\r\n\r\n"

        store.set(short_url, "")
        return text_response(status=HTTP_204)

    return resp + "\r\n\r\n"


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
