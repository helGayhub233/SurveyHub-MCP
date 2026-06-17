# Shodan API

> 文件时间：2026-06-17
> 接口版本：Shodan REST API v1
> 文档来源：https://developer.shodan.io/api

---

## 通用说明

### 基础URL

```
https://api.shodan.io
```

DNS 接口：
```
https://api.shodan.io/dns/...
```

### 认证方式

所有接口都需要 API Key，通过 **query 参数**传递：

```
?key=YOUR_API_KEY
```

免费账户可在 https://account.shodan.io/register 注册后获取 API Key。

### 响应格式

所有接口返回 JSON，错误格式：

```json
{"error": "error message"}
```

### 速率限制

所有 API 套餐统一限制为 **1 次请求/秒**。

### 查询额度

| 接口 | 消耗 query credits |
|---|---|
| `/shodan/host/search` | 每次过滤搜索或超过第 1 页时消耗 1 credit |
| `/shodan/host/count` | **不消耗** query credits |
| `/shodan/host/{ip}` | **不消耗** query credits |
| `/dns/domain/{domain}` | 每次查询消耗 1 credit |
| `/dns/resolve` | **不消耗** query credits |
| `/dns/reverse` | **不消耗** query credits |

---

## 搜索语法

### 基本规则

- 格式：`filter:value` — 过滤器名和值之间用 `:` 冒号分隔
- 多值：逗号分隔表示 OR 关系：`country:US,CN`
- 取反：前缀 `-` 表示排除：`-port:22`
- 自由文本：非过滤器的文本在所有 banner 数据中搜索
- 组合：`apache country:DE`
- 引号：含空格的字符串用双引号包裹：`"United States"`

### 常用过滤器

#### 通用
`asn`, `city`, `country`, `cpe`, `device`, `domain`, `geo`, `has_ssl`, `has_vuln`, `hostname`, `ip`, `isp`, `net`, `org`, `os`, `port`, `product`, `region`, `version`

#### HTTP
`http.title`, `http.status`, `http.html`, `http.favicon.hash`, `http.component`, `http.component_category`, `http.waf`, `http.robots_hash`, `http.securitytxt`, `http.server_hash`

#### SSL
`ssl`, `ssl.cert.expired`, `ssl.cert.issuer.cn`, `ssl.cert.subject.cn`, `ssl.ja3s`, `ssl.jarm`, `ssl.version`, `ssl.cipher.name`, `ssl.cert.fingerprint`, `ssl.cert.pubkey.bits`, `ssl.cert.pubkey.type`, `ssl.alpn`

#### Cloud
`cloud.provider`, `cloud.region`, `cloud.service`

#### SSH
`ssh.hassh`, `ssh.type`

#### 其他
`bitcoin.ip`, `bitcoin.ip_count`, `bitcoin.port`, `bitcoin.version`, `screenshot.label`, `screenshot.hash`, `ntp.ip`, `ntp.ip_count`, `ntp.more`, `ntp.port`, `snmp.contact`, `snmp.location`, `snmp.name`, `telnet.do`, `telnet.dont`, `telnet.option`, `telnet.will`, `telnet.wont`

> 完整过滤器列表：https://www.shodan.io/search/filters

### 搜索示例

```
apache country:CN
product:"Apache httpd" country:DE
port:22 country:US
org:"Google"
has_vuln:true
ssl.cert.subject.cn:"example.com"
http.title:"Login"
http.status:200
```

---

## 接口详情

### 1. 资产搜索

`GET /shodan/host/search`

搜索 Shodan 数据库中的所有资产。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `key` | string | ✅ | — | API Key |
| `query` | string | ✅ | — | Shodan 搜索查询（filter:value 语法） |
| `page` | int | ❌ | 1 | 页码，每页固定 100 条 |
| `facets` | string | ❌ | — | 逗号分隔的聚合字段，如 `org,os` 或 `country:100` |

**响应结构：**

```json
{
  "matches": [
    {
      "product": "Apache httpd",
      "hash": -123456789,
      "ip": 134744072,
      "org": "Google",
      "isp": "Google",
      "transport": "tcp",
      "cpe": ["cpe:/a:apache:http_server"],
      "data": "HTTP/1.1 200 OK...",
      "asn": "AS15169",
      "port": 80,
      "hostnames": ["example.com"],
      "location": {
        "city": "Mountain View",
        "region_code": "CA",
        "country_code": "US",
        "country_name": "United States",
        "latitude": 37.422,
        "longitude": -122.084
      },
      "timestamp": "2026-06-17T00:00:00.000000",
      "domains": ["example.com"],
      "http": {"html": "...", "title": "..."},
      "os": null,
      "_shodan": {"id": "...", "options": {}, "ptr": true, "module": "http", "crawler": "..."},
      "ip_str": "8.8.8.8",
      "version": "2.4.54"
    }
  ],
  "facets": {
    "org": [{"count": 100000, "value": "Google"}]
  },
  "total": 23047224
}
```

---

### 2. 搜索结果计数

`GET /shodan/host/count`

与 `/shodan/host/search` 查询参数相同，但只返回 `total` 和 `facets`，**不消耗 query credits**。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `key` | string | ✅ | — | API Key |
| `query` | string | ✅ | — | Shodan 搜索查询 |
| `facets` | string | ❌ | — | 逗号分隔的聚合字段 |

**响应结构：**

```json
{
  "matches": [],
  "facets": {
    "org": [{"count": 19590274, "value": "Google"}]
  },
  "total": 19590274
}
```

---

### 3. IP 主机信息

`GET /shodan/host/{ip}`

获取指定 IP 上所有开放服务的信息。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| `key` | string | ✅ | — | API Key |
| `ip` | string (path) | ✅ | — | 目标 IP，如 `8.8.8.8` |
| `history` | bool | ❌ | false | 返回所有历史 banner |
| `minify` | bool | ❌ | false | 仅返回端口和基本信息，不返回 banner |

**响应结构：**

```json
{
  "region_code": "CA",
  "ip": 134744072,
  "postal_code": "94043",
  "country_code": "US",
  "city": "Mountain View",
  "last_update": "2026-06-17T00:00:00.000000",
  "latitude": 37.422,
  "tags": ["cloud"],
  "country_name": "United States",
  "hostnames": ["example.com"],
  "org": "Google",
  "data": [
    {
      "port": 80,
      "transport": "tcp",
      "product": "Apache httpd",
      "version": "2.4.54",
      "data": "HTTP/1.1 200 OK...",
      "http": {"html": "...", "title": "..."},
      "ssl": null,
      "cpe": ["cpe:/a:apache:http_server:2.4.54"],
      "timestamp": "2026-06-17T00:00:00.000000",
      ...
    }
  ],
  "asn": "AS15169",
  "isp": "Google",
  "longitude": -122.084,
  "country_code3": "USA",
  "domains": ["example.com"],
  "ip_str": "8.8.8.8",
  "os": null,
  "ports": [80, 443]
}
```

---

### 4. API 配额信息

`GET /api-info`

获取当前 API Key 的计划和配额信息。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `key` | string | ✅ | API Key |

**响应结构：**

```json
{
  "scan_credits": 100000,
  "usage_limits": {
    "scan_credits": -1,
    "query_credits": -1,
    "monitored_ips": -1
  },
  "plan": "stream-100",
  "https": false,
  "unlocked": true,
  "query_credits": 100000,
  "monitored_ips": 19,
  "unlocked_left": 100000,
  "telnet": false
}
```

---

### 5. 域名信息

`GET /dns/domain/{domain}`

获取域名的所有子域名和 DNS 记录。**每次查询消耗 1 query credit**。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `key` | string | ✅ | API Key |
| `domain` | string (path) | ✅ | 域名，如 `google.com` |

**响应结构：**

```json
{
  "domain": "google.com",
  "tags": ["cloud"],
  "data": [
    {
      "subdomain": "mail.google.com",
      "type": "A",
      "value": "142.250.80.4",
      "last_seen": "2026-06-17"
    },
    {
      "subdomain": "",
      "type": "MX",
      "value": "smtp.google.com",
      "last_seen": "2026-06-17"
    }
  ],
  "subdomains": ["www", "mail", "drive"],
  "more": false
}
```

---

### 6. DNS 正向解析

`GET /dns/resolve`

将域名解析为 IP 地址。**不消耗 query credits**。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `key` | string | ✅ | API Key |
| `hostnames` | string | ✅ | 逗号分隔的域名列表，如 `google.com,bing.com` |

**响应结构：**

```json
{
  "google.com": "142.250.80.4",
  "bing.com": "13.107.21.200"
}
```

---

### 7. DNS 反向解析

`GET /dns/reverse`

将 IP 地址反向解析为域名。**不消耗 query credits**。

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `key` | string | ✅ | API Key |
| `ips` | string | ✅ | 逗号分隔的 IP 列表，如 `8.8.8.8,1.1.1.1` |

**响应结构：**

```json
{
  "8.8.8.8": ["dns.google"],
  "1.1.1.1": ["one.one.one.one"]
}
```

---

## API 套餐

| 功能 | Membership | Freelancer | Small Business | Corporate | Enterprise |
|---|---|---|---|---|---|
| **价格** | $49 (一次性) | $69/月 | $359/月 | $1,099/月 | 定制 |
| **Query Credits/月** | 100 | 10,000 | 200,000 | 无限制 | 无限制 |
| **Scan Credits/月** | 100 | 5,120 | 65,536 | 327,680 | 无限制 |
| **监控 IP 数** | 16 | 5,120 | 65,536 | 327,680 | 无限制 |
| **过滤器** | 除 vuln,tag | 除 vuln,tag | 除 tag | 全部 | 全部 |

---

## 错误码

| HTTP 状态码 | 说明 |
|---|---|
| 200 | 成功 |
| 401 | API Key 无效或缺失 |
| 403 | 权限不足（接口限高级套餐） |
| 404 | 资源不存在或 IP 超出扫描范围 |
| 429 | 超过速率限制 |
| 500 | 服务端错误 |

> 未列出接口详见官方文档：https://developer.shodan.io/api
