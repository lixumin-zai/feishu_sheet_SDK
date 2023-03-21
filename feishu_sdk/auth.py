import logging
from urllib.parse import urljoin

import requests

from .constants import FEIHSU_BASE_URL

logger = logging.getLogger(__name__)


class FeishuAuth(object):
    """飞书的鉴权模块，目前使用租户访问凭证"""

    tenant_token_api = urljoin(
        FEIHSU_BASE_URL, "auth/v3/tenant_access_token/internal/",
    )

    def __init__(self, app_id: str, app_key: str) -> None:
        self.app_id = app_id
        self.app_key = app_key

        self._access_token = None

    def get_tenant_access_token(self) -> str:
        """获取租户访问凭证"""
        if self._access_token is not None:
            return self._access_token

        resp = requests.post(
            self.tenant_token_api, json={
                "app_id": self.app_id, "app_secret": self.app_key,
            },
        )

        try:
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"无法获得有效凭证, 错误原因为: {e}")
            raise e

        self._access_token = resp.json()["tenant_access_token"]
        return self._access_token

    

    def generate_headers(self, token: str = None):
        """生成包含租户访问凭证的请求头"""
        token = token or self.get_tenant_access_token()

        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': "application/json charset=utf-8",
        }

    def generate_authed_session(self) -> requests.Session:
        """生成包含鉴权头的session"""
        sess = requests.Session()
        sess.headers.update(self.generate_headers())

        return sess
