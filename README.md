##Install
`easy_install pico`
or
`pip install pico`


##Write a Python module:
```python
# example.py
import pico

def hello(name="World"):
    return "Hello " + name

```

## Start the server:
`python -m pico.server`

Or run behind Apache with mod_wsgi

##Call your Python functions from Javascript:

```html
<!DOCTYPE HTML>
<html>
<head>
  <title>Pico Example</title>
    <script src="/pico/client.js"></script>
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

```

## What? How?

* Pico is a very small web application framework for Python & Javascript.
* Pico allows you to write Python modules, classes and functions that can be imported and called directly from Javascript.
* Pico is not a Python to Javascript compiler 
   - Pico is a bridge between server side Python and client side Javascript.
* Pico is a server, a Python libary and a Javascript library! The server is a WSGI application which can be run standalone or behind Apache with mod_wsgi.
* Pico is a Remote Procedure Call (RPC) library for Python without any of the hassle usually associated with RPC. Literally add one line of code (``import pico``) to your Python module to turn it into a web service that is accessible through the Javascript (and Python) Pico client libararies.



The Pico protocal is very simple so it is also easy to communicate with Pico web services from other languages (e.g. Java, Objective-C for mobile applications). See the client.py for a reference implementation.

See the [wiki](https://github.com/fergalwalsh/pico/wiki) for more information.


![](https://nojsstats.appspot.com/UA-34240929-1/github.com)
