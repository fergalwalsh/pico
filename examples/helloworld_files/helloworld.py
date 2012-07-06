import pico

def hello():
    return "Hello World"

def hi(name="World"):
    return "Hello %s"%name

def getLineNumbers(name, f):
    return 'Hello %s, your file has %s lines' % (name, len(f.readlines()))
