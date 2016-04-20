.. Pico documentation master file, created by
   sphinx-quickstart on Wed Apr 20 13:40:42 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Pico: Python HTTP APIs for Humans
================================

Release v\ |version|. (:ref:`installation`)

Pico is a very small HTTP API framework for Python. It enables you to write HTTP
APIs with minimal fuss, overhead and boilerplate code.

.. code-block:: python
   :caption: example.py

    from pico import PicoApp

    app = PicoApp()


    @app.expose()
    def hello(who="world"):
        s = "hello %s!" % who
        return s


    @app.expose()
    def goodbye(who):
        s = "goodbye %s!" % who
        return s


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
    <script src="client.js"></script>
    <script>
      pico.load("example");
    </script>
  </head>
  <body>
    <p id="message"></p>
    <script>
      example.hello("Fergal", function(response){
        document.getElementById('message').innerHTML = response;  
      });
    </script>
  </body>
  </html>

.. _features:

Features
--------

- Automatic URL routing
- Decorators
- Automatic JSON serialisation
- Automatic argument parsing & passing
- Simple streaming responses
- Development server with debugger
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
   guide/clientjs
   guide/clientpy


