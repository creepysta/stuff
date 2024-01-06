# ----------------------- Rate Limitter Algorithms -------------- #
import time
from collections import defaultdict

from litehttp import HTTP_400, HTTP_429, Loop, Request, Server, text_response


class _TokenBucket:
    def __init__(self, tokens, time_unit):
        """
        time_unit: (int): is considered number of seconds
        token:     (int): is the number of tokens to be added each `time_unit`
        """
        self.tokens = tokens
        self.time_unit = time_unit
        self.bucket = []
        self.last_refill_time = 0

    def refill_bucket(self):
        current_time = time.time()
        elapsed_time = current_time - self.last_refill_time
        tokens_to_add = int(elapsed_time / self.time_unit)
        rem = self.tokens - len(self.bucket)
        to_add = [None] * min(rem, tokens_to_add)
        self.bucket.extend(to_add)
        print(f"{rem=}, {tokens_to_add=}, {to_add=}, {self.bucket=}")
        self.last_refill_time = current_time

    def get_token(self):
        if not self.bucket:
            self.refill_bucket()

        if self.bucket:
            self.bucket.pop(0)
            return True

        return False

    def __repr__(self):
        args = ",".join([f"{k}={v!r}" for k, v in vars(self).items()])
        return f"{type(self).__name__}({args})"


class TokenBucket:
    def __init__(self, tokens, time_unit):
        self.tokens = tokens
        self.time_unit = time_unit
        self.buckets = defaultdict(lambda: _TokenBucket(self.tokens, self.time_unit))

    def get_token(self, key):
        return self.buckets[key].get_token()

    def __repr__(self):
        args = ",".join([f"{k}={v!r}" for k, v in vars(self).items()])
        return f"{type(self).__name__}({args})"


class _FixedWindowCounter:
    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.curr_window = []
        self.last_upd = time.time()

    def can_make_req(self):
        return len(self.curr_window) <= self.limit

    def reset_window(self):
        now = time.time()
        if now - self.last_upd > self.window:
            self.curr_window = []

    def make_req(self) -> bool:
        self.reset_window()
        if self.can_make_req():
            self.curr_window.append(None)
            return True

        return False

    def __repr__(self):
        args = ",".join([f"{k}={v!r}" for k, v in vars(self).items()])
        return f"{type(self).__name__}({args})"


class FixedWindowCounter:
    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.buckets = defaultdict(lambda: _FixedWindowCounter(limit, window))

    def can_make_req(self, key):
        return self.buckets[key].can_make_req()

    def __repr__(self):
        args = ",".join([f"{k}={v!r}" for k, v in vars(self).items()])
        return f"{type(self).__name__}({args})"


# ----------------------------------------------------------------#

tb = TokenBucket(10, 1)
wc = FixedWindowCounter(10, 1)


def handle_root(req: Request):
    if req.method == "GET":
        return text_response(text="Howdy!")

    return text_response(status=HTTP_400)


def handle_unlim(req: Request):
    if req.method == "GET":
        return text_response(text="Unlimited! Let's Go!")

    return text_response(status=HTTP_400)


def handle_lim(req: Request):
    if req.method == "GET":
        if not tb.get_token(req.remote_addr[0]):
            return text_response(status=HTTP_429)

        return text_response(text="Limited, don't over use me!")

    return text_response(status=HTTP_400)


handlers = [
    (lambda x: x == "/", handle_root),
    (lambda x: x == "/unlimited", handle_unlim),
    (lambda x: x == "/limited", handle_lim),
]

server = Server(loop=Loop(), handlers=handlers)
server.run(port=8080)
