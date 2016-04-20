.. _clientjs:

The Javascript Client
=====================

The Pico Javascript client makes it simple to call your API from a web application.
The client automatically generates proxy module objects and functions for your API so you can call your API functions just like any other library functions. All serialisation of arguments and deserialisation of responses is taken care of by the client so you can focus on your application logic. 

The only thing you need to be aware of is that all function calls are asynchronous so you must pass a callback to each function (or use promises).


Basic Structure
---------------

The basic structure of a web app using the Pico Javascript client is as follows:

.. code-block:: html
    :linenos:
    :emphasize-lines: 5,7,13-15

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

* Line 5: We include Pico's `client.js` library on inside the `head` of the document.
* Line 7: We load our `example` module in a `script` element in the `head`.
* Line 13-15: We use our `hello` function from a `script` element in the `body`.

The order and position of these elements within the document is important. `client.js` must always be loaded before the call to `pico.load` and these both must be in the `head` of the document to ensure they have completed by the time they are used later.


API
---
 
Asynchronous functions
^^^^^^^^^^^^^^^^^^^^^^

Each of these functions is asynchronous, meaning that they will not wait for the result before returning, instead they immediately return and later provide the result by calling a callback with the result as a parameter. For this reason all of these functions have a callback as the last argument.
Example::
    pico.load("example", function(module){
        module.hello(pico.log)
    });

Here we load the `example` module and then call its `hello` function from within a callback once the module has loaded. `module.hello` is also passed a callback which logs the response to the console when it has been retrieved from the server.

An alternative coding style is to use deferred objects. In this style we don't pass a callback to the function, instead we attach a callback to a deferred object returned by the function.
Example::
    d = pico.load("example");
    d.done(function(module){
        module.hello(pico.log);
    });

`d.done(function(...){...})` sets callback to be called once the response is available. The deferred object `d` also allows setting a callback in case of an error `d.fail(function(...){...})`. Pico deferred objects implement the same API as [JQuery deferred objects](http://api.jquery.com/category/deferred-object/).

All functions that take a callback as the last argument can also be used in deferred object style so feel free to use the style you prefer or mix and match as appropriate.


.. js:function:: pico.load(module, [callback])

   :param string module: The name of the module to load.
   :param callback: Gets called with the module object.
   
    Load the Python module named `module`. The module will be available as a global variable of the same name.   
    Submodules may be loaded by using dotted notation e.g. `module.sub_module`.  
    `module` may also be a full url to module on a different Pico server eg. `http://example.com/module/my_module`  
    If provided the `callback` will be called with the module object once it is loaded.  


.. js:function:: pico.load_as(module, alias, [callback])

   :param string module: The name of the module to load.
   :param string module: The global name you want to use for this module.
   :param callback: Gets called with the module object.

    Same as `pico.load` except that the `module` will be available as a global variable called `alias` instead of `module`. Use this version if you already have a variable with the same name as `module` that you do not wish to overwrite or if your module name is long/awkward. 
    Similar to `import foo as bar` in Python.


.. js:function:: pico.reload(module_proxy, [callback])
    
    :param object module_proxy: The module to reload.

    Reload the module definition and recreate the module proxy for the supplied `module_proxy` object.
    Note that `module_proxy` is a module proxy object, not a string.


Synchronous functions
^^^^^^^^^^^^^^^^^^^^^

.. js:function:: pico.help(proxy_object)

    :param object proxy_object: The function or module proxy you want help for.
    :returns: the docstring of a proxy module or function.


Callback helper functions
^^^^^^^^^^^^^^^^^^^^^^^^^
These functions are provided primarily for use as callbacks.


.. js:function:: pico.log

    A simple wrapper for `console.log` that can be passed as a callback to log the response to the Javascript console.


.. js:function:: pico.set(name, [root])

    :param string name: the variable to set the value of.
    :param object root: the object to which the variable will be attached.

    Return a function which may be used as a callback for the setting the value of a variable `name` with the response. If specified, the variable will be attached to `root` instead of the `window` global object.
    `pico.set("foo")` is shorthand for `function(response){window.foo = response}`
