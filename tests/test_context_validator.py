# -*- coding: utf-8 -*-

import py

import validino as V
from validino import util

def test_ContextValidator():
    def _is_in_database(value, context):
        if not value in context['database']:
            raise V.Invalid
        return True

    is_in_database = util.ContextValidator(_is_in_database)

    assert isinstance(is_in_database, util.ContextValidator)
    context = dict(database=['foo', 'bar', 'bum'])
    assert is_in_database('foo', context)

    with py.test.raises(V.Invalid) as e:
        assert is_in_database('flooble', context)

    foo_schema = V.Schema(dict(flibble=is_in_database))
    data = dict(flibble='foo')
    context = dict(database=['foo', 'bar', 'bum'])
    result = foo_schema(data, context)
    assert result

    with py.test.raises(V.Invalid) as e:
        data = dict(flibble='flansit')
        context = dict(database=['foo', 'bar', 'bum'])
        result = foo_schema(data, context)
