# -*- coding: utf-8 -*-

import validino
from validino import util

def test_ContextValidator():
    def value_is_in_context(value, context):
        if not value in context.values():
            raise validino.Invalid
        return True

    wrapped_viic = util.ContextValidator(value_is_in_context)

    assert isinstance(wrapped_viic, util.ContextValidator)
    context = dict(bar='foo')
    assert wrapped_viic('foo', context)

    foo_schema = validino.Schema(dict(flibble=wrapped_viic))
    data = dict(flibble='foo')
    context = dict(flibble='foo')
    result = foo_schema(data, context)
    assert result
