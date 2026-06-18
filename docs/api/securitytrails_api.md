# SecurityTrails API

> 文件时间：2026-06-17
> 接口版本：SecurityTrails API v1
> 文档来源：https://docs.securitytrails.com/

---

## 通用说明

### 基础URL

```
https://api.securitytrails.com/v1/
```

### 认证方式

所有接口需要 API Key，通过 query 参数 `apikey` 传递。

环境变量对应：
```
US_SECURITYTRAILS_API_KEY → API Key
```

API Key 获取：https://securitytrails.com/app/account/credentials

### 响应格式

所有接口返回 JSON，HTTP 状态码：

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数无效 |
| 401 | API Key 无效 |
| 403 | 权限不足 |
| 429 | 速率限制 |

### 速率限制

API 限制约 1 req/s，本项目使用 1.0s 节流确保合规。

---

## 接口列表

### 1. 获取域名信息

```
GET /v1/domain/{hostname}
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hostname | string | ✅ | 域名，如 example.com |
| apikey | string | ✅ | API Key |

**响应字段**：
- `current_dns`: 当前 DNS 记录（A, AAAA, MX, NS, SOA, TXT）
- `subdomain_count`: 子域名数量
- `alexa_rank`: Alexa 排名
- `hostname`: 域名
- `whois`: 注册信息

---

### 2. 获取子域名列表

```
GET /v1/domain/{hostname}/subdomains
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hostname | string | ✅ | 域名 |
| apikey | string | ✅ | API Key |

**响应字段**：
- `subdomain_count`: 子域名总数
- `subdomains`: 子域名列表

---

### 3. DNS 历史记录

```
GET /v1/history/{hostname}/dns/{type}
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hostname | string | ✅ | 域名 |
| type | string | ✅ | 记录类型：a, aaaa, mx, ns, soa, txt |
| page | int32 | ❌ | 页码，默认 1 |
| apikey | string | ✅ | API Key |

**响应字段**：
- `records`: 历史 DNS 记录列表
- `pages`: 总页数

---

### 4. IP WHOIS 查询

```
GET /v1/ips/{ip}/whois
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ip | string | ✅ | IPv4 地址 |
| apikey | string | ✅ | API Key |

**响应字段**：
- `ip`: IP 地址
- `organization`: 所属组织
- `asn`: 自治系统号
- `carrier`: 运营商
- `country`: 国家
- `range`: CIDR 范围
- `registered`: 注册日期
- `hostnames`: 关联主机名列表
