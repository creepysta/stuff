#!/usr/bin/env python3
from uuid import uuid4

from utils import Msg, serve


class Generate(Msg):
    def reply(self, my_id):
        rv = super().reply(my_id)
        rv["body"]["id"] = uuid4().hex
        return rv


serve(Generate)


"""
maelstrom test -w unique-ids --bin ./generate.py \
    --time-limit 30 \
    --rate 1000 \
    --node-count 3 \
    --availability total \
    --nemesis partition
"""
