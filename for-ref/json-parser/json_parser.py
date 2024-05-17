import argparse
import json
import string
import sys
import typing as t
from pathlib import Path

__all__ = ["json_p", "null_p", "bool_p", "string_p", "number_p", "array_p", "object_p"]


JsonNull: t.TypeAlias = None  # t.NewType('JsonNull', None)
JsonBool = t.NewType("JsonBool", bool)
JsonString = t.NewType("JsonString", str)  # NOTE: doesn't consider escape characters
JsonNumber = t.NewType("JsonNumber", int)  # NOTE: doesn't consider floats
JsonArray = t.NewType("JsonArray", list["JsonValue"])
JsonObject = t.NewType("JsonObject", dict[str, "JsonValue"])
JsonValue: t.TypeAlias = (
    JsonNull | JsonBool | JsonString | JsonNumber | JsonArray | JsonObject
)

ParserReturnType = tuple[JsonValue, str] | None

Char = str  # NOTE: represents a single character
T = t.TypeVar("T")

Parser = t.Callable[[str], tuple[T, str] | None]


def _char_p(ch: Char) -> Parser[Char]:
    def parse(src: str) -> tuple[Char, str] | None:
        src_ = [ch for ch in src]
        match src_:
            case [x, *xs] if x == ch:
                return (ch, "".join(xs))
            case _:
                return None

    return parse


def _str_p(what: str) -> Parser[str]:
    def parse(src: str) -> tuple[str, str] | None:
        rem = src
        got = None
        rv = ("", src)
        for ch in what:
            got = _char_p(ch)(rem)
            match got:
                case (now, rem):
                    rv = (rv[0] + now, rem)
                case _:
                    break

        return rv if got is not None else None

    return parse


def null_p() -> Parser[JsonValue]:
    def parse(src: str) -> tuple[JsonNull, str] | None:
        got = _str_p("null")(src)
        match got:
            case ("null", rem):
                return (None, rem)
            case _:
                return None

    return parse


def bool_p() -> Parser[JsonValue]:
    def parse(src: str) -> tuple[JsonBool, str] | None:
        got = _str_p("true")(src) or _str_p("false")(src)
        match got:
            case ("true", rem):
                return (JsonBool(True), rem)
            case ("false", rem):
                return (JsonBool(False), rem)
            case _:
                return None

    return parse


def _span_p(predicate: t.Callable[[Char], bool]) -> Parser[str]:
    def parse(src: str) -> tuple[str, str] | None:
        rem = src
        got = None
        rv = ("", src)
        for ch in src:
            got = _char_p(ch)(rem)
            match got:
                case (now, rem) if predicate(ch):
                    rv = (rv[0] + now, rem)
                case _:
                    break

        return rv if got is not None else None

    return parse


def string_p() -> Parser[JsonValue]:
    def parse(src: str) -> tuple[JsonString, str] | None:
        if not src or src[0] != '"':
            return None

        got = _span_p(lambda x: x != '"')(src[1:])
        match got:
            case (now, rem):
                return (JsonString(now), rem[1:])
            case _:
                return None

    return parse


def number_p() -> Parser[JsonValue]:
    def parse(src: str) -> tuple[JsonNumber, str] | None:
        got = _span_p(lambda x: x.isdigit())(src)
        match got:
            case (num, rem) if num.isnumeric():
                return (JsonNumber(int(num)), rem)
            case _:
                return None

    return parse


def ignore_sep(ch: t.Iterable[Char]):
    def parse(src: str):
        got = _span_p(lambda x: x in ch)(src)
        if got:
            return got[1]

        return src

    return parse


def ignore_ws(src: str):
    return ignore_sep(string.whitespace)(src)


# NOTE: consider consuming the first item so that we get the repeated structure of <, e>
# currently it parses arrays of the type [a1, a2,], in which the trailing ',' sould fail the parser
def array_p() -> Parser[JsonValue]:
    def parse(src: str) -> tuple[JsonArray, str] | None:
        if not src or src[0] != "[":
            return None

        src = src[1:]  # consume the '['
        src = ignore_ws(src)

        if src and src[0] == "]":
            return JsonArray([]), src[1:]

        rem = src
        rv = None
        while rem:
            rem = ignore_ws(rem)
            if not rem or rem[0] == "]":
                break

            p_rem = rem
            got = json_p()(rem)
            match got:
                case (now, rem):
                    rv = rv or []
                    rv.append(now)
                case _:
                    return None

            if p_rem == rem:
                break

            rem = ignore_ws(rem)
            if rem and rem[0] == ",":
                rem = rem[1:]

            rem = ignore_ws(rem)
            p_rem = rem

        if rem[0] != "]":
            return None

        rem = rem[1:]  # consume the ']'
        return (JsonArray(rv), rem) if rv is not None else None

    return parse


# NOTE: consider consuming the first item so that we get the repeated structure of <, k: v>
# currently it parses objects of the type {k1: v1, k2: v2,}, in which the trailing ',' sould fail the parser
def object_p() -> Parser[JsonValue]:
    def parse(src: str) -> tuple[JsonObject, str] | None:
        if not src or src[0] != "{":
            return None

        src = src[1:]  # consume the '{'
        src = ignore_ws(src)

        if src and src[0] == "}":
            return JsonObject({}), src[1:]

        rem = src
        rv = None
        while rem:
            rem = ignore_ws(rem)
            if not rem or rem[0] == "}":
                break

            p_rem = rem
            key_p = string_p()(rem)
            match key_p:
                case (some, rem):
                    key = some
                case _:
                    return None

            rem = ignore_ws(rem)
            if rem and rem[0] != ":":
                return None

            rem = rem[1:]
            rem = ignore_ws(rem)

            value = json_p()(rem)
            match value:
                case (now, rem):
                    rv = rv or {}
                    rv[key] = now
                case _:
                    pass

            if p_rem == rem:
                break

            rem = ignore_ws(rem)
            if rem and rem[0] == ",":
                rem = rem[1:]

            rem = ignore_ws(rem)
            p_rem = rem

        if rem[0] != "}":
            return None

        rem = rem[1:]  # consume '}'

        return (JsonObject(rv), rem) if rv is not None else None

    return parse


def json_p() -> Parser:
    funcs = [null_p, bool_p, string_p, number_p, array_p, object_p]

    def parse(src: str) -> tuple[JsonValue, str] | None:
        rv = None
        src = ignore_ws(src)
        for fn in funcs:
            rv = rv or fn()(src)

        match rv:
            case (now, rem):
                return (now, ignore_ws(rem))
            case _:
                return None

    return parse


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file")
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()

    content = None
    if args.stdin:
        content = sys.stdin.read()
    elif args.file:
        path = Path(args.file).absolute()
        if not path.exists():
            print(f"Given {path=} doesn't exist")
            return 1

        content = path.read_text()

    if content is None:
        print("Please provide a --file or --stdin for the json content")
        return 1

    got = json_p()(content)
    if got is None or got[1]:
        return 1

    print(json.dumps(got[0], indent=4))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
