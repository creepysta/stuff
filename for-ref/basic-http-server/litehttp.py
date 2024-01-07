import json
import logging
import socket
import sys
from argparse import ArgumentParser
from collections import deque
from enum import Enum
from functools import cached_property
from pathlib import Path
from select import select
from threading import Thread
from time import perf_counter
from urllib.parse import parse_qsl, urlparse
from uuid import uuid4

logger = logging.getLogger("litehttp")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


HTTP_200 = "HTTP/1.1 200 OK"
HTTP_201 = "HTTP/1.1 201 Created"
HTTP_204 = "HTTP/1.1 204 No Content"
HTTP_400 = "HTTP/1.1 400 Bad Request"
HTTP_404 = "HTTP/1.1 404 Not Found"
HTTP_302 = "HTTP/1.1 302 Found"
HTTP_411 = "HTTP/1.1 411 Length Required"
HTTP_429 = "HTTP/1.1 429 Too Many Requests"


class ServerOptions:
    static_path = ""


class IoWaitType(Enum):
    Recv = "recv"
    Send = "send"
    Sleep = "sleep"


class Request:
    def __init__(self, data: str, source):
        self._data = data.split("\r\n")
        self._body_start = -1
        self._header_end = -1
        self._body_end = -1
        self._source = source
        assert len(self._data) >= 2, "invalid request"

    @property
    def request(self) -> list[str]:
        return self._data[0].split(" ")

    @cached_property
    def request_id(self):
        return uuid4().hex

    @property
    def remote_addr(self):
        return self._source

    @property
    def protocol(self) -> str:
        return self.request[2]

    @property
    def _url(self):
        return urlparse(self.request[1])

    @property
    def path(self) -> str:
        return self._url.path

    @property
    def params(self) -> str:
        return self._url.params

    @property
    def query(self):
        return dict(parse_qsl(self._url.query))

    @property
    def method(self) -> str:
        return self.request[0]

    @property
    def _body_len(self) -> int | None:
        l = self.headers.get("content-length")
        if l is None:
            return None
        return int(l)

    @property
    def _got_body(self) -> bool:
        expected = self._body_len
        if expected is None:
            return False
        got = len(self.body) >= expected
        if got:
            self._body_end = expected

        return got

    @property
    def _is_done(self) -> tuple[bool, int]:
        """
        The tuple can be interpreted as (is_done, content-length header present?)
        If content-length is not set in headers, it will return False, 411
        If the entire request has arrived the it returns True, 0
        """
        body_sz = (
            self._body_len
        )  # until self.headers is called, self._header_end won't get updated
        got_headers = self._header_end > -1
        is_valid = got_headers and (body_sz is not None)
        if got_headers and self.method == "GET":
            return True, 0

        if not is_valid:
            return False, 411
        return self._got_body, 0

    @property
    def headers(self) -> dict:
        rv = {}
        for i, line in enumerate(self._data[1:]):
            if not line:
                if self._header_end == -1:
                    self._header_end = i + 2
                break

            pos = line.index(":")
            name, val = tuple(
                map(lambda x: x.strip().lower(), (line[:pos], line[pos + 1 :]))
            )
            rv[name] = val

        return rv

    @property
    def body(self) -> str:
        # TODO: body may contain binary data
        _ = self.headers  # prime the body pos just in case
        if self._header_end == -1:  # or self._header_end > len(self._data):
            return ""

        body = "\n".join(self._data[self._header_end :])
        return body

    def json(self) -> dict:
        return json.loads(self.body)

    def __repr__(self):
        args = ", ".join(
            [
                f"{k}={getattr(self, k)!r}"
                for k, v in vars(type(self)).items()
                if (isinstance(v, property) and not k.startswith("_"))
            ]
        )
        return f"{type(self).__name__}({args})"


class Loop:
    def __init__(self):
        self.tasks = deque()
        self.recv_wait = {}
        self.send_wait = {}

    def add_job(self, job):
        self.tasks.append(job)

    def get_next_job(self):
        return self.tasks.popleft()

    def run_job(self, job):
        return next(job)

    def _handle(self, why: IoWaitType, what: socket.socket, task):
        match why:
            case IoWaitType.Recv:
                self.recv_wait[what] = task
            case IoWaitType.Send:
                self.send_wait[what] = task
            case IoWaitType.Sleep:
                raise NotImplementedError("Async Sleep is not yet implemented")
            case _:
                raise ValueError(f"Unknown wait type specified {why}")

    def start(self):
        while any([self.tasks, self.recv_wait, self.send_wait]):
            while not self.tasks:
                # wait for IO
                can_recv, can_send, _ = select(self.recv_wait, self.send_wait, [])
                for task in can_recv:
                    self.add_job(self.recv_wait.pop(task))
                for task in can_send:
                    self.add_job(self.send_wait.pop(task))

            task = self.get_next_job()
            try:
                why, what = self.run_job(task)
                self._handle(why, what, task)
            except StopIteration:
                pass


def redirect_response(url: str) -> str:
    return text_response(headers={"location": url}, status=HTTP_302)


def resp_str(status, headers: dict, data=None):
    hs = [f"{k}: {v}" for k, v in headers.items()]
    payload = [status, *hs, ""]
    if data:
        payload.append(data)

    resp = "\r\n".join(payload)
    return resp


def bin_response(data: bytes, headers: dict = {}, status=HTTP_200) -> bytes:
    default_headers = {
        "content-type": "application/octet-stream",
        "content-length": len(data),
    }
    for k, v in headers.items():
        default_headers[k.lower()] = v

    resp = resp_str(status, default_headers).encode("utf-8")
    newline = "\r\n".encode("utf-8")
    return resp + newline + data + newline


def json_response(data: dict, headers: dict = {}, status=HTTP_200) -> str:
    return text_response(
        json.dumps(data),
        headers={"content-type": "application/json", **headers},
        status=status,
    )


def text_response(text: str = "", headers: dict = {}, status=HTTP_200) -> str:
    default_headers = {
        "content-type": "text/plain",
        "content-length": len(text),
    }
    for k, v in headers.items():
        default_headers[k.lower()] = v

    resp = resp_str(status, default_headers, text)
    return resp


def file_response(
    file_path: str, f_type="text", content_type="text/plain"
) -> bytes | None:
    root_dir = ServerOptions.static_path
    file = Path(root_dir) / file_path
    if not file.exists():
        return None

    if f_type == "binary":
        contents = file.read_bytes()
        resp = bin_response(
            contents,
            headers={"Content-Disposition": f"attachment; filename={file.name!r}"},
        )
        return resp

    contents = file.read_text()
    resp = text_response(text=contents, headers={"content-type": content_type})
    return resp.encode("utf-8")


def download_file(file_path: str, contents: str | bytes) -> None:
    root_dir = ServerOptions.static_path
    file = Path(root_dir) / file_path
    file.parent.mkdir(parents=True, exist_ok=True)
    mode = "w"
    if isinstance(contents, bytes):
        mode = "wb"

    with open(file.as_posix(), mode) as f:
        f.write(contents)  # type: ignore


class Server:
    def __init__(self, handlers, loop):
        self.handlers = handlers
        self.loop = loop

    def get_response(self, request: Request) -> str:
        rid = request.request_id
        logger.info(f"[{type(self).__name__}] Processing request: {rid} | {request=}")
        prev = perf_counter()
        res = text_response(status=HTTP_404)
        if request._is_done[1] == 411:
            res = text_response(status=HTTP_411)
        else:
            for fn, handler in self.handlers:
                if fn(request.path) is True:
                    res = handler(request)
                    break

        time_taken = perf_counter() - prev
        logger.info(f"[{type(self).__name__}] Request: {rid} took - {time_taken}s")
        return res

    def handle_client(self, client: socket.socket):
        data = ""
        req_addr = client.getpeername()
        logger.info(f"Client connected: {req_addr}")
        # maybe consider max timeout for which the server waits for client
        # client.settimeout(60.0)
        request: Request
        while True:
            # yield IoWaitType.Recv, client
            try:
                r = client.recv(1024)
            except TimeoutError:
                break
            logger.debug(f"Read chunk {len(r)=} | {r=}")
            data += r.decode("utf-8")
            if data:
                request = Request(data, req_addr)
                if any(request._is_done):
                    break

            # if not r:  # or len(r) < 1024:
            #     break

        logger.debug(f"Finished parsing {data=}")
        if not data:
            resp = text_response(status=HTTP_400)
        else:
            request = Request(data, req_addr)
            resp = self.get_response(request)

        # yield IoWaitType.Send, client
        if not isinstance(resp, bytes):
            resp = resp.encode("utf-8")

        client.sendall(resp)
        client.close()

    def serve(self, address: tuple[str, int]):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        sock.listen(5)
        while True:
            # yield IoWaitType.Recv, sock
            client, _ = sock.accept()
            t = Thread(target=self.handle_client, args=(client,))
            t.start()
            # self.loop.add_job(self.handle_client(client))

    def run(self, host: str = "127.0.0.1", port: int = 42999):
        logger.info(f"Server listening at {host}:{port}...")
        self.serve((host, port))
        # self.loop.add_job(self.serve((host, port)))
        # self.loop.start()


def setup_defaults(host: str, port: int):
    def handle_root(req: Request):
        assert req.path == "/"
        return text_response(status=HTTP_200)

    def handle_echo(req: Request):
        msg = req.path.split("/")[-1]
        resp = text_response(msg)
        return resp

    def handle_user_agent(req: Request):
        val = req.headers.get("User-Agent", "NA")
        resp = text_response(val)
        return resp

    def handle_files(req: Request):
        fname = "/".join(req.path.split("/")[2:])
        if req.method == "GET":
            got = file_response(fname)
            if got is not None:
                resp = got
                return resp
            else:
                return text_response(status=HTTP_400)

        if req.method == "POST":
            got = download_file(fname, req.body)
            resp = text_response(status=HTTP_201)
            return resp

    handlers = [
        (lambda path: path.startswith("/echo/"), handle_echo),
        (lambda path: path == "/user-agent", handle_user_agent),
        (lambda path: path.startswith("/files"), handle_files),
        (lambda path: path.startswith("/"), handle_root),
    ]

    server = Server(loop=Loop(), handlers=handlers)
    server.run(host, port)


def main(args_list: list[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default="5000")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--directory")
    args = parser.parse_args(args=args_list)

    if args.serve:
        setup_defaults(args.host, args.port)


if __name__ == "__main__":
    raise SystemExit(main())
