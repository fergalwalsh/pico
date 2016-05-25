import sys
import importlib
import socket

from werkzeug.serving import run_simple
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import import_string


def run_app(app, ip='127.0.0.1', port=4242, use_debugger=True, use_reloader=True, threaded=True):
    for url in app.url_map:
        print(url)
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/': 'static'
    })
    while True:
        try:
            run_simple(ip, port, app, use_debugger=use_debugger, use_reloader=use_reloader, threaded=threaded)
            break
        except (OSError, socket.error):
            port += 1


if __name__ == '__main__':
    if len(sys.argv) > 1:
        module_name = sys.argv[1]
        module_name = module_name.split('.py')[0]
        app = import_string(module_name + ':app')
    run_app(app)
