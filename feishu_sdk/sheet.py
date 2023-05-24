import base64
import io
import logging
import os
import re
from string import Template
from urllib.parse import urljoin
from uuid import uuid4

from PIL import Image

from .auth import FeishuAuth
from .constants import FEIHSU_BASE_URL
from .suite_base import SuiteBase

logger = logging.getLogger(__name__)


class FeishuImage(SuiteBase):
    download_url = Template(
        urljoin(FEIHSU_BASE_URL, "drive/v1/medias/$fileToken/download"),
    )

    def __init__(
        self,
        file_token: str = None,
        img_path: str = None,
        img_bytes: bytes = None,
    ) -> None:
        super().__init__()

        self.file_token = file_token
        self.img_path = img_path
        self._img_bytes = img_bytes

    @property
    def image_name(self):
        if self.img_path is None:
            return f"{uuid4().hex}.png"
        else:
            return os.path.basename(self.img_path)

    @property
    def image_bytes(self):
        if self._img_bytes is not None:
            return self._img_bytes
        elif self.img_path is not None:
            with open(self.img_path, "rb") as rfile:
                self._img_bytes = rfile.read()
            return self._img_bytes
        elif self.file_token is not None:
            download_url = self.download_url.substitute({"fileToken": self.file_token})
            resp = self._sess.get(download_url)
            self._img_bytes = resp.content
            return resp.content
        else:
            return b""

    @property
    def format(self):
        img = Image.open(io.BytesIO(self.image_bytes))
        return img.format.lower()

    @property
    def image_uri(self):
        return base64.b64encode(self.image_bytes).decode()

    @classmethod
    def load(cls, data):
        return FeishuImage(file_token=data["fileToken"])

    def download(self, save_path: str = None, auto_suffix: bool = False):
        if self.file_token is None:
            raise ValueError("无效fileToken，无法下载")

        download_url = self.download_url.substitute({"fileToken": self.file_token})
        resp = self._sess.get(download_url)

        self._img_bytes = resp.content

        if save_path is None:
            return resp.content
        else:
            if auto_suffix:
                save_path = save_path + f".{self.format}"

            with open(save_path, "wb") as wfile:
                wfile.write(resp.content)

            return save_path

    def __repr__(self) -> str:
        return f"<FeishuImage fileToken:{self.file_token}>"


class FeishuFormula(SuiteBase):
    def __init__(self, formula: str) -> None:
        super().__init__()

        self.formula = formula

    def serialize(self):
        return {
            "type": "formula",
            "text": self.formula,
        }


class FeishuSheet(SuiteBase):
    """飞书表格"""

    sheet_read_api = Template(
        urljoin(
            FEIHSU_BASE_URL, "sheets/v2/spreadsheets/$sheet_token/values/$sheetId",
        ),
    )
    sheet_write_api = Template(
        urljoin(
            FEIHSU_BASE_URL, "sheets/v2/spreadsheets/$sheet_token/values/",
        ),
    )
    sheet_write_image_api = Template(
        urljoin(
            FEIHSU_BASE_URL, "sheets/v2/spreadsheets/$sheet_token/values_image",
        ),
    )

    def __init__(self, sheet_token: str, sheet_id: str, auth: FeishuAuth = None):
        super().__init__(auth)

        # 飞书表格的底层信息，默认为空，进行懒加载
        self._data = None

        self.sheet_token = sheet_token
        self.sheet_id = sheet_id

        self.sheet_read_api = self.sheet_read_api.substitute(
            {"sheet_token": self.sheet_token, "sheetId": self.sheet_id},
        )
        self.sheet_write_api = self.sheet_write_api.substitute(
            {"sheet_token": self.sheet_token},
        )
        self.sheet_write_image_api = self.sheet_write_image_api.substitute(
            {"sheet_token": self.sheet_token},
        )

    @property
    def data(self):
        """通过接口获取的原始表格数据"""
        if self._data is None:
            self.refresh()

        return self._data

    @property
    def cols(self):
        if self.data:
            return len(self.data[0])
        else:
            return 0

    @property
    def rows(self):
        if self.data:
            return len(self.data)
        else:
            return 0

    def refresh(self):
        """刷新表格数据"""
        r = self._sess.get(url=self.sheet_read_api)

        try:
            r.raise_for_status()
        except Exception as e:
            logger.error(f"表格数据读取失败，失败原因为: {e}")

        res = r.json()
        if "data" not in res:
            raise ValueError(f"表格读取失败，相关信息为: {res}")

        self._data = self.desearize(res["data"]["valueRange"]["values"])

    def desearize(self, data):
        return [
            [self._desearize_item(col) for col in row] for row in data
        ]

    def _desearize_item(self, item):
        if isinstance(item, dict):
            if item.get("type") == "embed-image":
                return FeishuImage.load(item)

        return item

    def _num_index_to_str_index(self, num_index):
        str_index = ""

        while num_index:
            if num_index % 26:
                str_index = chr(num_index % 26 + ord("A")) + str_index

            str_index = (str_index - str_index % 26) // 26

        return str_index

    def _str_index_to_num_index(self, index: str):
        if not isinstance(index, str):
            raise IndexError("index必须是字符串")

        index = index.strip()
        res = re.match(r"([A-Z]+)([0-9]+)", index)

        if res:
            col, row_idx = res.group(1), int(res.group(2)) - 1
            col_idx = 0
            for c in col:
                col_idx = col_idx * 26 + ord(c) - ord("A") + 1

            return row_idx, col_idx - 1

        raise IndexError(f"无效下标: {index}")

    def _str_range_to_num_range(self, index):
        if isinstance(index, str):
            return self._str_index_to_num_index(index)
        elif isinstance(index, slice):
            start_row_idx, start_col_idx = self._str_index_to_num_index(index.start)
            end_row_idx, end_col_idx = self._str_index_to_num_index(index.stop)
            end_row_idx += 1
            end_col_idx += 1

            return start_row_idx, end_row_idx, start_col_idx, end_col_idx
        else:
            raise IndexError("index必须是字符串或slice")

    def write_data(self, range_, value):
        res = self._sess.put(
            self.sheet_write_api,
            json={
                "valueRange": {
                    "range": f"{self.sheet_id}!{range_}",
                    "values": value,
                },
            },
        )

        try:
            res.raise_for_status()
            print(f"飞书表格写入返回信息: {res.json()}")
        except Exception as e:
            raise ValueError(f"表格写入失败: {e}")

    def write_image_data(self, pos, value: FeishuImage):
        res = self._sess.post(
            self.sheet_write_image_api,
            json={
                "range": f"{self.sheet_id}!{pos}:{pos}",
                "image": value.image_uri,
                "name": value.image_name,
            },
        )

        try:
            res.raise_for_status()
        except Exception as e:
            raise ValueError(f"图片写入失败: {e}")

    def __getitem__(self, index):
        def _get(lhs, s, e):
            if s + 1 == e:
                return lhs[s]
            else:
                return lhs[s: e]

        res = self._str_range_to_num_range(index)
        if len(res) == 2:
            row_idx, col_idx = res
            return self.data[row_idx][col_idx]
        elif len(res) == 4:
            start_row_idx, end_row_idx, start_col_idx, end_col_idx = res
            return [
                _get(i, start_col_idx, end_col_idx)
                for i in self.data[start_row_idx: end_row_idx]
            ]
        else:
            raise IndexError("index必须是字符串或slice")

    def __setitem__(self, index, value):
        res = self._str_range_to_num_range(index)
        if len(res) == 2:
            row_idx, col_idx = res

            if isinstance(value, FeishuFormula):
                value = value.serialize()

            if isinstance(value, FeishuImage):
                self.write_image_data(index, value)
            else:
                self.write_data(f"{index}:{index}", [[value]])

            if row_idx < self.rows and col_idx < self.cols:
                self.data[row_idx][col_idx] = value
        elif len(res) == 4:
            start_row_idx, end_row_idx, start_col_idx, end_col_idx = res

            img_dict, all_img = {}, True
            for value_row_idx, row_idx in enumerate(range(start_row_idx, end_row_idx)):
                for value_col_idx, col_idx in enumerate(range(start_col_idx, end_col_idx)):
                    if isinstance(value[value_row_idx][value_col_idx], FeishuImage):
                        img_dict[
                            f"{self._num_index_to_str_index(col_idx+1)}{row_idx+1}"
                        ] = value[value_row_idx][value_col_idx]
                        value[value_row_idx][value_col_idx] = ""
                    elif isinstance(value[value_row_idx][value_col_idx], FeishuFormula):
                        value[value_row_idx][value_col_idx] = (
                            value[value_row_idx][value_col_idx].serialize()
                        )
                    else:
                        all_img = False

            if not all_img:
                self.write_data(f"{index.start}:{index.stop}", value)

            for pos, img in img_dict.items():
                self.write_image_data(pos, img)
