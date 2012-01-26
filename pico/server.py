from wsgiref.util import setup_testing_defaults
from wsgiref.simple_server import make_server

import sys
import cgi
import json
import inspect
import os
import mimetypes
import urlparse
import hashlib
import decimal
import traceback
import getopt
import re
import datetime
import time

import wsgiref
import SocketServer

import pico

path = (os.path.dirname(__file__) or '.') + '/'

class Response(object):
    def __init__(self, **kwds):
        self.status = '200 OK'
        self.headers = [('Content-type', 'text/plain')]
        self.type = "object"
        self.json_dumpers = {}
        self.__dict__.update(kwds)
    
    def __getattribute__(self, a):
        try:
            return object.__getattribute__(self, a)
        except AttributeError, e:
            return None
        
    @property
    def output(self):
        print(self.type)
        if self.type == "plaintext":
            return [self.content,]
        if self.type == "file":
            return self.content
        if self.type == "stream":
            def f(stream):
                for d in stream:
                    yield 'data: ' + pico.to_json(d) + '\n\n'
            return f(self.content)
        else:
            s = pico.to_json(self.content, self.json_dumpers)
            if self.callback:
                s = self.callback + '(' + s + ')'
            return s

def main():
    opts_args = getopt.getopt(sys.argv[1:], "hp:dm", ["help", "port="])
    args = dict(opts_args[0])
    port = int(args.get('--port', args.get('-p', 8800)))
    multithreaded = '-m' in args
    host = '0.0.0.0' #'localhost'
    app = wsgi_app
    if multithreaded:
        class ThreadedTCPServer(SocketServer.ForkingMixIn, wsgiref.simple_server.WSGIServer):
            pass
        server = ThreadedTCPServer((host, port), wsgiref.simple_server.WSGIRequestHandler)
        server.set_app(app)
        server_type = 'multiple threads'
    else:
        server = make_server(host, port, app)
        server_type = 'a single thread'
    print("Serving on http://localhost:%s/"%port)
    print("Using %s."%server_type)
    print("URL map: ")
    print('\t' + '\n\t'.join(["%s : %s "%(url, path) for url, path in STATIC_URL_MAP]))
    print("Hit CTRL-C to end")
    server.serve_forever()
    

def is_authorised(f, authenticated_user):
    if hasattr(f, 'private') and f.private:
        return False
    if getattr(f, 'protected', False):
        if (authenticated_user == None):
            return False
        else:
            if f.protected_username == None and f.protected_group == None:
                return True
            if f.protected_username and authenticated_user in f.protected_username:
                return True
            if f.protected_group and set(USERS.get(authenticated_user)['groups']).intersection(f.protected_group):
                return True
            return False
    else:
        return True
    return False

def call_function(module, function_name, parameters, authenticated_user=None):
    try:
        f = getattr(module, function_name)
    except:
        raise Exception("No matching function availble. You asked for %s with these parameters %s!"%(function_name, parameters))
    if not is_authorised(f, authenticated_user):
        raise Exception("You are not authorised to access this function")
    if 'pico_user' in f.func_code.co_varnames:
        parameters.update({'pico_user': authenticated_user})
    results = f(**parameters)
    response = Response(content=results)
    response.cacheable= (hasattr(f, 'cacheable') and f.cacheable)
    if hasattr(f, 'stream') and f.stream and STREAMING:
        response.headers = [('Content-Type', 'text/event-stream')]
        response.type = "stream"
    return response
    

def call_method(module, class_name, method_name, parameters, init_args, authenticated_user=None):
    try:
        obj = getattr(module, class_name)(*init_args)
    except KeyError, e:
        raise Exception("No matching class availble. You asked for %s!"%(class_name))
    return call_function(obj, method_name, parameters, authenticated_user)

def cache_key(params):
    params = dict(params)
    del params['_callback']
    hashstring = hashlib.md5(str(params)).hexdigest()
    cache_key = "__".join([params.get('_module', ''), params.get('_class', ''), params.get('_function', ''), hashstring])
    return cache_key.replace('.', '_')


def call(params):
    function = params.get('_function', '')
    module_name = params.get('_module', '')
    parameters = dict(params)
    for k in parameters.keys():
        if k.startswith('_') or k.startswith('pico_'):
            del parameters[k]
        else:
            parameters[k] = json.loads(parameters[k].replace("'", '"'))
    callback = params.get('_callback', None)
    init_args = json.loads(params.get('_init', '[]'))
    class_name = params.get('_class', None)
    usecache = json.loads(params.get('_usecache', 'false'))
    response = Response()
    if function == 'authenticate' and module_name == 'pico':
        response.content = authenticate(params)
    if usecache and os.path.exists(CACHE_PATH):
        try:
            response.content = open(CACHE_PATH + cache_key(params)).read()
            response.from_cache = True
            print("Serving from cache")
        except IOError:
            pass
    if not response.content:
        authenticated_user = authenticate(params)
        module = load_module(module_name)
        # parameters = map(lambda s: from_json(s, getattr(module, "json_loaders", [])), parameters)
        if class_name:
            init_args = map(lambda s: pico.from_json(s, getattr(module, "json_loaders", [])), init_args)
            response = call_method(module, class_name, function, parameters, init_args)
        else:
            response = call_function(module, function, parameters, authenticated_user)
        response.json_dumpers = getattr(module, "json_dumpers", {})
        if usecache and response.cacheable:
            try:
                os.stat(CACHE_PATH)
            except:
                os.mkdir(CACHE_PATH)
            print("Saving to cache")
            f = open(CACHE_PATH + cache_key(params), 'w')
            f.write(response.content)
            f.close()
    response.callback = callback
    return response

def get_module(params):
    module_name = params.get('_module', '')
    picojs = json.loads(params.get('_picojs', 'false'))
    callback = params.get('_callback', None)
    authenticated_user = authenticate(params)
    response = ''
    module = load_module(module_name)
    response = Response(content=module_dict(module, authenticated_user), callback=callback)
    return response

def module_dict(module, authenticated_user=None):
    module_dict = {}
    classes = inspect.getmembers(module, lambda x: inspect.isclass(x) and x.__module__ == module.__name__ and issubclass(x, pico.Pico))
    for class_name, cls in classes:
        class_dict = {'__class__': class_name}
        for m in inspect.getmembers(cls, inspect.ismethod):
            f = m[1]
            if not (m[0].startswith('_')  or hasattr(f, 'private')) or m[0] == '__init__':
                cachable = ((hasattr(f, 'cacheable') and f.cacheable))
                a = inspect.getargspec(f)
                args = list(reversed(map(None, reversed(a.args), reversed(a.defaults or [None]))))
                args = filter(lambda x: x[0] and not (x[0].startswith('pico_') or x[0] == 'self'), args)
                class_dict[m[0]] = {'args': args, 'cache': cachable, 'doc': f.__doc__}
        module_dict[class_name] = class_dict
    for m in inspect.getmembers(module, lambda x: inspect.isfunction(x) and x.__module__ == module.__name__):
        f = m[1]
        if not (m[0].startswith('_') or hasattr(f, 'private')):
            cachable = ((hasattr(f, 'cacheable') and f.cacheable))
            a = inspect.getargspec(f)
            args = list(reversed(map(None, reversed(a.args), reversed(a.defaults or [None]))))
            print(args)
            args = filter(lambda x: x[0] and not x[0].startswith('pico_'), args)
            module_dict[m[0]] = {'args': args, 'cache': cachable, 'doc': f.__doc__}
    return module_dict

def error(params):
    return Response(content="Error 404. Bad URl", type="plaintext")

def pico_js(params):
    return Response(content=open(path + 'client.js'), type="file")

def load_module(module_name):
    modules_path = './'
    if module_name in sys.modules and RELOAD: 
        del sys.modules[module_name]
    if not sys.path.__contains__(modules_path):
        sys.path.insert(0, modules_path)
    __import__(module_name)
    m = sys.modules[module_name]
    if RELOAD:
        m = reload(m)
    print("Module %s loaded"%module_name)
    if not (hasattr(m, 'pico') and m.pico.magic == pico.magic):
        raise ImportError('This module has not imported pico and therefore is not picoable!')
    return m

def file_handler(path):
    response = Response()
    file_path = ''
    for (url, directory) in STATIC_URL_MAP:
        m = re.match(url, path)
        if m:
            file_path = directory + ''.join(m.groups())
    print("Serving: " + file_path)
    if os.path.isfile(file_path):
        size = os.path.getsize(file_path)
        mimetype = mimetypes.guess_type(file_path)
        response.headers = [
            ("Content-type", mimetype[0]),
            ("Content-length", str(size)),
        ]
        response.content = open(file_path)
        response.type = "file"
    else:
        response.status = "404 NOT FOUND"
        response.content = "File not found!"
        response.type = "plaintext"
    return response

def _hash(s):
    m = hashlib.md5()
    m.update(s)
    return m.hexdigest()
    
def authenticate(params):
    username = params.get('_username', None)
    if username:
        key = params.get('_key', '')
        nonce = params.get('_nonce', '')
        dt =  time.time() - int(nonce)
        if dt > 60:
            raise Exception("Bad nonce. The time difference is: %s"%dt)
        password = USERS.get(username, {}).get('password', None)
        if password and key == _hash(password + str(nonce)):
            print("authenticated_user: %s"%username)
        else:
            raise Exception("Bad username or password")
        return username
    else:
        return None

def wsgi_app(environ, start_response):
    setup_testing_defaults(environ)
    try:
      request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
      request_body_size = 0
    params = environ['wsgi.input'].read(request_body_size)
    params = environ['QUERY_STRING'] + '&' + params
    params = cgi.parse_qs(params)
    for k in params:
        params[k] = params[k][0]
    print('------')
    print(params)
    picojs = json.loads(params.get('_picojs', 'false'))
    try:
        path = environ['PATH_INFO'].split(environ['HTTP_HOST'])[-1]
        if BASE_PATH: path = path.split(BASE_PATH)[1]
        print(path)
        handler = url_handlers.get(path.replace('/pico/', '/'), None)
        if handler:
            response = handler(params)
        else:
            response = file_handler(path)
    except Exception, e:
        response = Response()
        full_tb = traceback.extract_tb(sys.exc_info()[2])
        tb_str = ''
        for tb in full_tb:
            tb_str += "File '%s', line %s, in %s; "%(tb[0], tb[1], tb[2])
        report = {}
        report['exception'] = str(e)
        report['traceback'] = tb_str
        report['url'] = path.replace('/pico/', '/')
        report['params'] = params
        response.content = report
        if picojs:
            response.callback = 'pico.exception'
        else:
            response.status = '500 ' + str(e)
    start_response(response.status, response.headers)
    return response.output


CACHE_PATH = './cache/'
BASE_PATH = ''
url_handlers = {
    '/call/': call,
    '/module/': get_module,
    '/authenticate/': authenticate,
    '/pico.js': pico_js,
    '/client.js': pico_js
}
STATIC_URL_MAP = [
('^/(.*)$', './'),
]
RELOAD = True
STREAMING = False
USERS = {}
if __name__ == '__main__':
    main()
