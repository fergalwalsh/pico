.. _decorators:

Decorators
==========

Pico includes a number of useful decorators. These decorators all use the `request` object in some way. They are only active when the decorated function is called from Pico. If the the function is imported and called normally like any other Python function then the decorator is a nop.


.. py:module:: pico

.. py:decorator:: expose(*args, **kwargs)

        Exposes the decorated function via the HTTP API.

        Note: This decorator must be the final decorator applied to a function (it must be on top).


.. py:decorator:: prehandle(*args, **kwargs)

    Used to decorate a function of the form `f(request, kwargs)` which is called before the handler function is called. 

    This can be used to modify the request object (e.g. for setting the `.user` attribute based on cookies or headers) or the `kwargs` dictionary passed to the the handler function (e.g. to pop out and check a common `token` query parameter sent with every request)::

        @pico.prehandle()
        def set_user(request, kwargs):
            # check basic_auth
            if request.authorization:
                auth = request.authorization
                if not check_password(auth.username, auth.password):
                    raise Unauthorized("Incorrect username or password!")
                request.user = auth.username
            # check for session cookie
            elif 'session_id' in request.cookies:
                user = sessions.get(request.cookies['session_id'])
                request.user = user['username']
            elif 'token' in kwargs:
                token = kwargs.pop('token')
                user = sessions.get(token)
                request.user = user['username']
            else:
                ...


.. py:module:: pico.decorators

.. py:decorator:: request_args(*args, **kwargs)
    
    Passes the request object or attribute(s) of the request object to the decorated function. It has 3 different forms; a single argument, string keyword arguments, and functional keyword arguments.

    To pass the request object specify the argument name::

        @pico.expose()
        @request_args('req')
        def foo(req, something):
            return req.remote_addr

    To pass an attribute of the request object specify the argument and attribute as a keyword argument pair::

        @pico.expose()
        @request_args(ip='remote_addr')
        def foo(ip, something):
            return ip

    To pass a value computed from the request object specify a keyword argument with a function::
    
        def get_curent_user(request):
            # do something
            return request.user

        @pico.expose()
        @request_args(user=get_curent_user)
        def foo(user, something):
            pass


.. py:decorator:: protected(protector)

    Protects a function by preventing its execution in certain circumstances.
    
    :param function protector: A function of the form `protector(request, wrapped, args, kwargs)` which raises an `exception` or returns `False` when the decorated function should not be executed.

    An example of a function that can only be called via POST::

        def post_only(request, wrapped, args, kwargs):
            if not request.method == 'POST':
                raise MethodNotAllowed()

        @pico.expose()
        @protected(post_only)
        def foo():
            pass


.. py:decorator:: require_method(method)

    Requires that a specific HTTP method is used to call this function.
    
    :param str method: 'GET' or 'POST'
    :raises MethodNotAllowed: if the method is not correct. 

    The same example as above::

        @pico.expose()
        @require_method('POST')
        def foo():
            pass


.. py:decorator:: stream(*args, **kwargs)

    Marks the decorated function as a streaming response. The function should be a generator that `yield` its response. The response is transmitted in the `Event Stream <https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events#Event_stream_format>`_ format.

    An example of a streaming generator that yields messages from pubsub::

        @pico.expose()
        @stream()
        def subscribe(channels):
            pubsub = redis.pubsub()
            pubsub.subscribe(channels)
            while True:
                message = pubsub.get_message()
                yield message

