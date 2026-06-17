# Quake 搜索语法文档

来源：`https://quake.360.net/quake/#/help`（帮助中心 > 查询语句 > 检索关键词）

抓取时间：2026-06-18

## 基本规则

### 端口响应信息（Response）

互联网上各类设备通信依赖各类网络协议，Quake 具备对数千种常见网络协议识别、采集的能力。每个服务在建立连接后返回的信息都存储在称为 `response` 的对象中，这是整个空间测绘系统收集的基本数据单位以及检索的内容主体。

### 模糊搜索

在默认状态下，用户在搜索框里输入的任何内容均会与端口响应（Response）中的内容匹配。

### 分词现象

当搜索内容包含中文或空格时，输入的内容会被自动分词。例如检索"奇虎科技"会被拆分为"奇虎"和"科技"两个关键词。为避免此问题，强烈建议对需要检索的中文信息和包含空格的字符串使用英文双引号 `" "` 包裹。

### 逻辑运算符

| 运算符 | 含义 | 示例 |
| --- | --- | --- |
| `AND` | 与，同时满足多个条件 | `port:"443" AND country:"China"` |
| `OR` | 或，满足其中一个条件 | `port:"80" OR port:"443"` |
| `NOT` | 非，排除条件 | `port:"3389" AND NOT country:"CN"` |
| `()` | 括号内查询优先级最高 | `port:"80" AND (country:"China" OR country:"US")` |

## 基本信息字段查询

| 检索语法 | 字段名称 | 数据模式 | 说明 | 范例 |
| --- | --- | --- | --- | --- |
| `ip` | IP 地址及网段 | 主机数据、服务数据 | 支持检索单个 IP、CIDR 地址段、IPv6 地址 | `ip:"1.1.1.1"`、`ip:"1.1.1.1/16"`、`ip:"2804:29b8:500d:4184:40a8:2e48:9a5d:e2bd"` |
| `is_ipv6` | 搜索 IPv4/IPv6 资产 | 主机数据、服务数据 | 只接受 `true` 和 `false` | `is_ipv6:"true"`、`is_ipv6:"false"` |
| `is_latest` | 搜索最新资产 | 服务数据 | 只接受 `true` 和 `false` | `is_latest:"true"` |
| `port` | 端口 | 主机数据、服务数据 | 搜索开放的端口 | `port:"80"` |
| `ports` | 多端口 | 主机数据 | 搜索某个主机同时开放过的端口 | `ports:"80,8080,8000"` |
| `port:[* TO N]` | 端口范围 | 主机数据、服务数据 | 搜索满足某个端口范围的主机 | `port:[* TO 80]`、`port:[80 TO 1024]`、`port:[80 TO *]` |
| `transport` | 传输层协议 | 主机数据、服务数据 | 只接受 `tcp`、`udp` | `transport:"tcp"`、`transport:"udp"` |

## ASN 网络自治域

| 检索语法 | 字段名称 | 数据模式 | 说明 | 范例 |
| --- | --- | --- | --- | --- |
| `asn` | 自治域号码 | 主机数据、服务数据 | 自治域号码 | `asn:"12345"` |
| `org` | 自治域归属组织名称 | 主机数据、服务数据 | 自治域归属组织名称 | `org:"No.31,Jin-rong Street"` |

## 主机名与操作系统

| 检索语法 | 字段名称 | 数据模式 | 说明 | 范例 |
| --- | --- | --- | --- | --- |
| `hostname` | 主机名 | 服务数据 | 即 rDNS 数据 | `hostname:"50-87-74-222.unifiedlayer.com"` |
| `domain` | 网站域名 | 服务数据 | 网站域名信息，支持通配符 | `domain:"360.cn"`、`domain:*.360.cn` |
| `os` | 操作系统 | 服务数据 | 操作系统名称+版本 | `os:"Windows"` |

## 服务数据

| 检索语法 | 字段名称 | 数据模式 | 说明 | 范例 |
| --- | --- | --- | --- | --- |
| `service` | 服务名称 | 主机数据、服务数据 | 即应用协议名称 | `service:"http"` |
| `services` | 多个服务名称 | 主机数据 | 搜索某个主机同时支持的协议（仅主机数据模式） | `services:"rtsp,https,telnet"` |
| `app` | 服务产品 | 主机数据、服务数据 | 经过 Quake 指纹识别后的产品名称 | `app:"Apache"` |
| `app_version` | 产品版本 | 主机数据、服务数据 | 经过 Quake 指纹识别后的产品版本 | `app_version:"1.2.1"` |
| `response` | 服务原始响应 | 服务数据 | 包含端口信息最丰富的原始返回数据 | `response:"奇虎科技"`、`response:"220 ProFTPD 1.3.5a Server"` |
| `cert` | SSL/TLS 证书信息 | 主机数据、服务数据 | 格式解析后的证书信息字符串 | `cert:"奇虎科技"`、`cert:"360.cn"` |

## 精细化应用识别

| 检索语法 | 字段名称 | 数据模式 | 说明 | 范例 |
| --- | --- | --- | --- | --- |
| `catalog` | 应用类别 | 服务数据 | 应用类型的集合，更高层面的聚合 | `catalog:"IoT物联网"`、`catalog:"IoT物联网" OR catalog:"网络安全设备"` |
| `type` | 应用类型 | 服务数据 | 对应用进行的分类结果 | `type:"防火墙"`、`type:"VPN"` |
| `level` | 应用层级 | 服务数据 | 5 个级别：硬件设备层、操作系统层、服务协议层、中间支持层、应用业务层 | `level:"硬件设备层"`、`level:"应用业务层"` |
| `vendor` | 应用生产厂商 | 服务数据 | 某个应用设备的生产厂商 | `vendor:"Sangfor深信服科技股份有限公司"`、`vendor:"Sangfor" OR vendor:"微软"` |

## IP 归属与定位

| 检索语法 | 字段名称 | 数据模式 | 说明 | 范例 |
| --- | --- | --- | --- | --- |
| `country` | 国家（英文）与代码 | 主机数据、服务数据 | 支持英文国家名和国家代码 | `country:"China"`、`country:"CN"` |
| `country_cn` | 国家（中文） | 主机数据、服务数据 | 搜索中文国家名称 | `country_cn:"中国"` |
| `province` | 省份（英文） | 主机数据、服务数据 | 搜索英文省份名称 | `province:"Sichuan"` |
| `province_cn` | 省份（中文） | 主机数据、服务数据 | 搜索中文省份名称 | `province_cn:"四川"` |
| `city` | 城市（英文） | 主机数据、服务数据 | 搜索英文城市名称 | `city:"Chengdu"` |
| `city_cn` | 城市（中文） | 主机数据、服务数据 | 搜索中文城市名称 | `city_cn:"成都"` |
| `district` | 区县（中文） | 服务数据 | 搜索中文城市下的区县名称 | `district:"朝阳区"` |
| `owner` | IP 归属单位 | 主机数据、服务数据 | 归属并不精确 | `owner:"tencent.com"`、`owner:"清华大学"` |
| `isp` | 运营商 | 主机数据、服务数据 | 根据 IP 划分归属的运营商 | `isp:"联通"`、`isp:"amazon.com"` |

## 图像数据与应用场景

| 检索语法 | 字段名称 | 说明 | 范例 |
| --- | --- | --- | --- |
| `img_tag` | 图片标签 | 搜索图片的标签 | `img_tag:"windows"`、`img_tag:"web_login"`、`img_tag:"webcam"` |
| `img_ocr` | 图片 OCR | 搜索图片中的文字信息 | `img_ocr:"admin"`、`img_ocr:"login"` |
| `sys_tag` | 系统标签 | 搜索 IP 资产的应用场景 | `sys_tag:"卫星互联网"`、`sys_tag:"CDN"`、`sys_tag:"IDC"` |

## HTTP 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `status_code` | HTTP 返回状态码 | `status_code:200` |
| `http_path` | HTTP 请求路径 | `http_path:"/admin"` |
| `title` | 网页标题 | `title:"后台"` |
| `meta_keywords` | 网页关键字 | `meta_keywords:"网络安全"` |
| `server` | Web 服务器名称（HTTP Headers 中的 Server 字段） | `server:Nginx` |
| `service.http.server.keyword` | Web 服务器名称（精确查找） | `service.http.server.keyword:"Apache/2.4.29"` |
| `x_powered_by` | 网站开发语言（HTTP Headers 中的 X-Powered-By） | `powered_by:PHP` |
| `favicon` | 网页 Favicon 的 MD5 值 | `favicon:"0488faca4c19046b94d07c3ee83cf9d6"` |
| `host` | 请求 Host 的值 | `host:"google.com"` |
| `html_hash` | 网页 HTML 的 MD5 值 | `html_hash:"69d7683445fed9e517e33750615f46c0"` |
| `headers` | HTTP Headers 字符串 | `headers:"ThinkPHP"` |
| `header_order_hash` | HTTP 头部所有 Key 按序连接后取 MD5 | `header_order_hash:"42997ea42eb46037ecb1e514e8190b93"` |
| `body` | 网页 Body 内容 | `body:"奇虎"` |
| `robots_hash` | `robots.txt` 的 MD5 值 | `robots_hash:"e4c3bfe695710c5610cf51723b3bdae2"` |
| `robots` | `robots.txt` 的内容 | `robots:"Discuz"` |
| `sitemap_hash` | `sitemap.xml` 的 MD5 值 | `sitemap_hash:10f3aa0c1bd43f07ef8ed178d8b97df1` |
| `sitemap` | `sitemap.xml` 的内容 | `sitemap:"archive"` |
| `cookie_simhash` | Cookie Key 的 SimHash 值 | `cookie_simhash:"16149686953955343636"` |
| `cookie_order_hash` | Cookie 所有 Key 拼接后的 MD5 | `cookie_order_hash:"6ccfd3351761d2ac11b0963d916197e0"` |
| `dom_tree.simhash` | DOM 树节点的 SimHash | `dom_simhash:"13136671156032164472"` |
| `dom_tree.key` | DOM 树所有元素集合 | `dom_node:"html,head,body"` |
| `dom_tree.dom_hash` | DOM 树所有元素的哈希 | `dom_hash:"38d8daf979e511dfe3a421abe4f36561"` |
| `script_function` | Script 标签中的函数名 | `script_function:"func1"` |
| `script_variable` | Script 标签中的变量名 | `script_variable:"csrfToken"` |
| `css_class` | CSS 标签 Class 字段值 | `css_class:"center"` |
| `css_id` | CSS 标签 ID 字段值 | `css_id:"login"` |
| `url_load` | HTTP 加载流（不含静态资源） | `url_load:"/bim/"` |
| `icp` | ICP 备案号 | `icp:"京ICP备08010314号"` |
| `copyright` | 版权许可 | `copyright:"360网络安全响应中心（360-CERT）"` |
| `mail` | 邮箱地址 | `mail:"@163.com"` |
| `page_type` | 页面类型 | `page_type:"登录页"` |
| `iframe_url` | iframe 链接 | `iframe_url:"https://open.work.weixin.qq.com/wwopen/sso/v1/"` |
| `iframe_hash` | iframe URL 内容的 MD5 值 | `iframe_hash:"8c82d234e800eecbc2ff092905059cc3"` |
| `iframe_title` | iframe 链接标题 | `iframe_title:"企业微信登录"` |
| `iframe_keywords` | iframe 链接关键字 | `iframe_keywords:"电力能源"` |
| `domain_is_wildcard` | 是否存在泛解析域名 | `domain_is_wildcard:true` |
| `is_domain` | 是否存在域名 | `is_domain:true` |
| `icp_nature` | 备案主体性质 | `icp_nature:"企业"` |
| `icp_keywords` | 备案网站中的关键词或域名 | `icp_keywords:"奇虎"` |
| `_exists_:service.http.icp` | 是否存在 ICP 备案 | `_exists_:service.http.icp` 或 `not _exists_:service.http.icp` |

## FTP 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `is_anonymous` | 是否可匿名登录 | `service.ftp.is_anonymous:true` |

## SSH 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `server_keys.type` | 加密类型 | `service.ssh.server_keys.type:"ssh-rsa"` |
| `server_keys.fingerprint` | SSH Host Key 指纹 | `service.ssh.server_keys.fingerprint:"3c:14:84:40:c5:f3:d3:82:70:95:9f:91:bf:5f:a7:63"` |
| `ciphers` | 允许使用的加密算法 | `service.ssh.ciphers:"aes128-ctr"` |
| `kex` | 密钥交换算法 | `service.ssh.kex:"ecdh-sha2-nistp256"` |
| `digests` | 摘要算法 | `service.ssh.digests:"hmac-sha2-256"` |
| `key_types` | 密钥类型 | `service.ssh.key_types:"ssh-rsa"` |

## SNMP 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `sysname` | 系统名/设备标识/主机名 | `service.snmp.sysname:"CableHome"` |
| `sysdesc` | 设备描述/系统基本信息 | `service.snmp.sysdesc:"TC7200"` |
| `sysuptime` | 进程从启动开始的时间长度 | `service.snmp.sysuptime:"22230600"` |
| `syslocation` | 启用 SNMP Agent 的设备位置 | `service.snmp.syslocation:"HUMAX"` |
| `syscontact` | 设备管理联系人信息 | `service.snmp.syscontact:"SNMPv2"` |
| `sysobjectid` | 设备标识 | `service.snmp.sysobjectid:"1.3.6.1.4.1.8072.3.2.10"` |

## Docker 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `docker.containers.Image` | 镜像名 | `service.docker.containers.Image:"ubuntu"` |
| `docker.containers.Command` | 启动命令 | `service.docker.containers.Command:"wget"` |
| `version.Version` | Docker 版本 | `service.docker.version.Version:"19.03.1"` |
| `version.ApiVersion` | Docker API 版本 | `service.docker.version.ApiVersion:"1.40"` |
| `version.MinAPIVersion` | 服务器支持的最低 API 版本 | `service.docker.version.MinAPIVersion:"1.12"` |
| `version.GoVersion` | 编译 Docker 的 Golang 版本 | `service.docker.version.GoVersion:"go1.12.5"` |
| `version.Arch` | 服务器体系架构 | `service.docker.version.Arch:"arm"` |
| `version.KernelVersion` | 服务器内核版本 | `service.docker.version.KernelVersion:"3.10.70"` |

## DNS 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `id_server` | DNS 服务标识 | `service.domain.id_server:"pdns"` |
| `version_bind` | DNS 服务器版本信息 | `service.domain.version_bind:"Freenom"` |

## Elasticsearch 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `indices.health` | 服务器健康状态 | `service.elastic.indices.health:"green"` |
| `indices.status` | 服务器状态 | `service.elastic.indices.status:"open"` |
| `indices.index` | 索引名 | `service.elastic.indices.index:"user"` |
| `indices.docs_count` | 文档数量 | `service.elastic.indices.docs_count:"993"` |
| `indices.store_size` | 存储容量 | `service.elastic.indices.store_size:"945.4kb"` |

## MongoDB 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `authentication` | 是否开启授权 | `service.mongodb.authentication:false` |
| `buildInfo.version` | MongoDB 版本 | `service.mongodb.buildInfo.version:"4.0.6"` |
| `serverStatus.host` | 服务器 Host | `service.mongodb.serverStatus.host:"q361"` |
| `serverStatus.process` | 服务器进程名 | `service.mongodb.serverStatus.process:"mongod"` |
| `serverStatus.pid` | 服务进程 PID | `service.mongodb.serverStatus.pid:3666` |
| `serverStatus.connections.current` | 当前连接数 | `service.mongodb.serverStatus.connections.current:34` |
| `listDatabases.databases.name` | 数据库名 | `service.mongodb.listDatabases.databases.name:"admin"` |
| `listDatabases.totalSize` | 数据库大小 | `service.mongodb.listDatabases.totalSize:"103098089472"` |

## 工控协议字段

### Modbus

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `UnitId` | 单元 ID | `service.modbus.UnitId:1` |
| `DeviceIdentification` | 设备信息 | `service.modbus.DeviceIdentification:"Schneider Electric"` |
| `CpuModule` | CPU 型号 | `service.modbus.CpuModule:"BMX"` |

### S7（西门子 PLC）

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `Module` | 模块 | `service.s7.Module:"6ES7"` |
| `Basic_Hardware` | 硬件信息 | `service.s7.Basic_Hardware:"6ES7"` |
| `Name_of_the_PLC` | PLC 名称 | `service.s7.Name_of_the_PLC:"E40"` |

### Ethernet/IP

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `product_name` | 产品名 | `service.ethernetip.product_name:1763-L16BWA` |
| `vendor` | 制造商信息 | `service.ethernetip.vendor:"Rockwell Automation"` |
| `serial_num` | 设备序列号 | `service.ethernetip.serial_num:"0x40651da9"` |

## SMB 协议字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `ServerDefaultDialect` | 服务返回的默认版本 | `service.smb.ServerDefaultDialect:"SMB 3.0"` |
| `ListDialects` | 支持的 SMB 协议版本 | `service.smb.ListDialects:"SMB 3.1.1"` |
| `Authentication` | 认证开启情况 | `service.smb.Authentication:disabled` |
| `ServerOS` | 操作系统版本 | `service.smb.ServerOS:"Windows 6.1"` |
| `ServerDomain` | 域名称 | `service.smb.ServerDomain:"GFI"` |

## TLS 证书字段

| 字段 | 字段含义 | 搜索语法示例 |
| --- | --- | --- |
| `tls_AKID` / `tls_authority_key_id` | 颁发机构密钥标识符 | `tls_AKID:"142eb317b75856cbae500940e61faf9d8b14c2c6"` |
| `tls_SAN` / `tls_subject_alt_name` | 主体可选名称 | `tls_SAN:"baidu.com"` |
| `tls_SKID` / `tls_subject_key_id` | 主体密钥标识符 | `tls_SKID:"9ec979d7e95bab8a16cc328ec699e69f20423587"` |
| `tls_md5` | 证书哈希 MD5 | `tls_md5:"539b071cf7d2f02b1c85cc09da1186e5"` |
| `tls_sha1` | 证书哈希 SHA-1 | `tls_sha1:"fcb40a45f27eb391adb13f34a625968735ceddcb"` |
| `tls_sha256` | 证书哈希 SHA-256 | `tls_sha256:"2ed189349f818f3414132ebea309e36f620d78a0507a2fa523305f275062d73c"` |
| `tls_SPKI` / `tls_subject_key_info_sha256` | 公钥哈希 SHA-256 | `tls_SPKI:"ff9e7ca5dd58e557ab72fd59a12a8eac9583b21f6c4cc12894ce93f1cb0bb9c4"` |
| `tls_SN` / `tls_serial_number` | 证书序列号 | `tls_SN:"322522163434965920213346971099979782616521"` |
| `tls_issuer` | 签发者 | `tls_issuer:"O=GlobalSign"` |
| `tls_issuer_CN` / `tls_issuer_common_name` | 签发者通用名 | `tls_issuer_CN:"OV SS"` |

## 查询示例

```text
# 查找中国境内开放 443 端口的资产
port:"443" AND country_cn:"中国"

# 查找北京地区开放 3389 端口且不在广东省的资产
port:"3389" AND country_cn:"中国" AND NOT province_cn:"广东"

# 查找 Apache 产品且响应头包含 ThinkPHP 的资产
app:"Apache" AND headers:"ThinkPHP"

# 查找中国或美国且不在广东省的 3389 端口
port:"3389" AND (country:"China" OR country:"United States") AND NOT province_cn:"广东"

# 查找 80 端口且返回数据包不包括 baidu 的服务
port:"80" AND NOT response:"baidu"

# 查找证书中包含特定域名的资产
domain:"XXX.com" AND cert:"XXX\.com"

# 查找 IoT 物联网类别下的工控设备
catalog:"IoT物联网" AND type:"防火墙"

# 查找 MongoDB 未授权访问的资产
service.mongodb.authentication:false

# 查找特定 TLS 证书序列号的资产
tls_SN:"322522163434965920213346971099979782616521"
```
