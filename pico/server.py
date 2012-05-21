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
        self.cacheable = False
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
        if hasattr(self.content, 'read'):
            self.type = "file"
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
    opts_args = getopt.getopt(sys.argv[1:], "hp:dm", ["help", "port=", "no-reload"])
    args = dict(opts_args[0])
    port = int(args.get('--port', args.get('-p', 8800)))
    multithreaded = '-m' in args
    global RELOAD
    RELOAD = RELOAD and ('--no-reload' not in args)
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
            if f.protected_users == None and f.protected_groups == None:
                return True
            if f.protected_users and authenticated_user in f.protected_users:
                return True
            if f.protected_groups and set(USERS.get(authenticated_user)['groups']).intersection(f.protected_groups):
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
    if hasattr(f, 'cacheable') and f.cacheable:
        response.cacheable = True
        response.headers = [('Cache-Control', 'public, max-age=22222222')]
    if hasattr(f, 'stream') and f.stream and STREAMING:
        response.headers = [('Content-Type', 'text/event-stream')]
        response.type = "stream"
    return response
    

def call_method(module, class_name, method_name, parameters, init_args, authenticated_user=None):
    try:
        obj = getattr(module, class_name)(*init_args)
    except KeyError, e:
        raise Exception("No matching class availble. You asked for %s!"%(class_name))
    r = call_function(obj, method_name, parameters, authenticated_user)
    del obj
    return r 

def cache_key(params):
    params = dict(params)
    if '_callback' in params:
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
            try:
                parameters[k] = json.loads(parameters[k])
            except:
                try:
                    parameters[k] = json.loads(parameters[k].replace("'", '"'))
                except:
                    parameters[k] = parameters[k]
    callback = params.get('_callback', None)
    init_args = json.loads(params.get('_init', '[]'))
    class_name = params.get('_class', None)
    usecache = json.loads(params.get('_usecache', 'false'))
    response = Response()
    if module_name == 'pico':
        if function == 'authenticate':
            response.content = authenticate(params)
    elif usecache and os.path.exists(CACHE_PATH):
        try:
            response.content = open(CACHE_PATH + cache_key(params))
            response.from_cache = True
            print("Serving from cache")
        except IOError:
            pass
    elif not response.content:
        module = load_module(module_name)
        authenticated_user = authenticate(params, module)
        # parameters = map(lambda s: from_json(s, getattr(module, "json_loaders", [])), parameters)
        if class_name:
            init_args = map(lambda s: pico.from_json(s, getattr(module, "json_loaders", [])), init_args)
            response = call_method(module, class_name, function, parameters, init_args)
        else:
            response = call_function(module, function, parameters, authenticated_user)
        response.json_dumpers = getattr(module, "json_dumpers", {})
        print(usecache, response.cacheable)
        if usecache and response.cacheable:
            print("Saving to cache")
            try:
                os.stat(CACHE_PATH)
            except:
                os.mkdir(CACHE_PATH)
            f = open(CACHE_PATH + cache_key(params), 'w')
            out = response.content
            if hasattr(out, 'read'):
                out = out.read()
                response.content.seek(0)
            f.write(out)
            f.close()
    response.callback = callback
    return response

def load(module_name):
    module = load_module(module_name)
    return module_dict(module)

def module_dict(module):
    module_dict = {}
    classes = inspect.getmembers(module, lambda x: inspect.isclass(x) and x.__module__ == module.__name__ and issubclass(x, pico.Pico))
    for class_name, cls in classes:
        class_dict = {'__class__': class_name}
        for m in inspect.getmembers(cls, inspect.ismethod):
            f = m[1]
            if not (m[0].startswith('_')  or hasattr(f, 'private')) or m[0] == '__init__':
                class_dict[m[0]] = func_dict(f)
        module_dict[class_name] = class_dict
    for m in inspect.getmembers(module, lambda x: inspect.isfunction(x) and x.__module__ == module.__name__):
        f = m[1]
        if not (m[0].startswith('_') or hasattr(f, 'private')):
            module_dict[m[0]] = func_dict(f)
    return module_dict

def func_dict(f):
    cachable = ((hasattr(f, 'cacheable') and f.cacheable))
    stream = ((hasattr(f, 'stream') and f.stream))
    protected = ((hasattr(f, 'protected') and f.protected))
    a = inspect.getargspec(f)
    args = list(reversed(map(None, reversed(a.args), reversed(a.defaults or [None]))))
    args = filter(lambda x: x[0] and not (x[0].startswith('pico_') or x[0] == 'self'), args)
    return {'args': args, 'cache': cachable, 'stream': stream, 'protected': protected, 'doc': f.__doc__}

def error(params):
    return Response(content="Error 404. Bad URl", type="plaintext")

def pico_js(params):
    return Response(content=open(path + 'client.js'), type="file")

def load_module(module_name):
    if module_name == 'pico':
        return sys.modules['pico']
    if module_name == 'pico.server':
        if module_name in sys.modules:
            return sys.modules[module_name]
        else:
            return sys.modules[__name__]
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
            ("Cache-Control", 'public, max-age=22222222'),
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
    
def authenticate(params, module=None):
    users = USERS
    if users == {} or users == None:
        if module and hasattr(module, 'PICO_USERS'):
            users = module.PICO_USERS
        else:
            return None
    username = params.get('_username', None)
    if username:
        key = params.get('_key', '')
        nonce = params.get('_nonce', '')
        dt =  time.time() - int(nonce)
        if dt > 60:
            raise Exception("Bad nonce. The time difference is: %s"%dt)
        password = users.get(username, {}).get('password', None)
        # print(password, str(nonce), _hash(password + str(nonce)))
        if password and key == _hash(password + str(nonce)):
            print("authenticated_user: %s"%username)
        else:
            raise Exception("Bad username or password")
        return username
    else:
        return None

def wsgi_app(environ, start_response):
    setup_testing_defaults(environ)
    if environ['REQUEST_METHOD'] == 'OPTIONS':
        # This is to hanle the preflight request for CORS. 
        # See https://developer.mozilla.org/en/http_access_control
        response = Response()
        response.status = "200 OK"
    else:
        try:
          request_body_size = int(environ.get('CONTENT_LENGTH', 0))
        except (ValueError):
          request_body_size = 0
        post_params = environ['wsgi.input'].read(request_body_size)
        get_params = environ['QUERY_STRING'] 
        if get_params == '' and '/call/' in environ['PATH_INFO']:
            path = environ['PATH_INFO'].split('/')
            environ['PATH_INFO'] = '/'.join(path[:-1]) + '/'
            get_params = path[-1]
        params =  {}
        params.update(cgi.parse_qs(get_params))
        params.update(cgi.parse_qs(post_params))
        for k in params:
            params[k] = params[k][0]
        print('------')
        # print(params)
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
            report['params'] = dict([(k, params[k][:100] + ('...' if len(params[k]) > 100 else '')) for k in params])
            print(json.dumps(report, indent=1))
            response.content = report
            if picojs:
                response.callback = 'pico.exception'
            else:
                response.status = '500 ' + str(e)
    response.headers.append(('Access-Control-Allow-Origin', '*'))
    response.headers.append(('Access-Control-Allow-Headers', 'Content-Type'))
    start_response(response.status, response.headers)
    return response.output


CACHE_PATH = './cache/'
BASE_PATH = ''
url_handlers = {
    '/call/': call,
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
