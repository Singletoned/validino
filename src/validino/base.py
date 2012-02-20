# -*- coding: utf-8 -*-

import datetime
import re
import time
from uuid import UUID, uuid1
import types
import copy
import functools

from validino import util

__all__ = [
    'Invalid',
    'check',
    'clamp',
    'clamp_length',
    'confirm_type',
    'default',
    'dict_nest',
    'dict_unnest',
    'all_of',
    'either',
    'empty',
    'equal',
    'excursion',
    'fields_equal',
    'fields_match',
    'is_list',
    'is_scalar',
    'not_equal',
    'uuid',
    'is_integer',
    'to_integer',
    'to_boolean',
    'not_empty',
    'not_belongs',
    'belongs',
    'parse_date',
    'parse_datetime',
    'parse_time',
    'regex',
    'regex_sub',
    'Schema',
    'strip',
    'to_list',
    'to_scalar',
    'is_unicode',
    'to_unicode',
    'is_string',
    'to_string',
    'translate',
    'nested',
    'nested_many',
    'only_one_of']


_default = object()

def _add_error_message(d, k, msg):
    """
    internal utility for adding an error message to a
    dictionary of messages.
    """
    d.setdefault(k, [])
    if msg not in d[k]:
        d[k].append(msg)


def _msg(msg, key, default, msg_context=None):
    """
    internal message-handling routine.
    """
    msg_context = msg_context or dict()
    try:
        msg = msg.get(key, default)
    except AttributeError:
        if msg is None:
            msg = default
        else:
            msg = msg
    return msg % msg_context


def dict_nest(data, separator='.'):
    """
    takes a flat dictionary with string keys and turns it into a
    nested one by splitting keys on the given separator.
    """
    res = {}
    for k in data:
        levels = k.split(separator)
        d = res
        for k1 in levels[:-1]:
            d.setdefault(k1, {})
            d = d[k1]
        d[levels[-1]] = data[k]
    return res


def dict_unnest(data, separator='.'):
    """
    takes a dictionary with string keys and values which may be either
    such dictionaries or non-dictionary values, and turns them into a
    flat dictionary with keys consisting of paths into the nested
    structure, with path elements delimited by the given separator.

    This is the inverse operation of dict_nest().
    """
    res = {}
    for k, v in data.iteritems():
        if isinstance(v, dict):
            v = dict_unnest(v, separator)
            for k1, v1 in v.iteritems():
                res["%s%s%s" % (k, separator, k1)] = v1
        else:
            res[k] = v
    return res


class Invalid(Exception):
    """A general Exception for things that are Invalid"""
    def __init__(self, errors=None, field=_default):
        if not errors:
            errors = dict()
        elif not isinstance(errors, dict):
            errors = {None: errors}
        if not field is _default:
            self.field = field
        Exception.__init__(self, errors)
        self.errors = errors

    def _unpack_error(self, name, error):
        if isinstance(error, dict):
            result = dict(
                [self._unpack_error(key, value) for (key, value) in error.iteritems()])
        elif isinstance(error, (list, tuple)):
            name, result = self._unpack_error(name, error[0])
        elif isinstance(error, Invalid):
            name = getattr(error, 'field', name)
            result = error._unpack_errors()
        else:
            result = error
        return (name, result)

    def _unpack_errors(self):
        result = dict()
        for key, value in self.errors.iteritems():
            name, error = self._unpack_error(key, value)
            result[name] = error

        if result.keys() == [None]:
            return result[None]
        elif result.keys() == ['']:
            return result['']
        else:
            return result

    def unpack_errors(self):
        result = self._unpack_errors()
        if isinstance(result, basestring):
            return {None: result}
        else:
            return result


class Schema(object):
    """
    creates a validator from a dictionary of subvalidators that will
    be used to validate a dictionary of data, returning a new
    dictionary that contains the converted values.

    The keys in the validator dictionary may be either singular -- atoms
    (presumably strings) that match keys in the data dictionary, or
    plural -- lists/tuples of such atoms.

    The values associated with those keys should be subvalidator
    functions (or lists/tuples of functions that will be composed
    automatically) that are passed a value or values taken from the
    data dictionary according to the corresponding key in the data
    dictionary.  If the key is singular, the subvalidator will be
    passed the data dictionary's value for the key (or None); if
    plural, it will be passed a tuple of the data dictionary's values
    for all the items in the plural key (e.g., tuple(data[x] for x in
    key)).  In either case, the return value of the subvalidator
    should match the structure of the input.

    The subvalidators are sorted by key before being executed.  Therefore,
    subvalidators with plural keys will always be executed after those
    with singular keys.

    If allow_missing is False, then any missing keys in the input will
    give rise to an error.  Similarly, if allow_extra is False, any
    extra keys will result in an error.
    """

    def __init__(self,
                 subvalidators,
                 msg=None,
                 allow_missing=True,
                 allow_extra=True,
                 filter_extra=True):
        self.subvalidators = subvalidators
        self.msg = msg
        self.allow_missing = allow_missing
        self.allow_extra = allow_extra
        self.filter_extra = filter_extra

    def _keys(self):
        schemakeys = set()
        for x in self.subvalidators:
            if isinstance(x, (list, tuple)):
                for x1 in x:
                    schemakeys.add(x1)
            else:
                schemakeys.add(x)
        return schemakeys

    def __call__(self, data, context=None):
        if not context:
            context = dict()
        if not self.filter_extra:
            result = data
        else:
            result = {}
        exceptions = {}
        if not (self.allow_extra and self.allow_missing):
            inputkeys = set(data.keys())
            schemakeys = self._keys()
            if not self.allow_extra:
                if inputkeys.difference(schemakeys):
                    m = _msg(self.msg, 'schema.extra', 'extra keys in input')
                    raise Invalid(m)
            if not self.allow_missing:
                if schemakeys.difference(inputkeys):
                    m = _msg(self.msg, 'schema.missing', 'missing keys in input')
                    raise Invalid(m)

        for k in sorted(self.subvalidators):
            vfunc = self.subvalidators[k]
            if isinstance(vfunc, (list, tuple)):
                vfunc = all_of(*vfunc)
            have_plural = isinstance(k, (list,tuple))
            if have_plural:
                vdata = tuple(result.get(x, data.get(x)) for x in k)
            else:
                vdata = result.get(k, data.get(k))
            try:
                tmp = vfunc(vdata, context)
            except Invalid, e:
                # if the exception specifies a field name,
                # let that override the key in the validator
                # dictionary
                name = getattr(e, 'field', k)
                exceptions[name] = e._unpack_errors()
            else:
                if have_plural:
                    result.update(dict(zip(k, tmp)))
                else:
                    result[k] = tmp

        if exceptions:
            if not exceptions.has_key(None):
                m = _msg(self.msg, "schema.error",
                         "Problems were found in the submitted data.")
                exceptions[None] = m
            raise Invalid(exceptions)
        return result


def confirm_type(typespec, msg=None):
    @functools.wraps(confirm_type)
    def f(value, context=None):
        if isinstance(value, typespec):
            return value
        raise Invalid(_msg(msg, "confirm_type", "unexpected type"))
    return f


def translate(mapping, msg=None):
    @functools.wraps(translate)
    def f(value, context=None):
        try:
            return mapping[value]
        except KeyError:
            raise Invalid(_msg(msg, "belongs", "invalid choice"))
    return f


def is_unicode(msg=None):
    @functools.wraps(is_unicode)
    def f(value, context=None):
        if isinstance(value, unicode):
            return value
        else:
            raise Invalid(_msg(msg, 'is_unicode', 'not unicode'))
    return f


def to_unicode(encoding='utf8', errors='strict', msg=None):
    @functools.wraps(to_unicode)
    def f(value, context=None):
        if isinstance(value, unicode):
            return value
        elif value is None:
            return u''
        else:
            try:
                return value.decode(encoding, errors)
            except AttributeError:
                return unicode(value)
            except UnicodeError, e:
                raise Invalid(_msg(msg, 'to_unicode', 'encoding error'))
    return f


def is_string(msg=None):
    @functools.wraps(is_string)
    def f(value, context=None):
        if isinstance(value, str):
            return value
        else:
            raise Invalid(_msg(msg, 'is_string', 'not string'))
    return f


def to_string(encoding='utf8', errors='strict', coerce=True, msg=None):
    @functools.wraps(to_string)
    def f(value, context=None):
        if isinstance(value, str):
            return value
        elif not coerce:
            raise Invalid(_msg(msg, 'to_string', 'encoding error'))
        elif value is None:
            return ''
        else:
            try:
                return value.encode(encoding, errors)
            except AttributeError:
                return str(value)
            except UnicodeError, e:
                raise Invalid(_msg(msg, 'to_string', 'encoding error'))
    return f


def is_scalar(msg=None, listtypes=(list,)):
    """
    Raises an exception if the value is not a scalar.
    """
    @functools.wraps(is_scalar)
    def f(value, context=None):
        if isinstance(value, listtypes):
            raise Invalid(_msg(msg, 'is_scalar', 'expected scalar value'))
        return value
    return f


def is_list(msg=None, listtypes=(list,)):
    """
    Raises an exception if the value is not a list.
    """
    @functools.wraps(is_list)
    def f(value, context=None):
        if not isinstance(value, listtypes):
            raise Invalid(_msg(msg, "is_list", "expected list value"))
        return value
    return f


def to_scalar(listtypes=(list,)):
    """
    if the value is a list, return the first element.
    Otherwise, return the value.

    This raises no exceptions.
    """
    @functools.wraps(to_scalar)
    def f(value, context=None):
        if isinstance(value, listtypes):
            return value[0]
        return value
    return f


def to_list(listtypes=(list,)):
    """
    if the value is a scalar, wrap it in a list.
    Otherwise, return the value.

    This raises no exceptions.
    """
    @functools.wraps(to_list)
    def f(value, context=None):
        if not isinstance(value, listtypes):
            return [value]
        return value
    return f


def default(defaultValue):
    """
    if the value is None, return defaultValue instead.

    This raises no exceptions.
    """
    @functools.wraps(default)
    def f(value, context=None):
        if value is None:
            return defaultValue
        return value
    return f


def all_of(*validators):
    """
    Applies each of a series of validators in turn, passing the return
    value of each to the next.
    """
    @functools.wraps(all_of)
    def f(value, context=None):
        for v in validators:
            value = v(value, context=context)
        return value
    return f


def either(*validators):
    """
    Tries each of a series of validators in turn, swallowing any
    exceptions they raise, and returns the result of the first one
    that works.  If none work, the last exception caught is re-raised.
    """
    @functools.wraps(either)
    def f(value, context=None):
        last_exception = None
        for v in validators:
            try:
                value = v(value, context=context)
            except Exception, e:
                last_exception = e
            else:
                return value
        raise last_exception
    return f


def check(*validators):
    """
    Returns a function that runs each of a series of validators
    against input data, which is passed to each validator in turn,
    ignoring the validators return value.  The function returns the
    original input data (which, if it mutable, may have been changed).
    """
    @functools.wraps(check)
    def f(value, context=None):
        for v in validators:
            v(value, context=context)
        return value
    return f


def excursion(*validators):
    """
    Perform a series of validations that may break down the data
    passed in into a form that you don't deserve to retain; if the
    data survives validation, you get a copy of the data from the
    point the excursion started.
    """
    @functools.wraps(excursion)
    def f(value, context=None):
        return_value = copy.copy(value)
        all_of(*validators)(value)
        return return_value
    return f


def equal(val, msg=None):
    @functools.wraps(equal)
    def f(value, context=None):
        if value == val:
            return value
        raise Invalid(_msg(msg, 'eq', 'invalid value'))
    return f


def not_equal(val, msg=None):
    @functools.wraps(not_equal)
    def f(value, context=None):
        if value != val:
            return value
        raise Invalid(_msg(msg, 'eq', 'invalid value'))
    return f


def empty(msg=None):
    @functools.wraps(empty)
    def f(value, context=None):
        if value == '' or value is None:
            return value
        raise Invalid(_msg(msg, "empty", "No value was expected"))
    return f


def not_empty(msg=None):
    @functools.wraps(not_empty)
    def f(value, context=None):
        if value != '' and value != None:
            return value
        raise Invalid(_msg(msg, 'notempty', "A non-empty value was expected"))
    return f


def strip(value, context=None):
    """
    For string/unicode input, strips the value to remove pre- or
    postpended whitespace.  For other values, does nothing; raises no
    exceptions.
    """
    try:
        return value.strip()
    except AttributeError:
        return value


def clamp(min=None, max=None, msg=None):
    """
    clamp a value between minimum and maximum values (either
    of which are optional).
    """
    @functools.wraps(clamp)
    def f(value, context=None):
        if min is not None and value < min:
            raise Invalid(_msg(msg, "min", "value below minimum"))
        if max is not None and value > max:
            raise Invalid(_msg(msg, "max", "value above maximum"))
        return value
    return f


def clamp_length(min=None, max=None, msg=None):
    """
    clamp a value between minimum and maximum lengths (either
    of which are optional).
    """
    @functools.wraps(clamp_length)
    def f(value, context=None):
        vlen = len(value)
        msg_context = dict(min=min, max=max, length=vlen)
        if min is not None and vlen < min:
            raise Invalid(_msg(msg, "minlen", "too short", msg_context=msg_context))
        if max is not None and vlen > max:
            raise Invalid(_msg(msg, "maxlen", "too long", msg_context=msg_context))
        return value
    return f


def belongs(domain, msg=None):
    """
    ensures that the value belongs to the domain
    specified.
    """
    @functools.wraps(belongs)
    def f(value, context=None):
        if value in domain:
            return value
        raise Invalid(_msg(msg, "belongs", "invalid choice"))
    return f


def not_belongs(domain, msg=None):
    """
    ensures that the value does not belong to the domain
    specified.
    """
    @functools.wraps(not_belongs)
    def f(value, context=None):
        if value not in domain:
            return value
        raise Invalid(_msg(msg, "not_belongs", "invalid choice"))
    return f


def parse_time(format, msg=None):
    """
    attempts to parse the time according to
    the given format, returning a timetuple,
    or raises an Invalid exception.
    """
    @functools.wraps(parse_time)
    def f(value, context=None):
        try:
            return time.strptime(value, format)
        except ValueError:
            raise Invalid(_msg(msg, 'parse_time', "invalid time"))
    return f


def parse_date(format, msg=None):
    """
    like parse_time, but returns a datetime.date object.
    """
    @functools.wraps(parse_date)
    def f(value, context=None):
        v = parse_time(format, msg)(value)
        return datetime.date(*v[:3])
    return f


def parse_datetime(format, msg=None):
    """
    like parse_time, but returns a datetime.datetime object.
    """
    @functools.wraps(parse_datetime)
    def f(value, context=None):
        v = parse_time(format, msg)(value)
        return datetime.datetime(*v[:6])
    return f


def uuid(msg=None, default=False):
    """
    Accepts any value that can be converted to a uuid
    """
    @functools.wraps(uuid)
    def f(value, context=None):
        try:
            v = str(UUID(str(value)))
        except ValueError:
            if default and not value:
                return uuid1()
            else:
                raise Invalid(_msg(msg, "uuid", "invalid uuid"))
        return v
    return f


def to_integer(msg=None):
    """
    Attempts to coerce the value to an integer.

    >>> validator = to_integer(msg='me no convert')
    >>> validator('1')
    1
    >>> validator('two')
    Traceback (most recent call last):
    ...
    Invalid: {None: 'me no convert'}
    """
    @functools.wraps(to_integer)
    def f(value, context=None):
        try:
            return int(value)
        except (TypeError, ValueError):
            raise Invalid(_msg(msg, "integer", "not an integer"))
    return f


def is_integer(msg=None):
    """
    Tests whether the value in an integer
    """
    @functools.wraps(is_integer)
    def f(value, context=None):
        if isinstance(value, int):
            return value
        else:
            raise Invalid(_msg(msg, "is_integer", "not an integer"))
    return f


def to_boolean(msg=None, fuzzy=False):
    """
    Coerces the value to one of True or False.  If `fuzzy` is `True`
    it checks whether the value is one of a set of reasonable truthy
    strings, before coercion.
    >>> to_boolean()('false')
    True
    >>> to_boolean(fuzzy=True)('false')
    False
    >>> to_boolean()(0)
    False
    >>> to_boolean()([])
    False
    """
    true_strings = ['true', 't', 'y', 'yes']
    false_strings = ['false', 'f', 'n', 'no']
    @functools.wraps(to_boolean)
    def f(value, context=None):
        if fuzzy and isinstance(value, basestring):
            if value.lower() in true_strings:
                return True
            elif value.lower() in false_strings:
                return False
        return bool(value)
    return f


def regex(pat, msg=None):
    """
    tests the value against the given regex pattern
    and raises Invalid if it doesn't match.
    """
    @functools.wraps(regex)
    def f(value, context=None):
        m = re.match(pat, value)
        if not m:
            raise Invalid(_msg(msg, 'regex', "does not match pattern"))
        return value
    return f


def regex_sub(pat, sub):
    """
    performs regex substitution on the input value.
    """
    @functools.wraps(regex_sub)
    def f(value, context=None):
        return re.sub(pat, sub, value)
    return f


def fields_equal(msg=None, field=_default):
    """
    when passed a collection of values,
    verifies that they are all equal.
    """
    @functools.wraps(fields_equal)
    def f(values, context=None):
        if len(set(values)) != 1:
            m = _msg(msg, 'fields_equal', "fields not equal")
            if field is _default:
                raise Invalid(m)
            else:
                raise Invalid(m, field=field)
        return values
    return f


def fields_match(name1, name2, msg=None, field=_default):
    """
    verifies that the values associated with the keys 'name1' and
    'name2' in value (which must be a dict) are identical.
    """
    @functools.wraps(fields_match)
    def f(value, context=None):
        if value[name1] != value[name2]:
            m = _msg(msg, 'fields_match', 'fields do not match')
            if field is _default:
                raise Invalid(m)
            else:
                raise Invalid({field: m})
        return value
    return f


def nested(**kwargs):
    """
    Behaves like a dict.  It's keys are names, it's values are validators
    """
    @functools.wraps(nested)
    def f(value, context=None):
        data = dict()
        errors = dict()
        for k, v in kwargs.items():
            if isinstance(v, tuple):
                v = all_of(*v)
            try:
                data[k] = v(value[k], context=context)
            except (KeyError, TypeError):
                errors[k] = "key %r is missing" % k
            except Invalid, e:
                errors[k] = e
        if errors:
            raise Invalid(errors)
        return data
    return f


def nested_many(sub_validator):
    """
    Applies the validator to each of the values
    """
    @functools.wraps(nested_many)
    def f(value, context=None):
        data = dict()
        errors = dict()
        if value:
            for k, v in value.items():
                try:
                    data[k] = sub_validator(v, context=context)
                except Invalid, e:
                    errors[k] = e
            if errors:
                raise Invalid(errors)
            else:
                return data
        else:
            raise Invalid("No data found")
    return f


def only_one_of(msg=None, field=None):
    """
    Check that only one of the given values is True.
    """
    @functools.wraps(only_one_of)
    def f(values, context=None):
        if sum([int(bool(val)) for val in values]) > 1:
            m = _msg(msg, 'only_one_of', 'more than one value present')
            if field is not None:
                raise Invalid(m, field=field)
            else:
                raise Invalid(m)
        return values
    return f
