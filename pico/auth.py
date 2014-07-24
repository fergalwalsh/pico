import pico
from pico import PicoError


class NotAuthorizedError(PicoError):
    def __init__(self, message=''):
        PicoError.__init__(self, message)
        self.response.status = "401 Not Authorized"
        self.response.set_header("WWW-Authenticate",  "Basic")


class InvalidSessionError(PicoError):
    def __init__(self, message=''):
        PicoError.__init__(self, message)
        self.response.status = "440 Invalid Session"


class Bunch:
    def __init__(self, **kwds):
        self.__dict__.update(kwds)


class object(pico.object):
    account_manager = None
    __headers__ = {'X-SESSION-ID': ''}

    def __init__(self):
        super(object, self).__init__()
        self.user = None
        if type(self.account_manager) == dict:
            self.account_manager = Bunch(**self.account_manager)
        request = pico.get_request()
        if 'HTTP_AUTHORIZATION' in request:
            try:
                auth_header = request.get('HTTP_AUTHORIZATION')
                scheme, data = auth_header.split(None, 1)
                assert(scheme == 'Basic')
                username, password = data.decode('base64').split(':', 1)
                self.user = self._get_user(username, password)
            except Exception, e:
                raise NotAuthorizedError(str(e))
        elif 'HTTP_X_SESSION_ID' in request:
            session_id = request.get('HTTP_X_SESSION_ID')
            self.user = self._get_session(session_id)
        elif 'DUMMY_REQUEST' in request:
            pass
        else:
            raise NotAuthorizedError("No username or password supplied")

    def _get_user(self, username, password):
        if self.account_manager:
            return self.account_manager._get_user(username, password)

    def _get_session(self, session_id):
        if self.account_manager:
            return self.account_manager._get_session(session_id)
