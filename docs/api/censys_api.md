# Censys Search API

> 文件时间：2026-06-17
> 接口版本：Censys Search API v2
> 文档来源：https://search.censys.io/api 和 https://docs.censys.io/

---

## 通用说明

### 基础URL

```
https://search.censys.io/api
```

### 认证方式

所有接口需要 **HTTP Basic Auth**：

- **Username**: API ID（从 https://search.censys.io/account/api 获取）
- **Password**: API Secret

环境变量对应：
```
US_CENSYS_API_ID → API ID
US_CENSYS_API_SECRET → API Secret
```

### 响应格式

所有接口返回 JSON，错误格式：

```json
{
  "error": "error message",
  "status": "error/not_found/..."
}
```

### 速率限制

| 套餐 | 并发限制 | 月度 Credits |
|---|---|---|
| Free | 1 并发请求 | 100 credits/月 |
| Starter | 1 并发请求 | 已购 credits（12个月有效） |

> 本项目使用进程内 1.1s 节流确保串行访问，满足 1 并发限制。

### 额度消耗

| 操作 | Credit 消耗 |
|---|---|
| 实体查询（IP/指纹） | 1 credit |
| 标准搜索查询 | 5 credits |
| 高级查询（含正则） | 8 credits |
| 聚合查询 | 5–8 credits |
| 翻页（额外结果页） | 5–8 credits |

---

## 搜索语法

### 操作符

| 操作符 | 说明 | 示例 |
|---|---|---|
| `:` | 不区分大小写的分词搜索 | `services.service_name: HTTP` |
| `=` | 精确匹配（字符串区分大小写） | `location.country= "United States"` |
| `=~` | 正则匹配 | `services.banner=~\`nginx\`` |
| `<, >, <=, >=` | 比较 | `services.port > 1024` |
| `:*` | 字段存在（非空） | `services.banner: *` |

### 布尔操作符

- `and`, `or`, `not`（不区分大小写）
- 括号分组：`not (location.country="US" or location.country="CN")`
- 花括号值列表：`services.port: {80, 443}`

### 常用搜索字段

#### 主机
`ip`, `location.country`, `location.country_code`, `location.city`, `location.province`, `location.continent`, `location.coordinates`, `location.timezone`

#### 自治系统
`autonomous_system.asn`, `autonomous_system.name`, `autonomous_system.organization`, `autonomous_system.country_code`, `autonomous_system.bgp_prefix`

#### 服务
`services.port`, `services.service_name`, `services.transport_protocol`, `services.banner`, `services.software`, `services.tls`

#### HTTP
`services.http.response.html_title`, `services.http.response.status_code`, `services.http.response.body`

#### 操作系统
`operating_system.product`, `operating_system.version`, `operating_system.source`

#### DNS
`dns.names`, `dns.reverse_dns`

#### 其他
`last_updated_at`, `labels`

### 时间查询

```sql
last_updated_at: [2025-01-01 TO 2025-06-01]
```

### 嵌套查询

对单个服务对象施加条件：
```sql
services: (port=22 and service_name=SSH)
```

### 搜索示例

```
services.service_name: HTTP
location.country: "United States" and services.port: 443
autonomous_system.name: Google
services.http.response.html_title: "Login"
operating_system.product: "Windows"
not services.port: 22
services: (port=80 or port=443)
```

---

## 接口详情

### 1. 主机搜索

`GET /v2/hosts/search`

搜索 Censys 数据库中的所有主机。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `q` | string | ❌ | — | Censys 搜索查询 |
| `per_page` | int | ❌ | 50 | 每页结果数（最大 100） |
| `cursor` | string | ❌ | — | Base64 分页游标，从 `links.next` 获取 |
| `fields` | string | ❌ | — | 逗号分隔的 dot-notation 字段（最多 25 个） |
| `sort` | string | ❌ | — | `RELEVANCE`, `ASCENDING`, `DESCENDING` |
| `virtual_hosts` | string | ❌ | — | `EXCLUDE`, `INCLUDE`, `ONLY` |

**默认返回字段**: `ip`, `name`, `location`, `autonomous_system`, `last_updated_at`

**默认服务字段**: `port`, `service_name`, `extended_service_name`, `transport_protocol`

**响应结构：**

```json
{
  "code": 200,
  "status": "OK",
  "result": {
    "query": "services.service_name: HTTP",
    "total": 5000000,
    "duration_ms": 123,
    "hits": [
      {
        "ip": "8.8.8.8",
        "location": {
          "country": "United States",
          "country_code": "US",
          "city": "Mountain View",
          "province": "California",
          "continent": "North America",
          "coordinates": {"latitude": 37.422, "longitude": -122.084}
        },
        "autonomous_system": {
          "asn": 15169,
          "name": "GOOGLE",
          "organization": "Google LLC",
          "country_code": "US",
          "bgp_prefix": "8.8.8.0/24"
        },
        "services": [
          {
            "port": 443,
            "service_name": "HTTP",
            "transport_protocol": "TCP",
            "http": {
              "response": {
                "html_title": "Google"
              }
            }
          }
        ],
        "last_updated_at": "2026-06-17T00:00:00Z"
      }
    ],
    "links": {
      "next": "base64_cursor_token",
      "prev": null
    }
  }
}
```

---

### 2. 聚合查询

`GET /v2/hosts/aggregate`

按字段对搜索结果进行分组统计。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `q` | string | ✅ | 搜索查询 |
| `field` | string | ✅ | 聚合字段，如 `services.port` |
| `num_buckets` | int | ❌ | 分桶数（默认 50，最大 500） |

**响应结构：**

```json
{
  "code": 200,
  "status": "OK",
  "result": {
    "total": 5000000,
    "buckets": [
      {"key": "443", "count": 2000000},
      {"key": "80", "count": 1500000}
    ],
    "potential_total_buckets": 65535
  }
}
```

---

### 3. 主机详情

`GET /v2/hosts/{ip}`

获取指定 IP 的完整扫描信息。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `ip` | string (path) | ✅ | 目标 IP，如 `8.8.8.8` |
| `at_time` | string | ❌ | 历史快照时间戳（RFC 3339），如 `2025-01-01T00:00:00Z` |

**响应结构**：与该 IP 最近一次扫描的完整结果，包含所有 `services`、`location`、`autonomous_system`、`dns`、`labels` 等字段。

---

### 4. 账号配额

`GET /v1/account`

获取当前 API Key 的配额信息。

**响应结构：**

```json
{
  "quota": {
    "used": 25,
    "allowance": 100,
    "resets_at": "2026-07-01T00:00:00Z"
  }
}
```

---

## HTTP 状态码

| 状态码 | 说明 |
|---|---|
| 200 | 成功 |
| 401 | API ID 或 Secret 无效 |
| 403 | 权限不足或额度耗尽 |
| 404 | 资源不存在 |
| 429 | 超过速率限制 |
| 500 | 服务端错误 |

---

## 与 Shodan 的差异对比

| 特性 | Censys | Shodan |
|---|---|---|
| 认证 | HTTP Basic Auth（ID+Secret） | API Key query 参数 |
| 分页 | Cursor-based（`links.next`） | Page-based（1–N） |
| 速率限制 | 1 并发请求 | 1 req/s |
| 额度模型 | 每操作消耗 credits | query credits + scan credits |
| 聚合功能 | `/v2/hosts/aggregate` | `/shodan/host/count`（facet） |
| 查询语法 | `field:value`（Lucene-like） | `filter:value` |
| DNS 端点 | 内置在 host 详情中 | 独立 `/dns/*` 端点 |

> 未列出接口详见官方文档：https://docs.censys.io/
