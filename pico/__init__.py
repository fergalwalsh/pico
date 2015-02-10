"""
Pico is a very small RPC library and web application framework for Python.

Copyright (c) 2012, Fergal Walsh.
License: BSD
"""

__author__ = 'Fergal Walsh'
__version__ = '1.4.2'

import json
import os
import decimal
import datetime
import inspect

import wrapt

path = (os.path.dirname(__file__) or '.') + '/'


def cacheable(func):
    func.cacheable = True
    return func


def stream(func):
    func.stream = True
    return func


def private(func):
    func.private = True
    return func


def protected(protector):
    """
    Decorator for protecting a function.
    The protected function will not be called if the protector raises
     an exception.
    The protector should have the following signature:
        def protector(wrapped, *args, **kwargs):
            pass
    """
    @wrapt.decorator
    def wrapper(wrapped, instance, args, kwargs):
        request = get_request()
        if request != dummy_request:
            protector(wrapped, *args, **kwargs)
        return wrapped(*args, **kwargs)
    return wrapper


def get_request():
    """ Returns the wsgi environ dictionary for the current request """
    frame = None
    try:
        frame = [f for f in inspect.stack() if f[3] == 'call'][0]
        request = frame[0].f_locals['request']
    except Exception:
        request = dummy_request
    finally:
        del frame
    return request


def set_dummy_request(request):
    """ Set a dummy request dictionary - for use in the console and testing """
    dummy_request.clear()
    dummy_request.update(request)


class Pico(object):
    def __init__(self):
        pass


class object(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    @property
    def json(self):
        return to_json(self.__dict__)

    def __str__(self):
        return self.json


class JSONString(str):
    def __init__(self, s):
        pass


class PicoError(Exception):
    def __init__(self, message=''):
        Exception.__init__(self, message)
        self.response = Response(status="500 " + message, content=message)

    def __str__(self):
        return repr(self.message)


class Response(object):
    def __init__(self, **kwds):
        self.status = '200 OK'
        self._headers = {}
        self.content = ''
        self._type = "object"
        self.cacheable = False
        self.callback = None
        self.json_dumpers = {}
        self.__dict__.update(kwds)

    def __getattribute__(self, a):
        try:
            return object.__getattribute__(self, a)
        except AttributeError:
            return None

    def set_header(self, key, value):
        self._headers[key] = value

    @property
    def headers(self):
        headers = dict(self._headers)
        headers['Access-Control-Allow-Origin'] = '*'
        headers['Access-Control-Allow-Headers'] = 'Content-Type'
        headers['Access-Control-Expose-Headers'] = 'Transfer-Encoding'
        if self.cacheable:
            headers['Cache-Control'] = 'public, max-age=22222222'
        if self.type == 'stream':
            headers['Content-Type'] = 'text/event-stream'
        elif self.type == 'object':
            if self.callback:
                headers['Content-Type'] = 'application/javascript'
            else:
                headers['Content-Type'] = 'application/json'
            headers['Content-Length'] = str(len(self.output[0]))
        else:
            if 'Content-type' not in headers:
                headers['Content-Type'] = 'text/plain'
        return headers.items()

    @property
    def type(self):
        if all(hasattr(self.content, a) for a in ['read', 'seek', 'close']):
            # if it looks like a duck...
            # file, StringIO, codecs.StreamReaderWriter, etc.
            self._type = "file"
        return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def output(self):
        if self._output:
            return self._output
        if self.type == "plaintext":
            return [self.content, ]
        if self.type == "file":
            return self.content
        if self.type == "stream":
            def f(stream):
                for d in stream:
                    yield 'data: ' + to_json(d) + '\n\n'
                yield 'data: "PICO_CLOSE_STREAM"\n\n'
            return f(self.content)
        if self.type == "chunks":

            def f(response):
                yield (' ' * 1200) + '\n'
                yield '[\n'
                delimeter = ''
                for r in response:
                    yield delimeter + to_json(r, self.json_dumpers) + '\n'
                    delimeter = ','
                yield "]\n"
            return f(self.content)
        else:
            s = to_json(self.content, self.json_dumpers)
            if self.callback:
                s = self.callback + '(' + s + ')'
            s = [s, ]
            self._output = s
            return s


def convert_keys(obj):
    if type(obj) == dict:  # convert non string keys to strings
        return dict((str(k), convert_keys(obj[k])) for k in obj)
    else:
        return obj


def to_json(obj, extra_json_dumpers=None):
    if isinstance(obj, JSONString):
        return obj
    json_dumpers_ = dict(json_dumpers)
    json_dumpers_.update(extra_json_dumpers or {})
    obj = convert_keys(obj)

    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if type(obj) in json_dumpers_:
                obj = json_dumpers_[type(obj)](obj)
                convert_keys(obj)
                return obj
            for obj_type, dumper in json_dumpers_.iteritems():
                if isinstance(obj, obj_type):
                    return dumper(obj)
            if hasattr(obj, 'as_json'):
                return obj.as_json()
            if hasattr(obj, 'json'):
                return json.loads(obj.json)
            elif hasattr(obj, 'tolist'):
                return obj.tolist()
            elif all(hasattr(obj, a) for a in ['read', 'seek', 'close']):
                s = obj.read()
                obj.close()
                return s
            elif hasattr(obj, '__iter__'):
                return list(obj)
            else:
                return str(obj)

        def encode(self, obj):
            convert_keys(obj)
            return json.JSONEncoder.encode(self, obj)
    s = json.dumps(obj, cls=Encoder, separators=(',', ':'))
    return s


def from_json(v, extra_json_loaders=()):
    if isinstance(v, basestring):
        for f in list(extra_json_loaders) + json_loaders:
            try:
                v = f(v)
                break
            except Exception:
                continue
    return v


json_dumpers = {
    decimal.Decimal: lambda d: str(d)
}

json_loaders = [
    lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
    lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'),
    lambda s: datetime.datetime.strptime(s, '%Y-%m-%dT%H:%M:%S.%fZ')
]

STREAMING = False
dummy_request = {'DUMMY_REQUEST': True}
