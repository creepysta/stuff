#!/usr/bin/env python3
import json

from utils import Msg, Node, read, send, serve


class Broadcast(Msg):
    @property
    def topology(self):
        return self.body.get("topology")

    def reply(self, my_id: str, messages=None):
        rv = super().reply(my_id)
        match self.type:
            case "broadcast":
                del rv["body"]["message"]
                return rv
            case "topology":
                del rv["body"]["topology"]
                return rv
            case "read":
                rv["body"]["messages"] = messages
                return rv
            case err:
                raise NotImplementedError(f"type: {err!r} not implemented!")


def handle(node: Node):
    got = read()
    msg = Broadcast(json.loads(got))

    match msg.type:
        case "broadcast":
            return node.broadcast(msg)
        case "topology":
            node.topology = msg.topology
            reply = msg.reply(node.node_id)
            send(json.dumps(reply))
            return
        case "read":
            msg = msg.reply(node.node_id, node.all_received)
            send(json.dumps(msg))
            return


serve(handle_fn=handle)



"""
maelstrom test -w broadcast --bin ./broadcast_a.py \
    --node-count 1 \
    --time-limit 20 \
    --rate 10
"""
