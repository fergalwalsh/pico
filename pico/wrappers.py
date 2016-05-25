from werkzeug.wrappers import Response

from . import pragmaticjson as json


class JsonResponse(Response):
    def __init__(self, result, *args, **kwargs):
        kwargs['response'] = json.dumps(result)
        kwargs['content_type'] = u'application/json'
        super(JsonResponse, self).__init__(*args, **kwargs)

    def to_jsonp(self, callback):
        json_string = self.response[0]
        content = u'{callback}({json});'.format(callback=callback, json=json_string)
        self.set_data(content)
        self.content_type = u'text/javascript'
        return self
