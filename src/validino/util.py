# -*- coding: utf-8 -*-

try:
    from functools import partial
except ImportError:
    def partial(func, *args, **kw):
        def inner(*_args, **_kw):
            d = kw.copy()
            d.update(_kw)
            return func(*(args + _args), **d)
        return inner

class ContextValidator(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, value, context):
        return self.func(value, context)
