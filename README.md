## Install
`pip install --upgrade pico`


## Write a Python module:
```python
# example.py
import pico
from pico import PicoApp


@pico.expose()
def hello(who):
    s = "hello %s!" % who
    return s


@pico.expose()
def goodbye(who):
    s = "goodbye %s!" % who
    return s


app = PicoApp()
app.register_module(__name__)

```

## Start the server:
`python -m pico.server example`


## Call your http api functions from with any http client:
`curl http://localhost:4242/example/hello/?who="fergal"`

`curl http://localhost:4242/example/goodbye/?who="fergal"`


## Using the Javascript client:

```html
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
  var example = pico.importModule('example')
  example.hello("Fergal").then(function(response){
    document.getElementById('message').innerHTML = response;  
  });
  </script>
</body>
</html>

```

## Using the Python client:

```python
import pico.client

example = pico.client.load('http://localhost:4242/example')
example.hello('World')

```
