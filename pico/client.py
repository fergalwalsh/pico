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

__author__ = 'Fergal Walsh'
__version__ = '2.0.0-dev'


class PicoClient(object):
    def __init__(self, url):
        self.url = url
        self.session = requests.Session()
        self.session.timeout = 60.0

    def _request(self, url, args={}, timeout=None, headers={}):
        if not url.startswith('http'):
            url = self.url + url
        timeout = timeout or self.session.timeout
        if timeout < 0:
            timeout = None
        headers.update({'content-type': 'application/json'})
        body = json.dumps(args)
        r = self.session.post(url, data=body, timeout=timeout, headers=headers)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and 'exception' in data:
            raise Exception(data['exception'])
        else:
            return data

    def _stream(self, url, args={}, timeout=None, headers={}):
        if not url.startswith('http'):
            url = self.url + url
        timeout = timeout or self.session.timeout
        if timeout < 0:
            timeout = None
        r = self.session.get(url, params=args, stream=True, timeout=timeout, headers=headers)
        for line in r.iter_lines(chunk_size=1):
            line = line.decode()
            if 'data:' in line:
                s = json.loads(line[6:])
                if s == 'PICO_CLOSE_STREAM':
                    return
                else:
                    yield s

    def _call_function(self, module, function, args):
        url = '{base_url}/{module}/{function}/'.format(base_url=self.url, module=module.replace('.', '/'), function=function)
        return self._request(url, args)

    def load(self, module_name):
        """
        Load a remote module
        example = client.load("example")
        """
        module_dict = self._request(self.url + '/' + module_name.replace('.', '/'))
        return self.load_from_dict(module_dict)

    def load_from_dict(self, module_def):
        """
        Load a module from a definition dictionary
        example = client.load_from_dict({...})
        """
        module_name = module_def['name']
        module = imp.new_module(module_name)
        module.__doc__ = module_def['doc']
        module._pico_client = self
        for function_def in module_def['functions']:
            args = [(arg['name'], arg['default']) for arg in function_def['args']] + [('_timeout', None), ('_headers', {})]
            args_string = ', '.join(["%s=%r" % (a, d) for a, d in args])
            code = 'def {name}({arg_string}):\n'
            code += '    """ {docstring} """\n'
            code += '    args = locals()\n'
            code += '    args.pop("_timeout")\n'
            code += '    args.pop("_headers")\n'
            if function_def.get('stream'):
                code += '    return _pico_client._stream("{url}", args, timeout=_timeout, headers=_headers)'
            else:
                code += '    return _pico_client._request("{url}", args, timeout=_timeout, headers=_headers)'
            code = code.format(
                name=function_def['name'],
                docstring=function_def['doc'],
                arg_string=args_string,
                url=function_def['url'],
            )
            exec(code, module.__dict__)
        return module


def load(module_url):
    url, module_name = module_url.rsplit('/', 1)
    client = PicoClient(url)
    return client.load(module_name)
