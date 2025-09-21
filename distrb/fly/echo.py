#!/usr/bin/env python3
from utils import Msg, serve


class Echo(Msg):
    pass


serve(Echo)


"""
maelstrom test -w echo --bin ./echo.py --node-count 1 --time-limit 10
"""
