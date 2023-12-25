import json
from pathlib import Path

import pytest

from litehttp import file_response, json_response, text_response


# TODO: feat/parameter substitution from path
@pytest.mark.parametrize(
    "pattern, expected",
    [
        # ("/echo/<msg: str>", {"msg": "str"}),
        # ("/echo/<msg: str>/foo/<msg2: str>", {"msg": "str", "msg2": "str"}),
        # (
        #     "/echo/<msg: str>/<msg1: int>/<msg2: str>",
        #     {"msg": "str", "msg1": "int", "msg2": "str"},
        # ),
    ],
)
def test_binding(pattern, expected):
    import re

    res = re.finditer(r"/<(\w+): (\w+)>/?", pattern)
    print(f"{list(res)=}")
    res = re.findall(r"/<(\w+): (\w+)>/?", pattern)
    print(f"{res=}")
    assert dict(res) == expected


@pytest.fixture
def text_temp_file(tmp_path):
    path = tmp_path / "text_file.txt"
    with open(path.as_posix(), "w") as f:
        f.write("This is test content for litehttp.")
        return f.name


@pytest.fixture
def bin_temp_file():
    path = Path() / "tests" / "fixtures" / "sample-3s.mp3"
    return path.absolute()


def test_file_response(text_temp_file):
    with open(text_temp_file, "r") as f:
        content = f.read()

    resp = file_response(text_temp_file)

    lines = [
        "HTTP/1.1 200 OK",
        "content-type: text/plain",
        f"content-length: {len(content)}",
        "",
        content,
    ]
    expected = "\r\n".join(lines).encode("utf-8")
    assert resp == expected


def test_text_response(text_temp_file):
    with open(text_temp_file, "r") as f:
        content = f.read()
        resp = text_response(content)

    lines = [
        "HTTP/1.1 200 OK",
        "content-type: text/plain",
        f"content-length: {len(content)}",
        "",
        content,
    ]
    expected = "\r\n".join(lines)
    assert resp == expected


def test_bin_file_response(bin_temp_file):
    resp = file_response(bin_temp_file.as_posix(), f_type="binary")
    with open(bin_temp_file.as_posix(), "rb") as f:
        content = f.read()

    lines = [
        "HTTP/1.1 200 OK",
        "content-type: application/octet-stream",
        f"content-length: {len(content)}",
        f"content-disposition: attachment; filename={bin_temp_file.name!r}",
        "",
        "",
    ]
    pref = "\r\n".join(lines)
    expected = pref.encode("utf-8") + content + "\r\n".encode("utf-8")
    print(expected)
    assert resp == expected


def test_json_response():
    data = {"message": "This is a test"}
    resp = json_response(data)
    content = json.dumps(data)
    lines = [
        "HTTP/1.1 200 OK",
        "content-type: application/json",
        f"content-length: {len(content)}",
        "",
        content,
    ]
    expected = "\r\n".join(lines)
    assert resp == expected
