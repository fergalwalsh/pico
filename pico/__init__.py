"""
Pico is a minimalistic HTTP API framework for Python.

Copyright (c) 2012, Fergal Walsh.
License: BSD
"""

import sys
import inspect
import functools
import logging
import importlib
import os.path

from collections import defaultdict

from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wrappers import Request, Response

from . import pragmaticjson as json
from .decorators import json_response
from .wrappers import JsonResponse

__author__ = 'Fergal Walsh'
__version__ = '2.0.0-dev'

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


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

    def register_module(self, module_name):
        importlib.import_module(module_name)

    def _build_url_map(self):
        self.url_map = {}
        self.url_map['/pico.js'] = self.pico_js
        for module_name in self.registry:
            url = self.module_url(module_name)
            self.url_map[url] = functools.partial(self.describe_module, module_name)
            self.url_map[url + '.js'] = functools.partial(self.module_js, module_name)
            for func_name, func in self.registry[module_name].items():
                url = self.func_url(func)
                self.url_map[url] = func
                self.url_map[url + '/_doc'] = functools.partial(self.function_doc, func)

    def module_url(self, module_name):
        module_path = module_name.replace('.', '/')
        url = '/{module}'.format(module=module_path)
        return url

    def func_url(self, func):
        module_path = func.__module__.replace('.', '/')
        url = '/{module}/{func_name}'.format(module=module_path, func_name=func.__name__)
        return url

    def describe_module(self, module_name, **kwargs):
        d = {}
        d['name'] = module_name
        d['doc'] = self.modules[module_name].__doc__
        d['url'] = self.module_url(module_name)
        d['functions'] = []
        for func_name, func in self.registry[module_name].items():
            d['functions'].append(self.describe_function(func))
        return JsonResponse(d)

    def module_js(self, module_name, **kwargs):
        response = self.describe_module(module_name, **kwargs)
        response = response.to_jsonp('pico.load_from_obj')
        return response

    def describe_function(self, func, **kwargs):
        annotations = dict(func._annotations)
        request_args = annotations.pop('request_args', {})
        a = inspect.getargspec(func)
        arg_list_r = reversed(a.args)
        defaults_list_r = reversed(a.defaults or [None])
        args = reversed(map(None, arg_list_r, defaults_list_r))
        args = [{'name': a[0], 'default': a[1]} for a in args]
        args = filter(lambda x: x['name'] and x['name'] != 'self' and x['name'] not in request_args, args)
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
        args = ', '.join(['%{name}s=%{default}s'.format(**a) for a in d['args']])
        s = '{name}({args})\n{docstring}'.format(name=d['name'], docstring=d['doc'], args=args)
        return JsonResponse(d)

    def pico_js(self, **kwargs):
        path = os.path.dirname((inspect.getfile(inspect.currentframe())))
        s = open(path + '/client.js').read()
        response = Response(s, content_type='text/javascript')
        return response

    def not_found_handler(self, path):
        return "404 %s not found" % path

    def call_function(self, func, request, **kwargs):
        args = self.parse_args(request)
        args.update(kwargs)
        callback = args.pop('_callback', None)
        response = func(**args)
        if callback:
            response = response.to_jsonp(callback)
        return response

    def parse_args(self, request):
        # first we take the GET querystring args
        args = _multidict_to_dict(request.args)
        # update and override args with post form data
        args.update(_multidict_to_dict(request.form))
        # try to parse any strings as json
        for k in args:
            if isinstance(args[k], list):
                for i, v in enumerate(args[k]):
                    args[k][i] = json.try_loads(v)
            else:
                args[k] = json.try_loads(args[k])
        # update args with files
        args.update(_multidict_to_dict(request.files))
        # update and override args with json data
        if 'application/json' in request.headers.get('content-type'):
            args.update(json.loads(request.data))
        args['_request'] = request
        return args

    def dispatch_request(self, request):
        path = request.path
        if path[-1] == '/':
            path = path[:-1]
        if request.method == 'OPTIONS':
            path += '/_doc'
        request.path = path
        try:
            handler = self.url_map[path]
        except KeyError:
            try:
                path = request.script_root + path
                handler = self.url_map[path]
                request.path = path
            except KeyError:
                return NotFound()
        return self.handle_request(request, handler)

    def handle_request(self, request, handler, **kwargs):
        try:
            if self._before_request:
                self._before_request(request)
            response = self.call_function(handler, request, **kwargs)
        except HTTPException as e:
            return e
        except Exception as e:
            tags = {
                'module_name': handler.__module__,
                'function_name': handler.__name__
            }
            logger.error(e,
                         exc_info=True,
                         extra={'data': dict(tags), 'tags': dict(tags)})
            if not request.accept_mimetypes.accept_html:
                response = JsonResponse(dict(exception=unicode(e)))
                response.status = '500 Internal Server Error'
            else:
                raise
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
        def decorator(f):
            f = json_response()(f)
            self.register(f)
            return f
        return decorator

    def before_request(self, *args, **kwargs):
        def decorator(f):
            self._before_request = f
            return f
        return decorator


def _multidict_to_dict(m):
    """ Returns a dict with list values only when a key has multiple values. """
    d = {}
    for k, v in m.iterlists():
        if len(v) == 1:
            d[k] = v[0]
        else:
            d[k] = v
    return d
