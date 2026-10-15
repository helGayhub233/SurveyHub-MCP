> MCP 本地预算：搜索单页最多 1000 条；请求 body 时最多 500 条。公开 JSON 负载最多 64 KiB，长数据字符串保留前 4096 个字符并标记裁剪。上游 API 上限不代表 MCP 可请求上限；按 tools/list 的 Schema 调用。

# FOFA API 文档

来源：`https://fofa.info/api`

抓取时间：2026-10-15

## 基础信息

- 接入域名：`fofa.info`
- 协议：HTTPS
- 编码：UTF-8
- 请求方式：官方页面列出的接口均为 `GET`
- 鉴权：请求中携带 `key`。部分历史场景可能还会使用 `email`，但当前文档示例以 `key` 为主。

## 使用限制

- 个人账号调试或调用时，建议请求速率低于 `2/s`。
- 统计聚合接口限制为 `5 秒/次`。
- Host 聚合接口限制为 `1 秒/次`。
- 统计聚合、Host 聚合接口的访问限制与会员等级有关。
- 查询接口中如果返回字段包含 `cert` 或 `banner`，`size` 最大为 `2000`。
- 查询接口中如果返回字段包含 `body`，`size` 最大为 `500`。

### 本地 MCP 请求控制

- 同一凭证的全部 FOFA 工具（包含 `fofa_user_info`）共用账号级 `0.6 秒/次` 间隔（约 `1.67 次/秒`）。
- `fofa_search_stats` 另外遵守端点级 `5 秒/次`；`fofa_host` 另外遵守端点级 `1 秒/次`。SQLite 在一个事务中协调账号和端点两个范围，顺序交替调用也不会绕过账号桶。
- `fofa_search` 和 `fofa_search_next` 共用账号桶，默认字段统一为 `host,ip,port,domain,icp,icon_hash,cert`；下文参数表中的 `host,ip,port` 为上游默认值。
- `fofa_search` 和 `fofa_search_next` 会校验字段相关的 `size` 限制：返回 `body` 时最大 `500`，返回 `cert` 或 `banner` 时最大 `2000`。
- 相同凭证在同机、同用户且共用状态目录的 MCP 进程间共享节流；`SURVEYHUB_STATE_DIR` 可指定状态目录。多机或其他直接调用上游的客户端不在此协调范围内。
- 搜索、Host 和 Stats 均启用计费请求账本和安全重试；HTTP 200 中的 `error=true` 会转换为 MCP 业务失败，不进入成功缓存。
- `pagination.total` 读取上游搜索总量 `size`，`pagination.next_cursor` 原样保留 `next`，后续作为 `next_id` 入参。未知游标偏移不会被假设为 0；`full=true` 未获上游确认时不宣称完整。
- `meta.output` / `next_action=refine_query` 表示本地裁剪，应缩小单页或字段；不能直接翻页跳过本页省略的记录。这里的 500/2000 是记录条数限制，不是 body/cert/banner 的字符串长度限制。

## 请求结构

```text
GET https://fofa.info/api/v1/{endpoint}
```

## 查询接口

```http
GET /api/v1/search/all
```

用途：按 FOFA 查询语法搜索资产。

### 参数

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `key` | 是 | string | API Key |
| `qbase64` | 是 | string | 查询语法的 Base64 编码结果 |
| `fields` | 否 | string | 逗号分隔的返回字段，默认 `host,ip,port` |
| `page` | 否 | int | 页码，默认第 1 页 |
| `size` | 否 | int | 每页数量，默认 `100`，最大 `1000`（MCP 单次上限；上游文档上限为 10,000 条/页） |
| `full` | 否 | boolean | 默认查询一年内数据，`true` 查询全部数据 |
| `r_type` | 否 | string | 指定为 `json` 时返回 JSON |

### 示例

```bash
curl -X GET "https://fofa.info/api/v1/search/all?key={key}&qbase64={qbase64}&fields=host,ip,port&page=1&size=100&r_type=json"
```

### 响应字段

| 字段 | 说明 |
| --- | --- |
| `error` | 是否出错 |
| `consumed_fpoint` | 实际扣除 F 点 |
| `required_fpoints` | 应扣 F 点 |
| `size` | 查询总数 |
| `page` | 当前页 |
| `mode` | 查询模式 |
| `query` | 原始查询语句 |
| `results` | 结果数组，字段顺序与 `fields` 一致 |

### 可选返回字段

| 字段 | 说明 | 权限 |
| --- | --- | --- |
| `ip` | IP 地址 | 无 |
| `port` | 端口 | 无 |
| `protocol` | 协议名 | 无 |
| `country` | 国家代码 | 无 |
| `country_name` | 国家名 | 无 |
| `region` | 区域 | 无 |
| `city` | 城市 | 无 |
| `longitude` | 经度 | 无 |
| `latitude` | 纬度 | 无 |
| `asn` | ASN 编号 | 无 |
| `org` | ASN 组织 | 无 |
| `host` | 主机名 | 无 |
| `domain` | 域名 | 无 |
| `os` | 操作系统 | 无 |
| `server` | HTTP Server 信息 | 无 |
| `icp` | ICP 备案号 | 无 |
| `title` | 网站标题 | 无 |
| `jarm` | JARM 指纹 | 无 |
| `header` | 网站 Header | 无 |
| `banner` | 协议 Banner | 无 |
| `cert` | 证书 | 无 |
| `base_protocol` | 基础协议，如 `tcp`、`udp` | 无 |
| `link` | 资产 URL | 无 |
| `cert.issuer.org` | 证书颁发者组织 | 无 |
| `cert.issuer.cn` | 证书颁发者通用名称 | 无 |
| `cert.subject.org` | 证书持有者组织 | 无 |
| `cert.subject.cn` | 证书持有者通用名称 | 无 |
| `tls.ja3s` | JA3S 指纹 | 无 |
| `tls.version` | TLS 协议版本 | 无 |
| `cert.sn` | 证书序列号 | 无 |
| `cert.not_before` | 证书生效时间 | 无 |
| `cert.not_after` | 证书到期时间 | 无 |
| `cert.domain` | 证书中的根域名 | 无 |
| `status_code` | HTTP 状态码 | 无 |
| `header_hash` | HTTP/HTTPS 响应信息 Hash | 个人版及以上 |
| `banner_hash` | 协议响应完整 Hash | 个人版及以上 |
| `banner_fid` | 协议响应架构指纹 | 个人版及以上 |
| `cname` | 域名 CNAME | 专业版本及以上 |
| `lastupdatetime` | FOFA 最后更新时间 | 专业版本及以上 |
| `product` | 产品名 | 专业版本及以上 |
| `product_category` | 产品分类 | 专业版本及以上 |
| `product.version` | 产品版本号 | 商业版本及以上 |
| `icon_hash` | Icon Hash | 商业版本及以上 |
| `cert.is_valid` | 证书是否有效 | 商业版本及以上 |
| `cname_domain` | CNAME 的域名 | 商业版本及以上 |
| `body` | 网站正文 | 商业版本及以上 |
| `cert.is_match` | 证书颁发者和持有者是否相同 | 商业版本及以上 |
| `cert.is_equal` | 证书和域名是否匹配 | 商业版本及以上 |
| `icon` | Icon 图标 | 企业会员 |
| `fid` | FID | 企业会员 |
| `structinfo` | 结构化信息，部分协议支持 | 企业会员 |

## 连续翻页接口

```http
GET /api/v1/search/next
```

用途：针对同一查询持续翻页，避免页码翻页时因为数据变化导致结果错位。

### 参数

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `key` | 是 | string | API Key |
| `qbase64` | 是 | string | 查询语法的 Base64 编码结果 |
| `fields` | 否 | string | 逗号分隔的返回字段，默认 `host,ip,port` |
| `size` | 否 | int | 每页数量，默认 `100`，最大 `1000`（MCP 单次上限；上游文档上限为 10,000 条/页） |
| `next` | 否 | string | 上一次响应返回的翻页 ID；不传时返回第一页 |
| `full` | 否 | boolean | 默认查询一年内数据，`true` 查询全部数据 |
| `r_type` | 否 | string | 指定为 `json` 时返回 JSON |

### 示例

```bash
curl -X GET "https://fofa.info/api/v1/search/next?key={key}&qbase64={qbase64}&size=100&next={next_id}&r_type=json"
```

### 响应字段

除查询接口通用字段外，该接口会返回 `next`，用于下一页请求。

## 统计聚合接口

```http
GET /api/v1/search/stats
```

用途：按查询条件生成字段聚合统计，当前文档说明为每个字段返回前 5 排名。

### 参数

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `key` | 是 | string | API Key |
| `qbase64` | 是 | string | 查询语法的 Base64 编码结果 |
| `fields` | 否 | string | 逗号分隔的统计字段 |

### 可统计字段

`protocol`, `domain`, `port`, `title`, `os`, `server`, `country`, `asn`, `org`, `asset_type`, `fid`, `icp`

### 响应字段

| 字段 | 说明 |
| --- | --- |
| `error` | 是否出错 |
| `consumed_fpoint` | 实际扣除 F 点 |
| `required_fpoints` | 应扣 F 点 |
| `size` | 查询总数 |
| `distinct` | 唯一值统计，支持 `server`, `icp`, `domain`, `title`, `fid` |
| `aggs` | 聚合结果 |
| `lastupdatetime` | 数据最后更新时间 |

### 示例

```bash
curl -X GET "https://fofa.info/api/v1/search/stats?key={key}&qbase64={qbase64}&fields=protocol,domain,port"
```

## Host 聚合接口

```http
GET /api/v1/host/{host}
```

用途：查询单个 host 的聚合信息。`host` 通常是 IP。

### 参数

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `key` | 是 | string | API Key |
| `host` | 是 | string | 路径参数，通常传 IP |
| `detail` | 否 | boolean | 是否返回端口详情，默认 `false` |

### 示例

```bash
curl -X GET "https://fofa.info/api/v1/host/78.48.50.249?key={key}&detail=false"
curl -X GET "https://fofa.info/api/v1/host/78.48.50.249?key={key}&detail=true"
```

### `detail=false` 响应字段

| 字段 | 说明 |
| --- | --- |
| `error` | 是否出错 |
| `host` | Host |
| `ip` | IP |
| `asn` | ASN |
| `org` | ASN 组织 |
| `country_name` | 国家名 |
| `country_code` | 国家代码 |
| `protocol` | 协议列表 |
| `port` | 端口列表 |
| `domain` | 域名列表 |
| `category` | 分类标签 |
| `product` | 产品标签 |
| `update_time` | 更新时间 |

### `detail=true` 响应字段

| 字段 | 说明 |
| --- | --- |
| `ports` | 端口详情数组 |
| `ports[].port` | 端口 |
| `ports[].protocol` | 协议 |
| `ports[].products` | 产品详情列表 |
| `product` | 产品名 |
| `category` | 产品分类 |
| `level` | 产品分层，`5` 应用层，`4` 支持层，`3` 服务层，`2` 系统层，`1` 硬件层，`0` 无组件分层 |
| `soft_hard_code` | 是否硬件；`1` 表示硬件，其他值表示非硬件 |

## 账号信息接口

```http
GET /api/v1/info/my
```

用途：查看当前账号状态、邮箱、用户名、余额、会员等级等，不返回资产数据。

### 参数

| 参数 | 必填 | 类型 | 说明 |
| --- | --- | --- | --- |
| `key` | 是 | string | API Key |

### 示例

```bash
curl -X GET "https://fofa.info/api/v1/info/my?key={key}"
```

### 响应字段

| 字段 | 说明 |
| --- | --- |
| `error` | 是否出错 |
| `email` | 邮箱 |
| `username` | 用户名 |
| `category` | 用户类型 |
| `fcoin` | F 币 |
| `fofa_point` | F 点 |
| `remain_free_point` | 剩余免费 F 点 |
| `remain_api_query` | API 月度剩余查询次数 |
| `remain_api_data` | API 月度剩余返回数量 |
| `isvip` | 是否会员 |
| `vip_level` | 会员等级 |
| `is_verified` | 是否认证 |
| `avatar` | 头像 URL |
| `message` | 消息 |
| `fofacli_ver` | FOFA CLI 版本 |
| `fofa_server` | 服务状态标识 |
