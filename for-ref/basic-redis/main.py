# Uncomment this to pass the first stage
import socket
from threading import Thread
from enum import Enum


class CommandType(Enum):
    NoOp = "NOOP"
    Ping = "PING"
    Echo = "ECHO"


class ErrorType(Enum):
    Command = "command"
    WrongType = "wrong_type_operation"


def serve(host: str, port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    addr = (host, port)
    sock.bind(addr)
    sock.listen(5)
    while True:
        client, _ = sock.accept()
        t = Thread(target=handle_client, args=(client,))
        t.start()


def read_data(client: socket.socket) -> str:
    data = ""
    while r := client.recv(1024):
        data += r.decode("utf-8")
        if len(r) < 1024 or not r:
            break

    return data


def handle_err(cmd: str, args: list[str], error_type: ErrorType) -> str:
    match error_type:
        case ErrorType.Command:
            return f"-ERR unknown command {cmd!r}\r\n"
        case ErrorType.WrongType:
            return (
                "-WRONGTYPE Operation against a key holding the wrong kind"
                f"of value {args=}"
            )


def handle_echo(data: list[str]) -> tuple[CommandType, str]:
    rdata = " ".join(data)
    resp = f"+{rdata}\r\n"
    return CommandType.Echo, resp


def handle_ping() -> tuple[CommandType, str]:
    return CommandType.Ping, "+PONG\r\n"


def parse_array(data: str) -> tuple[CommandType, str] | tuple[None, str]:
    lines = data.split('\r\n')
    n = int(lines[0][1:])
    if n == 0:
        return CommandType.NoOp, "+\r\n"
    cmd = lines[2].lower()
    args = lines[4::2]
    match cmd:
        case "echo":
            return handle_echo(args)
        case "ping":
            return handle_ping()
        case _:
            return None, handle_err(cmd, args, ErrorType.Command)


# TODO: make a parser for reading nested data
def parse_data(data: str) -> tuple[CommandType, str] | tuple[None, str]:
    match data[0]:
        case '*':
            return parse_array(data)
        case _:
            return None, data


def handle_client(client: socket.socket):
    while data := read_data(client):
        print(f"{data=}")
        ctype, res = parse_data(data)
        print(f"{res=}")
        client.sendall(res.encode("utf-8"))
        if ctype is None:
            break

    client.close()


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")
    host = "localhost"
    port = 6379
    serve(host, port)


if __name__ == "__main__":
    main()
