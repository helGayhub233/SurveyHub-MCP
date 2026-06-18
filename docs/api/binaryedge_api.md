# BinaryEdge API

> 文件时间：2026-06-17
> 接口版本：BinaryEdge API v2
> 文档来源：https://docs.binaryedge.io/（已重定向至 Coalition），交叉验证自 pybinaryedge / api-publicdoc

---

## 通用说明

### 基础URL

```
https://api.binaryedge.io/v2/
```

### 认证方式

所有接口需要 API Key，通过 HTTP Header `X-Key` 传递。

环境变量对应：
```
PT_BINARYEDGE_API_KEY → API Key
```

API Key 获取：https://app.binaryedge.io/account

### 响应格式

所有接口返回 JSON。

### 分页

| 属性 | 值 |
|------|-----|
| 分页参数 | `page`（页码） |
| 最大页数 | 500 |
| 最大结果数 | 10,000 |

### 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 参数格式错误 |
| 401 | API Key 无效 |
| 404 | 资源未找到 |
| 429 | 速率限制/月度配额耗尽 |

---

## 接口列表

### 1. IP 情报查询

```
GET /v2/query/ip/{ip}
```

**参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ip | string (path) | ✅ | IPv4/IPv6 地址 |

**响应**：`{events: [...], total: int, page: int, pagesize: int}`

每个 event 包含：端口、协议、产品名、版本、国家、ASN、SSL 证书、模块扫描结果等。

---

### 2. 全域搜索

```
GET /v2/query/search
```

**参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | ✅ | — | 搜索查询 |
| page | int | ❌ | 1 | 页码（最大 500） |

**查询语法**：
- `product:nginx` — 按产品筛选
- `port:80` — 按端口筛选
- `country:CN` — 按国家筛选
- `tags:cve` — 按标签筛选
- 支持 `AND`/`OR` 组合

---

### 3. 子域名枚举

```
GET /v2/query/domains/subdomain/{domain}
```

**参数**：
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| domain | string (path) | ✅ | — | 目标域名 |
| page | int | ❌ | 1 | 页码 |

**响应**：返回通过被动 DNS 发现的子域名列表。

---

### 4. 账户信息

```
GET /v2/user/subscription
```

**参数**：无

**响应**：返回套餐详情、API 配额使用情况和剩余额度。
