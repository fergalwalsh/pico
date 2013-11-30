import inspect
import imp
import os
import sys
import types
import time
import importlib

import pico

_mtimes = {}


def module_dict(module):
    module_dict = {}
    pico_exports = getattr(module, 'pico_exports', None)
    members = inspect.getmembers(module)

    def function_filter(x):
        (name, f) = x
        return ((inspect.isfunction(f) or inspect.ismethod(f))
                and (pico_exports is None or name in pico_exports)
                and f.__module__ == module.__name__
                and not name.startswith('_')
                and not hasattr(f, 'private'))

    def class_filter(x):
        (name, c) = x
        return (inspect.isclass(c)
                and (issubclass(c, pico.Pico) or issubclass(c, pico.object))
                and (pico_exports is None or name in pico_exports)
                and c.__module__ == module.__name__)
    class_defs = map(class_dict, filter(class_filter, members))
    function_defs = map(func_dict, filter(function_filter, members))
    module_dict['classes'] = class_defs
    module_dict['functions'] = function_defs
    module_dict['__doc__'] = module.__doc__
    module_dict['__headers__'] = getattr(module, '__headers__', {})
    return module_dict


def class_dict(x):
    name, cls = x

    def method_filter(x):
        (name, f) = x
        return ((inspect.isfunction(f) or inspect.ismethod(f))
                and (not name.startswith('_') or name == '__init__')
                and not hasattr(f, 'private'))
    class_dict = {'__class__': cls.__name__}
    class_dict['name'] = name
    methods = filter(method_filter, inspect.getmembers(cls))
    class_dict['__init__'] = func_dict(methods.pop(0))
    class_dict['functions'] = map(func_dict, methods)
    class_dict['__doc__'] = cls.__doc__
    class_dict['__headers__'] = getattr(cls, '__headers__', {})
    return class_dict


def func_dict(x):
    name, f = x
    func_dict = {}
    func_dict['name'] = name
    func_dict['cache'] = ((hasattr(f, 'cacheable') and f.cacheable))
    func_dict['stream'] = ((hasattr(f, 'stream') and f.stream))
    a = inspect.getargspec(f)
    arg_list_r = reversed(a.args)
    defaults_list_r = reversed(a.defaults or [None])
    args = reversed(map(None, arg_list_r, defaults_list_r))
    args = filter(lambda x: x[0] and x[0] != 'self', args)
    func_dict['args'] = args
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
    if not sys.path.__contains__(modules_path):
        sys.path.insert(0, modules_path)
    m = importlib.import_module(module_name)
    if RELOAD:
        mtime = os.stat(m.__file__.replace('.pyc', '.py')).st_mtime
        if _mtimes.get(module_name, mtime) < mtime:
            if module_name in sys.modules:
                del sys.modules[module_name]
            m = importlib.import_module(module_name)
            m = reload(m)
            print("Reloaded module %s, changed at %s" % (module_name,
                                                         time.ctime(mtime)))
        _mtimes[module_name] = mtime
    if not (hasattr(m, 'pico') and m.pico == pico):
        raise ImportError('This module has not imported pico!')
    return m


def module_proxy(cls):
    module_name = cls.__module__
    module = imp.new_module(module_name)
    module.pico = pico

    def method_filter(x):
        (name, f) = x
        return ((inspect.isfunction(f) or inspect.ismethod(f))
                and (not name.startswith('_') or name == '__init__')
                and not hasattr(f, 'private'))
    methods = filter(method_filter, inspect.getmembers(cls))
    for (name, f) in methods:
        setattr(module, name, f)
    return module

json_dumpers = {
    types.ModuleType:  module_dict
}
