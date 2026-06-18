# Criminal IP API

> 文件时间：2026-06-17
> 接口版本：Criminal IP API v1
> 文档来源：https://search.criminalip.io/developer/api

---

## 通用说明

### 基础URL

```
https://api.criminalip.io/v1/
```

### 认证方式

通过 HTTP Header `x-api-key` 传递 API Key。

环境变量对应：
```
KR_CRIMINALIP_API_KEY → API Key
```

API Key 获取：https://www.criminalip.io/ 注册后在 My Information 页面获取。

### 速率限制

本项目使用 1.0s 节流。

---

## 接口列表

### 1. IP 资产报告

```
GET /v1/asset/ip/report?ip={ip}&full={true|false}
```

返回 IP 的综合资产报告：开放端口、服务 banner、SSL 证书、漏洞信息、恶意/可疑评分、VPN/托管检测、WHOIS、域名关联。

### 2. Banner 搜索

```
GET /v1/banner/search?query={query}&offset={offset}
```

全网服务 Banner 搜索。按协议、端口、产品、版本、地理位置、CVE 标签等过滤。

查询示例：`protocol:rdp`, `port:3306`, `product:nginx`, `country:US`, `cve:CVE-2021-44228`

### 3. 域名报告

```
GET /v1/domain/reports?domain={domain}
```

域名情报报告：风险评分、Web 技术、SSL 证书、子域名、钓鱼/恶意指标、滥用历史。

### 4. 账户信息

```
POST /v1/user/me
```

返回用户计划、credits 余额、搜索配额、会员等级。
