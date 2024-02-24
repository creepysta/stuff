#!/usr/bin/env python3
import json

from utils import Msg, Node, log, send, serve

got = []


class Broadcast(Msg):
    @property
    def message_val(self):
        return self.body.get("message")

    def reply(self, my_id):
        rv = super().reply(my_id)
        match self.type:
            case "broadcast":
                del rv["body"]["message"]
                got.append(self.message_val)
                return rv
            case "topology":
                del rv["body"]["topology"]
                return rv
            case "read":
                rv["body"]["messages"] = got
                return rv
            case err:
                raise NotImplementedError(f"type: {err!r} not implemented!")


def handle(node: Node):
    got = input()
    msg = Broadcast(json.loads(got))
    for kid in node.connections:
        reply = node.send_to(msg, kid)
        ser = json.dumps(reply)
        send(ser)


serve(handle_fn=handle)
