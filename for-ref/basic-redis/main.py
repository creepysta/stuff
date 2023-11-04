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


class Base:
    def __repr__(self):
        args = ",".join(
            [
                f"{k}={v!r}"
                for k, v in vars(self).items()
                if not (k.startswith("_") or hasattr(self, k))
            ]
        )
        cons = f"{type(self).__name__}({args})"
        return cons

    def __eq__(self, o):
        ok = True
        for k, v in vars(self).items():
            if not hasattr(self, k):
                continue

            ok = ok and (getattr(o, k) == v)

        return ok


class Error(Base):
    def __init__(self, msg: str):
        self.msg = msg

    def __str__(self):
        return f"-Err: {self.msg}\r\n"


class BulkError(Error):
    def __init__(self, sz: int, msg: str):
        self.sz = sz
        super().__init__(msg)

    def __str__(self):
        # TODO: think of a clean way to test this
        return f"!{self.sz}\r\n-Err: {self.msg}\r\n"


class BulkString(str, Base):
    def __init__(self, sz, *args):
        self.sz = sz
        super().__init__(*args)


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
        if ch in ("\r"):
            yield token
            token = ""
            continue
        elif ch == "\n":
            continue

        token += ch


def _next(gen: Generator) -> str | None:
    try:
        return next(gen)
    except StopIteration:
        return None


def next_token(data: Generator) -> str | None:
    return _next(data)


def parse_nulls() -> None:
    return None


def parse_int(token):
    match (token[0], token[1:]):
        case ("+", rest):
            return int(rest)
        case ("-", rest):
            return -int(rest)
        case _:
            return int(token)


def parse_bool(token):
    match token:
        case "t":
            return True
        case "f":
            return False
        case x:
            raise ValueError(f"Given input is not boolean : {x=}")


def parse_bulk_strings(sz, tokens) -> BulkString | None:
    if sz == -1:
        return None
    token = next(tokens)
    assert len(token) == sz
    return BulkString(len(token), token)


def parse_bulk_errors(sz, tokens) -> BulkError:
    token = next(tokens)
    assert len(token) == sz
    return BulkError(sz, token)


def parse_array(sz, tokens) -> list | None:
    if sz == -1:
        return None

    rv = []
    for _ in range(sz):
        parsed_token = parse_data(tokens)
        rv.append(parsed_token)

    return rv


def parse_sets(sz, tokens) -> set:
    rv = set()
    for _ in range(sz):
        parsed_token = parse_data(tokens)
        rv.add(parsed_token)

    return rv


def parse_maps(sz, tokens) -> dict:
    rv = {}
    for _ in range(sz):
        key = parse_data(tokens)
        val = parse_data(tokens)
        rv[key] = val

    return rv


def parse_simple_strings(token):
    return token


def parse_errors(token):
    return Error(token)


def parse_data(tokens):
    token = next_token(tokens)
    if token is None:
        return

    match (token[0], token[1:]):
        case ("+", rest):
            return parse_simple_strings(rest)
        case ("-", rest):
            return parse_errors(rest)
        case (":", rest):
            return parse_int(rest)
        case ("_", _):
            return parse_nulls()
        case ("#", rest):
            return parse_bool(rest)
        case ("!", rest):
            return parse_bulk_errors(int(rest), tokens)  # Simple
        case ("$", rest):
            return parse_bulk_strings(int(rest), tokens)
        case ("*", rest):
            return parse_array(int(rest), tokens)
        case ("%", rest):
            return parse_maps(int(rest), tokens)
        case ("~", rest):
            return parse_sets(int(rest), tokens)
        # case (",", _):
        #     # return doubles()
        # case ("(", _):
        #     # return big_numbers()
        # case ("=", _):
        #     # return verbatim_strings()
        # case (">", _):
        #     # return pushes()   # Agg
        case _:
            return None


def serialize_int(val: int) -> str:
    return ":{val}\r\n".format(val=val)


def serialize_str(val: str) -> str:
    return "+{val}\r\n".format(val=val)


def serialize_bulk_str(val: str) -> str:
    return "${sz}\r\n{val}\r\n".format(sz=len(val), val=val)


def serialize_bool(val: bool) -> str:
    return "#{val}\r\n".format(val="t" if val is True else "f")


def serialize_null() -> str:
    return "_\r\n"


def serialize_dict(data: dict) -> str:
    rv = f"%{len(data)}\r\n"
    for key, val in data.items():
        rv += serialize_data(key)
        rv += serialize_data(val)

    return rv


def serialize_list(data: list) -> str:
    rv = f"*{len(data)}\r\n"
    for item in data:
        rv += serialize_data(item)

    return rv


def serialize_set(data: set) -> str:
    rv = f"~{len(data)}\r\n"
    for item in data:
        rv += serialize_data(item)

    return rv


def serialize_error(data: Error) -> str:
    return str(data)


def serialize_bulk_error(data: BulkError) -> str:
    return str(data)


def serialize_data(data) -> str:
    match data:
        case int():
            return serialize_int(data)
        case BulkString():
            return serialize_bulk_str(data)
        case str():
            return serialize_str(data)
        case bool():
            return serialize_bool(data)
        case None:
            return serialize_null()
        case dict():
            return serialize_dict(data)
        case list():
            return serialize_list(data)
        case set():
            return serialize_set(data)
        case BulkError():
            return serialize_bulk_errors(data)  # Simple
        case Error():
            return serialize_error(data)
        # case float():
        #     return float():
        # case ("(", _):
        #     # return big_numbers()
        # case ("=", _):
        #     # return verbatim_strings()
        # case ("~", _):
        #     # return sets()
        # case (">", _):
        #    # return pushes()   # Agg
        case _:
            return serialize_null()


def read_data(client: socket.socket) -> str:
    data = ""
    while r := client.recv(1024):
        data += r.decode("utf-8")
        if len(r) < 1024 or not r:
            break

    return data


def get_response(data):
    tokens = parse_crlf(data)
    res = parse_data(tokens)
    print(f"{res=}")
    return None, ""


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
