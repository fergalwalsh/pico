import sys
import cgi
import json
import os
import time
import mimetypes
import hashlib
import traceback
import getopt
import re
import SocketServer
import threading
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

try:
    import gevent
    import gevent.pywsgi
    use_gevent = True
except ImportError:
    use_gevent = False

import pico
import pico.modules

from pico import PicoError, Response

pico_path = (os.path.dirname(__file__) or '.') + '/'
_server_process = None
pico_exports = []


class APIError(Exception):
    pass


def main():
    opts_args = getopt.getopt(sys.argv[1:], "hp:dm", ["help",
                                                      "port=",
                                                      "debug=",
                                                      "no-reload"])
    args = dict(opts_args[0])
    port = int(args.get('--port', args.get('-p', 8800)))
    multithreaded = '-m' in args
    global RELOAD, DEBUG
    RELOAD = RELOAD and ('--no-reload' not in args)
    DEBUG = args.get('--debug', 'true').lower() == 'true'
    host = '0.0.0.0'  # 'localhost'
    run(host, port, multithreaded)


def run(host='0.0.0.0', port=8800, multithreaded=False):
    server = _make_server(host, port, multithreaded)
    print("Serving on http://%s:%s/" % (host, port))
    if multithreaded:
        print("Using multiple threads.")
    print("URL map: ")
    print('\t' + '\n\t'.join(["%s : %s " % x for x in STATIC_URL_MAP]))
    print("Hit CTRL-C to end")
    server.serve_forever()


def _make_server(host='0.0.0.0', port=8800, multithreaded=False):
    if use_gevent:
        server = gevent.pywsgi.WSGIServer((host, port), wsgi_dev_app)
        global STREAMING
        STREAMING = True
    elif multithreaded:
        class ThreadedTCPServer(SocketServer.ForkingMixIn,
                                WSGIServer):
            pass
        server = ThreadedTCPServer((host, port), WSGIRequestHandler)
        server.set_app(wsgi_dev_app)
    else:
        server = make_server(host, port, wsgi_dev_app)

        def log_message(self, format, *args):
            if not SILENT:
                print(format % (args))
        server.RequestHandlerClass.log_message = log_message
    return server


def start_thread(host='127.0.0.1', port=8800, silent=True):
    global RELOAD, SILENT, _server_process
    RELOAD = False
    SILENT = silent

    class Server(threading.Thread):
        def __init__(self):
            super(Server, self).__init__()
            self._server = _make_server(host, port)

        def run(self):
            self._server.serve_forever()

        def stop(self):
            self._server.shutdown()
            self._server.socket.close()
            print("Pico server has stopped")

    _server_process = Server()
    _server_process.start()
    print("Serving on http://%s:%s/" % (host, port))
    return _server_process


def stop_thread():
    _server_process.stop()
    _server_process.join(1)


def call_function(module, function_name, parameters):
    try:
        f = getattr(module, function_name)
    except AttributeError:
        raise Exception("No matching function availble. "
                        "You asked for %s with these parameters %s!" % (
                            function_name, parameters))
    results = f(**parameters)
    response = Response(content=results)
    if hasattr(f, 'cacheable') and f.cacheable:
        response.cacheable = True
    if hasattr(f, 'stream') and f.stream and STREAMING:
        response.type = "stream"
    elif response.content.__class__.__name__ == 'generator':
        response.type = "chunks"
    return response


def call_method(module, class_name, method_name, parameters, init_args):
    try:
        cls = getattr(module, class_name)
        obj = cls(*init_args)
    except KeyError:
        raise Exception("No matching class availble."
                        "You asked for %s!" % (class_name))
    r = call_function(obj, method_name, parameters)
    del obj
    return r


def cache_key(params):
    params = dict(params)
    if '_callback' in params:
        del params['_callback']
    hashstring = hashlib.md5(str(params)).hexdigest()
    cache_key = "__".join([params.get('_module', ''),
                           params.get('_class', ''),
                           params.get('_function', ''),
                           hashstring])
    return cache_key.replace('.', '_')


def call(params, request):
    func = params.get('_function', '')
    module_name = params.get('_module', '')
    args = {}
    for k in params.keys():
        if not (k.startswith('_') or k.startswith('pico_')):
            params[k] = params[k]
            try:
                args[k] = json.loads(params[k])
            except Exception:
                try:
                    args[k] = json.loads(params[k].replace("'", '"'))
                except Exception:
                    args[k] = params[k]
    callback = params.get('_callback', None)
    init_args = json.loads(params.get('_init', '[]'))
    class_name = params.get('_class', None)
    usecache = json.loads(params.get('_usecache', 'true'))
    x_session_id = params.get('_x_session_id', None)
    if x_session_id:
        request['X-SESSION-ID'] = x_session_id
    response = Response()
    if usecache and os.path.exists(CACHE_PATH):
        try:
            response = serve_file(CACHE_PATH + cache_key(params))
            log("Serving from cache")
        except OSError:
            pass
    if not response.content:
        module = pico.modules.load(module_name, RELOAD)
        json_loaders = getattr(module, "json_loaders", [])
        from_json = lambda s: pico.from_json(s, json_loaders)
        for k in args:
            args[k] = from_json(args[k])
        if class_name:
            init_args = map(from_json, init_args)
            response = call_method(module, class_name, func, args, init_args)
        else:
            response = call_function(module, func, args)
        response.json_dumpers = getattr(module, "json_dumpers", {})
        log(usecache, response.cacheable)
        if usecache and response.cacheable:
            log("Saving to cache")
            try:
                os.stat(CACHE_PATH)
            except Exception:
                os.mkdir(CACHE_PATH)
            f = open(CACHE_PATH + cache_key(params) + '.json', 'w')
            out = response.output
            if hasattr(out, 'read'):
                out = out.read()
                response.output.seek(0)
            else:
                out = out[0]
            f.write(out)
            f.close()
    response.callback = callback
    return response


def _load(module_name, params, environ):
    params['_module'] = 'pico.modules'
    params['_function'] = 'load'
    params['module_name'] = '"%s"' % module_name
    return call(params, environ)


def date_time_string(timestamp=None):
    """Return the current date and time formatted for a message header."""
    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    if timestamp is None:
        timestamp = time.time()
    year, month, day, hh, mm, ss, wd, y, z = time.gmtime(timestamp)
    s = "%s, %02d %3s %4d %02d:%02d:%02d GMT" % (weekdayname[wd],
                                                 day, monthname[month], year,
                                                 hh, mm, ss)
    return s


def serve_file(file_path):
    response = Response()
    fs = os.stat(file_path)
    mimetype = mimetypes.guess_type(file_path)
    response.set_header("Content-length", str(fs.st_size))
    if file_path.endswith('.manifest'):
        response.set_header("Content-type", 'text/cache-manifest')
        response.set_header("Expires", 'access')
    else:
        response.set_header("Content-type", mimetype[0] or 'text/plain')
        response.set_header("Last-Modified", date_time_string(fs.st_mtime))
    response.content = open(file_path, 'rb')
    response.type = "file"
    return response


def static_file_handler(path):
    file_path = ''
    for (url, directory) in STATIC_URL_MAP:
        m = re.match(url, path)
        if m:
            if '{0}' not in directory:
                directory += '{0}'
            file_path = directory.format(*m.groups())

    # if the path does not point to a valid file, try default file
    file_exists = os.path.isfile(file_path)
    if not file_exists:
        file_path = os.path.join(file_path, DEFAULT)
    return serve_file(file_path)


def log(*args):
    if not SILENT:
        print(args[0] if len(args) == 1 else args)


def extract_params(environ):
    params = {}
    # if parameters are in the URL, we extract them first
    get_params = environ['QUERY_STRING']
    if get_params == '' and '/call/' in environ['PATH_INFO']:
        path = environ['PATH_INFO'].split('/')
        environ['PATH_INFO'] = '/'.join(path[:-1]) + '/'
        params.update(cgi.parse_qs(path[-1]))

    # now get GET and POST data
    fields = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
    for name in fields:
        if fields[name].filename:
            upload = fields[name]
            params[name] = upload.file
        elif type(fields[name]) == list and fields[name][0].file:
            params[name] = [v.file for v in fields[name]]
        else:
            params[name] = fields[name].value
    return params


def generate_exception_report(e, path, params):
    response = Response()
    report = {}
    report['exception'] = str(e)
    if DEBUG:
        full_tb = traceback.extract_tb(sys.exc_info()[2])
        tb_str = ''
        for tb in full_tb:
            tb_str += "File '%s', line %s, in %s; " % (tb[0], tb[1], tb[2])
        report['traceback'] = tb_str
    report['url'] = path.replace('/pico/', '/')
    report['params'] = dict([(k, _value_summary(params[k])) for k in params])
    log(json.dumps(report, indent=1))
    response.content = report
    response.status = '500 ' + str(e)
    return response


def _value_summary(value):
    s = repr(value)
    if len(s) > 100:
        s = s[:100] + '...'
    return s


def handle_api_v1(path, params, environ):
    if '/module/' in path:
        module_name = path.split('/')[2]
        return _load(module_name, params, environ)
    elif '/call/' in path:
        return call(params, environ)
    raise APIError()


def handle_api_v2(path, params, environ):
    # nice urls:
    #   /module_name/
    #   /module_name/function_name/?foo=bar
    #   /module_name/function_name/foo=bar # not implemented!
    #   /module_name/class_name/function_name/
    parts = [p for p in path.split('/') if p]
    if len(parts) == 1:
        return _load(parts[0], params, environ)
    elif len(parts) == 2:
        params['_module'] = parts[0]
        params['_function'] = parts[1]
        return call(params, environ)
    elif len(parts) == 3:
        params['_module'] = parts[0]
        params['_class'] = parts[1]
        params['_function'] = parts[2]
        return call(params, environ)
    raise APIError(path)


def handle_pico_js(path, params):
    if path == '/pico.js' or path == '/client.js':
        return serve_file(pico_path + 'client.js')
    raise APIError()


def not_found_error(path):
    response = Response()
    response.status = '404 NOT FOUND'
    response.content = '404 File not found'
    response.type = 'plaintext'
    return response


def wsgi_app(environ, start_response, enable_static=False):
    if environ['REQUEST_METHOD'] == 'OPTIONS':
        # This is to hanle the preflight request for CORS.
        # See https://developer.mozilla.org/en/http_access_control
        response = Response()
        response.status = "200 OK"
    else:
        params = extract_params(environ)
        log('------')
        path = environ['PATH_INFO'].split(environ['HTTP_HOST'])[-1]
        if BASE_PATH:
            path = path.split(BASE_PATH)[1]
        log(path)
        try:
            if '/pico/' in path:
                path = path.replace('/pico/', '/')
                try:
                    response = handle_api_v1(path, params, environ)
                except APIError:
                    try:
                        response = handle_pico_js(path, params)
                    except APIError:
                        try:
                            response = handle_api_v2(path, params, environ)
                        except APIError:
                            response = not_found_error(path)
            elif enable_static:
                try:
                    response = static_file_handler(path)
                except OSError, e:
                    response = not_found_error(path)
            else:
                response = not_found_error(path)
        except PicoError, e:
            response = e.response
        except Exception, e:
            response = generate_exception_report(e, path, params)
    start_response(response.status, response.headers)
    return response.output


def wsgi_dev_app(environ, start_response):
    return wsgi_app(environ, start_response, enable_static=True)


CACHE_PATH = './cache/'
BASE_PATH = ''
STATIC_URL_MAP = [
    ('^/(.*)$', './'),
]
DEFAULT = 'index.html'
RELOAD = True
STREAMING = False
SILENT = False
DEBUG = False

if __name__ == '__main__':
    main()
