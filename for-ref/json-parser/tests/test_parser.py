# Test files are taken from here
# http://www.json.org/JSON_checker/test.zip
# https://www.dropbox.com/s/vthtr4897fkuhw8/tests.zip?dl=0

from pathlib import Path
from json_parser import json_p
import pytest


def basics():
    asset_path = Path(__file__).parent / "assets"
    basics = asset_path / "basics"
    for step in range(1, 5):
        path = basics / f"step{step}"
        for file in path.glob("*.json"):
            content = file.read_text()
            name = file.name
            if "invalid" in name:
                yield name, content, 1
            elif "valid" in name:
                yield name, content, 0

basics_params = [(name, content, ec) for name, content, ec in basics()]


@pytest.mark.parametrize("data,expected", [
    ("null", (None, '')),
    ("true", (True, '')),
    ("false", (False, '')),
    ("123123", (123123, '')),
    ('"hello, world!"', ("hello, world!", '')),
    ('""', ("", '')),
    ("[]", ([], '')),
    ("{}", ({}, '')),
    ('[123, "foo bar", [true, null, [false,], 231], "baz", []]', ([123, "foo bar", [True, None, [False,], 231,], "baz", [],], '')),
    ('{"foo": ["bar", ["baz"], {"hello": "world"}, {},], "empty": {}, "NullableKey": null, "true": false, "key": "value"}', ({"foo": ["bar", ["baz"], {"hello": "world"}, {},], "empty": {}, "NullableKey": None, "true": False, "key": "value"}, '')),
])
def test_basics(data, expected):
    got = json_p()(data)
    assert got == expected


# @pytest.mark.parametrize("name,content,expected_ec", basics_params)
# def test_files(name, content, expected_ec):
#     for name, content, expected_ec in basics():
#         got = json_p()(content)
#         if expected_ec == 1:
#             assert got is None, f"{name=}, expected to error out"
#         elif expected_ec == 0:
#             assert got is not None, f"{name=} expected to pass"

