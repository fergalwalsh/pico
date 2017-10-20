.. _picoapp:

The PicoApp
==========

The `PicoApp` object is the actual WSGI application that gets called by the web server. It is the initial handler and router of all requests and acts as a registry of exposed modules and functions. Despite its central role in the execution of your application it has a very small public API. Many applications will simply create a `PicoApp` object and register modules.

Occasionally we need to override some of the functionality of `PicoApp` to implement app-wide custom logic. The most commonly overridden methods are `prehandle` and `handle_exception`. 


.. py:module:: pico

.. py:class:: PicoApp

    .. py:method:: register_module(module, alias=None)

        Imports and registers the exposed functions of the specified module.

        If an alias is provided this is used as the namespace for the exposed functions, otherwise the module name is used.

    .. py:method:: prehandle(request, kwargs)

        Called just before every execution of an exposed function.

        This method does nothing by default but may be overridden to apply modifications to the request object on every request. This is useful for performing authentication and setting a `user` attribute on the request object for example.

    .. py:method:: posthandle(request, response)

        Called after every execution of an exposed function and after any error handling.

        This method does nothing by default but may be overridden to apply modifications to the response object on every request, to clear a request cache, close database connections, etc.

    .. py:method:: handle_exception(exception, request, **kwargs)

        Called when any uncaught exception occurs.

        By default this returns a `JsonErrorResponse` with a `500 Internal Server Error` status. This can be overridden to customise error handling.


    .. py:method:: json_load(value)

        This method is used internally to load JSON. It can be overridden if you require custom JSON logic.

    .. py:method:: json_dump(value)

        This method is used internally to dump JSON. It can be overridden if you require custom JSON logic.

