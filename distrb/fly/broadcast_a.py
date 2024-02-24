#!/usr/bin/env python3
from utils import Msg, serve

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


serve(Broadcast)
