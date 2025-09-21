import json
import sys
from copy import deepcopy
from typing import Callable, Type


def read():
    return input()


def send(msg: str):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


def log(msg: str):
    sys.stderr.write(msg + "\n")
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

    @property
    def message_content(self):
        return self.body.get("message")

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
        self._topology: dict[str, list] = {}
        self._relayed: dict[int, bool] = {}
        self._received: list = []

    @property
    def node_id(self):
        return self._data.node_id

    @property
    def all_nodes(self):
        return self._data.node_ids

    @property
    def connections(self):
        if self.topology:
            return self.topology[self.node_id]

        return self.all_nodes

    @property
    def topology(self):
        return self._topology

    @topology.setter
    def topology(self, topo: dict):
        self._topology = topo

    def reply(self, msg: Msg):
        if msg.type and msg.type.endswith("_ok"):
            return None

        reply = msg.reply(self.node_id)
        return reply

    def send_to(self, msg: Msg, to_id: str):
        reply = msg.send_to(self.node_id, to_id)
        return reply

    @property
    def all_received(self):
        return self._received

    def broadcast(self, msg: Msg) -> None:
        reply = self.reply(msg)
        send(json.dumps(reply))

        log(f"[{self.node_id=}] {msg._msg=} | {self._relayed=} | {self.connections=}")

        # this was put in so that no loop gets created for a single broadcast
        # message content is considered instead of msg_id
        if self._relayed.get(msg.message_content):
            return

        self._received.append(msg.message_content)
        for node in self.connections:
            if node in [msg.src, self.node_id]:
                continue

            message = self.send_to(msg, node)
            send(json.dumps(message))

        self._relayed[msg.message_content] = True

    def gossip(self):
        for node in self.connections:
            pass



def handler(msg_type: Type[Msg], node: Node) -> dict | None:
    got = read()
    msg = msg_type(json.loads(got))
    reply = node.reply(msg)
    log(f"GOT MESSAGE: {msg} | {reply=}")
    return reply


def serve(
    msg_type: Type[Msg] | None = None, handle_fn: Callable[[Node], None] | None = None
) -> None:
    assert msg_type or handle_fn and not all([msg_type, handle_fn])

    got = read()
    msg = Init(json.loads(got))
    assert msg.type == "init"
    node = Node(msg)
    reply = node.reply(msg)
    if reply:
        send(json.dumps(reply))

    while True:
        if handle_fn:
            handle_fn(node)
            continue

        rv = handler(msg_type, node)  # type: ignore
        if rv:
            send(json.dumps(rv))
