# Hunter 个人版 API 文档

来源：`https://hunter.qianxin.com/home/helpCenter`

抓取时间：2026-05-14

## 基础信息

- 接入域名：`hunter.qianxin.com`
- 认证参数：`api-key`
- `api-key` 获取位置：登录后在个人中心获取
- `api-key` 有效期：不会自动过期，可在个人中心手动更新
- 请求方式：个人版 API 覆盖 `GET` 和 `POST`
- 查询语法编码：`search` 参数需要使用符合 RFC 4648 的 Base64 URL-safe 编码

## 认证说明

所有公开接口都需要携带 `api-key`。平台会校验账号权限，无权限时接口不可调用。

```json
{
  "code": 401,
  "message": "令牌过期",
  "data": null
}
```

## 语法查询接口

```http
GET /openApi/search
```

用途：小批量语法查询。平台搜索结果页可生成 Bash、Go、Python、PHP 调用样例。

### 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `api-key` | 是 | 个人 API Key |
| `search` | 是 | 查询语法的 Base64 URL-safe 编码结果 |
| `start_time` | 否 | 开始日期，格式 `YYYY-MM-DD`。个人版查询超出近 30 天会扣除权益积分 |
| `end_time` | 否 | 结束日期，格式 `YYYY-MM-DD`。个人版查询超出近 30 天会扣除权益积分 |
| `page` | 是 | 页码 |
| `page_size` | 是 | 每页资产条数 |
| `is_web` | 否 | 资产类型：`1` Web 资产，`2` 非 Web 资产，`3` 全部 |
| `status_code` | 否 | 状态码列表，逗号分隔，如 `200,401` |
| `fields` | 否 | 返回字段列表，逗号分隔 |

### 个人版 `fields` 枚举

```text
ip, port, domain, ip_tag, url, web_title, is_risk_protocol, protocol,
base_protocol, status_code, os, company, number, icp_exception, country,
province, city, is_web, isp, as_org, cert_sha256, ssl_certificate,
component, asset_tag, updated_at, header, header_server, banner
```

### 请求示例

```bash
curl -X GET -k "https://hunter.qianxin.com/openApi/search?api-key={api-key}&search={search}&page=1&page_size=10&is_web=1&start_time=2021-01-01&end_time=2021-03-01"
```

### Python 编码示例

```python
import base64

query = 'title="北京"'
search = base64.urlsafe_b64encode(query.encode("utf-8")).decode("ascii")
```

### 成功响应结构

| 字段 | 说明 |
| --- | --- |
| `code` | 状态码 |
| `message` | 响应消息 |
| `data.account_type` | 账号类型 |
| `data.total` | 资产总数 |
| `data.time` | 查询耗时 |
| `data.arr` | 资产列表 |
| `data.consume_quota` | 消耗积分 |
| `data.rest_quota` | 今日剩余积分 |
| `data.syntax_prompt` | 语法提示 |

## 批量查询接口

个人版支持通过搜索语法或 CSV 文件创建批量检索任务。接口调用成功后返回 `task_id`，后续用该 ID 查询进度或下载文件。

### 创建批量任务

```http
POST /openApi/search/batch
```

#### 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `api-key` | 是 | 个人 API Key |
| `search` | 否 | 查询语法的 Base64 URL-safe 编码结果；传文件时可不传 |
| `file` | 否 | CSV 文件，通过 multipart form 上传 |
| `start_time` | 否 | 开始日期，格式 `YYYY-MM-DD` |
| `end_time` | 否 | 结束日期，格式 `YYYY-MM-DD` |
| `is_web` | 否 | `1` Web 资产，`2` 非 Web 资产 |
| `status_code` | 否 | 状态码列表，逗号分隔 |
| `fields` | 否 | 返回字段列表，枚举同语法查询接口 |
| `search_type` | 否 | 上传文件类型，默认 `all` |
| `assets_limit` | 否 | 预期导出的资产数量 |

#### `search_type` 说明

| 值 | 说明 | 个人版数量限制 |
| --- | --- | --- |
| `all` | 混合检索，支持 IP、IP 段或域名 | 最多 10 个目标 |
| `ip` | 仅 IP、IP 段精确检索 | 最多 100 个目标 |
| `domain` | 仅域名检索，等效于 `domain.suffix` 语法 | 最多 100 个目标 |
| `company` | 仅企业名称检索，等效于 `icp.name` 精确检索 | 最多 100 个目标 |

#### 请求示例

```bash
curl -X POST -k -F "file=@batch_file_template.csv" "https://hunter.qianxin.com/openApi/search/batch?api-key={api-key}&is_web=1&start_time=2021-01-01&end_time=2021-03-01"

curl -X POST -k "https://hunter.qianxin.com/openApi/search/batch?api-key={api-key}&search={search}&is_web=1&start_time=2021-01-01&end_time=2021-03-01"
```

#### 成功响应字段

| 字段 | 说明 |
| --- | --- |
| `data.task_id` | 任务 ID |
| `data.filename` | 导出文件名 |
| `data.consume_quota` | 消耗积分 |
| `data.rest_quota` | 今日剩余积分 |

### 查询导出进度

```http
GET /openApi/search/batch/{task_id}
```

```bash
curl -X GET -k "https://hunter.qianxin.com/openApi/search/batch/{task_id}?api-key={api-key}"
```

| 字段 | 说明 |
| --- | --- |
| `data.status` | 任务状态 |
| `data.progress` | 进度百分比 |
| `data.rest_time` | 预计剩余时间 |

### 下载导出文件

```http
GET /openApi/search/download/{task_id}
```

```bash
curl -X GET -k "https://hunter.qianxin.com/openApi/search/download/{task_id}?api-key={api-key}" -o output.csv
```

常见错误包括任务不存在、文件仍在生成中。

## 用户信息接口

```http
GET /openApi/userInfo
```

用途：获取个人账号额度、积分和基础账号信息。

### 参数

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `api-key` | 是 | 个人 API Key |

### 示例

```bash
curl -X GET -k "https://hunter.qianxin.com/openApi/userInfo?api-key={api-key}"
```

### 响应字段

字段值为 `-1` 或字段缺失时，表示无对应限制。

| 字段 | 说明 |
| --- | --- |
| `data.type` | 账号类型，个人版为 `个人账号` |
| `data.rest_equity_point` | 剩余权益积分 |
| `data.rest_free_point` | 当日剩余免费积分 |
| `data.rest_export_quota` | 当日剩余导出额度 |
| `data.day_free_point` | 当日免费积分上限 |
| `data.day_export_quota` | 当日导出额度上限 |
| `data.once_export_quota` | 单次导出额度上限 |
| `data.personal_info.username` | 用户昵称 |
| `data.personal_info.phone` | 手机号 |
| `data.personal_info.is_charge` | 是否为充值用户 |

## 返回字段说明

| 字段 | 说明 |
| --- | --- |
| `ip` | IP |
| `port` | 端口 |
| `domain` | 域名 |
| `ip_tag` | IP 标签 |
| `url` | URL |
| `web_title` | 网站标题 |
| `is_risk_protocol` | 是否高危协议 |
| `protocol` | 协议 |
| `base_protocol` | 通讯协议 |
| `status_code` | 网站状态码 |
| `os` | 操作系统 |
| `company` | 备案单位 |
| `number` | 备案号 |
| `icp_exception` | 备案异常 |
| `country` | 国家 |
| `province` | 省份 |
| `city` | 城市 |
| `is_web` | 是否 Web 资产 |
| `isp` | 运营商 |
| `as_org` | 注册机构 |
| `cert_sha256` | 证书 SHA256 |
| `ssl_certificate` | 证书 |
| `component` | 应用或组件 |
| `asset_tag` | 资产标签 |
| `updated_at` | 探查时间 |
| `header` | Header |
| `header_server` | Header Server |
| `banner` | Banner |
| `consume_quota` | 消耗积分 |
| `rest_quota` | 今日剩余积分 |
| `account_type` | 账号类型 |
| `syntax_prompt` | 语法提示 |

公共字段说明中还列出了 `whois`, `body`, `vul_list`，但个人版语法查询与批量查询页面的 `fields` 枚举未包含这些企业版字段。
