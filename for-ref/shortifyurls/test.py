import pytest


@pytest.mark.parametrize(
    "pattern, expected",
    [
        ("/echo/<msg: str>", {"msg": "str"}),
        ("/echo/<msg: str>/foo/<msg2: str>", {"msg": "str", "msg2": "str"}),
        (
            "/echo/<msg: str>/<msg1: int>/<msg2: str>",
            {"msg": "str", "msg1": "int", "msg2": "str"},
        ),
    ],
)
def test_binding(pattern, expected):
    import re

    res = re.finditer(r"/<(\w+): (\w+)>/?", pattern)
    print(f"{list(res)=}")
    res = re.findall(r"/<(\w+): (\w+)>/?", pattern)
    print(f"{res=}")
    assert dict(res) == expected
