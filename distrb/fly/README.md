# Distributed challenges

Challenges from: https://fly.io/dist-sys/

## Setup

Install utils
```bash
$ sudo apt install software-properties-common
$ sudo add-apt-repository universe && sudo apt update  # required for graphviz
$ sudo apt-get install openjdk-17-jdk graphviz gnuplot
```

Install `maelstrom`
```bash
$ curl -LO https://github.com/jepsen-io/maelstrom/releases/download/v0.2.3/maelstrom.tar.bz2
$ tar -xvf maelstrom.tar.bz2
$ export PATH=$(pwd)/maelstrom/:$PATH
```

