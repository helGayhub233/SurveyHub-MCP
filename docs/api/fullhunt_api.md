# FullHunt API

> 文件时间：2026-06-17
> 接口版本：FullHunt API v1
> 文档来源：https://fullhunt.io/

---

## 通用说明

### 基础URL

```
https://fullhunt.io/api/v1/
```

### 认证方式

通过 HTTP Header `X-API-KEY` 传递 API Key。

环境变量对应：
```
AE_FULLHUNT_API_KEY → API Key
```

API Key 获取：注册后在 Profile Settings 中获取。

### 速率限制

默认 60 请求/分钟，本项目使用 1.0s 节流。

### Credit 系统

基于请求复杂度和响应大小消耗 credits。通过 `/auth/status` 查询余额。

---

## 接口列表

### 1. 域名详情

```
GET /api/v1/domain/{domain}/details
```

返回域名攻击面全貌：所有发现主机（IP/端口/服务/产品/CPE/SSL证书/Web技术）、WHOIS、DNS 记录、云/CDN信息。

### 2. 子域名列表

```
GET /api/v1/domain/{domain}/subdomains
```

返回发现的子域名主机名列表。

### 3. 主机详情

```
GET /api/v1/host/{host}
```

返回单个主机的完整信息：IP、开放端口、服务检测、产品/CPE、SSL证书、Web技术栈、云供应商等。

### 4. 账户信息

```
GET /api/v1/auth/status
```

返回用户计划、邮箱、credits 使用量、剩余额度、单次最大结果数。
