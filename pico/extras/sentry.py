

def set_context(client, request):
    client.http_context({
        'method': request.method,
        'url': request.base_url,
        'query_string': request.query_string,
        'data': request.get_data(),
        'headers': dict(request.headers),

    })
    if request.authorization:
        client.user_context({
            'user': request.authorization.username
        })


class SentryMixin(object):
    sentry_client = None

    def prehandle(self, request, kwargs):
        if self.sentry_client:
            set_context(self.sentry_client, request)
        super(SentryMixin, self).prehandle(request, kwargs)

    def handle_exception(self, exception, request, **kwargs):
        if self.sentry_client:
            sentry_id = self.sentry_client.captureException()
            if sentry_id:
                # The sentry_id is passed down to pico's JsonErrorResponse so it is
                #  included as a value in the response.
                kwargs['sentry_id'] = sentry_id[0]
        return super(SentryMixin, self).handle_exception(exception, request, **kwargs)
