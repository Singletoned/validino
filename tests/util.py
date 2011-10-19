# -*- coding: utf-8 -*-

import py

import validino as V

def assert_invalid(f, expected):
    with py.test.raises(V.Invalid) as e:
        f()
    errors = e.value.unpack_errors()
    assert errors == expected
