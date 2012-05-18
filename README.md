Pico is a very small web application framework for Python & Javascript.

Pico allows you to write Python modules, classes and functions that can be imported and called directly from Javascript.

Pico is NOT a Python to Javascript compiler - Pico IS a bridge between server side Python and client side Javascript.

It is a server, a Python libary and a Javascript library! The server is a WSGI application which can be run standalone or behind Apache with mod_wsgi.

Pico is basically a Remote Procedure Call (RPC) library for Python without any of the hassle usually associated with RPC. Literally add one line of code (``import pico``) to your Python module to turn it into a web service that is accessible through the Javascript (and Python) Pico client libararies.

The Pico protocal is very simple so it is also easy to communicate with Pico web services from other languages (e.g. Java, Objective-C for mobile applications). See the client.py for a reference implementation.

See the [wiki](https://github.com/fergalwalsh/pico/wiki) for more information.
