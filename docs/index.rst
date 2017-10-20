.. Pico documentation master file, created by
   sphinx-quickstart on Wed Apr 20 13:40:42 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pico: Simple Python HTTP APIs
================================

Release v\ |version|. (:ref:`installation`)

Pico is a very small HTTP API framework for Python. It enables you to write HTTP
APIs with minimal fuss, overhead and boilerplate code.

.. code-block:: python
   :caption: example.py

    import pico
    from pico import PicoApp

    @pico.expose()
    def hello(who="world"):
        s = "hello %s!" % who
        return s


    @pico.expose()
    def goodbye(who):
        s = "goodbye %s!" % who
        return s


    app = PicoApp()
    app.register_module(__name__)


Start the development server::

  python -m pico.server example

Call your http api functions from with any http client::

  curl http://localhost:4242/example/hello/
  curl http://localhost:4242/example/hello/?who="fergal"
  curl http://localhost:4242/example/goodbye/?who="fergal"


Use the Javascript client.

.. code-block:: html
  :caption: index.html

  <!DOCTYPE HTML>
  <html>
  <head>
    <title>Pico Example</title>
      <!-- Load the pico Javascript client, always automatically available at /pico.js -->
      <script src="/pico.js"></script>
       <!-- Load our example module -->
      <script src="/example.js"></script>
  </head>
  <body>
    <p id="message"></p>
    <script>
    example.hello("Fergal").then(function(response){
      document.getElementById('message').innerHTML = response;  
    });
    </script>
  </body>
  </html>


Use the Python client.

.. code-block:: python
  :caption: client.py

  import pico.client
  
  example = pico.client.load('http://localhost:4242/example')
  example.hello('World')



.. _features:

Features
--------

- Automatic URL routing
- Decorators
- Automatic JSON serialisation
- Automatic argument parsing & passing
- Simple streaming responses
- Development server with debugger
- WSGI Compliant
- Built upon `Werkzeug <http://werkzeug.pocoo.org/>`_
- Python Client
- Javascript Client



.. _installation:

.. include:: guide/installation.rst


The User Guide
--------------

An introduction to Pico and a guide to how to use it.

.. toctree::
   :maxdepth: 2

   guide/intro
   guide/installation
   guide/decorators
   guide/clientjs
   guide/clientpy
   guide/deployment
   guide/development_server
   guide/errorhandling
   guide/picoapp


Acknowledgements
----------------

Pico development is kindly supported by `Hipo <http://hipolabs.com>`_.
