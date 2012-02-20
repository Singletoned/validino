# -*- coding: utf-8 -*-

import uuid, datetime, functools

import py

import validino as V
from validino.util import partial
from util import assert_invalid


def is_in_context():
    @functools.wraps(is_in_context)
    def f(value, context):
        if not value in context:
            raise V.Invalid()
        return value
    return f


def test_Invalid():
    error = V.Invalid("foo")
    assert error.errors == {None: "foo"}
    error = V.Invalid(dict(foo="bar"))
    assert error.errors == {'foo': "bar"}


def test_Invalid_unpack_errors():
    error = V.Invalid(
        dict(
            foo=V.Invalid(
                dict(
                    bar="flim"))))
    expected = {'foo': {'bar':"flim"}}
    result = error.unpack_errors()
    assert expected == result

    error = V.Invalid(
        dict(
            foo=dict(
                bar="flim")))
    expected = {'foo': {'bar':"flim"}}
    result = error.unpack_errors()
    assert expected == result

    error = V.Invalid(
        V.Invalid(
            dict(
                foo="bar")))
    expected = {'foo': "bar"}
    result = error.unpack_errors()
    assert expected == result


def test_Schema_errors():
    schema = V.Schema(
        dict(
            foo=V.is_integer(msg="number, not word, idiot!")))
    data = dict(
        foo="one")
    expected = {
        'foo': "number, not word, idiot!",
        None: "Problems were found in the submitted data."}
    with py.test.raises(V.Invalid) as e:
        schema(data)
    result = e.value.errors
    assert expected == result


def test_nested_schema():
    nested_validators = dict(
        foo=V.to_unicode(),
        bar=V.nested(
            flim=V.to_unicode(),
            flam=V.to_unicode()))
    schema = V.Schema(nested_validators)
    data = dict(
        foo="Foo",
        bar=dict(
            flim="Flim",
            flam="Flam"))
    assert schema(data) == data


def test_nested():
    data = dict(
        flim="Flim",
        flam="Flam",
        bubble="Bubble")
    expected = dict(
        flim="Flim",
        flam="Flam")
    validator = V.nested(
        flim=V.to_unicode(),
        flam=V.to_unicode())
    assert validator(data) == expected
    assert validator.__name__ == "nested"

    validator = V.nested(
        flim=V.to_unicode(),
        flam=V.all_of(
            V.to_unicode(),
            is_in_context()))
    assert validator(data, context=dict(Flam=1)) == expected


def test_nested_missing():
    data = dict(
        flim="Flim")
    validator = V.nested(
        flim=(
            V.to_unicode(),
            V.not_empty()),
        flam=V.to_unicode())
    with py.test.raises(V.Invalid) as e:
        validator(data)
    errors = e.value.unpack_errors()
    assert errors == dict(flam="key 'flam' is missing")

    with py.test.raises(V.Invalid) as e:
        validator(None)
    errors = e.value.unpack_errors()
    assert errors == dict(
        flam="key 'flam' is missing",
        flim="key 'flim' is missing")

    validator = V.nested(
        flim=V.to_unicode(),
        flam=V.all_of(
            V.to_unicode(),
            is_in_context()))

    with py.test.raises(V.Invalid) as e:
        validator(data)
    errors = e.value.unpack_errors()
    assert errors == dict(flam="key 'flam' is missing")


def test_nested_with_bad_data():
    validator = V.nested(
        flam=V.to_unicode(),
        flim=V.is_integer())
    data = dict(
        flim="Flim",
        flam="Flam")
    with py.test.raises(V.Invalid) as e:
        validator(data)
    errors = e.value.unpack_errors()
    assert errors['flim'] == "not an integer"

    validator = V.nested(
        foo=V.nested(
            flam=V.to_unicode(),
            flim=V.is_integer()))
    data = dict(
            foo=dict(
                flim="Flim",
                flam="Flam"))
    with py.test.raises(V.Invalid) as e:
        validator(data)
    errors = e.value.unpack_errors()
    assert errors['foo']['flim'] == "not an integer"


def test_nested_many():
    validator = V.nested_many(
        V.to_integer())
    data = dict(
        a="1",
        b="2",
        c=3.0)
    expected = dict(
        a=1,
        b=2,
        c=3)
    result = validator(data)
    assert result == expected
    assert validator.__name__ == "nested_many"

    validator = V.nested_many(
        is_in_context())
    data = dict(
        a="flibble",
        b="flamble",
        c="flooble")
    expected = dict(
        a="flibble",
        b="flamble",
        c="flooble")
    result = validator(data, context=['flibble', 'flamble', 'flooble'])
    assert result == expected


def test_nested_many_fail():
    validator = V.nested_many(
        V.is_integer())
    data = dict(
        a=1,
        b="two",
        c=3)

    with py.test.raises(V.Invalid) as e:
        result = validator(data)
    errors = e.value.unpack_errors()
    assert errors['b'] == "not an integer"

    with py.test.raises(V.Invalid) as e:
        result = validator(None)
    errors = e.value.unpack_errors()
    assert errors == {None: "No data found"}


def test_nested_many_fail_nested_errors():
    schema = V.Schema(
        dict(
            foo=V.nested_many(
                V.is_integer())))
    data = dict(
        foo=dict(
            a=1,
            b="two",
            c=3))
    with py.test.raises(V.Invalid) as e:
        result = schema(data)
    errors = e.value.unpack_errors()
    expected = {
        'foo': {'b': "not an integer"},
        None: "Problems were found in the submitted data."}
    assert expected == errors


def test_only_one_of():
    v = V.only_one_of(msg="Please only choose one value")
    assert v.__name__ == "only_one_of"
    assert v((0, 1)) == (0, 1)
    assert v((1, False, None, [])) == (1, False, None, [])
    with py.test.raises(V.Invalid) as e:
        v((1, False, None, True))
    assert e.value.unpack_errors() == {None: "Please only choose one value"}
    schema = V.Schema({
        'field1': (V.to_integer()),
        'field2': (V.to_integer()),
        ('field1', 'field2'):
            V.only_one_of(
                msg="Please only choose one value",
                field='field1')})
    assert schema(dict(field1="0", field2="1")) == dict(field1=0, field2=1)
    with py.test.raises(V.Invalid) as e:
        schema(dict(field1=True, field2=1))

    errors = e.value.unpack_errors()
    expected = {
        None: "Problems were found in the submitted data.",
        "field1": "Please only choose one value"}
    assert expected == errors


def test_to_boolean():
    validator = V.to_boolean()
    assert validator.__name__ == "to_boolean"
    def do_test(v, t_or_f):
        assert validator(v) == t_or_f
    true_values = [True, 'True', 'False', 'true', 'None', 1, object(), [False], 'f', 'no']
    false_values = [False, '', [], {}, 0, None]
    for v in true_values:
        yield do_test, v, True
    for v in false_values:
        yield do_test, v, False


def test_to_boolean_fuzzy():
    validator = V.to_boolean(fuzzy=True)
    def do_test(v, t_or_f):
        assert validator(v) == t_or_f
    true_values = [True, 'True', 'true', 'None', 1, object(), [False], 't', 'y', 'yes']
    false_values = [False, '', [], {}, 0, None, 'False', 'n', 'NO']
    for v in true_values:
        yield do_test, v, True
    for v in false_values:
        yield do_test, v, False


def test_is_scalar():
    msg = 'sc'
    v = V.is_scalar(msg=msg)
    assert v.__name__ == "is_scalar"
    assert v(40) == 40
    assert_invalid(
        lambda: v([40]),
        {None: msg})


def test_is_list():
    msg = "list"
    v = V.is_list(msg=msg)
    assert v.__name__ == "is_list"
    assert v([40]) == [40]
    assert_invalid(
        lambda: v(40),
        {None: msg})


def test_to_scalar():
    v = V.to_scalar()
    assert v.__name__ == "to_scalar"
    assert v([40]) == 40
    assert v(40) == 40
    assert v(range(40)) == 0


def test_to_list():
    v = V.to_list()
    assert v.__name__ == "to_list"
    assert v(['a', 'b']) == ['a', 'b']
    assert v('a') == ['a']


def test_clamp():
    msg = 'You are a pear'
    v = V.clamp(min=30, msg=msg)
    assert v.__name__ == "clamp"
    assert v(50) == 50
    assert_invalid(
        lambda: v(20),
        {None: msg})

    v = V.clamp(max=100, msg=dict(min='haha', max='kong'))
    assert v(40) == 40
    assert_invalid(
        lambda: v(120),
        {None: 'kong'})

    v = V.clamp(max=100, msg=dict(min='haha'))
    assert_invalid(
        lambda: v(120),
        {None: 'value above maximum'})


def test_clamp_length():
    msg = 'You are a pear'
    v = V.clamp_length(min=3, msg=msg)
    assert v.__name__ == "clamp_length"
    assert v('500') == '500'
    assert_invalid(
        lambda: v('eh'),
        {None: msg})
    v = V.clamp_length(max=10, msg=dict(minlen='haha', maxlen='kong'))
    assert v('40') == '40'
    assert_invalid(
        lambda: v('I told you that Ronald would eat it when you were in the bathroom'),
        {None: 'kong'})

    msg = "Enter less than %(max)s.  You entered %(length)s."
    v = V.clamp_length(max=30, msg=msg)
    with py.test.raises(V.Invalid) as e:
        v("*"*50)
    errors = e.value.unpack_errors()
    expected = {None: "Enter less than 30.  You entered 50."}
    assert errors == expected

def test_check():
    d = dict(x=5, y=100)
    def add_z(val, context=None):
        val['z'] = 300
    def len_d(v2, size, context=None):
        if len(v2) != size:
            raise V.Invalid("wrong size")
    d2 = V.check(add_z, partial(len_d, size=3))(d)
    assert d2 is d
    assert d['z'] == 300

    d = dict(x=5, y=100)
    validator = V.check(
        is_in_context(),
        add_z,
        partial(len_d, size=3))
    assert validator.__name__ == "check"
    result = validator(d, context=[dict(x=5, y=100)])
    assert result is d
    assert d['z'] == 300


def test_default():
    v = V.default("pong")
    assert v(None) == 'pong'
    assert v.__name__ == "default"


def test_dict_nest():
    d = {
        'robots.bob.size' : 34,
        'robots.bob.color' : 'blue',
        'robots.sally.size' : 12,
        'robots.sally.color' : 'green',
        'robots.names' : ['sally', 'bob'],
        'frogs.names' : ['oswald', 'humphrey'],
        'frogs.oswald.size' : 'medium',
        'frogs.humphrey.size' : 'large',
        'x' : 33,
        'y' : 22}
    expected = dict(
        robots=dict(
            bob=dict(size=34, color='blue'),
            sally=dict(size=12, color='green'),
            names=['sally', 'bob']),
        frogs=dict(
            names=['oswald', 'humphrey'],
            oswald=dict(size='medium'),
            humphrey=dict(size='large')),
        x=33,
        y=22)
    d1 = V.dict_nest(d)
    assert d1 == expected
    assert d1['robots']['names'] == ['sally', 'bob']
    assert d1['x'] == 33
    assert d1['y'] == 22
    assert d1['frogs']['oswald'] == {'size' : 'medium'}
    d2 = V.dict_unnest(d1)
    assert d == d2
    # Test empty values
    assert V.dict_nest(dict()) == dict()
    assert V.dict_unnest(dict()) == dict()


def test_uuid():
    msg = "Please enter a uuid"
    v = V.uuid(msg=msg)
    assert v.__name__ == "uuid"
    guid = uuid.uuid5(uuid.NAMESPACE_DNS, "a test id")
    assert v(guid) == str(guid)
    assert v(str(guid)) == str(guid)
    with py.test.raises(V.Invalid) as e:
        assert v(None)
    assert e.value.unpack_errors() == {None: "Please enter a uuid"}
    with py.test.raises(V.Invalid) as e:
        assert v('hullo')
    assert e.value.unpack_errors() == {None: "Please enter a uuid"}

    v = V.uuid(msg=msg, default=True)
    assert v(None)
    assert v(False)
    assert v([])
    with py.test.raises(V.Invalid) as e:
        assert v('hullo')


def test_all_of():
    v = V.all_of(V.to_string('foo'), V.not_empty('bar'))
    assert v.__name__ == "all_of"
    assert v('bob') == 'bob'
    with py.test.raises(V.Invalid) as e:
        assert v('')
    assert e.value.unpack_errors() == {None: "bar"}

    v = V.all_of(
        is_in_context(),
        V.not_empty('bar'))
    assert v('bob', context=dict(bob=1)) == 'bob'


def test_all_of_2():
    messages = dict(to_integer='not an integer',
                  belongs='invalid choice',
                  min='too small',
                  max='too big')
    v = V.all_of(V.default(40),
                V.strip,
                V.to_integer(msg=messages),
                V.belongs(range(4, 100, 4), messages),
                V.clamp(min=20, max=50, msg=messages))
    assert v(None) == 40
    assert v('40') == 40
    assert v('44  ') == 44
    assert_invalid(
        lambda: v(' prick '),
        {None: messages['to_integer']})
    assert_invalid(
        lambda: v(' 41  '),
        {None: messages['belongs']})
    assert_invalid(
        lambda: v('96'),
        {None: messages['max']})
    assert_invalid(
        lambda: v('8'),
        {None: messages['min']})


def test_either():
    msg = "please enter an integer"
    v = V.either(V.empty(), V.to_integer(msg=msg))
    assert v.__name__ == "either"
    assert v('') == ''
    assert v('40') == 40
    assert_invalid(
        lambda: v('bonk'),
        {None: msg})

    v = V.either(
        is_in_context(),
        V.to_integer(msg=msg))
    assert v('40') == 40
    assert v('foo', context=['foo']) == 'foo'


def test_empty():
    v = V.empty(msg="scorch me")
    assert v.__name__ == "empty"
    assert v('') == ''
    assert v(None) == None
    assert_invalid(
        lambda: v("bob"),
        {None: 'scorch me'})


def test_equal():
    v = V.equal('egg', msg="not equal")
    assert v.__name__ == "equal"
    assert v('egg') == 'egg'
    assert_invalid(
        lambda: v('bob'),
        {None: 'not equal'})


def test_not_equal():
    v = V.not_equal('egg', msg='equal')
    assert v.__name__ == "not_equal"
    assert v('plop') == 'plop'
    assert_invalid(
        lambda: v('egg'),
        {None: 'equal'})


def test_is_integer():
    msg = "please enter an integer"
    v = V.is_integer(msg=msg)
    assert v.__name__ == "is_integer"
    assert v(40) == 40
    assert_invalid(
        lambda: v('whack him until he screams'),
        {None: msg})


def test_to_integer():
    msg = "please enter an integer"
    v = V.to_integer(msg=msg)
    assert v.__name__ == "to_integer"
    assert v('40') == 40
    assert_invalid(
        lambda: v('whack him until he screams'),
        {None: msg})


def test_not_empty():
    msg = "hammer my xylophone"
    v = V.not_empty(msg=msg)
    assert v.__name__ == "not_empty"
    assert v("frog") == 'frog'
    assert_invalid(
        lambda: v(''),
        {None: msg})
    assert_invalid(
        lambda: v(None),
        {None: msg})


def test_belongs():
    msg = "rinse me a robot"
    v = V.belongs('pinko widget frog lump'.split(), msg=msg)
    assert v.__name__ == "belongs"
    assert v('pinko') == 'pinko'
    assert_invalid(
        lambda: v('snot'),
        {None: msg})


def test_not_belongs():
    msg = "belittle my humbug"
    v = V.not_belongs(range(5), msg=msg)
    assert v.__name__ == "not_belongs"
    assert v('pinko') == 'pinko'
    assert_invalid(
        lambda: v(4),
        {None: msg})


def test_parse_date():
    fmt = '%m %d %Y'
    msg = 'Gargantua and Pantagruel'
    v = V.parse_date(fmt, msg)
    assert v.__name__ == "parse_date"
    dt = v('07 02 2007')
    assert dt.year == 2007
    assert dt.month == 7
    assert dt.day == 2
    assert isinstance(dt, datetime.date)


def test_parse_datetime():
    fmt = '%m %d %Y %H:%M'
    msg = 'Gargantua and Pantagruel'
    v = V.parse_datetime(fmt, msg)
    assert v.__name__ == "parse_datetime"
    dt = v('07 02 2007 12:34')
    assert dt.year == 2007
    assert dt.hour == 12
    assert dt.minute == 34
    assert isinstance(dt, datetime.datetime)


def test_parse_time():
    fmt = '%m %d %Y'
    msg = "potted shrimp"
    v = V.parse_time(fmt, msg)
    assert v.__name__ == "parse_time"
    ts = v('10 03 2007')[:3]
    assert ts == (2007, 10, 3)
    assert_invalid(
        lambda: v('tough nuggie'),
        {None: msg})


def test_regex():
    v = V.regex('shrubbery\d{3}$', 'regex')
    assert v.__name__ == "regex"
    assert v('shrubbery222') == 'shrubbery222'
    assert_invalid(
        lambda: v('buy a shrubbery333, ok?'),
        {None: 'regex'})


def test_regex_sub():
    v = V.regex_sub('shrubbery', 'potted plant')
    assert v.__name__ == "regex_sub"
    res = v('a shrubbery would be nice')
    assert res == 'a potted plant would be nice'


def test_schema_1():
    s = V.Schema(
        dict(username=(V.strip,
                       V.regex('[a-z][a-z0-9]+',
                               'invalid username'),
                       V.clamp_length(max=16,
                                      msg='username is too long'),
                       ),
             user_id=V.either(V.empty(),
                              V.all_of(V.to_integer('not an integer'),
                                        V.clamp(min=1, max=9999, msg='out of range')
                                        )
                              ),
             department=(V.strip,
                         V.belongs(['interactive', 'programming'],
                                   'department not recognized')
                         ),
             ),
        "there were errors with your submission"
        )
    data = dict(username='jsmullyan',
                user_id='1',
                department='interactive')
    newdata = s(data)
    assert data['username'] == newdata['username']
    assert int(data['user_id']) == newdata['user_id']
    assert data['department'] == newdata['department']


def test_schema_2():
    s = V.Schema(
        dict(x=(V.is_integer('intx'), V.clamp(min=5, max=100, msg='clampx')),
             y=(V.is_integer('inty'), V.clamp(min=5, max=100, msg='clampy')),
             text=V.strip),
        "schema"
        )
    def check_keys(data, context=None):
        allkeys = set(('x', 'y', 'text'))
        found = set(data.keys())
        if allkeys.difference(found):
            raise V.Invalid("incomplete data")
        if found.difference(allkeys):
            raise V.Invalid("extra data")
    v = V.all_of(V.check(check_keys), s)
    d1 = dict(x=40, y=20, text='hi there')
    assert v(d1) == d1
    d2 = dict(x=1, y=20, text='hi there')
    assert_invalid(
        lambda: v(d2),
        {None: 'schema', 'x': 'clampx'})
    d3 = dict(x=10, y=10)
    assert_invalid(
        lambda: v(d3),
        {None: 'incomplete data'})
    d4 = dict(x=10, y=10, text='ho', pingpong='lather')
    assert_invalid(
        lambda: v(d4),
        {None: 'extra data'})


def test_schema_3():
    v = V.Schema(
        dict(x=(V.is_integer('intx'), V.clamp(min=5, max=100, msg='clampx')),
             y=(V.is_integer('inty'), V.clamp(min=5, max=100, msg='clampy')),
             text=V.strip),
        {'schema.error' : 'schema',
         'schema.extra' : 'extra',
         'schema.missing' : 'missing'},
        False,
        False
        )

    d1 = dict(x=40, y=20, text='hi there')
    assert v(d1) == d1
    d2 = dict(x=1, y=20, text='hi there')
    assert_invalid(
        lambda: v(d2),
        {None: 'schema', 'x': 'clampx'})
    d3 = dict(x=10, y=10)
    assert_invalid(
        lambda: v(d3),
        {None: 'missing'})
    d4 = dict(x=10, y=10, text='ho', pingpong='lather')
    assert_invalid(
        lambda: v(d4),
        {None: 'extra'})


def test_schema_4():
    s = V.Schema(
        {
            'foo': V.is_integer(),
            'bar': V.is_integer(),
            ('foo', 'bar'): V.fields_equal(msg='flam', field=None)
        },
        msg="flibble")
    d = dict(foo=1, bar=2)
    with py.test.raises(V.Invalid) as e:
        s(d)
    errors = e.value.unpack_errors()
    assert errors == {None: 'flam'}


def test_filter_missing():
    s = V.Schema(
        dict(
            x=V.to_integer(),
            y=V.to_integer()),
        filter_extra=False)

    d1 = dict(x="1", y="2", foo="bar")
    expected = dict(x=1, y=2, foo="bar")
    assert s(d1) == expected


def test_strip():
    assert V.strip('   foo   ') == 'foo'
    assert V.strip(None) == None


def test_fields_match():
    d = dict(foo=3,
           goo=3,
           poo=56)
    v = V.fields_match('foo', 'goo')
    assert v.__name__ == "fields_match"
    assert d == v(d)
    v = V.fields_match('foo', 'poo', 'oink')
    assert_invalid(
        lambda: v(d),
        {None: 'oink'})
    # Check field=None
    v = V.fields_match('foo', 'bar', msg='flibble', field=None)
    with py.test.raises(V.Invalid) as e:
        v(dict(foo=1, bar=2))
    assert e.value.unpack_errors() == {None: 'flibble'}


def test_fields_equal():
    values = ("pong", "pong")
    v = V.fields_equal('hog')
    assert v.__name__ == "fields_equal"
    assert values == v(values)
    values = ('tim', 'worthy')
    assert_invalid(
        lambda: v(values),
        {None: 'hog'})
    s = V.Schema({
        'foo': V.to_integer(),
        ('foo', 'bar'): V.fields_equal(u"foo and bar don't match")})
    d = dict(foo='1', bar=1)
    expected = dict(foo=1, bar=1)
    assert s(d) == expected
    # Check field=None
    s = V.Schema({
        'foo': V.to_integer(),
        ('foo', 'bar'): V.fields_equal(u"foo and bar don't match", field=None)})
    d = dict(foo='1', bar=2)
    with py.test.raises(V.Invalid) as e:
        s(d)
    errors = e.value.unpack_errors()
    assert errors == {None: u"foo and bar don't match"}


def test_excursion():
    x = 'gadzooks@wonko.com'

    v = V.excursion(
        lambda x, context: x.split('@')[0],
        V.belongs(['gadzooks', 'willy'], msg='pancreatic'))
    assert v.__name__ == "excursion"
    assert x == v(x)
    assert_invalid(
        lambda: v('hieratic impulses'),
        {None: 'pancreatic'})

    v = V.excursion(lambda x, context: x.add('foo'))
    data = set(['bar'])
    result = v(data)
    assert result == set(['bar'])
    assert data == set(['bar', 'foo'])


def test_confirm_type():
    v = V.confirm_type((int, float), 'not a number')
    assert v.__name__ == "confirm_type"
    assert v(45) == 45
    assert_invalid(
        lambda: v('45'),
        {None: 'not a number'})


def test_translate():
    v = V.translate(dict(y=True, f=False),  'dong')
    assert v.__name__ == "translate"
    assert v('y') == True
    assert_invalid(
        lambda: v('pod'),
        {None: 'dong'})


def test_to_unicode():
    v = V.to_unicode(msg='cats')
    assert v.__name__ == "to_unicode"
    assert v(u"brisbane") == u"brisbane"
    assert v(1) == u"1"
    for t in [
        u'parrots', 'parrots', 1, object(), None,
        ]:
        assert isinstance(v(t), unicode)
    u = u"\N{GREEK CAPITAL LETTER OMEGA} my gawd"
    s = u.encode('utf-8')
    assert v(s) == u
    with py.test.raises(V.Invalid) as e:
        v = V.to_unicode(encoding='ascii', msg='cats')
        v(s)
    assert e.value.unpack_errors() == {None: "cats"}


def test_is_unicode():
    v = V.is_unicode(msg="This is not unicode")
    assert v.__name__ == "is_unicode"
    assert v(u"parrot") == u"parrot"
    assert isinstance(v(u"parrot"), unicode)
    with py.test.raises(V.Invalid) as e:
        v("parrot")
    assert e.value.unpack_errors() == {None: "This is not unicode"}
    with py.test.raises(V.Invalid) as e:
        v(1)
    assert e.value.unpack_errors() == {None: "This is not unicode"}


def test_to_string():
    v = V.to_string(msg="cats")
    assert v.__name__ == "to_string"
    assert v('parrots') == 'parrots'
    for t in [
        u'parrots', 'parrots', 1, object(), None,
        ]:
        assert isinstance(v(t), str)
    u = u"\N{GREEK CAPITAL LETTER OMEGA} my gawd"
    s = u.encode('utf-8')
    assert v(u) == s
    with py.test.raises(V.Invalid) as e:
        v = V.to_string(encoding='ascii', msg='cats')
        v(u)
    assert e.value.unpack_errors() == {None: "cats"}


def test_is_string():
    v = V.is_string(msg="This is not a string")
    assert v.__name__ == "is_string"
    assert v("parrot") == "parrot"
    assert isinstance(v("parrot"), str)
    with py.test.raises(V.Invalid) as e:
        v(u"parrot")
    assert e.value.unpack_errors() == {None: "This is not a string"}
    with py.test.raises(V.Invalid) as e:
        v(1)
    assert e.value.unpack_errors() == {None: "This is not a string"}


def test_unpack_1():
    e = V.Invalid({'ding' : [V.Invalid('pod')],
                 'dong' : [V.Invalid('piddle')]})
    res = e.unpack_errors()
    assert res == {'ding' : 'pod', 'dong' : 'piddle'}
    e2 = V.Invalid({'' : [e]})
    res2 = e.unpack_errors()
    assert res == res2


def test_unpack_2():
    "Empty string keys should be collapsed"
    e = V.Invalid({'ding' : [V.Invalid('pod')],
                 'dong' : [V.Invalid('piddle')]})

    e2 = V.Invalid({'' : [e]})
    e3 = V.Invalid({'' : [e2]})
    r1 = e.unpack_errors()
    r2 = e2.unpack_errors()
    r3 = e3.unpack_errors()
    assert r1 == r3


def test_unpack_3():
    errors = dict(frog="My peachy frog hurts",
                dog="My dog has warts up and down his spine",
                insect="I would characterize this insect as flawed")
    e = V.Invalid(errors)

    u = e.unpack_errors()
    assert set(u) == set(('frog', 'dog', 'insect'))
    for v in u.itervalues():
        assert isinstance(v, basestring)

    e2 = V.Invalid(dict(frog='squished'))
    u2 = e2.unpack_errors()
    assert u2 == dict(frog='squished')

    e3 = V.Invalid(errors,
                 {'' : e2})
    u3 = e3.unpack_errors()
    assert set(u3) == set(('frog', 'dog', 'insect'))
    for k, v in u3.iteritems():
        assert isinstance(v, basestring)


def test_errors():
    schema = V.Schema(
        dict(
            foo=(
                V.to_unicode(msg="foo can't be converted"),
                V.not_empty(msg="foo is empty")),
            bar=(
                V.is_integer(msg="bar isn't an integer"),
                V.not_empty(msg="bar is empty"))),
        msg="Check the errors and try again.  Moron.")

    with py.test.raises(V.Invalid) as e:
        data = schema(dict(foo=None, bar=None))

    expected = {
        None: 'Check the errors and try again.  Moron.',
        'bar': "bar isn't an integer",
        'foo': 'foo is empty'}

    result = e.value.unpack_errors()
    assert result == expected
