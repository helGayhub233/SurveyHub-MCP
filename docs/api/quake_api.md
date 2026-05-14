# Quake API 文档

来源：`https://quake.360.net/quake/#/help?id=5e77423bcb9954d2f8a01656&title=%E4%BD%BF%E7%94%A8%E8%AF%B4%E6%98%8E`

抓取时间：2026-05-14

文档范围：`API接口 / 使用说明` 至 `服务数据接口`

## 基础信息

- 接入域名：`quake.360.net`
- API 版本路径：`/api/v3`
- 认证方式：在 HTTP Header 中携带 `X-QuakeToken`
- POST 请求内容类型：`Content-Type: application/json`
- API Key 获取位置：登录 Quake 后进入 `个人中心`
- 权限校验：API Key 与用户身份绑定，无接口权限时不可调用
- 使用限制：使用文档未收录接口爬取数据可能导致账户被封禁

## 鉴权

所有公开 API 均使用 API Key 认证。

```http
X-QuakeToken: {API Key}
```

POST 请求还需要设置：

```http
Content-Type: application/json
```

### 请求示例

```bash
curl -X POST \
  -H "X-QuakeToken: {API Key}" \
  -H "Content-Type: application/json" \
  "https://quake.360.net/api/v3/search/quake_service" \
  -d '{"query":"port: 443","start":0,"size":10}'
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
}

data = {
    "query": "port: 443",
    "start": 0,
    "size": 10,
}

response = requests.post(
    "https://quake.360.net/api/v3/search/quake_service",
    headers=headers,
    json=data,
)
print(response.json())
```

## 统一响应结构

| 字段 | 类型 | 必含 | 说明 |
| --- | --- | --- | --- |
| `code` | int | 是 | 请求状态码，`0` 表示成功 |
| `message` | string | 是 | 请求信息，成功时通常为 `Successful` 或 `Successful.` |
| `data` | object/list | 否 | 接口返回的数据主体 |
| `meta` | object | 否 | 额外信息，例如分页信息 |

### 错误码

| Code | 说明 |
| --- | --- |
| `q3004` | 验证码验证错误 |
| `q3005` | 访问已被限速，请输入验证码 |
| `q3007` | 用户积分不足 |
| `u3009` | 缺少请求参数 |
| `u3010` | 参数类型错误 |
| `q3011` | 用户缺少必要权限，请联系管理员 `<quake@360.cn>` |
| `q3015` | 查询语句解析错误 |
| `q3017` | 暂不支持该字段查询 |

## 积分规则

- 不同等级用户每月会获得对应的免费 API 调用次数，可在个人中心查看剩余额度。
- 免费 API 次数用完后，通过 API 调用返回的资产数量会消耗同等数量积分，即 `1 条资产 = 1 积分`。

## 接口列表

| 接口名 | 方法 | 地址 |
| --- | --- | --- |
| 用户信息 | GET | `/api/v3/user/info` |
| 获取服务数据筛选字段 | GET | `/api/v3/filterable/field/quake_service` |
| 服务数据实时查询 | POST | `/api/v3/search/quake_service` |
| 服务数据深度查询 | POST | `/api/v3/scroll/quake_service` |
| 获取聚合数据筛选字段 | GET | `/api/v3/aggregation/quake_service` |
| 服务聚合数据查询 | POST | `/api/v3/aggregation/quake_service` |

## 用户信息

```http
GET /api/v3/user/info
```

用途：获取当前 API Key 对应的用户详情。

### Header

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `X-QuakeToken` | 是 | string | 用户 API Key |

### 示例

```bash
curl -X GET \
  "https://quake.360.net/api/v3/user/info" \
  -H "X-QuakeToken: {API Key}"
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
}

response = requests.get(
    "https://quake.360.net/api/v3/user/info",
    headers=headers,
)
print(response.json())
```

### 响应字段

| 字段 | 说明 |
| --- | --- |
| `data.id` | 用户详情记录 ID |
| `data.user.id` | 用户 ID |
| `data.user.username` | 用户名 |
| `data.user.fullname` | 姓名 |
| `data.user.email` | 邮箱 |
| `data.baned` | 是否封禁 |
| `data.ban_status` | 账号状态 |
| `data.credit` | 月度积分 |
| `data.persistent_credit` | 长效积分 |
| `data.token` | 当前 API Token |
| `data.role` | 用户角色列表 |

## 服务数据接口

### 获取服务数据筛选字段

```http
GET /api/v3/filterable/field/quake_service
```

用途：获取服务数据接口中可用于 `include`、`exclude` 的字段列表。

### 示例

```bash
curl -X GET \
  "https://quake.360.net/api/v3/filterable/field/quake_service" \
  -H "X-QuakeToken: {API Key}"
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
}

response = requests.get(
    "https://quake.360.net/api/v3/filterable/field/quake_service",
    headers=headers,
)
print(response.json())
```

### 可筛选字段示例

```text
components.product_level
components.product_catalog
location.country_cn
domain
service.http.favicon.hash
service.http.host
components.product_vendor
location.city_en
service.http.title
service.name
time
location.isp
transport
location.province_en
components.product_name_cn
asn
location.city_cn
location.province_cn
service.http.status_code
service.http.infomation.mail
org
service.http.icp.main_licence.unit
location.district_cn
service.cert
service.http.server
hostname
service.http.body
components.product_type
location.district_en
service.http.favicon.data
ip
service.http.icp.licence
components.version
location.country_en
port
service.response
```

### 服务数据实时查询

```http
POST /api/v3/search/quake_service
```

用途：小批量服务数据查询。存在深度翻页或一次性查询大量数据需求时，使用深度查询接口。

### 参数

| 参数 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `query` | 是 | string | `*` | 查询语句 |
| `rule` | 否 | string | 无 | 类型为 IP 列表的服务数据收藏名称 |
| `ip_list` | 否 | List[string] | 无 | IP 列表 |
| `start` | 否 | int | `0` | 返回结果起始下标 |
| `size` | 否 | int | `10` | 返回结果数量 |
| `ignore_cache` | 否 | bool | `false` | 是否忽略缓存 |
| `start_time` | 否 | string | 无 | 查询起始时间，格式 `2020-10-14 00:00:00`，时区 UTC |
| `end_time` | 否 | string | 无 | 查询截止时间，格式 `2020-10-14 00:00:00`，时区 UTC |
| `include` | 否 | List[string] | 无 | 包含字段 |
| `exclude` | 否 | List[string] | 无 | 排除字段 |
| `latest` | 否 | bool | `true` | 是否使用最新数据 |
| `shortcuts` | 否 | List[string] | 无 | Web 页面中的快捷过滤项，例如过滤无效请求、排除蜜罐、排除 CDN |

说明：

- 仅付费用户能够指定查询时间，非付费用户默认仅查询近一年数据。
- `include` 和 `exclude` 的可传字段来自 `GET /api/v3/filterable/field/quake_service`。

### 可返回字段

注册用户服务数据字段：

```text
ip, port, hostname, transport, asn, org, service.name,
location.country_cn, location.province_cn, location.city_cn,
service.http.host, service.http.title, service.http.server
```

会员用户服务数据字段：

```text
ip, port, hostname, transport, asn, org, service.name,
location.country_cn, location.province_cn, location.city_cn,
service.http.host, time, service.http.title, service.http.server,
service.response, service.cert, components.product_catalog,
components.product_type, components.product_level, components.product_vendor,
location.country_en, location.province_en, location.city_en,
location.district_en, location.district_cn, location.isp,
service.http.body, components.product_name_cn, components.version,
service.http.infomation.mail, service.http.favicon.hash,
service.http.favicon.data, domain, service.http.status_code
```

### 示例

```bash
curl --location "https://quake.360.net/api/v3/search/quake_service" \
  --header "X-QuakeToken: {API Key}" \
  --header "Content-Type: application/json" \
  --data '{
    "query": "country:\"china\"",
    "start": 0,
    "size": 10,
    "ignore_cache": false,
    "latest": true,
    "shortcuts": [
      "610ce2adb1a2e3e1632e67b1"
    ]
  }'
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
    "Content-Type": "application/json",
}

data = {
    "query": "service: http",
    "start": 0,
    "size": 1,
    "ignore_cache": False,
    "latest": True,
    "shortcuts": ["610ce2adb1a2e3e1632e67b1"],
}

response = requests.post(
    "https://quake.360.net/api/v3/search/quake_service",
    headers=headers,
    json=data,
)
print(response.json())
```

### 响应示例

```json
{
  "code": 0,
  "message": "Successful.",
  "data": [],
  "meta": {
    "pagination": {
      "count": 1,
      "page_index": 1,
      "page_size": 1,
      "total": 68184
    }
  }
}
```

### 服务数据深度查询

```http
POST /api/v3/scroll/quake_service
```

用途：通过 `pagination_id` 获取更多分页数据，适用于深度翻页。分页 ID 过期时间为 5 分钟。

### 参数

| 参数 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `pagination_id` | 否 | string | 无 | 分页 ID；首次请求不传，后续请求传上一页返回的 ID |
| `query` | 是 | string | `*` | 查询语句 |
| `rule` | 否 | string | 无 | 类型为 IP 列表的服务数据收藏名称 |
| `ip_list` | 否 | List[string] | 无 | IP 列表 |
| `size` | 否 | int | `10` | 单次分页大小 |
| `ignore_cache` | 否 | bool | `false` | 是否忽略缓存 |
| `start_time` | 否 | string | 无 | 查询起始时间，格式 `2020-10-14 00:00:00`，时区 UTC |
| `end_time` | 否 | string | 无 | 查询截止时间，格式 `2020-10-14 00:00:00`，时区 UTC |
| `include` | 否 | List[string] | 无 | 包含字段 |
| `exclude` | 否 | List[string] | 无 | 排除字段 |
| `latest` | 否 | bool | `true` | 是否使用最新数据 |

使用流程：

1. 首次请求不传 `pagination_id`。
2. 响应中的 `meta.pagination_id` 为本次查询的分页 ID。
3. 后续请求保持其他参数不变，并传入 `pagination_id`。
4. 当 `pagination_id` 不变且 `data` 为空时，代表翻到最后一页。

### 首次请求示例

```bash
curl -X POST \
  "https://quake.360.net/api/v3/scroll/quake_service" \
  -H "X-QuakeToken: {API Key}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "service: http",
    "size": 1,
    "ignore_cache": false,
    "start_time": "2021-01-07 00:13:14",
    "end_time": "2021-05-20 01:13:14"
  }'
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
    "Content-Type": "application/json",
}

data = {
    "query": "service: http",
    "size": 1,
    "ignore_cache": False,
    "latest": True,
    "shortcuts": ["610ce2adb1a2e3e1632e67b1"],
}

response = requests.post(
    "https://quake.360.net/api/v3/scroll/quake_service",
    headers=headers,
    json=data,
)
print(response.json())
```

### 后续请求示例

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
    "Content-Type": "application/json",
}

data = {
    "query": "service: http",
    "pagination_id": "66c5937994f2d3e429523da4",
    "size": 1,
    "ignore_cache": False,
    "start_time": "2021-01-07 00:13:14",
    "end_time": "2021-05-20 01:13:14",
}

response = requests.post(
    "https://quake.360.net/api/v3/scroll/quake_service",
    headers=headers,
    json=data,
)
print(response.json())
```

### 响应示例

```json
{
  "code": 0,
  "message": "Successful.",
  "data": [],
  "meta": {
    "total": {
      "value": 8078638343,
      "relation": "eq"
    },
    "pagination_id": "66c5937994f2d3e429523da4"
  }
}
```

### 获取聚合数据筛选字段

```http
GET /api/v3/aggregation/quake_service
```

用途：获取服务聚合查询可用的聚合字段。

### 示例

```bash
curl -X GET \
  "https://quake.360.net/api/v3/aggregation/quake_service" \
  -H "X-QuakeToken: {API Key}"
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
}

response = requests.get(
    "https://quake.360.net/api/v3/aggregation/quake_service",
    headers=headers,
)
print(response.json())
```

### 可聚合字段示例

```text
ip
port
service
product
os
asn
org
title
server
app
catalog
type
level
vendor
isp
status_code
powered_by
meta_keywords
page_type
icp
app_and_version
service_and_version
unique_ip
unique_domain
unique_port
unique_product
unique_asn
unique_org
unique_isp
unique_title
unique_server
unique_app
unique_catalog
unique_type
unique_level
unique_vendor
unique_country
unique_province
unique_city
province
province_cn
country
country_cn
country_code
city
city_cn
district
district_cn
province_of_china
```

### 服务聚合数据查询

```http
POST /api/v3/aggregation/quake_service
```

用途：基于查询语句返回服务数据的聚合统计信息。

### 参数

| 参数 | 必填 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `query` | 是 | string | `*` | 查询语句 |
| `rule` | 否 | string | 无 | 类型为 IP 列表的服务数据收藏名称 |
| `ip_list` | 否 | List[string] | 无 | IP 列表 |
| `size` | 否 | int | `5` | 每项聚合数据数量，最大 `10000` |
| `ignore_cache` | 否 | bool | `false` | 是否忽略缓存 |
| `aggregation_list` | 是 | List[string] | 无 | 聚合字段列表，最多支持两个字段 |
| `start_time` | 否 | string | 无 | 查询起始时间，格式 `2020-10-14 00:00:00`，时区 UTC |
| `end_time` | 否 | string | 无 | 查询截止时间，格式 `2020-10-14 00:00:00`，时区 UTC |
| `latest` | 否 | bool | `true` | 是否使用最新数据 |

### 示例

```bash
curl -X POST \
  "https://quake.360.net/api/v3/aggregation/quake_service" \
  -H "X-QuakeToken: {API Key}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "country: China",
    "size": 1,
    "ignore_cache": false,
    "aggregation_list": ["service"],
    "start_time": "2021-01-07 00:13:14",
    "end_time": "2021-05-20 01:13:14"
  }'
```

```python
import requests

headers = {
    "X-QuakeToken": "{API Key}",
}

data = {
    "query": "country: China",
    "size": 1,
    "ignore_cache": False,
    "aggregation_list": ["service"],
    "start_time": "2024-01-07 00:13:14",
    "end_time": "2024-05-20 01:13:14",
}

response = requests.post(
    "https://quake.360.net/api/v3/aggregation/quake_service",
    headers=headers,
    json=data,
)
print(response.json())
```

### 响应示例

```json
{
  "code": 0,
  "message": "Successful.",
  "data": {
    "service": [
      {
        "key": "http",
        "doc_count": 137128183
      }
    ]
  },
  "meta": {}
}
```
