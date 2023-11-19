import pytest
from songsender.app import search_path_match, Request, handle_root, text_response


@pytest.fixture
def get_request():
    data = (
        "GET /search?name=hey+there+delilah HTTP/1.1\r\n"
        "Host: localhost:5005\r\n"
        "User-Agent: curl/7.88.1\r\n"
        "Accept: */*\r\n"
    )
    return Request(data)


@pytest.fixture
def get_root_request():
    data = (
        "GET / HTTP/1.1\r\n"
        "Host: localhost:5005\r\n"
        "User-Agent: curl/7.88.1\r\n"
        "Accept: */*\r\n"
    )
    return Request(data)


def test_handle_root(get_root_request):
    res = handle_root(get_root_request)
    assert res == text_response("Howdy!")


@pytest.mark.parametrize(
    "pattern, expected",
    [
        ("/search", True),
        ("/search/?name", False),
        ("/search/name", False),
    ],
)
def test_search_path_match(pattern, expected):
    assert search_path_match(pattern) is expected
