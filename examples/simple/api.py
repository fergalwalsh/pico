import pico
from pico import PicoApp


@pico.expose()
def hello(name):
    return 'Hello %s!' % name


app = PicoApp()
app.register_module(__name__)
