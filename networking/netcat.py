import io
import socket
import sys
import time
from argparse import ArgumentParser


class flushfile(io.TextIOWrapper):
    def __init__(self, f):
        self.f = f

    def write(self, x):
        val = self.f.write(x)
        self.f.flush()
        return val


# sys.stdout = flushfile(sys.stdout)


def netcat(host: str, port: int, content: str | None = None):
    if content is None:
        content = f"GET / HTTP/1.1\nHost: {host}\n\n"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    content = content.encode("utf-8")  # type: ignore
    sock.sendall(content)  # type: ignore
    time.sleep(0.2)
    sock.shutdown(socket.SHUT_WR)

    res = ""
    while True:
        data = sock.recv(1024)
        if not data:
            break

        res += data.decode("utf-8")

    sys.stdout.write(res)
    sys.stdout.write("Connection closed")

    sock.close()


def main() -> int:
    parser = ArgumentParser()
    parser.add_argument('host')
    parser.add_argument('port', type=int)
    args = parser.parse_args()
    hostname, port = args.host, args.port
    netcat(hostname, port)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
