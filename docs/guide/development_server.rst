.. _development_server:

Development Server
==================

Pico includes a development server, based on Werkzeug's amazing development server. It auto reloads code when it changes and includes and interactive debugger.

To start a Pico application with the development server simply run::

    $ python -m pico.server myapp
     * Running on http://127.0.0.1:4242/ (Press CTRL+C to quit)
     * Restarting with fsevents reloader


This assumes your ``PicoApp`` object instance is called ``app`` in a module called ``myapp``.
If your app instance is named something else like ``foo`` then you need to specify it as follows::

    python -m pico.server myapp:foo


The server chooses the first available port starting with ``4242``.

.. warning::
    This server is for development only. It is inefficient and insecure compared to production web/application servers. Please read the :ref:`deployment` guide for details on how to deploy a Pico app in production.
