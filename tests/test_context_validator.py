# -*- coding: utf-8 -*-

import py

import validino as V
from validino import util

def test_ContextValidator():
    def _is_in_database(msg="it's not in the database"):
        "Checks if something is in the database"
        def f(value, context):
            if not value in context['database']:
                raise V.Invalid(msg)
            return True
        return f

    is_in_database = util.context_validator(_is_in_database)

    assert is_in_database.__name__ == _is_in_database.__name__
    assert is_in_database.__doc__ == _is_in_database.__doc__
    v = is_in_database()
    assert isinstance(v, util.ContextValidator)

    context = dict(database=['foo', 'bar', 'bum'])
    assert is_in_database()('foo', context)

    with py.test.raises(V.Invalid) as e:
        assert is_in_database()('flooble', context)
    errors = e.value.unpack_errors()
    assert errors == {None: "it's not in the database"}

    with py.test.raises(V.Invalid) as e:
        assert is_in_database("ting nah in db")('flooble', context)
    errors = e.value.unpack_errors()
    assert errors == {None: "ting nah in db"}

    foo_schema = V.Schema(dict(flibble=is_in_database()))
    data = dict(flibble='foo')
    context = dict(database=['foo', 'bar', 'bum'])
    result = foo_schema(data, context)
    assert result == dict(flibble=True)

    with py.test.raises(V.Invalid) as e:
        data = dict(flibble='flansit')
        context = dict(database=['foo', 'bar', 'bum'])
        result = foo_schema(data, context)
    errors = e.value.unpack_errors()
    assert errors == {
        None: "Problems were found in the submitted data.",
        'flibble': "it's not in the database"}
