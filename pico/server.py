import sys
import importlib

from werkzeug.serving import run_simple
from werkzeug.wsgi import SharedDataMiddleware


def run_app(app, ip='127.0.0.1', port=4242, use_debugger=True, use_reloader=True, threaded=True):
    for url in app.url_map:
        print(url)
    app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
        '/': 'static'
    })
    run_simple(ip, port, app, use_debugger, use_reloader, threaded=threaded)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        for module_name in sys.argv[1:]:
            m = importlib.import_module(module_name.split('.py')[0])
            app = m.app
    run_app(app)
