## About The Project

目前我们大量使用飞书文档来做数据的管理，并通过API文档进行数据的读取和写入，但目前大家的实现比较分散，该项目旨在通过包装接口的方式，提高整个飞书文档的易用性，方便后期的维护，目前主要实现的是对表格作兼容。

## Getting Started

### Installation

```shell
pip install git+https://github.com/lixumin-zai/feishu_sheet_SDK.git
```

## Usage

### 鉴权登录

目前的实现只支持tenant（租户）的登录方式，要进行鉴权的话，需要通过飞书开发者平台创建一个应用，拿到应用对应的app id和app secret key才能正常登录。

```python
>>> import feishu_sdk
>>> app_id, app_key = "", ""
>>> feishu_sdk,login(app_id, app_key)
```

### 飞书表格

飞书的表格由两个编码决定，一个是工作表的编码，一个子表的编码，两个编码唯一的确定了一张表。对应的编码需要通过表格的访问链接得到，比如：
* https://isw1t6yp68.feishu.cn/sheets/shtcn9sCFZxKrt53nBbOnDOxc5g?sheet=yJ1oUS
对应的sheet token为shtcn9sCFZxKrt53nBbOnDOxc5g，对应的sheet id为yJ1oUS

```python
>>> from feishu_sdk.sheet import FeishuSheet, FeishuImage
>>> sheet_token, sheet_id = "shtcn9sCFZxKrt53nBbOnDOxc5g", "yJ1oUS"
>>> sheet = FeishuSheet(sheet_token, sheet_id)
>>> sheet.rows
100
>>> sheet.cols
100
```

#### 表格读取
> 要想进行表格的读取，需要对应的文档权限为【组织内有链接可阅读】

在表格上的读取分两种情况，一种为单个cell的读取，一种为范围读取，每个单元格支持的类型有:

* 数字
* 字符串
* 图片

当格式为图片时，会被自动转换成feishu_sdk.sheet.FeishuImage类的实例，用于图片的下载。若为范围读取，则返回的类型会是个二维列表，若对于单行或单列，则会自动转换成一个一维列表，使用时需注意

* 单个cell读取
```python
>>> sheet["C1"]  # 读取C1对应的单元
10
>>> img = sheet["C2"]
>>> print(img)
<FeishuImage dfaasd>
>>> img.format
"png"
>>> img.download()  # 当不指定路径时，会直接返回下载的图片二进制流
b""
>>> img.download("./test/test.png")  # 将图片下载为./test/test.png，返回值为图片保存链接
"./test/test.png"
>>> img.download("./test/test", auto_suffix=True)  # 不确定图片格式时，会自动的决定图片格式
"./test/test.png"
>>> sheet["C3"]
"test"
```

* 多个cell读取

```python
>>> sheet["C1": "C3"]
[10, <FeishuImage dfaasd>, "test"]
```

#### 表格写入
> 要想进行表格的读取，需要对应的文档权限为【组织内有链接可编辑】

表格的写入支持的格式与读取时相同，但对于单行或者单列，则还要求为二维列表
> 注：表格被写入后不会被实时的更新，因此当需要再读取时，要调用`sheet.flush()`来与线上数据同步

```python
>>> sheet["C1"] = 10
>>> sheet["C2"] = FeishuImage("./test/test.png")  # 将./test/test.png上传
>>> sheet["C2"] = FeishuImage(open("./test/test.png", "rb").read())  # 支持二进制上传
```

* [飞书API开发文档](https://open.feishu.cn/document/ukTMukTMukTM/uATMzUjLwEzM14CMxMTN/overview)
