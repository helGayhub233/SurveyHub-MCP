# ZoomEye 搜索语法文档

来源：`https://www.zoomeye.org/doc`、`docs/api/zoomeye_api.md`

抓取时间：2026-06-18

## 基本规则

- 搜索范围覆盖设备资产（IPv4、IPv6）以及网站域名资产。
- 直接输入字符串时，会按全局模式匹配 HTTP、SSH、FTP 等协议内容，包括 HTTP Header、Body、SSL、Title 以及其他协议 Banner。
- 默认搜索不区分大小写，并会进行分词匹配。
- 使用 `==` 时为精确匹配，区分大小写，也可搜索空值。
- 字符串建议使用单引号或双引号包裹，例如 `"Cisco System"`。
- 字符串内的引号或括号需要转义，例如 `"a\"b"`、`portinfo\(\)`。

## 逻辑运算符

| 运算符 | 说明 | 示例 |
| --- | --- | --- |
| `=` | 包含关键词 | `title="知道创宇"` |
| `==` | 精确匹配，区分大小写 | `title=="知道创宇"` |
| `||` | 或 | `service="ssh" || service="http"` |
| `&&` | 且 | `device="router" && after="2020-01-01"` |
| `!=` | 非 | `country="CN" && subdivisions!="beijing"` |
| `()` | 优先处理 | `(country="CN" && port!=80) || (country="US" && title!="404 Not Found")` |
| `*` | 模糊匹配 | `title="google*"` |

## 地理位置

| 语法 | 说明 | 备注 |
| --- | --- | --- |
| `country="CN"` | 国家或地区 | 支持国家缩写、中英文全称，如 `country="中国"` |
| `subdivisions="beijing"` | 行政区 | 中国省份支持中文和英文，如 `subdivisions="北京"` |
| `city="changsha"` | 城市 | 中国城市支持中文和英文，如 `city="长沙"` |

## 证书

| 语法 | 说明 |
| --- | --- |
| `ssl="google"` | SSL 证书中包含指定字符串 |
| `ssl.cert.fingerprint="F3C98F223D82CC41CF83D94671CCC6C69873FABF"` | 证书指纹 |
| `ssl.chain_count=3` | SSL 证书链数量 |
| `ssl.cert.alg="SHA256-RSA"` | 证书签名算法 |
| `ssl.cert.issuer.cn="pbx.wildix.com"` | 证书签发者通用名称 |
| `ssl.cert.pubkey.rsa.bits=2048` | RSA 公钥位数 |
| `ssl.cert.pubkey.ecdsa.bits=256` | ECDSA 公钥位数 |
| `ssl.cert.pubkey.type="RSA"` | 证书公钥类型 |
| `ssl.cert.serial="18460192207935675900910674501"` | 证书序列号 |
| `ssl.cipher.bits="128"` | 加密套件位数 |
| `ssl.cipher.name="TLS_AES_128_GCM_SHA256"` | 加密套件名称 |
| `ssl.cipher.version="TLSv1.3"` | 加密套件版本 |
| `ssl.version="TLSv1.3"` | SSL/TLS 版本 |
| `ssl.cert.subject.cn="example.com"` | 证书持有者通用名称 |
| `ssl.jarm="29d29d15d29d29d00029d29d29d29dea0f89a2e5fb09e4d8e099befed92cfa"` | JARM 指纹 |
| `ssl.ja3s=45094d08156d110d8ee97b204143db14` | JA3S 指纹 |

## IP 与域名

| 语法 | 说明 | 备注 |
| --- | --- | --- |
| `ip="8.8.8.8"` | IPv4 资产 |  |
| `ip="2600:3c00::f03c:91ff:fefc:574a"` | IPv6 资产 |  |
| `cidr="52.2.254.36/24"` | CIDR 网段 | `/24`、`/16`、`/8` 分别可用于不同范围网段 |
| `org="北京大学"` | 组织资产 | 也可使用 `organization="北京大学"` |
| `isp="China Mobile"` | 网络服务提供商 | 可结合组织字段补充 |
| `asn=42893` | ASN 资产 |  |
| `port=80` | 端口资产 | 暂不支持同时开放多端口目标搜索 |
| `hostname="google.com"` | 主机名 |  |
| `domain="baidu.com"` | 域名及子域名资产 |  |
| `icp.number="京ICP备10040895号-40"` | ICP 备案号 | 通过域名关联备案资产 |
| `icp.name="知道创宇"` | ICP 备案主体 | 查询企业备案域名资产 |
| `banner="FTP"` | 协议报文 | 适用于非 HTTP 协议 Banner |
| `http.header="http"` | HTTP 响应头 |  |
| `http.header_hash="27f9973fe57298c3b63919259877a84d"` | HTTP 响应头 Hash |  |
| `http.header.server="Nginx"` | HTTP Server |  |
| `http.header.version="1.2"` | HTTP Server 版本 |  |
| `http.header.status_code="200"` | HTTP 状态码 | 如 `200`、`302`、`404` |
| `http.body="document"` | HTML 正文 |  |
| `http.body_hash="84a18166fde3ee7e7c974b8d1e7e21b4"` | HTML 正文 Hash |  |

## 指纹

| 语法 | 说明 | 备注 |
| --- | --- | --- |
| `app="Cisco ASA SSL VPN"` | 应用指纹 |  |
| `service="ssh"` | 服务协议 | 常见如 `http`、`ftp`、`ssh`、`telnet` |
| `device="router"` | 设备类型 | 常见如 `router`、`switch`、`storage-misc` |
| `os="RouterOS"` | 操作系统 | 常见如 Linux、Windows、RouterOS、IOS、JUNOS |
| `title="Cisco"` | HTML 标题 |  |
| `industry="政府"` | 行业类型 | 可结合组织字段补充 |
| `product="Cisco"` | 组件产品 | 支持主流资产组件 |
| `protocol="TCP"` | 传输协议 | 常见如 TCP、UDP、TCP6、SCTP |
| `is_honeypot="True"` | 蜜罐筛选 |  |

## 时间

时间过滤器需要与其他过滤条件组合使用。

| 语法 | 说明 |
| --- | --- |
| `after="2020-01-01" && port="50050"` | 查询指定日期之后更新且匹配端口的资产 |
| `before="2020-01-01" && port="50050"` | 查询指定日期之前更新且匹配端口的资产 |

## Dig

| 语法 | 说明 |
| --- | --- |
| `dig="baidu.com 220.181.38.148"` | 查询相关 Dig 内容 |

## Iconhash

| 语法 | 说明 |
| --- | --- |
| `iconhash="f3418a443e7d841097c714d69ec4bcb8"` | 使用 MD5 图标 Hash 查询 |
| `iconhash="1941681276"` | 使用 MMH3 图标 Hash 查询 |

## Filehash

| 语法 | 说明 |
| --- | --- |
| `filehash="0b5ce08db7fb8fffe4e14d05588d49d9"` | 根据解析出的文件数据查询 |

## 查询示例

```text
# 查找中国境内开放 22 端口的 Linux 资产
country="CN" && port=22 && os="Linux"

# 查找特定 IP 段的 HTTP 服务
cidr="192.168.1.0/24" && service="http"

# 查找使用 Nginx 且状态码为 200 的网站
http.header.server="Nginx" && http.header.status_code="200"

# 查找证书颁发者为 Let's Encrypt 的中国域名
country="CN" && ssl.cert.issuer.cn="Let's Encrypt"

# 查找 Cisco VPN 设备且不在美国
app="Cisco ASA SSL VPN" && country!="US"

# 查找指定 JARM 指纹的资产
ssl.jarm="29d29d15d29d29d00029d29d29d29dea0f89a2e5fb09e4d8e099befed92cfa"

# 查找指定 Icon Hash 的网站
iconhash="f3418a443e7d841097c714d69ec4bcb8"

# 查找 2024 年之后更新的蜜罐资产
is_honeypot="True" && after="2024-01-01"

# 查找 ICP 备案为特定企业的域名资产
icp.name="知道创宇"

# 复杂组合查询
(country="CN" && port!=80) || (country="US" && title!="404 Not Found")
```
