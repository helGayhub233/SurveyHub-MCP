# Hunter 搜索语法文档

来源：`https://hunter.qianxin.com/`（首页"查询语法"弹窗）

抓取时间：2026-06-18

## 基本规则

- 搜索语法适用于 Hunter 企业版和个人版，两个版本的搜索语法一致，差异仅在 API 接口层面。
- 直接输入关键词时，将在所有资产字段中进行模糊匹配。
- 多个条件组合时，建议使用括号 `()` 明确优先级。

## 逻辑运算符

| 连接符 | 查询含义 |
| --- | --- |
| `=` | 模糊查询，表示查询包含关键词的资产 |
| `==` | 精确查询，表示查询有且仅有关键词的资产 |
| `!=` | 模糊剔除，表示剔除包含关键词的资产；使用 `!=""` 时，可查询值不为空的情况 |
| `!==` | 精确剔除，表示剔除有且仅有关键词的资产 |
| `&&`、`||` | 多种条件组合查询，`&&` 同 `and`，表示和；`||` 同 `or`，表示或 |
| `()` | 括号内表示查询优先级最高 |

## IP 类

| 语法 | 语法说明 |
| --- | --- |
| `ip="1.1.1.1"` | 搜索 IP 为 "1.1.1.1" 的资产 |
| `ip="220.181.111.0/24"` | 搜索网段为 "220.181.111.0" 的 C 段资产 |
| `ip.port="80"` | 搜索开放端口为 "80" 的资产 |
| `ip.country="中国"` 或 `ip.country="CN"` | 搜索 IP 对应主机所在国为 "中国" 的资产 |
| `ip.province="江苏"` | 搜索 IP 对应主机在江苏省的资产 |
| `ip.city="北京"` | 搜索 IP 对应主机所在城市为 "北京" 市的资产 |
| `ip.isp="电信"` | 搜索运营商为 "中国电信" 的资产 |
| `ip.os="Windows"` | 搜索操作系统标记为 "Windows" 的资产 |
| `ip.ports="80"` && `ip.ports="443"` | 查询开放了 80 和 443 端口号的资产 |
| `ip.port_count>"2"` | 搜索开放端口大于 2 的 IP（支持等于、大于、小于） |
| `ip.tag="CDN"` | 查询包含 IP 标签 "CDN" 的资产（枚举值：云厂商、CDN、疑似蜜罐、无标签） |

## 域名类（Domain）

| 语法 | 语法说明 |
| --- | --- |
| `is_domain=true` | 搜索域名标记不为空的资产 |
| `domain="qianxin"` | 搜索域名包含 "qianxin" 的网站 |
| `domain.suffix="qianxin.com"` | 搜索主域为 "qianxin.com" 的网站 |
| `domain.suffix="qianxin.com" && domain!="app"` | 搜索主域为 "qianxin.com"，且域名不包含 "app" 的网站 |
| `domain.registrant_email=="admin@domains.microsoft"` | 搜索域名注册人邮箱为 "admin@domains.microsoft" 的网站 |
| `domain.status="clientDeleteProhibited"` | 搜索域名状态为 "clientDeleteProhibited" 的网站 |
| `domain.whois_server="whois.markmonitor.com"` | 搜索 WHOIS 服务器为 "whois.markmonitor.com" 的网站 |
| `domain.name_server="ns1.qq.com"` | 搜索名称服务器为 "ns1.qq.com" 的网站 |
| `domain.creation_date="2022-06-01"` | 搜索域名创建时间为 "2022-06-01" 的网站 |
| `domain.expiry_date="2022-06-01"` | 搜索域名到期时间为 "2022-06-01" 的网站 |
| `domain.updated_date="2022-06-01"` | 搜索域名更新时间为 "2022-06-01" 的网站 |
| `domain.cname="a6c56dbcc1f22283.qaxanyu.com"` | 搜索 CNAME 包含 "a6c56dbcc1f22283.qaxanyu.com" 的网站 |
| `is_domain.cname=true` | 搜索含有 CNAME 解析记录的网站 |

## 响应头类（Header）

| 语法 | 语法说明 |
| --- | --- |
| `header.server=="Microsoft-IIS/10"` | 搜索 Server 全名为 "Microsoft-IIS/10" 的服务器 |
| `header.content_length="691"` | 搜索 HTTP 消息主体大小为 691 的网站 |
| `header.status_code="402"` | 搜索 HTTP 请求返回状态码为 "402" 的资产 |
| `header="elastic"` | 搜索 HTTP 响应头中含有 "elastic" 的资产 |

## 网站信息类（Web）

| 语法 | 语法说明 |
| --- | --- |
| `is_web=true` | 搜索 Web 资产 |
| `web.title="北京"` | 从网站标题中搜索 "北京" |
| `web.body="网络空间测绘"` | 搜索网站正文包含 "网络空间测绘" 的资产 |
| `after="2021-01-01" && before="2021-12-31"` | 搜索 2021 年的资产 |
| `web.similar="baidu.com:443"` | 查询与 baidu.com:443 网站的特征相似的资产 |
| `web.similar_icon=="17262739310191283300"` | 查询网站 Icon 与该 Icon 相似的资产 |
| `web.icon="22eeab765346f14faf564a4709f98548"` | 查询网站 Icon 与该 Icon 相同的资产 |
| `web.similar_id="3322dfb483ea6fd250b29de488969b35"` | 查询与该网页相似的资产 |
| `web.tag="登录页面"` | 查询包含资产标签 "登录页面" 的资产 |

`web.tag` 枚举值（Top 30）：Web servers、CDN、登录页面、WAF、主机面板、CMS、网络摄像设备、信息页面、数据库管理器、防火墙设备、SEO、任务管理器、OA、SaaS、版本管理仓库、VoIP、API Manager、IaaS、Blogs、人机界面、航班跟踪系统、警卫追踪系统、Payment processors、蜜罐、电力适配设备、RoIP、Comment systems、Tag managers、违规资产、平台即服务。

## ICP 备案类

| 语法 | 语法说明 |
| --- | --- |
| `icp.number="京ICP备16020626号-8"` | 搜索通过域名关联的 ICP 备案号为 "京ICP备16020626号-8" 的网站资产 |
| `icp.web_name="奇安信"` | 搜索 ICP 备案网站名中含有 "奇安信" 的资产 |
| `icp.name="奇安信"` | 搜索 ICP 备案单位名中含有 "奇安信" 的资产 |
| `icp.type="企业"` | 搜索 ICP 备案主体为 "企业" 的资产 |
| `icp.industry="软件和信息技术服务业"` | 搜索 ICP 备案行业为 "软件和信息技术服务业" 的资产 |
| `icp.province="江苏"` | 搜索 ICP 备案企业注册地址在江苏省的资产 |
| `icp.city="上海"` | 搜索 ICP 备案企业注册地址在 "上海" 这个城市的资产 |
| `icp.district="杨浦"` | 搜索 ICP 备案企业注册地址在 "杨浦" 这个区县的资产 |
| `icp.is_exception=true` | 搜索含有 ICP 备案异常的资产 |

## 协议/端口响应类

| 语法 | 语法说明 |
| --- | --- |
| `protocol="http"` | 搜索协议为 "http" 的资产 |
| `protocol.transport="udp"` | 搜索传输层协议为 "udp" 的资产 |
| `protocol.banner="nginx"` | 查询端口响应中包含 "nginx" 的资产 |

## 组件信息类（App）

| 语法 | 语法说明 |
| --- | --- |
| `app.name="小米 Router"` | 搜索标记为 "小米 Router" 的资产 |
| `app.type="开发与运维"` | 查询包含组件分类为 "开发与运维" 的资产 |
| `app.vendor="PHP"` | 查询包含组件厂商为 "PHP" 的资产 |
| `app.version="1.8.1"` | 查询包含组件版本为 "1.8.1" 的资产 |

## 证书类（Cert）

| 语法 | 语法说明 |
| --- | --- |
| `cert="baidu"` | 搜索证书中带有 "baidu" 的资产 |
| `cert.subject="qianxin.com"` | 搜索证书使用者包含 "qianxin.com" 的资产 |
| `cert.subject.suffix="qianxin.com"` | 搜索证书使用者为 "qianxin.com" 的资产 |
| `cert.subject_org="奇安信科技集团股份有限公司"` | 搜索证书使用者组织是 "奇安信科技集团股份有限公司" 的资产 |
| `cert.issuer="Let's Encrypt Authority X3"` | 搜索证书颁发者是 "Let's Encrypt Authority X3" 的资产 |
| `cert.issuer_org="Let's Encrypt"` | 搜索证书颁发者组织是 "Let's Encrypt" 的资产 |
| `cert.sha-1="be7605a3b72b60fcaa6c58b6896b9e2e7442ec50"` | 搜索证书签名哈希算法 SHA-1 匹配的资产 |
| `cert.sha-256="4e529a65512029d77a28cbe694c7dad1e60f98b5cb89bf2aa329233acacc174e"` | 搜索证书签名哈希算法 SHA-256 匹配的资产 |
| `cert.sha-md5="aeedfb3c1c26b90d08537523bbb16bf1"` | 搜索证书签名哈希算法 MD5 匹配的资产 |
| `cert.serial_number="35351242533515273557482149369"` | 搜索证书序列号匹配的资产 |
| `cert.is_expired=true` | 搜索证书已过期的资产 |
| `cert.is_trust=true` | 搜索证书可信的资产 |

## 漏洞信息类（Vul）

| 语法 | 语法说明 |
| --- | --- |
| `vul.gev="GEV-2021-1075"` | 查询存在该专项漏洞的资产 |
| `vul.cve="CVE-2021-2194"` | 查询存在该 CVE 漏洞的资产 |
| `vul.cve="CVE-2023-22007" && vul.state="已修复"` | 查询存在该 CVE 漏洞且该漏洞已修复的资产 |
| `web.is_vul=true` | 查询存在历史漏洞的资产 |

## AS 类

| 语法 | 语法说明 |
| --- | --- |
| `as.number="136800"` | 搜索 ASN 为 "136800" 的资产 |
| `as.name="CLOUDFLARENET"` | 搜索 ASN 名称为 "CLOUDFLARENET" 的资产 |
| `as.org="PDR"` | 搜索 ASN 注册机构为 "PDR" 的资产 |

## TLS-JARM 类

| 语法 | 语法说明 |
| --- | --- |
| `tls-jarm.hash="21d19d00021d21d21c21d19d21d21da1..."` | 搜索 TLS-JARM 哈希匹配的资产 |
| `tls-jarm.ans="c013|0303|h2|ff01-0000-0001-000b-0023-0010-0017,..."` | 搜索 TLS-JARM ANS 匹配的资产 |

## 特色语法

以下语法为 Hunter 平台独有的特色查询能力：

| 语法 | 语法说明 |
| --- | --- |
| `web.similar="baidu.com:443"` | 查询与指定网站特征相似的资产 |
| `web.similar_icon=="17262739310191283300"` | 查询网站 Icon 与指定 Icon 相似的资产 |
| `web.similar_id="3322dfb483ea6fd250b29de488969b35"` | 查询与指定网页相似的资产 |
| `cert.is_trust=true` | 搜索证书可信的资产 |
| `ip.tag="CDN"` | 查询包含 IP 标签的资产 |
| `web.tag="登录页面"` | 查询包含资产标签的资产 |
| `domain.registrant_email=="admin@domains.microsoft"` | 搜索域名注册人邮箱 |
| `icp.is_exception=true` | 搜索 ICP 备案异常的资产 |

## 查询示例

```text
# 查找中国境内开放 3389 端口的 Windows 资产
ip.country="CN" && ip.port="3389" && ip.os="Windows"

# 查找特定域名后缀下非子域名的网站
domain.suffix="example.com" && domain!="admin"

# 查找使用 Nginx 且标题包含"登录"的网站
header.server=="Nginx" && web.title="登录"

# 查找证书可信且属于某组织的资产
cert.is_trust=true && cert.subject_org="奇安信科技集团股份有限公司"

# 查找特定 CVE 漏洞影响的资产
vul.cve="CVE-2023-22007"

# 查找 2024 年内更新的 Web 资产
is_web=true && after="2024-01-01" && before="2024-12-31"

# 查找与指定网站特征相似的资产
web.similar="target.com:443"
```
