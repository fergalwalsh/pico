# api.py

import time

import pico
from pico import PicoApp
from pico.decorators import request_args, set_cookie, delete_cookie, stream
from pico.decorators import header, cookie

from werkzeug.exceptions import Unauthorized, ImATeapot, BadRequest


@pico.expose()
def hello(who='world'):
    return 'Hello %s' % who


@pico.expose()
def multiply(x, y):
    return x * y


@pico.expose()
def fail():
    raise Exception('fail!')


@pico.expose()
def make_coffee():
    raise ImATeapot()


@pico.expose()
def upload(upload, filename):
    if not filename.endswith('.txt'):
        raise BadRequest('Upload must be a .txt file!')
    return upload.read().decode()


@pico.expose()
@request_args(ip='remote_addr')
def my_ip(ip):
    return ip


@pico.expose()
@request_args(ip=lambda req: req.remote_addr)
def my_ip3(ip):
    return ip


@pico.prehandle()
def set_user(request, kwargs):
    if request.authorization:
        if request.authorization.password != 'secret':
            raise Unauthorized('Incorrect username or password')
        request.user = request.authorization.username
    else:
        request.user = None


@pico.expose()
@request_args(username='user')
def current_user(username):
    return username


@pico.expose()
@request_args(session=cookie('session_id'))
def session_id(session):
    return session


@pico.expose()
@set_cookie()
def start_session():
    return {'session_id': '42'}


@pico.expose()
@delete_cookie('session_id')
def end_session():
    return True


@pico.expose()
@request_args(session=header('x-session-id'))
def session_id2(session):
    return session


@pico.expose()
@stream()
def countdown(n=10):
    for i in reversed(range(n)):
        yield '%i' % i
        time.sleep(0.5)


@pico.expose()
def user_description(user):
    return '{name} is a {occupation} aged {age}'.format(**user)


@pico.expose()
def show_source():
    return open(__file__.replace('.pyc', '.py')).read()


app = PicoApp()
app.register_module(__name__)
