# Netlas API

> 文件时间：2026-06-17
> 接口版本：Netlas API v1
> 文档来源：https://docs.netlas.io/api-reference/

---

## 通用说明

### 基础URL

```
https://app.netlas.io/api/
```

### 认证方式

所有接口通过 HTTP Header `Authorization: Bearer <API_KEY>` 认证。

环境变量对应：
```
CY_NETLAS_API_KEY → API Key
```

API Key 获取：https://app.netlas.io/profile/

### 查询语法

使用 Lucene Query Syntax，详见：https://docs.netlas.io/knowledge-base/query-language/

### 速率限制

| 操作 | 限制 |
|------|------|
| 搜索/计数（除证书外） | 60 请求/分钟 |
| 证书搜索/计数 | 3 请求/分钟 |

本项目使用 1.0s 节流确保合规。

### 分页

所有搜索端点支持 `start` 偏移（0~9980），最多返回 10,000 条结果。需大量数据时使用 Download 端点。

---

## 接口列表

### 1. 互联网扫描数据搜索

```
GET /api/responses/?q=...&start=...
```

搜索互联网扫描数据（banner、HTTP、SSL 证书等）。

**查询示例**：
- `host:example.com` — 按域名搜索
- `port:443 protocol:http` — 按端口和协议
- `http.title:"Admin"` — 按 HTTP 标题

---

### 2. DNS 记录搜索

```
GET /api/domains/?q=...&start=...
```

搜索 DNS 记录（A、AAAA、NS、MX、TXT、CNAME）。

**查询示例**：
- `domain:example.com` — 按域名
- `domain:*.example.com a:*` — 通配符 + 有 A 记录

---

### 3. IP WHOIS 搜索

```
GET /api/whois_ip/?q=...&start=...
```

搜索 IP WHOIS 数据。

**查询示例**：
- `ip:8.8.8.8` — 按 IP
- `net.organization:"Google"` — 按组织

---

### 4. 账户信息

```
GET /api/users/profile_data/
```

返回请求配额、coins 余额和扫描 coins。
