# Best Engineering Interview Question Ever

Taking a stab at it

Ref - https://quuxplusone.github.io/blog/2022/01/06/memcached-interview/

```console
$ curl -O https://memcached.org/files/memcached-1.4.15.tar.gz
$ tar zxvf memcached-1.4.15.tar.gz
$ cd memcached-1.4.15
$ ./configure
$ make
```

Required before running `./configure`
```console
$ sudo apt install libevent-dev
```

> Note: Comment out `-Werror` in the Makefile to build with deprecation warnings about `signal`
