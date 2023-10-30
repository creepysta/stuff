# Uncomment this to pass the first stage
import socket
from enum import Enum
from threading import Thread
from typing import Generator


class CommandType(Enum):
    NoOp = "NOOP"
    Ping = "PING"
    Echo = "ECHO"
    Get = "GET"
    Set = "SET"


class ErrorType(Enum):
    Command = "command"
    InvalidData = "invalid_data"
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


def handle_err(cmd: str | None, args: list[str] | None, error_type: ErrorType) -> str:
    match error_type:
        case ErrorType.Command:
            return f"-ERR unknown command {cmd!r}\r\n"
        case ErrorType.WrongType:
            return (
                "-WRONGTYPE Operation against a key holding the wrong kind"
                f"of value {args=}"
            )
        case ErrorType.InvalidData:
            return f"-ERR invalid input, cannot parse data: {cmd!r}"


def command_echo(data: list[str]) -> tuple[CommandType, str]:
    rdata = " ".join(data)
    resp = f"+{rdata}\r\n"
    return CommandType.Echo, resp


def command_ping() -> tuple[CommandType, str]:
    return CommandType.Ping, "+PONG\r\n"


def parse_crlf(data: str) -> Generator[str, None, None]:
    token = ""
    for ch in data:
        if ch in ('\r'):
            yield token
            token = ""
            continue
        elif ch == '\n':
            continue

        token += ch


def _next(gen: Generator):
    try:
        return next(gen)
    except StopIteration:
        raise StopIteration("Not enough values to unpack")


def next_token(data: str | Generator) -> tuple[str, Generator[str, None, None]]:
    match data:
        case Generator():
            return _next(data), data
        case str():
            gen = parse_crlf(data)
            return _next(gen), gen
        case _:
            raise ValueError(
                "Invalid input, token can be only of type str | Generator"
                f" {data=!r}"
            )


def parse_int(data: str) -> tuple[int, Generator[str, None, None]]:
    token, rest = next_token(data)
    return int(token), rest


def parse_bool(data: str) -> tuple[bool, Generator[str, None, None]]:
    token, rest = next_token(data)
    match token:
        case 't':
            return True, rest
        case 'f':
            return False, rest
        case _:
            raise ValueError(f"Given input is not boolean : {data=}")


def parse_array(data: str) -> tuple[list, Generator[str, None, None]]:
    token, rest = next_token(data)
    num_items = int(token)
    rv = []
    for _ in range(num_items):
        token: str
        try:
            token, rest = next_token(rest)
        except StopIteration:
            raise Exception(f"Client sent less items than promised in {data=}")

        num_items -= 1
        parsed_token, _ = parse_data(token)
        rv.append(parsed_token)

    return rv, rest


# TODO: make a parser for reading nested data
def parse_data(data: str):
    match data.split():
        case ["+", _]:
            # return simple_strings()
            pass
        case ["-", _]:
            # return simple_errors()
            pass
        case [":", _]:
            return parse_int(data)
        case ["_", _]:
            # return nulls()
            pass
        case ["#", _]:
            return parse_bool(data)
        case [",", _]:
            # return doubles()
            pass
        case ["(", _]:
            # return big_numbers()
            pass
        case ["!", _]:
            # return bulk_errors()  # Simple
            pass
        case ["$", _]:
            # return bulk_strings()
            pass
        case ["*", rest]:
            got = parse_array(rest)
            return got
        case ["=", _]:
            # return verbatim_strings()
            pass
        case ["%", _]:
            # return maps()
            pass
        case ["~", _]:
            # return sets()
            pass
        case [">", _]:
            # return pushes()   # Agg
            pass
        case _:
            return None, handle_err(data, None, ErrorType.InvalidData)


def read_data(client: socket.socket) -> str:
    data = ""
    while r := client.recv(1024):
        data += r.decode("utf-8")
        if len(r) < 1024 or not r:
            break

    return data


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
