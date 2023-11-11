import socket
from argparse import ArgumentParser
from collections import deque
from enum import Enum
from pathlib import Path
from select import select
from urllib.parse import parse_qsl, urlparse

HTTP_200 = "HTTP/1.1 200 OK"
HTTP_201 = "HTTP/1.1 201 Created"
HTTP_400 = "HTTP/1.1 400 Bad Request"
HTTP_404 = "HTTP/1.1 404 Not Found"


class ServerOptions:
    static_path = ""


class IoWaitType(Enum):
    Recv = "recv"
    Send = "send"
    Sleep = "sleep"


class Request:
    def __init__(self, data: str):
        self._data = data.split("\r\n")
        self._body_start = -1
        assert len(self._data) > 2, "invalid request"

    @property
    def request(self) -> list[str]:
        return self._data[0].split(" ")

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
    def headers(self) -> dict:
        rv = {}
        for i, line in enumerate(self._data[1:]):
            if not line:
                if self._body_start == -1:
                    self._body_start = i + 2
                break

            pos = line.index(":")
            name, val = line[:pos].strip(), line[pos + 1 :].strip()
            rv[name] = val

        return rv

    @property
    def body(self) -> str:
        _ = self.headers  # prime the body pos just in case
        if self._body_start == -1 or self._body_start > len(self._data):
            return ""

        return "\n".join(self._data[self._body_start :])

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


def text_response(text: str) -> str:
    resp = "\r\n".join(
        [
            HTTP_200,
            "Content-Type: text/plain",
            f"Content-Length: {len(text)}",
            "",
            text,
        ]
    )
    return resp


def file_response(file_path: str) -> str | None:
    root_dir = ServerOptions.static_path
    file = Path(root_dir) / file_path
    if not file.exists():
        return None

    contents = file.read_text()
    resp = "\r\n".join(
        [
            HTTP_200,
            "Content-Type: application/octet-stream",
            f"Content-Length: {len(contents)}",
            "",
            contents,
            "",
        ]
    )
    return resp


def download_file(file_path: str, contents: str | bytes) -> None:
    root_dir = ServerOptions.static_path
    file = Path(root_dir) / file_path
    file.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(contents, bytes):
        contents = contents.decode("utf-8")

    with open(file.as_posix(), "w") as f:
        f.write(contents)  # type: ignore


class Server:
    def __init__(self, handlers, loop):
        self.handlers = handlers
        self.loop = loop

    def get_response(self, req: Request) -> str:
        resp = HTTP_404 + "\r\n\r\n"
        for fn, handler in self.handlers:
            if fn(req.path) is True:
                return handler(req)

        # print(f"{req=}")
        # if req.path == "/":
        #     resp = HTTP_200 + "\r\n\r\n"
        # elif req.path.startswith("/echo"):
        #     val = req.path.lstrip("/echo/")
        #     resp = text_response(val)
        # elif req.path == "/user-agent":
        #     val = req.headers.get("User-Agent", "NA")
        #     resp = text_response(val)
        # elif req.path.startswith("/files"):
        #     fname = req.path.lstrip("/files")
        #     if req.method == "GET":
        #         got = file_response(fname)
        #         if got is not None:
        #             resp = got
        #     elif req.method == "POST":
        #         got = download_file(fname, req.body)
        #         resp = HTTP_201 + "\r\n\r\n"

        print(f"{resp=}")
        return resp

    def handle_client(self, client: socket.socket):
        data = ""
        print("Client connected:", client)
        while True:
            yield IoWaitType.Recv, client
            r = client.recv(1024)
            data += r.decode("utf-8")
            if not r or len(r) < 1024:
                break

        request = Request(data)
        print(f"{request=}")
        resp = self.get_response(request)
        yield IoWaitType.Send, client
        client.sendall(resp.encode("utf-8"))
        client.close()

    def serve(self, address: tuple[str, int]):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)
        sock.listen(5)
        while True:
            yield IoWaitType.Recv, sock
            client, _ = sock.accept()
            self.loop.add_job(self.handle_client(client))

    def run(self, host: str = "127.0.0.1", port: int = 42999):
        print(f"Server listening at {host}:{port}...")
        self.loop.add_job(self.serve((host, port)))
        self.loop.start()


def setup_defaults(host: str, port: int):
    def handle_root(req: Request):
        assert req.path == "/"
        return HTTP_200 + "\r\n\r\n"

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
            else:
                resp = HTTP_400

            return resp + "\r\n\r\n"

        if req.method == "POST":
            got = download_file(fname, req.body)
            resp = HTTP_201 + "\r\n\r\n"
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
