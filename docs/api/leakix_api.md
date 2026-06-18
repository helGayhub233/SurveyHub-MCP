# LeakIX API

> 文件时间：2026-06-17
> 接口版本：LeakIX API v1
> 文档来源：https://docs.leakix.net/

---

## 通用说明

### 基础URL

```
https://leakix.net/
```

### 认证方式

所有接口通过 HTTP Header `api-key` 传递 API Key，同时需要 `accept: application/json`。

环境变量对应：
```
FR_LEAKIX_API_KEY → API Key
```

API Key 获取：登录 LeakIX → Profile → Settings → API key

### 速率限制

所有端点 1 req/s，超限返回 HTTP 429 + `x-limited-for` 头。

本项目使用 1.0s 节流确保合规。

### 分页

Search API 支持 `page` 参数，从 0 开始。

---

## 查询语法（YQL）

基于 [YQL-Elastic](https://github.com/LeakIX/YQL-Elastic) 库：

| 语法 | 含义 |
|------|------|
| `term` | 单术语（必选） |
| `"phrase"` | 短语匹配 |
| `+term` | 必需条件（AND） |
| `-term` | 排除条件（NOT） |
| `term1 term2` | 无前缀 = 可选（OR） |
| `field:value` | 字段精确匹配 |
| `field:>value` | 大于 |
| `field:<value` | 小于 |

---

## 接口列表

### 1. 搜索

```
GET /search?scope={service|leak}&q={YQL}&page={page}
```

按 YQL 查询搜索 service（开放服务/端口/SSL）或 leak（配置泄露/漏洞/勒索）数据。

### 2. Host 详情

```
GET /host/{ip}
```

返回指定 IP 上发现的所有 Services 和 Leaks，包含端口、协议、SSL、软件、地理信息等。

### 3. 子域名发现

```
GET /api/subdomains/{domain}
```

返回子域名列表（子域名名、独立 IP 数、最后发现时间）。免费版最多 50 条。

### 4. 插件列表

```
GET /api/plugins
```

列出所有检测插件及近 1h/24h/7d 事件统计。
