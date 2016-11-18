.. _deployment:

Deployment
============

While Pico includes a :ref:`development_server` it should **only** be used for development. To deploy a Pico app for Internet wide access you should always use a WSGI server together with a HTTP server.

Pico is based on the standard WSGI interface so any compliant WSGI server is capable running a Pico app. 

.. note::
    When other WSGI related documentation refers to the ``WSGI application`` or ``WSGI callable`` this is the instance of the ``PicoApp``, usually called ``app``.

If you have a favourite WSGI/HTTP server combo then go ahead and use that as you normally do. If not, I recommend uWSGI & nginx.


uWSGI
-----

There are **many** configuration options for uWSGI. The most simple way to run a Pico app with uWSGI is like this::

    uwsgi -s /tmp/uwsgi.sock --plugins python --module=api:app

Where ``api`` is the name of the module with a ``PicoApp`` instance called ``app``.


nginx
-----

To setup nginx to proxy requests to this app we do the following::

    server {
        listen   80;
        server_name example.com;

        location / {
                include uwsgi_params;
                uwsgi_pass unix:/tmp/uwsgi.sock;
        }

    }

If we want only requests under a certain path (``/myapp/``) to go to our app we do this::

    server {
        listen   80;
        server_name example.com;

        location /myapp/ {
                include uwsgi_params;
                uwsgi_param HTTP_X_SCRIPT_NAME /myapp/;
                uwsgi_pass unix:/tmp/uwsgi.sock;
        }

    }

Pico uses the ``HTTP_X_SCRIPT_NAME`` variable to correct the path. If you don't include this and make a request to ``example.com/myapp/api/`` it will try to call a function called ``api`` from a module called ``myapp``. Setting ``HTTP_X_SCRIPT_NAME`` correctly tells Pico to strip this part of the path before processing.

If we have static files (html, js, css, images, etc) in a static folder we can do this::

    server {
        listen   80;
        server_name example.com;

        location /myapp/ {
                root path/to/static/;
                try_files $uri @app;
        }

        location @app {
                uwsgi_param HTTP_X_SCRIPT_NAME /myapp/;
                include uwsgi_params;
                uwsgi_pass unix:/tmp/uwsgi.sock;
        }

    }


For more general information about deploying Python WSGI applications with uWSGI and nginx please see the official `Quickstart for Python/WSGI applications <http://uwsgi-docs.readthedocs.io/en/latest/WSGIquickstart.html>`_ 
