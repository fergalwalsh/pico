if (!window.console)
    console = {
        'debug': function(x) {},
        'log': function(x) {}
    };
var pico = ( function() {
    var pico = {
        '__author__': 'Fergal Walsh',
        '__version__': '2.0.0-dev'
    }

    function contains(str, sub) {
        return (str.indexOf(sub) != -1);
    }
    ;

    function urlencode(params) {
        return map(function(k) {
            return k + "=" + encodeURIComponent(params[k])
        }, keys(params)).join('&');
    }

    function values(object) {
        var result = [];
        for (var key in object) {
            result.push(object[key]);
        }
        return result;
    }

    function keys(object) {
        if (Object.keys) {
            return Object.keys(object);
        } else {
            var result = []
            for (var key in object) {
                if (Object.prototype.hasOwnProperty.call(object, key)) result.push(key);
            }
            return result;
        }
    }

    function map(f, array) {
        var result = [];
        if (Array.prototype.map) {
            result = Array.prototype.map.call(array, f);
        } else {
            for (var i in array) {
                result.push(f(array[i]));
            }
        }
        return result;
    }

    /**
     * Returns true if `callback` returns true for any property
     * else false
     */
    function some(object, callback, thisObject) {
        for (var k in object) {
            if (callback.call(thisObject, object[k], k, callback)) {
                return true;
            }
        }
        return false;
    }

    /**
     * Returns true of the object is a File or FileList
     * else false
     */
    function is_file_or_filelist(obj) {
        return window.File && window.FileList && (obj instanceof File || obj instanceof FileList);
    }

    /**
     * Returns an object with properties from `keys` and values from `values`
     */
    function combine(keys, values) {
        var obj = {};
        for (var i = 0, l = keys.length; i < l; i++) {
            obj[keys[i]] = values[i];
        }
        return obj;
    }

    /**
     * Creates a namespace from a point-seperated string.
     */
    function create_namespace(ns, root) {
        var m = root || window,
            parts = ns.split('.'),
            level;

        for (var i = 0, l = parts.length; i < l; i++) {
            level = parts[i];
            m = (m[level] = m[level] || {});
        }
        return m;
    }

    function create_function_proxy(definition, function_name, obj) {
        var args = map(function(x) {
                return x[0];
            }, definition.args),
            use_cache = !!definition.cache;

        var proxy = function() {
            var args_dict = combine(args, arguments),
                callback;

            if (arguments.length === args.length + 1 &&
                    typeof arguments[arguments.length - 1] === 'function') {
                callback = arguments[arguments.length - 1];
            }
            var f = pico[definition.stream ? 'stream' : 'call_function']
            return f(obj, function_name, args_dict, callback, use_cache);
        };

        // generate doc string
        proxy.__doc__ = "function(" + args.join(', ') + ', callback)';
        if (definition.doc) {
            proxy.__doc__ = [proxy.__doc__, definition.doc].join('\n');
        }

        proxy.toString = function() {
            return this.__doc__;
        };

        // helper function to get generate pico URL
        proxy.prepare_url = function() {
            var data = combine(args, arguments),
                request = pico.prepare_request(obj, function_name, data, use_cache);

            return request.base_url + '?' + request.data;
        };

        return proxy;
    }

    function Request(url, data, callback) {
        this.url = url
        this.base_url = url
        this.data = this._prepareData(data)
        this.callback = callback
        this.xhr = new XMLHttpRequest()
        this.parser = JSON.parse
        this.deferred = new pico.Deferred()
        this.responseType = 'json'
        this.allow_chunked = false
        this.exception = pico.exception
        this.headers = {}
    }

    Request.prototype.send = function() {
        var isFormData = (window.FormData && this.data instanceof FormData)
        var method = this.data.length > 0 || isFormData ? 'POST' : 'GET'
        if (!isFormData) {
            this.setHeader('Content-Type', 'application/x-www-form-urlencoded');
        }
        this.xhr.open(method, this.url);
        for (var header in this.headers) {
            this.xhr.setRequestHeader(header, this.headers[header]);
        }
        this.xhr.responseType = "text";
        this.deferred.fail(this.exception)
        this.deferred.done(this.callback)
        var characters_read = 0;
        var request = this
        this.xhr.onreadystatechange = function() {
            if (request.allow_chunked && this.readyState == 3 && this.getResponseHeader("Transfer-Encoding") == "chunked") {
                var i = this.response.indexOf("\n", request._characters_read + 1);
                while (i > -1) {
                    var response = this.response.substring(characters_read, i);
                    response = (response.match(/([^\,\n][^\n\[\]]*\S+[^\n\[\]]*)/) || [undefined])[0];
                    characters_read = i;
                    if (response) {
                        var result = request.parser(response);
                        this._last_result = result;
                        request.deferred.notify(result, url);
                    }
                    i = this.response.indexOf("\n", characters_read + 1);
                }
            }
            if (this.readyState == 4) {
                if (this.status == 200) {
                    if (characters_read == 0) {
                        request.deferred.resolve(request.parser(this.response || this.responseText), request.url);
                    } else {
                        request.deferred.resolve(this._last_result, request.url);
                    }
                } else {
                    if (characters_read == 0) {
                        if (this.response || this.responseText) {
                            var e = request.parser(this.response || this.responseText)
                            e = e || {
                                status: this.status,
                                exception: this.statusText
                            }
                            request.deferred.reject(e);
                        }
                    } else {
                        request.deferred.reject({
                            'exception': "Exception in chunked response"
                        });
                    }
                }
            }
        }
        this.xhr.send(this.data)
        return this.deferred.promise(this.xhr)
    }

    Request.prototype.setResponseType = function(type) {
        this.responseType = type
        this.parser = function(d) {
            return d
        }
        this.allow_chunked = false
    }

    Request.prototype.setHeader = function(header, value) {
        this.headers[header] = value
    }

    Request.prototype.sign = function(auth_string) {
        var b64 = btoa(unescape(encodeURIComponent(auth_string)))
        this.setHeader('Authorization', 'Basic ' + b64)
    }

    Request.prototype.setCallback = function(callback) {
        this.callback = callback
    }

    Request.prototype._prepareData = function(data) {
        if (typeof (data) == "undefined") {
            data = {};
        }
        if (typeof (data) == "object") {
            if (some(data, is_file_or_filelist)) {
                var orig_data = data;
                data = new FormData();
                for (var k in orig_data) {
                    if (orig_data[k] instanceof File) {
                        data.append(k, orig_data[k]);
                    } else if (orig_data[k] instanceof FileList) {
                        var list = orig_data[k];
                        for (var i = 0, l = list.length; i < l; i++) {
                            data.append(k, list[i]);
                        }
                    } else {
                        data.append(k, orig_data[k]);
                    }
                }
            } else {
                data = urlencode(data);
                data = data.replace(/%20/g, "+");
            }
        }
        return data
    }

    var scripts = document.getElementsByTagName("script"),
        src = scripts[scripts.length - 1].src;

    pico.url = src.substr(0, src.indexOf("client.js")) || src.substr(0, src.indexOf("pico.js"));
    pico.urls = [];
    pico.cache = {
        enabled: true
    };
    pico.debug = false;
    pico.td = 0;

    pico.on_error = function(e) {
        console.error(e);
    };

    pico.exception = function(e) {
        pico.on_error(e);
    };

    pico.get_json = function(url, callback) {
        var request = new Request(url, {}, callback)
        return request.send()
    };

    pico.get_text = function(url, callback) {
        var request = new Request(url, {}, callback)
        request.setResponseType('text')
        return request.send()
    };


    pico.get = function(url, data, callback) {
        if (document.getElementsByTagName("body").length > 0 && !contains(url, '.js') && !contains(url, '.css')) {
            var request = new Request(url, data, callback)
            return request.send()
        }
        if (typeof (data) == "function" && typeof (callback) == "undefined") {
            callback = data;
            data = undefined;
        }
        if (typeof (data) == "undefined") {
            data = {};
        }
        if (typeof (data) == "object") {
            data = urlencode(data);
        }
        url = encodeURI(url);
        if (data) {
            url += "&" + data;
        }
        if (typeof (callback) == "object" && callback.resolve && callback.notify) {
            var deferred = callback;
        } else {
            var deferred = new pico.Deferred();
        }
        if (callback) {
            var callback_name = 'jsonp' + Math.floor(Math.random() * 10e10);
            window[callback_name] = function(result) {
                deferred.resolve(result, url); /*delete window[callback_name]*/
            };
            deferred.done(callback);
            var params = {
                '_callback': callback_name
            };
            url += url.indexOf('?') > -1 ? '&' : '?';
            url += urlencode(params);
        }
        var elem;
        if (document.getElementsByTagName("body").length > 0) {
            elem = document.getElementsByTagName("body")[0];
            if (url.substr(-4) == '.css') {
                var style = document.createElement('link');
                style.type = 'text/css';
                style.src = url;
                style.rel = "stylesheet";
                style.onload = function() {
                    document.getElementsByTagName("body")[0].removeChild(this);
                };
                elem.appendChild(style);
            } else {
                var script = document.createElement('script');
                script.type = 'text/javascript';
                script.src = url;
                script.onload = function() {
                    document.getElementsByTagName("body")[0].removeChild(this);
                };
                elem.appendChild(script);
            }
            if (pico.debug) {
                console.log("pico.get in BODY " + url);
            }
        } else {
            if (pico.debug) console.log("pico.get in HEAD " + url);
            if (url.substr(-4) == '.css') {
                document.write('<link type="text/css" href="' + url + '" rel="stylesheet" />');
            } else {
                document.write('<script type="text/javascript" src="' + url + '"></scr' + 'ipt>');
            }

        }
        return deferred.promise();
    };

    pico.call_function = function(object, function_name, args, callback, use_cache) {
        var request = pico.prepare_request(object, function_name, args, use_cache);
        request.setCallback(callback);
        return request.send()
    };

    pico.stream = function(object, function_name, args, callback, use_cache) {
        var request = pico.prepare_request(object, function_name, args, use_cache),
            stream = {},
            deferred = new pico.Deferred();


        if (typeof callback === 'function') {
            deferred.progress(callback);
        }

        stream.open = function() {
            var url = request.base_url + '?' + request.data
            if (request.headers['X-SESSION-ID']) {
                url += '&_x_session_id=' + request.headers['X-SESSION-ID']
            }
            stream.socket = new EventSource(url);
            stream.socket.onmessage = function(e) {
                var message = JSON.parse(e.data)
                if (message == 'PICO_CLOSE_STREAM') {
                    stream.close()
                } else {
                    deferred.notify(message);
                }
            };
        };
        stream.close = function() {
            stream.socket.close();
            deferred.resolve();
        };
        stream.status = function() {
            var states = ["Connecting", "Open", "Closed"]
            return states[stream.socket.readyState];
        };
        stream.open();

        return deferred.promise(stream);
    };

    pico.prepare_request = function(module, function_name, args, use_cache) {
        var data = {};
        for (k in args) {
            if (args[k] != undefined) {
                data[k] = is_file_or_filelist(args[k]) ? args[k] : pico.json.dumps(args[k]);
            }
        }
        var url = module.__url__ + function_name + '/'

        var request = new Request(url, data)
        if (module._beforeSend) {
            module._beforeSend(request, module)
        }
        return request;
    };

    pico.load = function(module, result_handler) {
        return pico.load_as(module, undefined, result_handler);
    };

    pico.load_as = function(module, alias, result_handler) {

        if (module.substr(0, 7) != 'http://') {
            var url = pico.url + module.replace('.', '/');
        }
        if (alias == undefined) {
            alias = module;
        }
        var callback = function(result, url) {
            // url = url.substr(0, url.indexOf("module/"));
            var module_proxy = pico.module_proxy(result, module, alias, url);
            if (result_handler) {
                result_handler(module_proxy);
            }
        };
        return pico.get(url, undefined, callback)
    };

    pico.module_proxy = function(definition, module_name, alias, url) {
        if (alias == undefined) {
            alias = module_name;
        }
        var ns = create_namespace(alias);
        for (var k in ns) {
            delete ns[k];
        }
        ns.__name__ = definition.name;
        ns.__alias__ = alias;
        ns.__url__ = definition.url || pico.url;
        ns.__doc__ = definition.doc;
        ns._beforeSend = undefined;
        for (var i = 0; i < definition.functions.length; i++) {
            var func_def = definition.functions[i];
            var func_name = func_def.name;
            ns[func_name] = create_function_proxy(func_def, func_name, ns);
        }
        ;
        return ns;
    };

    pico.authenticate = function(object, username, password) {
        var auth_string = username + ':' + password
        var b64 = btoa(unescape(encodeURIComponent(auth_string)))
        object._beforeSend = function(req) {
            req.setHeader('Authorization', 'Basic ' + b64)
        }
    }

    pico.deauthenticate = function(object) {
        object._beforeSend = undefined
    }

    pico.save_session = function(object, session_id) {
        var key = object.__name__ + 'X-SESSION-ID'
        localStorage[key] = session_id
        pico.open_session(object)
    }

    pico.clear_session = function(object) {
        var key = object.__name__ + 'X-SESSION-ID'
        delete localStorage[key]
    }

    pico.open_session = function(object) {
        var key = object.__name__ + 'X-SESSION-ID'
        object._beforeSend = function(req) {
            req.setHeader('X-SESSION-ID', localStorage[key])
        }
    }

    pico.main = function() {};

    pico.json = {
        dumps: function(obj) {
            return JSON.stringify(obj, function(k, v) {
                return v && typeof v === 'object' && typeof v.json === 'string' ? JSON.parse(v.json) : v;
            });
        },
        loads: JSON.parse
    };

    pico.help = function(f) {
        return f.__doc__;
    };

    pico.reload = function(module, callback) {
        return pico.load_as(module.__url__ + 'module/' + module.__name__, module.__alias__, callback);
    };

    pico.log = function(arg) {
        console.log(arg);
    };

    pico.set = function(name, root) {
        return function(r) {
            (root || window)[name] = r;
        };
    };

    return pico;
}());
if (!document.addEventListener) {
    document.attachEvent('DOMContentLoaded', function() {
        pico.main()
    });
} else {
    document.addEventListener('DOMContentLoaded', function() {
        pico.main()
    }, false);
}

/*
 * Implementation of the jQuery deferred interface
 * https://github.com/warpdesign/Standalone-Deferred
 *
 * This software is distributed under an MIT licence.
 *
 * Copyright 2012 © Nicolas Ramz
 */
( function(e) {
function t(e) {
    return Object.prototype.toString.call(e) === "[object Array]"
}
function n(e, n) {
    if (t(e))
        for (var r = 0; r < e.length; r++) n(e[r]);
    else n(e)
}
function r(e) {
    var i = "pending",
        s = [],
        o = [],
        u = [],
        a = null,
        f = {
            done: function() {
                for (var e = 0; e < arguments.length; e++) {
                    if (!arguments[e]) continue;
                    if (t(arguments[e])) {
                        var n = arguments[e];
                        for (var r = 0; r < n.length; r++) i === "resolved" && n[r].apply(this, a), s.push(n[r])
                    } else i === "resolved" && arguments[e].apply(this, a), s.push(arguments[e])
                }
                return this
            },
            fail: function() {
                for (var e = 0; e < arguments.length; e++) {
                    if (!arguments[e]) continue;
                    if (t(arguments[e])) {
                        var n = arguments[e];
                        for (var r = 0; r < n.length; r++) i === "rejected" && n[r].apply(this, a), o.push(n[r])
                    } else i === "rejected" && arguments[e].apply(this, a), o.push(arguments[e])
                }
                return this
            },
            progress: function() {
                for (var e = 0; e < arguments.length; e++) {
                    if (!arguments[e]) continue;
                    if (t(arguments[e])) {
                        var n = arguments[e];
                        for (var r = 0; r < n.length; r++) i == "pending" && u.push(n[r])
                    } else i === "pending" && u.push(arguments[e])
                }
                return this
            },
            then: function() {
                arguments.length > 1 && arguments[1] && this.fail(arguments[1]), arguments.length > 0 && arguments[0] && this.done(arguments[0]), arguments.length > 2 && arguments[2] && this.progress(arguments[2])
            },
            promise: function(e) {
                if (e == null) return f;
                for (var t in f) e[t] = f[t];
                return e
            },
            state: function() {
                return i
            },
            debug: function() {
                console.log("[debug]", s, o, i)
            },
            isRejected: function() {
                return i == "rejected"
            },
            isResolved: function() {
                return i == "resolved"
            },
            pipe: function(e, t, i) {
                return r(function(r) {
                    n(e, function(e) {
                        typeof e == "function" ? l.done(function() {
                            var t = e.apply(this, arguments);
                            t && typeof t == "function" ? t.promise().then(r.resolve, r.reject, r.notify) : r.resolve(t)
                        }) : l.done(r.resolve)
                    }), n(t, function(e) {
                        typeof e == "function" ? l.fail(function() {
                            var t = e.apply(this, arguments);
                            t && typeof t == "function" ? t.promise().then(r.resolve, r.reject, r.notify) : r.reject(t)
                        }) : l.fail(r.reject)
                    })
                }).promise()
            }
        },
        l = {
            resolveWith: function(e) {
                if (i == "pending") {
                    i = "resolved";
                    var t = a = arguments.length > 1 ? arguments[1] : [];
                    for (var n = 0; n < s.length; n++) s[n].apply(e, t)
                }
                return this
            },
            rejectWith: function(e) {
                if (i == "pending") {
                    i = "rejected";
                    var t = a = arguments.length > 1 ? arguments[1] : [];
                    for (var n = 0; n < o.length; n++) o[n].apply(e, t)
                }
                return this
            },
            notifyWith: function(e) {
                if (i == "pending") {
                    var t = a = arguments.length > 1 ? arguments[1] : [];
                    for (var n = 0; n < u.length; n++) u[n].apply(e, t)
                }
                return this
            },
            resolve: function() {
                return this.resolveWith(this, arguments)
            },
            reject: function() {
                return this.rejectWith(this, arguments)
            },
            notify: function() {
                return this.notifyWith(this, arguments)
            }
        },
        c = f.promise(l);
    return e && e.apply(c, [c]), c
}
r.when = function() {
    if (arguments.length < 2) {
        var e = arguments.length ? arguments[0] : undefined;
        return e && typeof e.isResolved == "function" && typeof e.isRejected == "function" ? e.promise() : r().resolve(e).promise()
    }
    return function(e) {
        var t = r(),
            n = e.length,
            i = 0,
            s = new Array(n);
        for (var o = 0; o < e.length; o++) ( function(r) {
                e[r].done(function() {
                    s[r] = arguments.length < 2 ? arguments[0] : arguments, ++i == n && t.resolve.apply(t, s)
                }).fail(function() {
                    t.reject(arguments)
                })
            } )(o);
        return t.promise()
    }(arguments)
}, e.Deferred = r
} )(pico);
