# -*- coding: utf-8 -*-


import validino as V
from util import assert_invalid


def test_ip():
    v = V.ip('donkey')
    i = '192.168.1.243'
    assert v(i) == i
    assert_invalid(lambda: v("this is not an ip"), {None: 'donkey'})


def test_url():
    v = V.url()
    u = 'http://www.wnyc.org/'
    assert v(u) == u
    v = V.url(True)
    assert v(u) == u
