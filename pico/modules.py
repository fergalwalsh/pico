import inspect
import imp
import sys
import types
import pico

def module_dict(module):
    module_dict = {}
    pico_exports = getattr(module, 'pico_exports', None)
    members = inspect.getmembers(module)
    def function_filter(x):
        (name, f) = x
        return (inspect.isfunction(f) or inspect.ismethod(f)) \
        and (pico_exports == None or name in pico_exports) \
        and f.__module__ == module.__name__ \
        and not name.startswith('_') \
        and not hasattr(f, 'private')

    def class_filter(x):
        (name, f) = x
        return inspect.isclass(f) \
        and (issubclass(f, pico.Pico) or issubclass(f, pico.object)) \
        and (not pico_exports or name in pico_exports) \
        and f.__module__ == module.__name__ \
        and not name.startswith('_') \
        and not hasattr(f, 'private')
    class_defs = [class_dict(cls) for (name, cls) in filter(class_filter, members)]
    function_defs = [func_dict(f, name) for (name, f) in filter(function_filter, members)]
    module_dict['classes'] = class_defs
    module_dict['functions'] = function_defs
    module_dict['__doc__'] = module.__doc__
    return module_dict

def class_dict(cls):
    def method_filter(x):
        (name, f) = x
        return (inspect.isfunction(f) or inspect.ismethod(f)) \
        and (not name.startswith('_') or name == '__init__') \
        and not hasattr(f, 'private')
    class_dict = {'__class__': cls.__name__}
    class_dict['name'] = cls.__name__
    methods = filter(method_filter, inspect.getmembers(cls))
    class_dict['functions'] = [func_dict(f, name) for (name, f) in methods]
    class_dict['__doc__'] = cls.__doc__
    return class_dict

def func_dict(f, name):
    func_dict = {}
    func_dict['name'] = name
    func_dict['cache'] = ((hasattr(f, 'cacheable') and f.cacheable))
    func_dict['stream'] = ((hasattr(f, 'stream') and f.stream))
    func_dict['protected'] = ((hasattr(f, 'protected') and f.protected))
    a = inspect.getargspec(f)
    args = list(reversed(map(None, reversed(a.args), reversed(a.defaults or [None]))))
    func_dict['args'] = filter(lambda x: x[0] and not (x[0].startswith('pico_') or x[0] == 'self'), args)
    func_dict['doc'] = f.__doc__
    return func_dict

def load(module_name, RELOAD=False):
    if module_name == 'pico':
        return sys.modules['pico']
    if module_name == 'pico.modules':
        if module_name in sys.modules:
            return sys.modules[module_name]
        else:
            return sys.modules[__name__]
    modules_path = './'
    if module_name in sys.modules and RELOAD: 
        del sys.modules[module_name]
    if not sys.path.__contains__(modules_path):
        sys.path.insert(0, modules_path)
    m = __import__(module_name)
    m = sys.modules[module_name]
    if RELOAD:
        m = reload(m)
    if not (hasattr(m, 'pico') and m.pico.magic == pico.magic):
        raise ImportError('This module has not imported pico and therefore is not picoable!')
    return m

def module_proxy(cls):
    module_name = cls.__module__
    module = imp.new_module(module_name)
    module.pico = pico
    def method_filter(x):
        (name, f) = x
        return (inspect.isfunction(f) or inspect.ismethod(f)) \
        and (not name.startswith('_') or name == '__init__') \
        and not hasattr(f, 'private')
    methods = filter(method_filter, inspect.getmembers(cls))
    for (name, f) in methods:
        setattr(module, name, f)
    return module

json_dumpers = {
    types.ModuleType:  module_dict
}
