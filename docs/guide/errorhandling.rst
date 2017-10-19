.. _errorhandling:

Error Handling
==============


Pico catches all exceptions raised in your app and returns an appropriate response in JSON format in all cases. If the exception is a subclass of `werkzeug.exceptions.HTTPException` then the exception's `code` and `name` are used for the `status` of the `Response`. The body will be JSON as follows::

    {
        "name": "Forbidden",
        "code": 403,
        "message": "You don't have the permission to access the requested resource. It is either read-protected or not readable by the server."
    }

For all other exceptions a generic `500 Internal Server Error` will be returned with the following body::

    {
        "name": "Internal Server Error",
        "code": 500,
        "message": "'The server encountered an internal error and was unable to complete your request.  Either the server is overloaded or there is an error in the application."
    }

If `PicoApp.debug == True` an extra key `__debug__` will contain details of the internal error::

    {
        "name": "Internal Server Error",
        "code": 500,
        "message": "'The server encountered an internal error and was unable to complete your request.  Either the server is overloaded or there is an error in the application.",
        "__debug__": {
            "stack_trace": [
                "./api.py:25 in fail: raise Exception('fail!')"
            ],
            "message": "fail!",
            "name": "Exception"
        }
    }

.. note:: 
    The debug information is only provided to aid manual debugging. It should not be programatically accessed and should never be enabled on public services as it could easily expose sensitive information.


Sentry
------

`Sentry <https://sentry.io/>`_ is a popular exception reporting system for Python and many other languages. It is so useful and popular in Python web API applications that a Sentry 'mixin' is included in Pico.

To enable it just do the following::

    from raven import Client  # sentry client library 

    from pico import PicoApp
    from pico.extras.sentry import SentryMixin

    class App(SentryMixin, PicoApp):
        sentry_client = Client()  # uses SENTRY_DSN from environment by default

    app = App()
    app.register_module(__name__)
    ...


The `SentryMixin` provides custom `handle_exception` and `prehandle` methods that take care of capturing exceptions and context and sending these to Sentry. When an exception is captured by Sentry a identifier string called `sentry_id` is added to the exception JSON response. This can be used to quickly find the related issue in the Sentry web UI.

For more details please see the `source code <https://github.com/fergalwalsh/pico/blob/master/pico/extras/sentry.py>`_. It is very simple and can easily be overridden or used as a model for other similar services if you wish.
