import time

from pico import PicoApp

from pico.decorators import require_method, request_arg, set_cookie, delete_cookie, stream
from pico.decorators import header, cookie, basic_auth
app = PicoApp()


@app.expose()
def hello(who='world'):
    return 'Hello %s' % who


@app.expose()
def multiply(x, y):
    return x * y


@app.expose()
def upload(upload):
    return upload.read()


@app.expose()
@require_method('POST')
def post_only():
    return True


@app.expose()
def not_post_only():
    return post_only()


@app.expose()
@request_arg(ip='remote_addr')
def my_ip1(ip):
    return ip


@app.expose()
@request_arg('req')
def my_ip2(req):
    return req.remote_addr


@app.expose()
@request_arg(ip=lambda req: req.remote_addr)
def my_ip3(ip):
    return ip


@app.before_request()
def set_user(request):
    request.user = 'arthurd42'


@app.expose()
@request_arg(username='user')
def current_user(username):
    return username


@app.expose()
@request_arg(auth=basic_auth())
def basicauth(auth):
    return auth


@app.expose()
@request_arg(session=cookie('session_id'))
def session_id(session):
    return session


@app.expose()
@set_cookie()
def start_session():
    return {'session_id': '42'}


@app.expose()
@delete_cookie('session_id')
def end_session():
    return True


@app.expose()
@request_arg(session=header('session-id'))
def session_id2(session):
    return session


@app.expose()
@stream()
def streamer(n=10):
    for i in range(n):
        yield '%i' % i
        time.sleep(0.5)
