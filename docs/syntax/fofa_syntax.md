# FOFA 搜索语法文档

来源：`https://fofa.info/`（首页"语法"弹窗）

抓取时间：2026-06-18

## 基本规则

- 直接输入查询语句，将从标题、HTML 内容、HTTP 头信息、URL 字段中搜索。
- 如果查询表达式有多个与或关系，尽量在外面用 `()` 包含起来。
- 关于建站软件的搜索语法请参考 FOFA 组件列表。

## 逻辑运算符

| 运算符 | 含义 |
| --- | --- |
| `=` | 匹配；`=""` 时，可查询不存在字段或者值为空的情况 |
| `==` | 完全匹配；`==""` 时，可查询存在且值为空的情况 |
| `&&` | 与 |
| `||` | 或 |
| `!=` | 不匹配；`!=""` 时，可查询值不为空的情况 |
| `*=` | 模糊匹配，使用 `*` 或者 `?` 进行搜索 |
| `()` | 确认查询优先级，括号内容优先级最高 |

## 基础类（General）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `ip` | `ip="1.1.1.1"` | 通过单一 IPv4 地址进行查询 | ✓ | ✓ | - |
| `ip` | `ip="220.181.111.1/24"` | 通过 IPv4 C 段进行查询 | ✓ | ✓ | - |
| `ip` | `ip="2600:9000:202a:2600:18:4ab7:f600:93a1"` | 通过单一 IPv6 地址进行查询 | ✓ | ✓ | - |
| `port` | `port="6379"` | 通过端口号进行查询 | ✓ | ✓ | ✓ |
| `domain` | `domain="qq.com"` | 通过根域名进行查询 | ✓ | ✓ | ✓ |
| `host` | `host=".fofa.info"` | 通过主机名进行查询 | ✓ | ✓ | ✓ |
| `os` | `os="centos"` | 通过操作系统进行查询 | ✓ | ✓ | ✓ |
| `server` | `server="Microsoft-IIS/10"` | 通过服务器进行查询 | ✓ | ✓ | ✓ |
| `asn` | `asn="19551"` | 通过自治系统号进行搜索 | ✓ | ✓ | ✓ |
| `org` | `org="LLC Baxet"` | 通过所属组织进行查询 | ✓ | ✓ | ✓ |
| `is_domain` | `is_domain=true` | 筛选拥有域名的资产 | ✓ | - | - |
| `is_domain` | `is_domain=false` | 筛选没有域名的资产 | ✓ | - | - |
| `is_ipv6` | `is_ipv6=true` | 筛选是 IPv6 的资产 | ✓ | - | - |
| `is_ipv6` | `is_ipv6=false` | 筛选是 IPv4 的资产 | ✓ | - | - |

## 标记类（Special Label）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `app` | `app="Microsoft-Exchange"` | 通过 FOFA 整理的规则进行查询 | ✓ | - | - |
| `fid` | `fid="sSXXGNUO2FefBTcCLIT/2Q=="` | 通过 FOFA 聚合的站点指纹进行查询 | ✓ | ✓ | - |
| `product` | `product="NGINX"` | 通过 FOFA 标记的产品名进行查询 | ✓ | ✓ | - |
| `product.version` | `product="Roundcube-Webmail" && product.version="1.6.10"` | 通过 FOFA 标记的产品版本号进行查询（商业版及以上） | ✓ | ✓ | - |
| `category` | `category="服务"` | 通过 FOFA 标记的分类进行查询（个人版及以上） | ✓ | ✓ | - |
| `type` | `type="service"` | 筛选协议资产 | ✓ | - | - |
| `type` | `type="subdomain"` | 筛选服务（网站类）资产 | ✓ | - | - |
| `cloud_name` | `cloud_name="Aliyundun"` | 通过云服务商进行查询 | ✓ | ✓ | ✓ |
| `is_cloud` | `is_cloud=true` | 筛选是云服务的资产 | ✓ | - | - |
| `is_cloud` | `is_cloud=false` | 筛选不是云服务的资产 | ✓ | - | - |
| `is_fraud` | `is_fraud=true` | 筛选是仿冒垃圾站群的资产（专业版及以上） | ✓ | - | - |
| `is_fraud` | `is_fraud=false` | 筛选不是仿冒垃圾站群的资产（已默认筛选） | ✓ | - | - |
| `is_honeypot` | `is_honeypot=true` | 筛选是蜜罐的资产（专业版及以上） | ✓ | - | - |
| `is_honeypot` | `is_honeypot=false` | 筛选不是蜜罐的资产（已默认筛选） | ✓ | - | - |

## 协议类（type=service）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `protocol` | `protocol="quic"` | 通过协议名称进行查询 | ✓ | ✓ | ✓ |
| `banner` | `banner="users"` | 通过协议返回信息进行查询（注册用户及以上） | ✓ | ✓ | - |
| `banner_hash` | `banner_hash="7330105010150477363"` | 通过协议响应体计算的 Hash 值进行查询（个人版及以上） | ✓ | ✓ | - |
| `banner_fid` | `banner_fid="zRpqmn0FXQRjZpH8MjMX55zpMy9SgsW8"` | 通过协议返回信息结构计算的指纹值进行查询（个人版及以上） | ✓ | ✓ | - |
| `base_protocol` | `base_protocol="udp"` | 查询传输层为 UDP 协议的资产 | ✓ | ✓ | - |
| `base_protocol` | `base_protocol="tcp"` | 查询传输层为 TCP 协议的资产 | ✓ | ✓ | - |

## 网站类（type=subdomain）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `title` | `title="beijing"` | 通过网站标题进行查询 | ✓ | ✓ | ✓ |
| `header` | `header="elastic"` | 通过响应标头进行查询（注册用户及以上） | ✓ | ✓ | - |
| `header_hash` | `header_hash="1258854265"` | 通过 HTTP/HTTPS 响应头计算的 Hash 值进行查询（个人版及以上） | ✓ | ✓ | ✓ |
| `body` | `body="网络空间测绘"` | 通过 HTML 正文进行查询（注册用户及以上） | ✓ | ✓ | - |
| `body_hash` | `body_hash="-2090962452"` | 通过 HTML 正文计算的 Hash 值进行查询（个人版及以上） | ✓ | ✓ | - |
| `js_name` | `js_name="js/jquery.js"` | 通过 HTML 正文包含的 JS 进行查询 | ✓ | ✓ | ✓ |
| `js_md5` | `js_md5="82ac3f14327a8b7ba49baa208d4eaa15"` | 通过 JS 源码进行查询 | ✓ | ✓ | ✓ |
| `cname` | `cname="customers.spektrix.com"` | 通过别名记录进行查询 | ✓ | ✓ | ✓ |
| `cname_domain` | `cname_domain="siteforce.com"` | 通过别名记录解析的主域名进行查询 | ✓ | ✓ | ✓ |
| `icon_hash` | `icon_hash="-247388890"` | 通过网站图标的 Hash 值进行查询 | ✓ | ✓ | - |
| `status_code` | `status_code="402"` | 筛选服务状态为 402 的服务（网站）资产 | ✓ | ✓ | - |
| `icp` | `icp="京ICP证030173号"` | 通过 HTML 正文包含的 ICP 备案号进行查询 | ✓ | ✓ | ✓ |
| `sdk_hash` | `sdk_hash="Are3qNnP2Eqn7q5kAoUO3l+w3mgVIytO"` | 通过网站嵌入的第三方代码计算的 Hash 值进行查询（商业版及以上） | ✓ | ✓ | - |

## 地理位置（Location）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `country` | `country="CN"` | 通过国家的简称代码进行查询 | ✓ | ✓ | - |
| `country` | `country="中国"` | 通过国家中文名称进行查询 | ✓ | ✓ | - |
| `region` | `region="Zhejiang"` | 通过省份/地区英文名称进行查询 | ✓ | ✓ | - |
| `region` | `region="浙江"` | 通过省份/地区中文名称进行查询（仅支持中国地区） | ✓ | ✓ | - |
| `city` | `city="Hangzhou"` | 通过城市英文名称进行查询 | ✓ | ✓ | - |

## 证书类（Certificate）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `cert` | `cert="baidu"` | 通过证书进行查询（注册用户及以上） | ✓ | ✓ | - |
| `cert.subject` | `cert.subject="Oracle Corporation"` | 通过证书的持有者进行查询 | ✓ | ✓ | ✓ |
| `cert.issuer` | `cert.issuer="DigiCert"` | 通过证书的颁发者进行查询 | ✓ | ✓ | ✓ |
| `cert.subject.org` | `cert.subject.org="Oracle Corporation"` | 通过证书持有者的组织进行查询 | ✓ | ✓ | ✓ |
| `cert.subject.cn` | `cert.subject.cn="baidu.com"` | 通过证书持有者的通用名称进行查询 | ✓ | ✓ | ✓ |
| `cert.issuer.org` | `cert.issuer.org="cPanel, Inc."` | 通过证书颁发者的组织进行查询 | ✓ | ✓ | ✓ |
| `cert.issuer.cn` | `cert.issuer.cn="Synology Inc. CA"` | 通过证书颁发者的通用名称进行查询 | ✓ | ✓ | ✓ |
| `cert.domain` | `cert.domain="huawei.com"` | 通过证书持有者的根域名进行查询 | ✓ | ✓ | ✓ |
| `cert.is_equal` | `cert.is_equal=true` | 筛选证书颁发者和持有者匹配的资产（个人版及以上） | ✓ | - | - |
| `cert.is_equal` | `cert.is_equal=false` | 筛选证书颁发者和持有者不匹配的资产（个人版及以上） | ✓ | - | - |
| `cert.is_valid` | `cert.is_valid=true` | 筛选证书是有效证书的资产（个人版及以上） | ✓ | - | - |
| `cert.is_valid` | `cert.is_valid=false` | 筛选证书是无效证书的资产（个人版及以上） | ✓ | - | - |
| `cert.is_match` | `cert.is_match=true` | 筛选证书和域名匹配的资产（个人版及以上） | ✓ | - | - |
| `cert.is_match` | `cert.is_match=false` | 筛选证书和域名不匹配的资产（个人版及以上） | ✓ | - | - |
| `cert.is_expired` | `cert.is_expired=true` | 筛选证书已过期的资产（个人版及以上） | ✓ | - | - |
| `cert.is_expired` | `cert.is_expired=false` | 筛选证书未过期的资产（个人版及以上） | ✓ | - | - |
| `jarm` | `jarm="2ad2ad0002ad2ad22c2ad2ad2ad2ad2eac92ec34bcc0cf7520e97547f83e81"` | 通过 JARM 指纹进行查询 | ✓ | ✓ | ✓ |
| `tls.version` | `tls.version="TLS 1.3"` | 通过 TLS 的协议版本进行查询 | ✓ | ✓ | - |
| `tls.ja3s` | `tls.ja3s="15af977ce25de452b96affa2addb1036"` | 通过 TLS 的 JA3S 指纹进行查询 | ✓ | ✓ | ✓ |
| `cert.sn` | `cert.sn="356078156165546797850343536942784588840297"` | 通过证书序列号进行查询 | ✓ | ✓ | - |
| `cert.not_after.after` | `cert.not_after.after="2025-03-01"` | 筛选某证书到期日期后的证书（个人版及以上） | ✓ | - | - |
| `cert.not_after.before` | `cert.not_after.before="2025-03-01"` | 筛选某证书到期日期前的证书（个人版及以上） | ✓ | - | - |
| `cert.not_before.after` | `cert.not_before.after="2025-03-01"` | 筛选某证书生效日期后的证书（个人版及以上） | ✓ | - | - |
| `cert.not_before.before` | `cert.not_before.before="2025-03-01"` | 筛选某证书生效日期前的证书（个人版及以上） | ✓ | - | - |

## 时间类（Last Update Time）

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `after` | `after="2023-01-01"` | 筛选某一时间之后有更新的资产（个人版及以上） | ✓ | - | - |
| `before` | `before="2023-12-01"` | 筛选某一时间之前有更新的资产（个人版及以上） | ✓ | - | - |
| `after` & `before` | `after="2023-01-01" && before="2023-12-01"` | 筛选某一时间区间有更新的资产（个人版及以上） | ✓ | - | - |

## 独立 IP 语法

以下语法需配合 `ip_filter` 或 `ip_exclude` 组合使用（商业版及以上）：

| 语法 | 例句 | 用途说明 | `=` | `!=` | `*=` |
| --- | --- | --- | --- | --- | --- |
| `ip_filter()` | `ip_filter(banner="SSH-2.0-OpenSSH_6.7p2") && ip_filter(icon_hash="-1057022626")` | 同源 IP 多资产特征匹配 | ✓ | - | - |
| `ip_exclude()` | `ip_filter(banner="SSH-2.0-OpenSSH_6.7p2" && asn="3462") && ip_exclude(title="EdgeOS")` | 同源 IP 多资产特征不匹配 | ✓ | - | - |
| `port_size` | `port_size="6"` | 筛选开放端口数量等于 6 个的独立 IP | ✓ | ✓ | - |
| `port_size_gt` | `port_size_gt="6"` | 筛选开放端口数量大于 6 个的独立 IP | ✓ | - | - |
| `port_size_lt` | `port_size_lt="12"` | 筛选开放端口数量小于 12 个的独立 IP | ✓ | - | - |
| `ip_ports` | `ip_ports="80,161"` | 筛选同时开放不同端口的独立 IP | ✓ | - | - |
| `ip_country` | `ip_country="CN"` | 通过国家代码查询独立 IP | ✓ | - | - |
| `ip_region` | `ip_region="Zhejiang"` | 通过省份英文名称查询独立 IP | ✓ | - | - |
| `ip_city` | `ip_city="Hangzhou"` | 通过城市英文名称查询独立 IP | ✓ | - | - |
| `ip_after` | `ip_after="2021-03-18"` | 筛选某一时间之后有更新的独立 IP | ✓ | - | - |
| `ip_before` | `ip_before="2019-09-09"` | 筛选某一时间之前有更新的独立 IP | ✓ | - | - |

## 查询示例

```text
# 查找开放 Redis 端口的中国资产
port="6379" && country="CN"

# 查找特定 IP 段内非 80 端口的资产
ip="192.168.1.0/24" && port!="80"

# 查找 Apache 服务器且标题包含管理后台的网站
app="Apache" && title="后台管理"

# 查找证书颁发者为 Let's Encrypt 的中国域名资产
cert.issuer="Let's Encrypt" && country="CN" && type="subdomain"

# 查找最近一年更新的蜜罐资产
is_honeypot=true && after="2025-01-01"

# 同源 IP 多特征匹配：SSH 版本 + 图标 Hash
ip_filter(banner="SSH-2.0-OpenSSH_6.7p2") && ip_filter(icon_hash="-1057022626")
```
