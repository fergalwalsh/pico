import sys
sys.stdout = sys.stderr # sys.stdout access restricted by mod_wsgi
paths = ['/home/me/python/'] # my python modules directory (pico is in here)
for path in paths:
    if path not in sys.path:
        sys.path.insert(0, path)

import pico
application = pico.wsgi_app 


