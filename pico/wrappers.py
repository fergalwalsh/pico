from copy import deepcopy
from werkzeug.wrappers import Response

from . import pragmaticjson as json


class JsonResponse(Response):
    def __init__(self, result, *args, **kwargs):
        kwargs['response'] = json.dumps(result)
        kwargs['content_type'] = u'application/json'
        super(JsonResponse, self).__init__(*args, **kwargs)

    def to_jsonp(self, callback):
        r = deepcopy(self)
        json_string = r.response[0]
        content = u'{callback}({json});'.format(callback=callback, json=json_string)
        r.set_data(content)
        r.content_type = u'text/javascript'
        return r
