# coding: utf-8

from __future__ import unicode_literals

import time

import pico
from pico import PicoApp

from pico.decorators import require_method, request_args, set_cookie, delete_cookie, stream
from pico.decorators import header, cookie, basic_auth


@pico.expose()
def hello(who='world'):
    return 'Hello %s' % who


@pico.expose()
def multiply(x, y):
    return x * y


@pico.expose()
def upload(upload):
    return upload.read().decode()


@pico.expose()
@require_method('POST')
def post_only():
    return True


@pico.expose()
def not_post_only():
    return post_only()


@pico.expose()
@request_args(ip='remote_addr')
def my_ip1(ip):
    return ip


@pico.expose()
@request_args('req')
def my_ip2(req):
    return req.remote_addr


@pico.expose()
@request_args(ip=lambda req: req.remote_addr)
def my_ip3(ip):
    return ip


@pico.prehandle()
def set_user(request, kwargs):
    request.user = 'arthurd42'


@pico.expose()
@request_args(username='user')
def current_user(username):
    return username


@pico.expose()
@request_args(auth=basic_auth())
def basicauth(auth):
    return auth


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
@request_args(session=header('session-id'))
def session_id2(session):
    return session


@pico.expose()
@stream()
def streamer(n=10):
    for i in range(n):
        yield '%i' % i
        time.sleep(0.5)


@pico.expose()
def fail():
    raise Exception('oops!')

app = PicoApp()
app.register_module(__name__)
