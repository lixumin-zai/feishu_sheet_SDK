from .auth import FeishuAuth

DEFAULT_AUTH = FeishuAuth("cli_a12ac5906d7c900e", "jSFDBwE3MbtXA6o9fSsOHdGbd3pVj1WY")


def default_auth():
    global DEFAULT_AUTH

    return DEFAULT_AUTH


def login(app_id: str, app_key: str):
    global DEFAULT_AUTH

    DEFAULT_AUTH = FeishuAuth(app_id, app_key)
