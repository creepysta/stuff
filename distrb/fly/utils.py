import json
import sys
from copy import deepcopy
from typing import Callable, Type


def send(msg: str):
    sys.stdout.write(msg.strip("\n") + "\n")
    sys.stdout.flush()


def log(msg: str):
    sys.stderr.write(msg)
    sys.stderr.flush()


class Msg:
    def __init__(self, msg: dict) -> None:
        self._msg = msg

    @property
    def body(self):
        return self.message.get("body", {})

    @property
    def src(self):
        return self.message.get("src")

    @property
    def dest(self):
        return self.message.get("dest")

    @property
    def type(self):
        return self.body.get("type")

    @property
    def msg_id(self):
        return self.body.get("msg_id")

    @property
    def message(self):
        return deepcopy(self._msg)

    @property
    def reply_type(self):
        if self.type and not self.type.endswith("_ok"):
            return self.type + "_ok"

    def reply(self, my_id: str):
        rv = self.message
        rv["src"] = my_id or self.src
        rv["dest"] = self.src
        rv["body"]["in_reply_to"] = self.msg_id
        rv["body"]["type"] = self.reply_type
        return rv

    def send_to(self, my_id: str, to_id: str):
        rv = self.message
        rv["src"] = my_id
        rv["dest"] = to_id
        return rv


class Init(Msg):
    @property
    def node_id(self):
        return self.body.get("node_id")

    @property
    def node_ids(self):
        return self.body.get("node_ids")


class Node:
    def __init__(self, init_msg: Init) -> None:
        self._data = init_msg
        self._alr_related: dict = {}

    @property
    def node_id(self):
        return self._data.node_id

    @property
    def connections(self):
        return self._data.node_ids

    def handle_msg(self, msg: Msg):
        if msg.type and msg.type.endswith("_ok"):
            return None

        reply = msg.reply(self.node_id)
        return reply

    def send_to(self, msg: Msg, to_id: str):
        reply = msg.send_to(self.node_id, to_id)
        return reply


def handler(msg_type: Type[Msg], node: Node) -> dict | None:
    got = input()
    msg = msg_type(json.loads(got))
    reply = node.handle_msg(msg)
    log(f"GOT MESSAGE: {msg} | {reply=}")
    return reply


def serve(
    msg_type: Type[Msg] | None = None, handle_fn: Callable[[Node], None] | None = None
) -> None:
    assert msg_type or handle_fn and not all([msg_type, handle_fn])

    got = input()
    msg = Init(json.loads(got))
    assert msg.type == "init"
    node = Node(msg)
    reply = node.handle_msg(msg)
    if reply:
        send(json.dumps(reply))

    while True:
        if handle_fn:
            handle_fn(node)
            continue

        rv = handler(msg_type, node)  # type: ignore
        if rv:
            send(json.dumps(rv))
