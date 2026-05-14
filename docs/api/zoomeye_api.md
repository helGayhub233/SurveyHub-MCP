# ZoomEye API 文档

来源：

- `https://www.zoomeye.org/`
- `https://www.zoomeye.org/doc`
- 本地参考：`zoomeye/server.py`、`zoomeye/prompts.py`

抓取时间：2026-05-14

## 基础信息

- 接入域名：`api.zoomeye.org`
- 协议：HTTPS
- API 版本路径：`/v2`
- 鉴权方式：HTTP Header 中携带 `API-KEY`
- API Key 获取位置：登录 ZoomEye 后进入个人资料页
- 查询语句编码：资产搜索接口使用 `qbase64`，即查询语句的 Base64 编码
- 本地 MCP 环境变量：`ZOOMEYE_API_KEY`

## 鉴权

```http
API-KEY: {API_KEY}
```

示例：

```bash
curl -X POST "https://api.zoomeye.org/v2/userinfo" \
  -H "API-KEY: ${ZOOMEYE_API_KEY}"
```

## 接口列表

| 接口名 | 方法 | 地址 | 说明 |
| --- | --- | --- | --- |
| 用户信息查询 | POST | `/v2/userinfo` | 获取用户信息、订阅信息和积分情况 |
| 资产搜索 | POST | `/v2/search` | 根据 ZoomEye 查询语法检索网络资产 |

## 用户信息查询

```http
POST /v2/userinfo
```

用途：获取当前 API Key 对应的用户信息、订阅信息和积分情况。

### 请求示例

```bash
curl -X POST "https://api.zoomeye.org/v2/userinfo" \
  -H "API-KEY: ${ZOOMEYE_API_KEY}"
```

### 响应示例

```json
{
  "code": 60000,
  "message": "success",
  "data": {
    "username": "abc",
    "email": "user@example.com",
    "phone": "+1234567890",
    "created_at": "2013-01-15T08:00:00Z",
    "subscription": {
      "plan": "Premium",
      "end_date": "2024-01-20T00:00:00Z",
      "points": "30000",
      "zoomeye_points": "10000000"
    }
  }
}
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | integer | 响应代码 |
| `message` | string | 响应消息 |
| `data` | object | 用户信息和订阅信息 |
| `username` | string | 用户名 |
| `email` | string | 用户邮箱 |
| `phone` | string | 用户电话 |
| `created_at` | string(date-time) | 用户创建时间 |
| `subscription` | object | 订阅信息 |
| `plan` | string | 订阅计划 |
| `end_date` | string(date-time) | 订阅结束时间 |
| `points` | string | 普通积分 |
| `zoomeye_points` | string | 权益积分 |

## 资产搜索

```http
POST /v2/search
```

用途：根据 ZoomEye 查询语法获取网络资产信息。

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `qbase64` | string | 是 | 无 | Base64 编码后的查询语句 |
| `fields` | string | 否 | `ip, port, domain, update_time` | 返回字段，多个字段用英文逗号分隔 |
| `sub_type` | string | 否 | `v4` | 数据类型，支持 `v4`、`v6`、`web` |
| `page` | integer | 否 | `1` | 页码，按更新时间排序 |
| `pagesize` | integer | 否 | `10` | 每页数量；官方文档说明最大 `10000`，当前本地 MCP tool schema 限制最大 `1000` |
| `facets` | string | 否 | 无 | 聚合统计项，多个字段用英文逗号分隔 |
| `ignore_cache` | boolean | 否 | `false` | 是否忽略缓存，商业版及以上支持 |

`facets` 支持：

```text
country, subdivisions, city, product, service, device, os, port
```

### 查询语句编码

将查询条件转换为 Base64 后传入 `qbase64`。

```bash
echo 'title="knownsec"' | base64
```

Python 示例：

```python
import base64

query = 'title="knownsec"'
qbase64 = base64.b64encode(query.encode("utf-8")).decode("ascii")
```

### 请求示例

```bash
curl -L "https://api.zoomeye.org/v2/search" \
  -H "API-KEY: ${ZOOMEYE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "qbase64": "dGl0bGU9ImNpc2NvIHZwbiIK",
    "page": 1,
    "pagesize": 10,
    "fields": "ip,port,domain,update_time",
    "sub_type": "v4"
  }'
```

```python
import base64
import os

import requests

query = 'title="cisco vpn"'
qbase64 = base64.b64encode(query.encode("utf-8")).decode("ascii")

headers = {
    "API-KEY": os.environ["ZOOMEYE_API_KEY"],
    "Content-Type": "application/json",
}

payload = {
    "qbase64": qbase64,
    "page": 1,
    "pagesize": 10,
    "fields": "ip,port,domain,update_time",
    "sub_type": "v4",
}

response = requests.post(
    "https://api.zoomeye.org/v2/search",
    headers=headers,
    json=payload,
)
print(response.json())
```

### 响应结构

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `code` | integer | 响应代码；成功示例为 `60000` |
| `message` | string | 响应消息；成功示例为 `success` |
| `total` | integer | 命中资产总数 |
| `query` | string | 原始查询语句 |
| `data` | list | 资产结果列表 |

### 可选返回字段

| 字段 | 类型 | 说明 | 权限 |
| --- | --- | --- | --- |
| `ip` | string | IP 地址 | 所有用户 |
| `domain` | string | 域名 | 所有用户 |
| `url` | string | Web 资产完整 URL | 所有用户 |
| `ssl.jarm` | string | SSL JARM 指纹 | 所有用户 |
| `ssl.ja3s` | string | SSL JA3S 指纹 | 所有用户 |
| `iconhash_md5` | string | icon 图像 MD5 | 专业版及以上 |
| `robots_md5` | string | `robots.txt` MD5 | 商业版及以上 |
| `security_md5` | string | 安全设置文件 MD5 | 商业版及以上 |
| `hostname` | string | 主机名 | 所有用户 |
| `os` | string | 操作系统 | 所有用户 |
| `port` | integer | 端口 | 所有用户 |
| `service` | string | 应用协议，如 HTTP、SSH | 所有用户 |
| `title` | list | 网页标题 | 所有用户 |
| `version` | string | 组件版本 | 所有用户 |
| `device` | string | 设备名称 | 所有用户 |
| `rdns` | string | 反向 DNS | 所有用户 |
| `product` | string | 产品组件 | 所有用户 |
| `header` | string | HTTP 响应头 | 所有用户 |
| `header_hash` | string | HTTP 响应头 Hash | 专业版及以上 |
| `banner` | string | 服务 Banner | 所有用户 |
| `body` | string | HTML 正文 | 商业版及以上 |
| `body_hash` | string | HTML 正文 Hash | 专业版及以上 |
| `update_time` | string | 资产更新时间 | 所有用户 |
| `header.server.name` | string | HTTP Server 名称 | 所有用户 |
| `continent.name` | string | 大洲名称 | 所有用户 |
| `country.name` | string | 国家名称 | 所有用户 |
| `province.name` | string | 省份名称 | 所有用户 |
| `city.name` | string | 城市名称 | 所有用户 |
| `isp.name` | string | ISP 名称 | 所有用户 |
| `organization.name` | string | 组织名称 | 所有用户 |
| `zipcode` | integer | 邮政编码 | 所有用户 |
| `idc` | string | 是否为 IDC，`0` 否，`1` 是 | 所有用户 |
| `lon` | string | 经度 | 所有用户 |
| `lat` | string | 纬度 | 所有用户 |
| `asn` | string | ASN 自治系统编号 | 所有用户 |
| `protocol` | string | 传输层协议，如 TCP、UDP | 所有用户 |
| `honeypot` | integer | 是否蜜罐，`0` 否，`1` 是 | 所有用户 |
| `ssl` | string | SSL x509 证书信息 | 所有用户 |
| `primary_industry` | string | 主行业 | 商业版及以上 |
| `sub_industry` | string | 子行业 | 商业版及以上 |
| `rank` | integer | 资产重要性分值，越大越重要 | 商业版及以上 |

## 搜索语法

### 基本规则

- 搜索范围覆盖设备资产，即 IPv4、IPv6，以及网站域名资产。
- 直接输入字符串时，会按全局模式匹配 HTTP、SSH、FTP 等协议内容，包括 HTTP Header、Body、SSL、Title 以及其他协议 Banner。
- 默认搜索不区分大小写，并会进行分词匹配。
- 使用 `==` 时为精确匹配，区分大小写，也可搜索空值。
- 字符串建议使用单引号或双引号包裹，例如 `"Cisco System"`。
- 字符串内的引号或括号需要转义，例如 `"a\"b"`、`portinfo\(\)`。

### 逻辑运算

| 运算符 | 说明 | 示例 |
| --- | --- | --- |
| `=` | 包含关键词 | `title="知道创宇"` |
| `==` | 精确匹配，区分大小写 | `title=="知道创宇"` |
| `||` | 或 | `service="ssh" || service="http"` |
| `&&` | 且 | `device="router" && after="2020-01-01"` |
| `!=` | 非 | `country="CN" && subdivisions!="beijing"` |
| `()` | 优先处理 | `(country="CN" && port!=80) || (country="US" && title!="404 Not Found")` |
| `*` | 模糊匹配 | `title="google*"` |

### 地理位置

| 语法 | 说明 | 备注 |
| --- | --- | --- |
| `country="CN"` | 国家或地区 | 支持国家缩写、中英文全称，如 `country="中国"` |
| `subdivisions="beijing"` | 行政区 | 中国省份支持中文和英文，如 `subdivisions="北京"` |
| `city="changsha"` | 城市 | 中国城市支持中文和英文，如 `city="长沙"` |

### 证书

| 语法 | 说明 |
| --- | --- |
| `ssl="google"` | SSL 证书中包含指定字符串 |
| `ssl.cert.fingerprint="F3C98F223D82CC41CF83D94671CCC6C69873FABF"` | 证书指纹 |
| `ssl.chain_count=3` | SSL 证书链数量 |
| `ssl.cert.alg="SHA256-RSA"` | 证书签名算法 |
| `ssl.cert.issuer.cn="pbx.wildix.com"` | 证书签发者通用名称 |
| `ssl.cert.pubkey.rsa.bits=2048` | RSA 公钥位数 |
| `ssl.cert.pubkey.ecdsa.bits=256` | ECDSA 公钥位数 |
| `ssl.cert.pubkey.type="RSA"` | 证书公钥类型 |
| `ssl.cert.serial="18460192207935675900910674501"` | 证书序列号 |
| `ssl.cipher.bits="128"` | 加密套件位数 |
| `ssl.cipher.name="TLS_AES_128_GCM_SHA256"` | 加密套件名称 |
| `ssl.cipher.version="TLSv1.3"` | 加密套件版本 |
| `ssl.version="TLSv1.3"` | SSL/TLS 版本 |
| `ssl.cert.subject.cn="example.com"` | 证书持有者通用名称 |
| `ssl.jarm="29d29d15d29d29d00029d29d29d29dea0f89a2e5fb09e4d8e099befed92cfa"` | JARM 指纹 |
| `ssl.ja3s=45094d08156d110d8ee97b204143db14` | JA3S 指纹 |

### IP 与域名

| 语法 | 说明 | 备注 |
| --- | --- | --- |
| `ip="8.8.8.8"` | IPv4 资产 |  |
| `ip="2600:3c00::f03c:91ff:fefc:574a"` | IPv6 资产 |  |
| `cidr="52.2.254.36/24"` | CIDR 网段 | `/24`、`/16`、`/8` 分别可用于不同范围网段 |
| `org="北京大学"` | 组织资产 | 也可使用 `organization="北京大学"` |
| `isp="China Mobile"` | 网络服务提供商 | 可结合组织字段补充 |
| `asn=42893` | ASN 资产 |  |
| `port=80` | 端口资产 | 页面说明暂不支持同时开放多端口目标搜索 |
| `hostname="google.com"` | 主机名 |  |
| `domain="baidu.com"` | 域名及子域名资产 |  |
| `icp.number="京ICP备10040895号-40"` | ICP 备案号 | 通过域名关联备案资产 |
| `icp.name="知道创宇"` | ICP 备案主体 | 查询企业备案域名资产 |
| `banner="FTP"` | 协议报文 | 适用于非 HTTP 协议 Banner |
| `http.header="http"` | HTTP 响应头 |  |
| `http.header_hash="27f9973fe57298c3b63919259877a84d"` | HTTP 响应头 Hash |  |
| `http.header.server="Nginx"` | HTTP Server |  |
| `http.header.version="1.2"` | HTTP Server 版本 |  |
| `http.header.status_code="200"` | HTTP 状态码 | 如 `200`、`302`、`404` |
| `http.body="document"` | HTML 正文 |  |
| `http.body_hash="84a18166fde3ee7e7c974b8d1e7e21b4"` | HTML 正文 Hash |  |

### 指纹

| 语法 | 说明 | 备注 |
| --- | --- | --- |
| `app="Cisco ASA SSL VPN"` | 应用指纹 | 更多规则可在页面导航或搜索提示中查看 |
| `service="ssh"` | 服务协议 | 常见如 `http`、`ftp`、`ssh`、`telnet` |
| `device="router"` | 设备类型 | 常见如 `router`、`switch`、`storage-misc` |
| `os="RouterOS"` | 操作系统 | 常见如 Linux、Windows、RouterOS、IOS、JUNOS |
| `title="Cisco"` | HTML 标题 |  |
| `industry="政府"` | 行业类型 | 可结合组织字段补充 |
| `product="Cisco"` | 组件产品 | 支持主流资产组件 |
| `protocol="TCP"` | 传输协议 | 常见如 TCP、UDP、TCP6、SCTP |
| `is_honeypot="True"` | 蜜罐筛选 |  |

### 时间

时间过滤器需要与其他过滤条件组合使用。

| 语法 | 说明 |
| --- | --- |
| `after="2020-01-01" && port="50050"` | 查询指定日期之后更新且匹配端口的资产 |
| `before="2020-01-01" && port="50050"` | 查询指定日期之前更新且匹配端口的资产 |

### Dig

| 语法 | 说明 |
| --- | --- |
| `dig="baidu.com 220.181.38.148"` | 查询相关 Dig 内容 |

### Iconhash

| 语法 | 说明 |
| --- | --- |
| `iconhash="f3418a443e7d841097c714d69ec4bcb8"` | 使用 MD5 图标 Hash 查询 |
| `iconhash="1941681276"` | 使用 MMH3 图标 Hash 查询 |

### Filehash

| 语法 | 说明 |
| --- | --- |
| `filehash="0b5ce08db7fb8fffe4e14d05588d49d9"` | 根据解析出的文件数据查询 |

## 本地 MCP 实现对应关系

当前 `zoomeye/server.py` 中的 MCP 工具：

| 工具 | 对应接口 | 说明 |
| --- | --- | --- |
| `zoomeye_search` | `POST /v2/search` | 执行 ZoomEye 资产搜索 |

MCP 输入参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `qbase64` | string | 无 | Base64 编码后的查询语句，必填 |
| `page` | integer | `1` | 页码 |
| `pagesize` | integer | `10` | 每页数量；当前 schema 最大 `1000` |
| `fields` | string | 无 | 逗号分隔的返回字段 |
| `sub_type` | string | 无 | `v4`、`v6`、`web` |
| `facets` | string | 无 | 逗号分隔的统计项 |
| `ignore_cache` | boolean | 无 | 是否忽略缓存 |

本地实现通过 `ZOOMEYE_API_KEY` 读取 API Key，并以如下请求头调用 ZoomEye：

```http
API-KEY: {ZOOMEYE_API_KEY}
Content-Type: application/json
```
