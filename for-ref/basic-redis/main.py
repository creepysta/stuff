# Uncomment this to pass the first stage
import socket
from enum import Enum
from threading import Thread
from typing import Generator
from argparse import ArgumentParser


class Redis:
    def __init__(self):
        self.store = {}

    def set(self, key, val) -> str:
        self.store[key] = val
        return "OK"

    def get(self, key: str):
        return self.store.get(key)

    def exists(self, keys: list) -> int:
        return sum([key in self.store.keys() for key in keys])

    def del_keys(self, keys: list) -> int:
        rv = 0
        for key in keys:
            if key in self.store.keys():
                rv += 1
                del self.store[key]

        return rv

    def incr(self, key: str) -> int | None:
        if not (self.get(key) is None or isinstance(self.get(key), int)):
            return None

        self.set(key, (self.get(key) or 0) + 1)
        return self.get(key)  # type: ignore

    def decr(self, key: str) -> int | None:
        if not (self.get(key) is None or isinstance(self.get(key), int)):
            return None

        self.set(key, (self.get(key) or 0) - 1)
        return self.get(key)  # type: ignore

    def lpush(self, key: str, vals: list) -> int | None:
        if not (self.get(key) is None or isinstance(self.get(key), list)):
            return None

        vals.reverse()
        if self.get(key) is None:
            self.set(key, [])

        self.set(key, vals + self.get(key))  # type: ignore
        return len(self.get(key))  # type: ignore

    def rpush(self, key: str, vals: list) -> int | None:
        if not (self.get(key) is None or isinstance(self.get(key), list)):
            return None

        if self.get(key) is None:
            self.set(key, [])

        self.set(key, self.get(key) + vals)  # type: ignore
        return len(self.get(key))  # type: ignore

    def save(self) -> str:
        return "OK"


store = Redis()


class CommandType(Enum):
    NoOp = "NOOP"
    Ping = "PING"
    Del = "DEL"
    Echo = "ECHO"
    Exists = "EXISTS"
    Get = "GET"
    Set = "SET"
    Incr = "INCR"
    Decr = "DECR"
    Save = "SAVE"
    Lpush = "LPUSH"
    Rpush = "RPUSH"


class ErrorType(Enum):
    Command = "command"
    InvalidData = "invalid_data"
    WrongType = "wrong_type_operation"


class Base:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        super().__init__()

    @property
    def _margs(self):
        args = ",".join(
            [
                f"{k}={v!r}"
                for k, v in vars(self).items()  # self.kwargs.items()
                if not (k.startswith("_"))
            ]
        )
        return args

    def __repr__(self):
        cons = f"{type(self).__name__}({self._margs})"
        return cons

    def __eq__(self, o):
        if not isinstance(o, type(self)):
            raise NotImplementedError()

        ok = True
        for k, v in vars(self).items():
            if not hasattr(self, k):
                continue

            ok = ok and (getattr(o, k) == v)

        return ok

    def __hash__(self):
        args = self._margs
        return hash(args)


class Error(Base):
    def __init__(self, msg: str, **kwargs):
        self.msg = msg
        super().__init__(msg=msg, **kwargs)

    def ser(self):
        return f"-Err: {self.msg}\r\n"

    def __str__(self):
        return self.msg


class BulkError(Error):
    def __init__(self, sz: int, msg: str, **kwargs):
        self.sz = sz
        self.msg = msg
        super().__init__(msg=msg, **kwargs)

    def ser(self):
        return f"!{self.sz}\r\n-Err: {self.msg}\r\n"

    def __str__(self):
        return self.msg


class BulkString(str):
    def __new__(cls, sz: int, data: str):
        # ref - https://stackoverflow.com/questions/7255655/how-to-subclass-str-in-python
        cls.sz = sz
        return super().__new__(cls, data)

    def __init__(self, sz: int, data: str):
        self.sz = sz
        self.data = data

    def __str__(self):
        return self.data

    def ser(self):
        return f"${self.sz}\r\n{self.data}\r\n"

    def __repr__(self):
        return f"{type(self).__name__}(sz={self.sz},data={self.data})"


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
    return ":{val}\r\n".format(val=str(val))


def serialize_str(val: str) -> str:
    return "+{val}\r\n".format(val=val)


def serialize_bulk_str(val: BulkString) -> str:
    return val.ser()


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
    return data.ser()


def serialize_bulk_error(data: BulkError) -> str:
    return data.ser()


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
            return serialize_bulk_error(data)  # Simple
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


def handle_command(command: str, body: list):
    match command.upper():
        case CommandType.Ping.value:
            return CommandType.Ping, serialize_data("PONG")
        case CommandType.Echo.value:
            rv = serialize_data(body[0])
            return CommandType.Echo, rv
        case CommandType.Exists.value:
            resp = store.exists(body[1:])
            rv = serialize_data(resp)
            return CommandType.Exists, rv
        case CommandType.Set.value:
            resp = store.set(body[0], body[1])
            rv = serialize_data(resp)
            return CommandType.Set, rv
        case CommandType.Get.value:
            rv = serialize_data(store.get(body[0]))
            return CommandType.Get, rv
        case CommandType.Incr.value:
            resp = store.incr(body[0])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(Error(
                    f"Cannot increment data for key={body[0]}."
                    f" Current value stored: {store.get(body[0])!r}"
                ))
            return CommandType.Incr, rv
        case CommandType.Decr.value:
            resp = store.decr(body[0])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(Error(
                    f"Cannot decrement data for key={body[0]}."
                    f" Current value stored: {store.get(body[0])!r}"
                ))
            return CommandType.Decr, rv
        case CommandType.Lpush.value:
            resp = store.lpush(body[0], body[1:])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(Error(
                    f"Cannot perform LPUSH for key={body[0]}."
                    f" Current value stored: {store.get(body[0])!r}"
                ))
            return CommandType.Lpush, rv
        case CommandType.Rpush.value:
            resp = store.rpush(body[0], body[1:])
            rv = serialize_data(resp)
            if resp is None:
                rv = serialize_data(Error(
                    f"Cannot perform RPUSH for key={body[0]}."
                    f" Current value stored: {store.get(body[0])!r}"
                ))
            return CommandType.Rpush, rv
        case CommandType.Save.value:
            resp = store.save()
            rv = serialize_data(resp)
            return CommandType.Save, rv
        case _:
            return None, serialize_error(Error("Invalid command"))


def get_response(data):
    tokens = parse_crlf(data)
    res = parse_data(tokens)
    print(f"{res=}")
    match res:
        case list() if len(res) > 0:
            rv = handle_command(res[0], res[1:])
            return rv
        case _:
            return None, f"-Err: Can't respond to unknown input {data=}\r\n"


def handle_client(client: socket.socket):
    while data := read_data(client):
        print(f"{data=}")
        ctype, res = get_response(data)
        print(f"{res=}")
        client.sendall(res.encode("utf-8"))
        if ctype is None:
            break

    client.close()


def main(argv: list[str] | None = None):
    parser = ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args(argv)

    if args.serve:
        host = "localhost"
        port = 6379
        print(f"Server listening on {host=}, {port=}")
        serve(host, port)


if __name__ == "__main__":
    main()
