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


def _next(gen: Generator) -> str | None:
    try:
        return next(gen)
    except StopIteration:
        return None


def next_token(data: Generator) -> str | None:
    return _next(data)


def parse_int(token):
    match (token[0], token[1:]):
        case ('+', rest):
            return int(rest)
        case ('-', rest):
            return -int(rest)
        case _:
            return int(token)


def parse_bool(token):
    match token:
        case 't':
            return True
        case 'f':
            return False
        case x:
            raise ValueError(f"Given input is not boolean : {x=}")


def parse_bulkstrings(sz, tokens):
    token = next(tokens)
    assert len(token) == sz
    return token


def parse_array(sz, tokens) -> list:
    token = next_token(tokens)
    rv = []
    if token is None:
        return []

    for _ in range(sz):
        parsed_token = parse_data(tokens)
        rv.append(parsed_token)

    return rv


# TODO: make a parser for reading nested data
def parse_data(tokens):
    token = next_token(tokens)
    if token is None:
        return

    match (token[0], token[1:]):
        case ("+", _):
            # return simple_strings()
            pass
        case ("-", _):
            # return simple_errors()
            pass
        case (":", rest):
            return parse_int(rest)
        case ("_", _):
            # return nulls()
            pass
        case ("#", rest):
            return parse_bool(rest)
        case (",", _):
            # return doubles()
            pass
        case ("(", _):
            # return big_numbers()
            pass
        case ("!", _):
            # return bulk_errors()  # Simple
            pass
        case ("$", rest):
            return parse_bulkstrings(int(rest), tokens)
        case ("*", rest):
            got = parse_array(int(rest), tokens)
            return got
        case ("=", _):
            # return verbatim_strings()
            pass
        case ("%", _):
            # return maps()
            pass
        case ("~", _):
            # return sets()
            pass
        case (">", _):
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


def get_response(data):
    tokens = parse_crlf(data)
    ctype, res = parse_data(tokens)
    return ctype, ""


def handle_client(client: socket.socket):
    while data := read_data(client):
        print(f"{data=}")
        ctype, res = get_response(data)
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
