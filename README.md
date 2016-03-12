##Install
`pip install pico`


##Write a Python module:
```python
# example.py
from pico import PicoApp

app = PicoApp()


@app.expose()
def hello(who):
    s = "hello %s!" % who
    return s


@app.expose()
def goodbye(who):
    s = "goodbye %s!" % who
    return s

```

## Start the server:
`python -m pico.server example`

##Call your http api functions from Javascript:

```html
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

```

##Call your http api functions from with any http client:
`curl http://localhost:4242/example/hello/?who="fergal"`
`curl http://localhost:4242/example/goodbye/?who="fergal"`




The Pico protocal is very simple so it is also easy to communicate with Pico web services from other languages (e.g. Java, Objective-C for mobile applications). See the client.py for a reference implementation.

See the [wiki](https://github.com/fergalwalsh/pico/wiki) for more information.


![](https://nojsstats.appspot.com/UA-34240929-1/github.com)
