# DayDayMap API 文档

来源：`https://www.daydaymap.com/help/document`

抓取时间：2026-06-17

## 基础信息

- 接入域名：`www.daydaymap.com`
- 协议：HTTPS
- 编码：UTF-8
- 请求方式：`POST`
- 鉴权：请求头 `api-key` 传递用户 API KEY

## 使用限制

- 每页最大条数：`10000` 条/页。
- 最多只能查看前 `10000` 条数据（`page × page_size` 的偏移不超过 10000）。
- 搜索字符串须使用**英文双引号** `""`，不区分大小写。
- API 语法检索消耗 `1 积分/次`；查看 IPv4 数据 `1 积分/条`，IPv6 数据 `3 积分/条`。
- 积分优先扣除每日积分，每日积分为 0 后扣除权益积分。

### 会员体系

| 等级 | 说明 |
| --- | --- |
| 白银会员 | 基础权益 |
| 黄金会员 | 中等权益 |
| 铂金会员 | 高级权益 |
| Plus 定制 | 定制权益 |

## 请求结构

```text
POST https://www.daydaymap.com/api/v1/raymap/search/all
```

## 认证方式

- 登录 DayDayMap 平台 → 右上角昵称 → 【个人中心】→【个人信息】→ 复制 API KEY。
- API KEY 默认不过期，用户可在个人中心手动刷新。
- API KEY 与用户身份绑定，每个用户独有；泄露后需及时刷新。

## 数据查询接口

```http
POST /api/v1/raymap/search/all
```

用途：按 DayDayMap 查询语法搜索网络空间资产。

### 请求头

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `api-key` | 是 | string | 用户 API KEY |
| `Content-Type` | 是 | string | `application/json` |

### 请求体

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `page` | 是 | number | 页码，范围 1–10000 |
| `page_size` | 是 | number | 每页条数，最大 10000 |
| `keyword` | 是 | string | 搜索语法的 Base64 编码 |
| `fields` | 否 | string | 逗号分隔的自定义响应字段，优先级高于 `exclude_fields` |
| `exclude_fields` | 否 | string | 逗号分隔的排除字段，仅当未指定 `fields` 时有效 |

### 示例

```bash
curl -XPOST -k 'https://www.daydaymap.com/api/v1/raymap/search/all' \
-H 'api-key: xxxxxx07fe2248ac9a6944a622xxxxxx' \
-H 'Content-Type: application/json' \
-d '{
    "page": 1,
    "page_size": 10,
    "keyword": "cG9ydD0iODAi"
}'
```

### 成功响应

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "ip": "1.1.1.1",
        "port": 80,
        "protocol": "tcp",
        "domain": null,
        "title": "Example",
        "country": "美国",
        "service": "http",
        "server": "nginx",
        "time_stamp": "2024-03-24T05:17:03.934963+08:00"
      }
    ],
    "page": 1,
    "page_size": 10,
    "total": 1,
    "use_time": "92"
  },
  "msg": "检索成功"
}
```

### 失败响应

```json
{
  "code": 2001,
  "data": {},
  "msg": "请检查api-key是否正确"
}
```

### 错误码

| Code | 描述 |
| --- | --- |
| 2001 | api-key 错误，请检查后重试 |
| 2002 | 参数错误（查询语法解析失败、参数类型错误、缺少参数、不支持的字段、page 超出范围等） |
| 2003 | 会员权限不足，请提升会员权限 |
| 2004 | 积分不足，请充值后使用 |
| 2005 | 最多只能查看前 1 万条数据 |
| 2006 | 数据获取失败，请重试 |

### 本地 MCP 请求控制

- DayDayMap API 始终返回 HTTP 200，因此本地模块会额外解析 JSON 响应中的 `code` 字段，对非 200 的业务错误码做可读性翻译。
- 参数 schema 限制 `page` 范围 1–10000、`page_size` 范围 1–10000，请求前还会校验 `page × page_size <= 10000`。
- 空白查询会在本地拒绝，不会调用计费接口。
- 业务错误会区分为鉴权错误、参数错误、权限不足、积分不足、分页越界和平台错误。

## 返回字段

共 38 个字段：

| 字段 | 说明 |
| --- | --- |
| `ip` | IP 地址 |
| `is_ipv6` | 是否 IPv6 |
| `is_website` | 是否网站 |
| `port` | 端口 |
| `protocol` | 传输层协议（tcp/udp） |
| `url` | 资产 URL 链接 |
| `continent` | 大洲 |
| `country` | 国家 |
| `country_code` | 国家代码（两字码） |
| `province` | 省 |
| `city` | 市 |
| `postal_code` | 邮政编码 |
| `asn` | 自治系统编号 |
| `asn_org` | 自治域组织 |
| `longitude` | 经度 |
| `latitude` | 纬度 |
| `isp` | 网络运营商 |
| `domain` | 域名 |
| `icp_reg_name` | ICP 备案名称 |
| `industry` | 行业（数组） |
| `title` | 网页标题 |
| `icon_md5` | icon 图标 hash 值 |
| `banner` | Banner 信息 |
| `header` | HTTP 响应头数据 |
| `body` | 网页 Body 数据 |
| `os` | 操作系统 |
| `device_type` | 设备类型 |
| `manufacturer` | 设备厂商 |
| `server` | Web 服务（如 nginx、Apache） |
| `lang` | 开发语言（如 PHP） |
| `device` | 设备名称 |
| `product` | 组件名称（数组） |
| `service` | 服务协议（如 http、https） |
| `tags` | 标签（数组，如 CDN、蜜罐等） |
| `time_stamp` | 资产更新时间（ISO 8601） |
| `cert` | 证书信息 |
| `cert_selfsigned` | 证书是否自签 |
| `SSL` | 证书详细信息（指纹、序列号、颁发/失效时间等） |

## 查询语法

共 14 大类、50 余条查询语法。搜索字符串须使用**英文双引号**，不区分大小写。

### IP 类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `ip` | 检索 IP 或 IP 段 | 否 | `ip="1.1.1.1"`, `ip="1.1.1.1/24"`, `ip="1.1.1.0-1.1.1.255"` |
| `ip.port` | 检索端口 | 否 | `ip.port="80"`, `ip.port>="80"`, `ip.port>"80" && ip.port<"1024"` |
| `ip.isp` | 检索运营商 | 是 | `ip.isp="电信"` |
| `ip.os_family` | 检索操作系统类型 | 否 | `ip.os_family="Windows"` |
| `ip.os` | 检索操作系统 | 是 | `ip.os="Windows Server 2016"` |
| `ip.tag` | 检索标签 | 否 | `ip.tag="CDN"`, `ip.tag="蜜罐"`, `ip.tag="云厂商"` |
| `ip.industry` | 检索行业 | 是 | `ip.industry="银行"`, `ip.industry="教育"` |
| `is_ipv6` | 检索 IP 类型 | 否 | `is_ipv6="true"`, `is_ipv6="false"` |

### 域名类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `is_domain` | 是否域名资产 | 否 | `is_domain="true"`, `is_domain="false"` |
| `domain` | 检索域名 | 是 | `domain="www.example.com"`（匹配该域名及子域名） |
| `domain.root` | 检索主域名的子域名 | 是 | `domain.root="example.com"` |

### 地理位置类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `ip.country` | 国家 | 是 | `ip.country="中国"`, `ip.country="CN"`, `ip.country="CHN"` |
| `ip.province` | 省份 | 是 | `ip.province="陕西省"`, `ip.province="陕西"` |
| `ip.city` | 城市 | 是 | `ip.city="北京市"`, `ip.city="北京"` |
| `ip.district` | 区县 | 是 | `ip.district="朝阳区"`, `ip.district="朝阳"` |

### ICP 备案类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `icp.number` | ICP 备案号 | 是 | `icp.number="京ICP备17003970号"` |
| `icp.name` | 备案企业名称 | 是 | `icp.name="远江盛邦"` |
| `icp.name_prefix` | 备案企业名称（前缀匹配） | 否 | `icp.name_prefix="远江"` |
| `icp.webname` | 备案网站名称 | 是 | `icp.webname="盛邦安全"` |

### AS 域类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `asn.number` | ASN 编号 | 否 | `asn.number="AS15169"` |
| `asn.org` | ASN 组织名称 | 是 | `asn.org="amazon"` |

### WEB 类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `is_web` | 是否 web 资产 | 否 | `is_web="true"`, `is_web="false"` |
| `web.server` | web 服务类型 | 是 | `web.server="Apache"` |
| `web.status_code` | HTTP 状态码 | 否 | `web.status_code="200"` |
| `web.header` | 响应头 | 是 | `web.header="elastic"` |
| `web.title` | 网站标题 | 是 | `web.title="管理系统"` |
| `web.lang` | 开发语言 | 否 | `web.lang="PHP"` |
| `web.body` | 网页内容 | 是 | `web.body="网络空间测绘"` |
| `web.icon` | icon 图标 MD5 | 否 | `web.icon="c60ea375c39d1ab273c4d1bee717287a"` |

### 协议类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `protocol.transport` | 传输层协议 | 否 | `protocol.transport="tcp"`, `protocol.transport="udp"` |
| `protocol.service` | 服务协议 | 否 | `protocol.service="http"` |
| `protocol.banner` | Banner 信息 | 是 | `protocol.banner="nginx"` |

### 应用/组件类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `app.name` | 应用名称 | 否 | `app.name="物联网平台"` |
| `product` | 组件名称 | 否 | `product="Nginx"` |

### 设备类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `device.name` | 设备名称 | 是 | `device.name="Aruba Device"` |
| `device.type` | 设备类型 | 是 | `device.type="安全防护设备"` |
| `device.type_sub` | 设备子类型 | 是 | `device.type_sub="邮件安全系统"` |
| `brand` | 设备品牌 | 否 | `brand="Cisco"` |
| `model` | 设备型号 | 否 | `model="Chromecast"` |
| `manufacturer` | 设备厂商 | 是 | `manufacturer="Hikvision"` |

### 证书类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `cert.issuer` | 颁发者 | 是 | `cert.issuer="Amazon"` |
| `cert.issuer.cn` | 颁发者通用名 | 是 | `cert.issuer.cn="GeoTrust CN RSA CA G1"` |
| `cert.issuer.country` | 颁发者国家 | 是 | `cert.issuer.country="US"` |
| `cert.issuer.org` | 颁发者组织 | 是 | `cert.issuer.org="DigiCert Inc"` |
| `cert.subject` | 持有者 | 是 | `cert.subject="Technicolor"` |
| `cert.subject.cn` | 持有者通用名 | 是 | `cert.subject.cn="example.com"` |
| `cert.subject.country` | 持有者国家 | 是 | `cert.subject.country="CN"` |
| `cert.subject.org` | 持有者组织 | 是 | `cert.subject.org="DigiCert Inc"` |
| `cert.sn` | 证书序列号 | 否 | `cert.sn="0ECDAB152D2161F7C843D25F3F00FCDE"` |
| `cert.org` | 持有者组织 | 是 | `cert.org="Plesk"` |
| `cert.md5` | 证书 MD5 | 否 | `cert.md5="0aeb8908c10b3bff4b920bdb199eb09a"` |
| `cert.is_expired` | 是否过期 | 否 | `cert.is_expired="true"`, `cert.is_expired="false"` |
| `cert.is_trust` | 是否可信 | 否 | `cert.is_trust="true"`, `cert.is_trust="false"` |
| `cert.startdate` | 起始时间 | 否 | `cert.startdate>"2024-01-01"`, 支持范围查询 |
| `cert.enddate` | 终止时间 | 否 | `cert.enddate>"2024-01-01"`, 支持范围查询 |

### 时间类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `time` | 资产更新时间 | 否 | `time="2024-01-01 08:00:00"`, `time>"2023-01-01" && time<"2024-01-01"` |

### 漏洞类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `vul.cve` | CVE 漏洞 | 是 | `vul.cve="CVE-2021-42013"` |
| `vul.dvb` | DVB 漏洞 | 否 | `vul.dvb="DVB-2021-2898"` |

### 资产归属类

| 语法 | 用途 | 模糊匹配 | 示例 |
| --- | --- | --- | --- |
| `org.name` | 资产归属 | 是 | `org.name="远江盛邦"` |
| `org.name_prefix` | 资产归属（前缀匹配） | 否 | `org.name_prefix="远江"` |

### 逻辑运算

- **AND**: `&&`，例如 `ip.port>"80" && ip.port<"1024"`
- **比较**: `=`, `>`, `<`, `>=`, `<=`

### 兼容语法

部分字段提供短名兼容语法，可直接使用短名查询：

| 短名 | 等效全名 |
| --- | --- |
| `port` | `ip.port` |
| `isp` | `ip.isp` |
| `os_family` | `ip.os_family` |
| `os` | `ip.os` |
| `tag` | `ip.tag` |
| `industry` | `ip.industry` |
| `country` | `ip.country` |
| `province` / `region` | `ip.province` |
| `city` | `ip.city` |
| `district` / `county` | `ip.district` |
| `icp` | `icp.number` |
| `asn` | `asn.number` |
| `is_website` | `is_web` |
| `server` | `web.server` |
| `status_code` / `code` / `http_status` | `web.status_code` |
| `header` / `web.response` / `response` | `web.header` |
| `title` | `web.title` |
| `lang` | `web.lang` |
| `body` | `web.body` |
| `icon` | `web.icon` |
| `transport` / `protocol` | `protocol.transport` |
| `service` | `protocol.service` |
| `banner` | `protocol.banner` |
| `app` | `app.name` |
| `device` | `device.name` |
| `device_type` | `device.type` |
| `time_stamp` | `time` |
| `cve` | `vul.cve` |
| `dvb` | `vul.dvb` |
| `org` | `org.name` |
| `org_prefix` | `org.name_prefix` |
