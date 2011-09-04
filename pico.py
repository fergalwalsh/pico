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

import wsgiref
import SocketServer

import pico as caching

cacheable_functions = {}

def cacheable(func):
    func.cacheable = True
    cacheable_functions.setdefault(func.__module__, {})[func.__name__] = True
    return func


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
    print('\t' + '\n\t'.join(["%s : %s "%(url, path) for url, path in static_url_map]))
    print("Hit CTRL-C to end")
    server.serve_forever()
    

class Pico(object):
    def __init__(self):
        pass
    
    

def call_function(module, function_name, parameters):
    try:
        f = getattr(module, function_name)
    except AttributeError, e:
        raise Exception("No matching function availble. You asked for %s with these parameters %s!"%(function, parameters))
    results = f(*parameters)
    return results

def call_method(module, class_name, method_name, parameters, init_args):
    try:
        obj = getattr(module, class_name)(*init_args)
    except KeyError, e:
        raise Exception("No matching class availble. You asked for %s!"%(class_name))
    try:
        f = getattr(obj, method_name)
    except AttributeError, e:
        raise Exception("No matching method availble. You asked for %s with these parameters %s!"%(method_name, parameters))
    results = f(*parameters)
    return results

def call(params, url):
    function = params.get('function', '')
    parameters = params.get('parameters', '[]')
    parameters = parameters.replace("'", '"')
    parameters = json.loads(parameters)
    callback = params.get('callback', '')
    module_name = params.get('module', '')
    init_args = json.loads(params.get('init', '[]'))
    class_name = params.get('class', None)
    # check if it is a cacheable function
    should_cache = caching.cacheable_functions.get(module_name, {}).get(function, False)
    response = None
    if should_cache:
        cache_path = './cache/'
        cache_filename = module_name + '_' + function + '_' + str(hashlib.md5(params.get('parameters', '[]')).hexdigest())
        try:
            response = open(cache_path + cache_filename).read()
            print("Serving from cache")
        except IOError:
            pass
    if not response:
        module = load_module(module_name)
        parameters = map(lambda s: from_json(s, getattr(module, "json_loaders", [])), parameters)
        if class_name:
            init_args = map(lambda s: from_json(s, getattr(module, "json_loaders", [])), init_args)
            response = call_method(module, class_name, function, parameters, init_args)
        else:
            response = call_function(module, function, parameters)
        response = to_json(response, getattr(module, "json_dumpers", {}))
        if should_cache:
            print("Saving to cache")
            f = open(cache_path + cache_filename, 'w')
            f.write(response)
            f.close()
    if callback != '':
        response = callback + '(' + response + ')'
    return response

def get_module(params, url):
    module_name = params.get('module', '')
    picojs = json.loads(params.get('picojs', 'false'))
    callback = params.get('callback', '')
    response = ''
    if not picojs: response += base(url=url)
    if module_name in globals():
        print('loading class')
        module = globals()[module_name]
        js_proxy = js_proxy_class(module)
    else:
        module = load_module(module_name)
        js_proxy = js_proxy_module(module)
    response += 'pico.urls["%s"] = "%s";\n'%(module_name, url)
    a = "window"
    for n in module_name.split('.'):
        response += 'if(%s.%s == undefined)%s.%s={}; '%(a,n,a,n)
        a += "." + n
    response += "\n%s = %s;"%(module_name, js_proxy)
    if callback != '':
        response += "\n%s(%s);"%(callback, module_name)
    return response


def base(params=None, url=''):
    response = """
if(typeof pico === 'undefined')
{
    String.prototype.contains = function (sub){return(this.indexOf(sub)!=-1);};
    if(!window.console) console = {'debug': function(x){}, 'log': function(x){}};
    pico = {};
    pico.url = '%(url)s';
    pico.urls = [];
    pico.cache = {};
    pico.onerror = function(e){console.error(e)}
    pico.get = function(url, callback)
    {
        var callback_name = 'console.log';
        if(callback)
        {
            if(!url.contains('?')) url += '?';
            callback_name = 'jsonp' + Math.floor(Math.random()*10e10);
            window[callback_name] = function(data){callback(data); delete window[callback_name]};
            url += '&callback=' + callback_name;
        }
        if(url.contains('?')) url += '&picojs=true';
        url = encodeURI(url);
        var elem;
        if(document.getElementsByTagName("body").length > 0)
        {
            elem = document.getElementsByTagName("body")[0];
            if(url.substr(-4) == '.css'){
                var style = document.createElement('link');
                style.type = 'text/css';
                style.src = url;
                style.rel = "stylesheet";
                style.onload = function(){document.getElementsByTagName("body")[0].removeChild(this)};
                elem.appendChild(script);
            }
            else{
                var script = document.createElement('script');
                script.type = 'text/javascript';
                script.src = url;
                script.onload = function(){document.getElementsByTagName("body")[0].removeChild(this)};
                elem.appendChild(script);
            }
            console.log("pico.get in BODY " + url);
        }
        else
        {
            console.log("pico.get in HEAD " + url);
            if(url.substr(-4) == '.css'){
                document.write('<link type="text/css" href="' + url + '" rel="stylesheet" />');
            }
            else
            {
                document.write('<script type="text/javascript" onload="'+callback_name+'()"  src="' + url + '"></scr' + 'ipt>');
            }
            
        }
    }
    pico.call_module_function = function(module, function_name, args, use_cache)
    {
        var args = Array.prototype.slice.call(args);
        args = args.map(function(a){return (isFinite(a) && parseFloat(a)) || a});
        if(args.slice(-1)[0] instanceof Function) var callback = args.pop(-1);
        else var callback = function(response){console.debug(response)};
        var url = pico.urls[module] + '/pico/call/?module='+module+'&function='+function_name+'&parameters='+JSON.stringify(args);
        if(use_cache && pico.cache[url])
        {
            console.log("Served from client side cache: " + url);
            callback(pico.cache[url]);
        }
        else
        {
            if(use_cache)
            {
                var new_callback = function(callback, response){ pico.cache[url] = response; callback(response) }
                callback = pico.partial(new_callback, callback);
            }
            pico.get(url, callback);
        }
    }
    pico.call_class_method = function(object, method_name, args, use_cache)
    {
        var module = object.__module__;
        var class_name = object.__class__;
        var init_args = object.__args__;
        
        var args = Array.prototype.slice.call(args);
        args = args.map(function(a){return (isFinite(a) && parseFloat(a)) || a});
        if(args.slice(-1)[0] instanceof Function) var callback = args.pop(-1);
        else if(object.__default_callback__) var callback = object.__default_callback__;
        else var callback = function(response){console.debug(response)};
        
        var new_callback = function(callback, response){ callback(response, {'object': object, 'method_name': method_name});  };
        callback = pico.partial(new_callback, callback);
        
        var url = pico.urls[module] + '/pico/call/?module='+module+'&class=' + class_name + '&function='+method_name+'&parameters='+JSON.stringify(args);
        if(init_args.length > 0) url+= '&init=' + JSON.stringify(init_args);
        if(use_cache && pico.cache[url])
        {
            console.log("Served from client side cache: " + url);
            callback(pico.cache[url]);
        }
        else
        {
            if(use_cache)
            {
                var new_callback = function(callback, response){ pico.cache[url] = response; callback(response) }
                callback = pico.partial(new_callback, callback);
            }
            pico.get(url, callback);
        }
    }
    pico.import = function(module, result_handler)
    {
        if(module.substr(0, 7) != 'http://') var url = pico.url + '/pico/module/?module='+module;
        else var url = module;
        pico.get(url, result_handler);
    }
    pico.partial = function(func /*, 0..n args */) {
        var args = Array.prototype.slice.call(arguments, 1);
        return function() {
            var allArguments = args.concat(Array.prototype.slice.call(arguments));
            return func.apply(this, allArguments);
        };
    }
    pico.main = function(){console.log('Pico: DOMContentLoaded')};
    document.addEventListener('DOMContentLoaded', function(){pico.main()}, false);
}
"""%{'url': url}
    return response

def error(params):
    return "Error 404. Bad URl"

def load_module(module_name):
    modules_path = './'
    caching.cacheable_functions[module_name] = {}
    if module_name in sys.modules: del sys.modules[module_name]
    if not sys.path.__contains__(modules_path):
        sys.path.insert(0, modules_path)
    __import__(module_name)
    m = sys.modules[module_name]
    m = reload(m)
    print("Module %s loaded"%module_name)
    if not (hasattr(m, 'pico') and m.pico.magic == magic):
        raise ImportError('This module has not imported pico and therefore is not picoable!')
    return m

def js_proxy_module(module):
    out = "{\n"
    classes = inspect.getmembers(module, lambda x: inspect.isclass(x) and x.__module__ == module.__name__ and issubclass(x, Pico))
    for class_name, cls in classes:
        out += '"%s": %s,\n'%(class_name, js_proxy_class(cls))
    functions = []
    for m in inspect.getmembers(module, inspect.isfunction):
        if not m[0].startswith('_'):
            #cachable = '@pico.caching.cacheable' in inspect.getsource(m[1])
            cachable = False
            functions.append((m[0],inspect.getargspec(m[1])[0], cachable))
    object_name = module.__name__
    for function_name, parameters, cache in functions:
        params = parameters + ['callback']
        param_string = ', '.join(params)
        out += """
        "%(function)s": function(%(params)s){
            pico.call_module_function("%(class)s", "%(function)s", arguments, %(cache)s)
        },
        \n"""%{'function': function_name, 'params': param_string, 'class': object_name.lower(), 'cache': str(cache).lower()}
    out += "}\n"
    return out

def js_proxy_class(cls):
    methods = {}
    for m in inspect.getmembers(cls, inspect.ismethod):
        if not m[0].startswith('_') or m[0] == '__init__':
            #cachable = '@pico.caching.cacheable' in inspect.getsource(m[1])
            cachable = False
            methods[m[0]] = (m[0],inspect.getargspec(m[1])[0], cachable)
    class_name = cls.__name__
    out = """(function() {
    var %(class)s = function(%(args)s) {
        this.__args__ = Array.prototype.slice.call(arguments);
        this.__module__ = "%(module)s";
        this.__class__ =  "%(class)s";
    }
    """%{'class': class_name, 'args': ', '.join(methods['__init__'][1][1:]), 'module': cls.__module__}
    for method_name, parameters, cache in methods.values():
        params = parameters[1:] + ['callback']
        param_string = ', '.join(params)
        out += """
    %(class)s.prototype.%(method)s = function(%(params)s){
        pico.call_class_method(this, "%(method)s", arguments, %(cache)s)
    };
    """%{'class': class_name, 'method': method_name, 'params': param_string, 'class': class_name, 'cache': str(cache).lower()}
    out += """return %(class)s;
    })()"""%{'class': class_name}
    return out


def convert_keys(obj):
    if type(obj) == dict: # convert non string keys to strings
        for k in obj:
            convert_keys(obj[k])
            if not isinstance(k, basestring):
                obj[str(k)] = obj[k]
                del obj[k]

    
def to_json(obj, _json_dumpers = {}):
    class Encoder(json.JSONEncoder):
        def default(self, obj):
            if type(obj) in _json_dumpers:
                obj = _json_dumpers[type(obj)](obj)
                convert_keys(obj)
                return obj
            if hasattr(obj, 'json'):
                return json.loads(obj.json)
            elif hasattr(obj, 'tolist'):
                return obj.tolist()
            elif hasattr(obj, '__iter__'):
                return list(obj)
            else:
                return str(obj)
    
        def encode(self, obj):
            convert_keys(obj)
            return json.JSONEncoder.encode(self, obj)
    for k in json_dumpers:
        if k not in _json_dumpers:
            _json_dumpers[k] = json_dumpers
    s = json.dumps(obj, cls=Encoder, separators=(',',':'))
    return s

def from_json(v, _json_loaders = []):
    if isinstance(v, basestring):
        _json_loaders.extend(json_loaders)
        for f in _json_loaders:
            try:
                v = f(v)
                break
            except Exception, e:
                continue
    return v


def wsgi_app(environ, start_response):
    setup_testing_defaults(environ)
    try:
      request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    except (ValueError):
      request_body_size = 0
    # print(environ)
    # 'wsgi.url_scheme': 'http'
    # 'PATH_INFO': '/index.html'
    # 'HTTP_HOST': 'localhost:8800'
    # 'QUERY_STRING': 'module=Test'
    params = environ['wsgi.input'].read(request_body_size)
    params = environ['QUERY_STRING'] + '&' + params
    params = cgi.parse_qs(params)
    for k in params:
        params[k] = params[k][0]
    print('------')
    print(params)
    picojs = json.loads(params.get('picojs', 'false'))
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    try:
        url = urlparse.urlunsplit((environ['wsgi.url_scheme'], environ['HTTP_HOST'], environ['PATH_INFO'], environ['QUERY_STRING'], ''))
        path = environ['PATH_INFO']
        if base_path: path = path.split(base_path)[1]
        print(path)
        base_url = urlparse.urlunsplit((environ['wsgi.url_scheme'], environ['HTTP_HOST'], base_path, '', ''))
        handler = url_handlers.get(path, None)
        if handler:
            response = handler(params, base_url)
        else:
            file_path = ''
            for (url, directory) in static_url_map:
                m = re.match(url, path)
                if m:
                    file_path = directory + ''.join(m.groups())
            print("Serving: " + file_path)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                mimetype = mimetypes.guess_type(file_path)
                headers = [
                    ("Content-type", mimetype[0]),
                    ("Content-length", str(size)),
                ]
                response = open(file_path)
            else:
                status = "404 NOT FOUND"
                response = "File not found!"
    except Exception, e:
        full_tb = traceback.extract_tb(sys.exc_info()[2])
        tb_str = ''
        for tb in full_tb:
            tb_str += "File '%s', line %s, in %s; "%(tb[0], tb[1], tb[2])
        response = 'Python exception: %s. %s'%(e, tb_str)
        print(response)
        if picojs: 
            response = 'pico.onerror("' + response + '");'
        else:
            status = '500 ' + str(e)
    start_response(status, headers)
    if isinstance(response, str):
        response = [response,]
    return response


json_dumpers = {
    decimal.Decimal: lambda d: float(d)
}

json_loaders = [
lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
]

base_path = ''
url_handlers = {
    '/pico/call/': call,
    '/pico/module/': get_module,
    '/pico/pico.js': base
}
static_url_map = [
('^/(.*)$', './'),
]
magic = 'hjksdfjgg;jfgfdggldfgj' # used in the check to see if a module has explicitly imported Pico to make it Picoable    
if __name__ == '__main__':
    main()
