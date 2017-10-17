.. _intro:

Introduction
============

Pico is designed to help you build a HTTP API with the minimal amount of interference and maximal relief from mundane tasks. It enables you to focus on the application logic while it takes care of all the lower level details of URL routing, serialisation and argument handling. I believe that writing a HTTP API handler should be no different to writing a normal Python module function. Instead of writing functions that take Request objects and extract arguments from GET or POST data structures we should be writing functions that take the arguments we need to use. Instead of serialising our result objects and returning Response objects we should simply return our result objects. The framework can and should take care of those details for us. It is not just a case of being lazy. It is more about writing clean, maintainable, reusable and testable code.


URL Routing
-----------

With Pico you name your API endpoint once when you write your handler function. The name of the function is used to name the endpoint. If you have a function called ``profile`` in a module called ``users`` then its URL will be ``/users/profile``. You have no choice over the URL so it is one less thing to think about. It is also always clear which module a function is defined in when you look at the URL.

When Pico handles a request it finds the appropriate handler function by looking up a dictionary mapping URLs to functions.


Argument Passing
----------------

Pico creates a keyword argument dictionary, ``kwargs``, from the `GET` and `POST` parameters in the request object and passes this to the handler function as ``handler(**kwargs)``. The expected parameters for an endpoint are defined by the arguments in the function signature. The usual Python semantics apply for default arguments. It is an error to request an endpoint with parameters it does not expect or to not supply a value for an argument with no default value::
    
    @pico.expose()
    def hello(who='world'):
        return 'Hello %s' % who

    curl http://localhost:4242/example/hello/
    >>> "Hello world"

    curl http://localhost:4242/example/hello/?who=Fergal
    >>> "Hello Fergal"

    curl http://localhost:4242/example/hello/?spam=foo
    >>> 500 INTERNAL SERVER ERROR
    >>> ....
    >>> TypeError: hello() got an unexpected keyword argument 'spam'


Request Arguments
-----------------

Most web application backends require access to some properties of the ``Request`` object sooner or later for uses other than accessing GET or POST data. You may need the client IP address, headers, cookies, or some arbitrary value set by some other WSGI middleware. Most frameworks usually provide access to the ``Request`` object as an argument to every handler, a property of the handler class, a `global`, or via a module level function. Pico takes a different approach. 

Any handler function may accept any property of the request object as an argument. The author indicates this to Pico by using the :py:func:`@request_args <pico.decorators.request_args>` decorator to specify which arguments should be mapped to which properties. When the handler function is called by Pico these arguments are populated with the appropriate values from the ``Request`` object. In this example we need the users IP address::

    @pico.expose()
    @request_args(ip='remote_addr')
    def list_movies(ip):
        client_country = lookup_ip(ip)
        movies = fetch_movies(client_country)
        ...

The ``Request`` object in Pico is an instance of `werkzeug.wrappers.Request <http://werkzeug.pocoo.org/docs/0.11/wrappers/#werkzeug.wrappers.Request>`_ so you can refer to its documentation to see all available attributes.

.. note::
    If the HTTP client passes a value for an argument mapped with ``@request_args`` it will be ignored. 
    For example the following would **not** give you a list of movies in South Korea::

        curl http://localhost:4242/example/list_movies/?ip="42.42.42.42"

In another situation we may want to get the username of the currently logged in user. We could pass the cookies header and the authentication token header and basic auth header and check each inside our function to see if there is a logged user. This would be quite messy though, especially when we need this value in many different functions. Instead we can use :py:func:`@request_args <pico.decorators.request_args>` with a helper function to return a computed property of the ``Request`` object::

    def current_user(request):
        # check basic_auth
        if request.authorization:
            auth = request.authorization
            if not check_password(auth.username, auth.password):
                raise Unauthorized("Incorrect username or password!")
            return auth.username
        # check for session cookie
        elif 'session_id' in request.cookies:
            user = sessions.get(request.cookies['session_id'])
            return user['username']
        else:
            ...

    @pico.expose()
    @request_args(user=current_user)
    def profile(user):
        return Profiles.get(user=user)


    @pico.expose()
    @request_args(user=current_user)
    def save_post(user, post):
        pass


By explicitly specifying which properties of the ``Request`` object we want to use we keep the code cleaner and easier to understand and maintain. It also allows us to continue to use the functions from other code without having to pass a request object. If our function needs an IP address then we simply pass a string IP address, not a ``Request`` object containing an IP address. The same applies for testing. We don't need to mock the ``Request`` object for most tests. We write tests for our API in the same way as any other library.:: 

    class TestMoviesList(unittest.TestCase):

        def test_movies_ireland(self):
            movies = example.list_movies('86.45.123.136')
            self.assertEqual(movies, movies_list['ie'])

As you can see this is a normal (contrived) unit test without mocked request objects. We simply test the public interface of our module.

The only exceptions of course are helper functions like ``get_user`` above which operate directly on the ``Request`` object. They should be properly tested with a mock ``Request`` object. There should be very few such functions in a typical application however.

.. note::
    The arguments specified with ``@request_args`` are **only** populated when the function is called by Pico. If the function is called directly (inside another function, in a script, in the console, etc) this decorator is a `nop`. 


Protectors
----------

There are other situations where you may need to access properties of the ``Request`` object to check if the function may be called with the used HTTP method, by the current user or from the remote IP address, for example. These checks are part of your application logic but are usually not specific to an individual function and not necessarily related to the actual function being called. For example imagine we have a function to delete posts::

    @pico.expose()
    def delete_post(id):
        # delete the post

We want to restrict this endpoint to `admin` users. We could do the following::

    @pico.expose()
    @request_args(user=current_user)
    def delete_post(id, user):
        if user in admin_users:
            # delete the post
        else:
            raise Forbidden

This works but now we have made our function dependant on a ``user`` even though the actual user isn't relevant to the real logic of the function. If we want to use this function elsewhere in our code we need to pass a admin user as a parameter just to pass the check. Pico provides another decorator to help with this common situation: :py:func:`@protected <pico.decorators.protected>`::

    def is_admin(request, wrapped, args, kwargs):
        user = current_user(request)
        if user not in admin_users:
            raise Forbidden

    @pico.expose()
    @protected(is_admin)
    def delete_post(id):
        # delete the post

If the protector function (``is_admin``) doesn't return ``False`` or raise an exception then the function is executed as normal. As you can see from the protector's signature it can use any of the request object, function object, ``args`` and ``kwargs`` in its decision to pass or raise.

.. note:: 
    Just like ``@request_args``, ``@protected`` is **only** active when Pico calls the function. If it is called directly elsewhere the decorator is a `nop`.
