import socket
from argparse import ArgumentParser
from pathlib import Path
from threading import Thread

HTTP_200 = "HTTP/1.1 200 OK"
HTTP_201 = "HTTP/1.1 201 Created"
HTTP_404 = "HTTP/1.1 404 Not Found"


class ServerOptions:
    static_path = ""


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
        return self.request[-1]

    @property
    def path(self) -> str:
        return self.request[-2]

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


def serve(address: tuple[str, int]):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    while True:
        client, _ = sock.accept()
        t = Thread(target=handle_client, args=(client,), daemon=True)
        t.start()


def handle_client(client: socket.socket):
    data = ""
    while r := client.recv(1024):
        data += r.decode("utf-8")
        if not r or len(r) < 1024:
            break

    request = Request(data)
    resp = get_response(request)
    client.sendall(resp.encode("utf-8"))
    client.close()


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
        ]
    )
    return resp


def download_file(file_path: str, contents: str | bytes) -> None:
    root_dir = ServerOptions.static_path
    file = Path(root_dir) / file_path
    if isinstance(contents, bytes):
        contents = contents.decode("utf-8")

    with open(file.as_posix(), "w") as f:
        f.write(contents)


def get_response(req: Request) -> str:
    # print(req)
    resp = HTTP_404 + "\r\n\r\n"
    if req.path == "/":
        resp = HTTP_200 + "\r\n\r\n"
    elif req.path.startswith("/echo"):
        val = req.path.lstrip("/echo/")
        resp = text_response(val)
    elif req.path == "/user-agent":
        val = req.headers.get("User-Agent")
        resp = text_response(val)
    elif req.path.startswith("/files"):
        fname = req.path.lstrip("/files")
        if req.method == "GET":
            got = file_response(fname)
            if got is not None:
                resp = got
        elif req.method == "POST":
            got = download_file(fname, req.body)
            resp = HTTP_201 + "\r\n\r\n"

    # print(resp)
    return resp


def main(args_list: list[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default='5000')
    parser.add_argument('--run', action='store_true')
    parser.add_argument("--directory")
    args = parser.parse_args(args=args_list)

    host, port = args.host, args.port
    serve((host, port))


if __name__ == '__main__':
    raise SystemExit(main())
