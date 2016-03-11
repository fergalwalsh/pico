"""
Load and call functions from a remote pico module.

example = pico.client.load('example')
s = example.hello()
# s == "Hello World"

s = example.hello("Python")
# s == "Hello Python"

Use help(example.hello) or example.hello? as normal to check function parameters and docstrings.
"""

import pico.pragmaticjson as json
import imp
import requests
import pico

__author__ = 'Fergal Walsh'
__version__ = '2.0.0-dev'


class PicoClient(object):
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()

    def _get(self, url, args={}):
        body = json.dumps(args)
        data = self.session.post(url, data=body, timeout=5.0, headers={'content-type': 'application/json'}).json()
        if isinstance(data, dict) and 'exception' in data:
            raise Exception(data['exception'])
        else:
            return data

    def _stream(self, url, args):
        r = self.session.get(url, params=args, stream=True)
        for line in r.iter_lines(chunk_size=1):
            if 'data:' in line:
                yield json.loads(line[6:])

    def _call_function(self, module, function, args, stream=False):
        url = '{base_url}/{module}/{function}/'.format(base_url=self.url, module=module.replace('.', '/'), function=function)
        if not stream:
            return self._get(url, args)
        else:
            return self._stream(url, args)

    def load(self, module_name):
        """
        Load a remote module
        example = pico.client.load("example")
        """
        module_dict = self._get(self.url + '/' + module_name)
        module = imp.new_module(module_name)
        module.__doc__ = module_dict['doc']
        functions = module_dict['functions']
        for function_def in functions:
            name = function_def['name']
            args = function_def['args']
            args_string = ', '.join(["%s=%s" % (arg, json.dumps(default).replace("null", "None")) for arg, default in args if arg is not None])
            stream = function_def['stream']
            docstring = function_def['doc']
            module._pico_client = self
            code = 'def %s(%s):\n    """ %s """\n    return _pico_client._call_function("%s", "%s", locals(), %s)' % (
                name, args_string, docstring, module_name, name, stream)
            exec code in module.__dict__
        return module


def load(module_url):
    url, module_name = module_url.rsplit('/', 1)
    client = PicoClient(url)
    return client.load(module_name)
