#!/usr/bin/env python3
from utils import Msg, serve


class Echo(Msg):
    pass


serve(Echo)
