# -*- coding: utf-8 -*-

from functools import wraps

try:
    from functools import partial
except ImportError:
    def partial(func, *args, **kw):
        def inner(*_args, **_kw):
            d = kw.copy()
            d.update(_kw)
            return func(*(args + _args), **d)
        return inner

def context_validator(func_maker):
    @wraps(func_maker)
    def inner(*args, **kwargs):
        f = func_maker(*args, **kwargs)
        cm = ContextValidator(f)
        return cm
    return inner

class ContextValidator(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, value, context=None):
        return self.func(value, context)
