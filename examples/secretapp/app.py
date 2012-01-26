import pico.server

pico.server.USERS = {
    'monty': {'password': pico.server._hash('python'), 'groups': ['users']},
    'arthur': {'password': pico.server._hash('camelot'), 'groups': ['users']},
    'brian': {'password': pico.server._hash('cohen'), 'groups': ['users', 'admins']}
}


# If running this application through WSGI you must set 
#  the path to your app's modules

#import sys
#sys.stdout = sys.stderr # sys.stdout access restricted by mod_wsgi
# paths = ['/home/username/my_app/']
# for path in paths:
#     if path not in sys.path:
#         sys.path.insert(0, path)

# Set the WSGI application handler
application = pico.server.wsgi_app

if __name__ == '__main__':
    # Setup and run the development server
    pico.server.STATIC_URL_MAP = [('^/(.*)$', './')]
    pico.server.main()