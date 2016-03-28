"""
Pico is a minimalistic HTTP API framework for Python.

Copyright (c) 2012, Fergal Walsh.
License: BSD
"""

import sys
import pico.pragmaticjson as json
import inspect
import functools

from collections import defaultdict

from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Request, Response

from decorators import base_decorator

__author__ = 'Fergal Walsh'
__version__ = '2.0.0-dev'


class PicoApp(object):

    def __init__(self):
        self.registry = defaultdict(dict)
        self.modules = {}
        self.url_map = {}
        self._before_request = None

    def register(self, func):
        self.modules[func.__module__] = sys.modules[func.__module__]
        self.registry[func.__module__][func.__name__] = func
        self._build_url_map()

    def _build_url_map(self):
        self.url_map = {}
        for module_name in self.registry:
            url = self.module_url(module_name)
            self.url_map[url] = functools.partial(self.describe_module, module_name)
            for func_name, func in self.registry[module_name].items():
                url = self.func_url(func)
                self.url_map[url] = func
                self.url_map[url + '_doc/'] = functools.partial(self.function_doc, func)

    def module_url(self, module_name):
        module_path = module_name.replace('.', '/')
        url = '/{module}/'.format(module=module_path)
        return url

    def func_url(self, func):
        module_path = func.__module__.replace('.', '/')
        url = '/{module}/{func_name}/'.format(module=module_path, func_name=func.__name__)
        return url

    def describe_module(self, module_name, **kwargs):
        d = {}
        d['name'] = module_name
        d['doc'] = self.modules[module_name].__doc__
        d['url'] = self.module_url(module_name)
        d['functions'] = []
        for func_name, func in self.registry[module_name].items():
            d['functions'].append(self.describe_function(func))
        return json_reponse(d)

    def describe_function(self, func, **kwargs):
        annotations = dict(func._annotations)
        request_args = annotations.pop('request_args', {})
        a = inspect.getargspec(func)
        arg_list_r = reversed(a.args)
        defaults_list_r = reversed(a.defaults or [None])
        args = reversed(map(None, arg_list_r, defaults_list_r))
        args = filter(lambda x: x[0] and x[0] != 'self' and x[0] not in request_args, args)
        d = dict(
            name=func.__name__,
            doc=func.__doc__,
            url=self.func_url(func),
            args=args,
        )
        d.update(annotations)
        return d

    def function_doc(self, func, **kwargs):
        d = self.describe_function(func)
        args = ', '.join(['%s=%s' % a for a in d['args']])
        s = '{name}({args})\n{docstring}'.format(name=d['name'], docstring=d['doc'], args=args)
        return Response(s)

    def not_found_handler(self, path):
        return "404 %s not found" % path

    def call_function(self, func, request, **kwargs):
        args = self.parse_args(request)
        args.update(kwargs)
        callback = args.pop('_callback', None)
        response = func(**args)
        if callback:
            response = jsonp_reponse(response=response, callback=callback)
        return response

    def parse_args(self, request):
        args = request.args.to_dict(flat=True)
        if request.headers.get('content-type') != 'application/json':
            args.update(request.form.to_dict(flat=True))
            for k in args:
                try:
                    args[k] = json.loads(args[k])
                except ValueError:
                    pass
            args.update(request.files.to_dict(flat=True))
        else:
            args.update(json.loads(request.data))
        args['_request'] = request
        return args

    def dispatch_request(self, request):
        path = request.path
        if path[-1] != '/':
            path += '/'
        try:
            handler = self.url_map[path]
        except KeyError:
            try:
                path = request.script_root + path
                handler = self.url_map[path]
            except KeyError:
                return Response(self.not_found_handler(path))
        try:
            if self._before_request:
                self._before_request(request, path)
            response = self.call_function(handler, request)
        except HTTPException, e:
            return e
        except Exception, e:
            return json_reponse(dict(exception=str(e)))
        return response

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def _decorate_and_register(self, wrapper):
        def decorator(f):
            f = wrapper(f)
            self.register(f)
            return f
        return decorator

    def expose(self, *args, **kwargs):
        @base_decorator()
        def wrapper(wrapped, args, kwargs, request):
            result = wrapped(*args, **kwargs)
            if isinstance(result, Response):
                response = result
            else:
                response = json_reponse(result)
            return response
        return self._decorate_and_register(wrapper)

    def before_request(self, *args, **kwargs):
        def decorator(f):
            self._before_request = f
            return f
        return decorator


def json_reponse(result):
    return Response(json.dumps(result), content_type='application/json')


def jsonp_reponse(result=None, response=None, callback=None):
    if response:
        json_string = response.response[0]
    if result:
        json_string = json.dumps(result)
    content = '{callback}({json});'.format(callback=callback, json=json_string)
    return Response(content, content_type='text/javascript')
