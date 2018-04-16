# -*- coding: utf-8 -*-

"""
Some validators commonly used in web applications.
"""

import http.client
import re
import socket
import urllib.parse

from validino.base import Invalid, _msg, regex
from validino.util import partial

# lifted from formencode
_usernameRE = re.compile(r"^[^ \t\n\r@<>()]+$", re.I)
_domainRE = re.compile(r"^[a-z0-9][a-z0-9\.\-_]*\.[a-z]+$", re.I)

__all__ = [
    'ip',
    'url']

_ip_pat = '^%s$' % r'\.'.join(['|'.join([str(x) for x in range(256)]*4)])

ip = partial(regex, _ip_pat)
ip.__doc__ = """
Returns a validator that tests whether an ip address is properly formed.
"""

def url(check_exists=False,
        schemas=('http', 'https'),
        default_schema='http',
        default_host='',
        msg=None):

    def f(value):
        if f.check_exists and set(f.schemas).difference(set(('http', 'https'))):
            m = "existence check not supported for schemas other than http and https"
            raise RuntimeError(m)
        schema, netloc, path, params, query, fragment = urllib.parse.urlparse(value)
        if schema not in f.schemas:
            raise Invalid(_msg(f.msg,
                               "url.schema",
                               "schema not allowed"))
        if schema == '' and f.default_schema:
            schema = f.default_schema
        if netloc == '' and f.default_host:
            netloc = f.default_host

        url = urllib.parse.urlunparse((schema, netloc, path, params, query, fragment))
        if f.check_exists:
            newpath = urllib.parse.urlunparse(('', '', path, params, query, fragment))
            if schema == 'http':
                conn = http.client.HTTPConnection
            elif schema == 'https':
                conn = http.client.HTTPSConnection
            else:
                assert False, "not reached"
            try:
                c = conn(netloc)
                c.request('HEAD', newpath)
                res = c.getresponse()
            except (http.client.HTTPException, socket.error) as e:
                raise Invalid(_msg(f.msg,
                                   "url.http_error",
                                   "http error"))
            else:
                if 200 <= res.status < 400:
                    # this fudges on redirects.
                    return url
                raise Invalid(_msg(f.msg,
                                   'url.not_exists',
                                   "url not OK"))
        return url
    f.default_schema = default_schema
    f.default_host = default_host
    f.check_exists = check_exists
    f.schemas = schemas
    f.msg = msg
    return f
