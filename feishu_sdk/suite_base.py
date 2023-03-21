from .globals import default_auth


class SuiteBase(object):
    """飞书套件的基类"""

    def __init__(self, auth=None) -> None:
        if auth is None:
            self._auth = default_auth()
        else:
            self._auth = auth

        self._sess = self._auth.generate_authed_session()
