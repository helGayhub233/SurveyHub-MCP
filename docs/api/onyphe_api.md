# Onyphe API

> 文件时间：2026-06-17
> 接口版本：Onyphe API v2
> 文档来源：https://search.onyphe.io/docs

---

## 通用说明

### 基础URL

```
https://www.onyphe.io/api/v2/
```

### 认证方式

所有接口通过 HTTP Header `Authorization: bearer <API_KEY>` 认证。

环境变量对应：
```
FR_ONYPHE_API_KEY → API Key
```

### 速率限制

所有 Plan 平均 1 req/s，本项目使用 1.0s 节流。

### 分页

Search API 支持 `page` 分页，最多 10,000 条结果。

---

## 接口列表

### 1. 资产搜索

```
GET /api/v2/search/?q=...&page=...
```

使用 OQL 搜索互联网扫描数据，覆盖 datascan、resolver、geoloc、inetnum、threatlist、vulnscan、ctl 等类别。

**OQL 示例**：
- `protocol:rdp` — 按协议
- `domain:example.com` — 按域名
- `os:windows country:CN` — OS + 国家
- `category:datascan ip:8.8.8.8` — 指定类别

---

### 2. IP 资产摘要

```
GET /api/v2/summary/ip/{IP}
```

聚合最近 30 天所有类别的数据，每个类别返回最新 10 或 100 条结果。

---

### 3. 域名资产摘要

```
GET /api/v2/summary/domain/{DOMAIN}
```

聚合 resolver、ctl、datascan、threatlist、whois 类别的域名数据。

---

### 4. 账户信息

```
GET /api/v2/user
```

返回许可证类型、剩余 credit、到期日、可用类别和字段。
