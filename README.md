# SurveyHub-MCP

基于 `FastMCP` 编写的网络空间测绘 MCP Server，聚合查询 FOFA、Quake、Hunter、ZoomEye、DayDayMap、Shodan、Censys、SecurityTrails、BinaryEdge、Netlas、Onyphe、LeakIX、FullHunt、Criminal IP。

适合在 Claude Desktop、Cursor、Codex 程序中作为 MCP 连接器使用。

## 支持平台

| 平台 | 能力 |
| --- | --- |
| FOFA | 资产搜索、连续翻页、统计聚合、Host 聚合、账号信息 |
| 360 Quake | 服务搜索、深度翻页、聚合查询、字段查询、账号信息 |
| Hunter 个人版 | 资产搜索、批量任务、任务状态、结果下载、账号信息 |
| Hunter 企业版 | 资产搜索、批量任务、任务状态、结果下载、结果拉取、账号信息 |
| ZoomEye | 资产搜索、账号信息 |
| DayDayMap | 资产搜索 |
| Shodan | 资产搜索、统计聚合、Host 详情、DNS 查询、账号信息 |
| Censys | 资产搜索、聚合统计、Host 详情、账号信息 |
| SecurityTrails | 域名信息、子域名枚举 |
| BinaryEdge | 全域搜索、子域名枚举、账户信息 |
| Netlas | 互联网扫描搜索、DNS 搜索、账户信息 |
| Onyphe | 资产搜索、IP 摘要、域名摘要、账户信息 |
| LeakIX | 资产搜索、Host 详情、子域名发现 |
| FullHunt | 域名攻击面、子域名枚举、Host 详情 |
| Criminal IP | IP 资产报告、Banner 搜索、域名报告 |

## 快速开始

### 通过 pip 安装

要求 Python `>=3.10`。用户无需 clone 源码，可直接从 PyPI 安装：

```bash
python -m pip install -U surveyhub-mcp
```

安装后可直接启动聚合 MCP Server：

```bash
surveyhub-mcp
```

MCP 客户端配置：

```json
{
  "mcpServers": {
    "surveyhub": {
      "command": "surveyhub-mcp",
      "args": [],
      "env": {
        "CN_FOFA_KEY": "your_fofa_key",
        "CN_FOFA_EMAIL": "optional_fofa_email",
        "CN_QUAKE_KEY": "your_quake_key",
        "CN_ZOOMEYE_API_KEY": "your_zoomeye_api_key",
        "CN_HUNTER_KEY": "fallback_hunter_key",
        "CN_HUNTER_PERSONAL_KEY": "your_hunter_personal_key",
        "CN_HUNTER_ENTERPRISE_KEY": "your_hunter_enterprise_key",
        "CN_DAYDAYMAP_API_KEY": "your_daydaymap_api_key",
        "US_SHODAN_API_KEY": "your_shodan_api_key",
        "US_CENSYS_API_ID": "your_censys_api_id",
        "US_CENSYS_API_SECRET": "your_censys_api_secret",
        "US_SECURITYTRAILS_API_KEY": "your_securitytrails_api_key",
        "PT_BINARYEDGE_API_KEY": "your_binaryedge_api_key",
        "CY_NETLAS_API_KEY": "your_netlas_api_key",
        "FR_ONYPHE_API_KEY": "your_onyphe_api_key",
        "FR_LEAKIX_API_KEY": "your_leakix_api_key",
        "AE_FULLHUNT_API_KEY": "your_fullhunt_api_key",
        "KR_CRIMINALIP_API_KEY": "your_criminalip_api_key"
      }
    }
  }
}
```

只运行单个平台入口时：

```bash
fofa-mcp
quake-mcp
zoomeye-mcp
hunter-personal-mcp
hunter-enterprise-mcp
daydaymap-mcp
shodan-mcp
censys-mcp
securitytrails-mcp
binaryedge-mcp
netlas-mcp
onyphe-mcp
leakix-mcp
fullhunt-mcp
criminalip-mcp
```

### 通过 uvx 免安装运行

如果不想提前安装，也可以在 MCP 客户端中使用 `uvx` 直接运行 PyPI 包：

```json
{
  "mcpServers": {
    "surveyhub": {
      "command": "uvx",
      "args": [
        "surveyhub-mcp"
      ],
      "env": {
        "CN_FOFA_KEY": "your_fofa_key",
        "CN_FOFA_EMAIL": "optional_fofa_email",
        "CN_QUAKE_KEY": "your_quake_key",
        "CN_ZOOMEYE_API_KEY": "your_zoomeye_api_key",
        "CN_HUNTER_KEY": "fallback_hunter_key",
        "CN_HUNTER_PERSONAL_KEY": "your_hunter_personal_key",
        "CN_HUNTER_ENTERPRISE_KEY": "your_hunter_enterprise_key",
        "CN_DAYDAYMAP_API_KEY": "your_daydaymap_api_key",
        "US_SHODAN_API_KEY": "your_shodan_api_key",
        "US_CENSYS_API_ID": "your_censys_api_id",
        "US_CENSYS_API_SECRET": "your_censys_api_secret",
        "US_SECURITYTRAILS_API_KEY": "your_securitytrails_api_key",
        "PT_BINARYEDGE_API_KEY": "your_binaryedge_api_key",
        "CY_NETLAS_API_KEY": "your_netlas_api_key",
        "FR_ONYPHE_API_KEY": "your_onyphe_api_key",
        "FR_LEAKIX_API_KEY": "your_leakix_api_key",
        "AE_FULLHUNT_API_KEY": "your_fullhunt_api_key",
        "KR_CRIMINALIP_API_KEY": "your_criminalip_api_key"
      }
    }
  }
}
```

只运行单个平台入口时：

```bash
uvx --from surveyhub-mcp fofa-mcp
uvx --from surveyhub-mcp quake-mcp
uvx --from surveyhub-mcp zoomeye-mcp
uvx --from surveyhub-mcp hunter-personal-mcp
uvx --from surveyhub-mcp hunter-enterprise-mcp
uvx --from surveyhub-mcp daydaymap-mcp
uvx --from surveyhub-mcp shodan-mcp
uvx --from surveyhub-mcp censys-mcp
uvx --from surveyhub-mcp securitytrails-mcp
uvx --from surveyhub-mcp binaryedge-mcp
uvx --from surveyhub-mcp netlas-mcp
uvx --from surveyhub-mcp onyphe-mcp
uvx --from surveyhub-mcp leakix-mcp
uvx --from surveyhub-mcp fullhunt-mcp
uvx --from surveyhub-mcp criminalip-mcp
```

### 从源码运行

```bash
git clone https://github.com/helGayhub233/SurveyHub-MCP.git
cd SurveyHub-MCP
uv sync
uv run surveyhub-mcp
```

也可以只启动单个平台：

```bash
uv run fofa-mcp
uv run quake-mcp
uv run zoomeye-mcp
uv run hunter-personal-mcp
uv run hunter-enterprise-mcp
uv run daydaymap-mcp
uv run shodan-mcp
uv run censys-mcp
```

## MCP 配置

从源码运行时，推荐使用 `uv --directory` 固定项目目录。使用 PyPI 包时可直接参考上方 `pip` 或 `uvx` 配置。

```json
{
  "mcpServers": {
    "surveyhub": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/SurveyHub-MCP",
        "run",
        "surveyhub-mcp"
      ],
      "env": {
        "CN_FOFA_KEY": "your_fofa_key",
        "CN_FOFA_EMAIL": "optional_fofa_email",
        "CN_QUAKE_KEY": "your_quake_key",
        "CN_ZOOMEYE_API_KEY": "your_zoomeye_api_key",
        "CN_HUNTER_KEY": "fallback_hunter_key",
        "CN_HUNTER_PERSONAL_KEY": "your_hunter_personal_key",
        "CN_HUNTER_ENTERPRISE_KEY": "your_hunter_enterprise_key",
        "CN_DAYDAYMAP_API_KEY": "your_daydaymap_api_key"
      }
    }
  }
}
```

只使用某一个平台时，把 `args` 最后一个命令替换为对应入口，并只保留对应平台的 Key。

| 平台 | 单平台入口 | 必要环境变量 |
| --- | --- | --- |
| FOFA | `fofa-mcp` | `CN_FOFA_KEY` |
| Quake | `quake-mcp` | `CN_QUAKE_KEY` |
| ZoomEye | `zoomeye-mcp` | `CN_ZOOMEYE_API_KEY` |
| Hunter 个人版 | `hunter-personal-mcp` | `CN_HUNTER_PERSONAL_KEY` |
| Hunter 企业版 | `hunter-enterprise-mcp` | `CN_HUNTER_ENTERPRISE_KEY` |
| DayDayMap | `daydaymap-mcp` | `CN_DAYDAYMAP_API_KEY` |
| Shodan | `shodan-mcp` | `US_SHODAN_API_KEY` |
| Censys | `censys-mcp` | `US_CENSYS_API_ID` + `US_CENSYS_API_SECRET` |
| SecurityTrails | `securitytrails-mcp` | `US_SECURITYTRAILS_API_KEY` |
| BinaryEdge | `binaryedge-mcp` | `PT_BINARYEDGE_API_KEY` |
| Netlas | `netlas-mcp` | `CY_NETLAS_API_KEY` |
| Onyphe | `onyphe-mcp` | `FR_ONYPHE_API_KEY` |
| LeakIX | `leakix-mcp` | `FR_LEAKIX_API_KEY` |
| FullHunt | `fullhunt-mcp` | `AE_FULLHUNT_API_KEY` |
| Criminal IP | `criminalip-mcp` | `KR_CRIMINALIP_API_KEY` |

`mcp.json.example` 和 `.env.example` 提供了可直接修改的示例。

## 环境变量

环境变量使用地区前缀命名规范。

| 环境变量 | 说明 |
| --- | --- |
| `CN_FOFA_KEY` | FOFA API Key |
| `CN_FOFA_EMAIL` | FOFA Email，可选 |
| `CN_QUAKE_KEY` | 360 Quake API Key |
| `CN_ZOOMEYE_API_KEY` | ZoomEye API Key |
| `CN_HUNTER_KEY` | Hunter 通用 fallback API Key |
| `CN_HUNTER_PERSONAL_KEY` | Hunter 个人版 API Key |
| `CN_HUNTER_ENTERPRISE_KEY` | Hunter 企业版 API Key |
| `CN_DAYDAYMAP_API_KEY` | DayDayMap API Key |
| `US_SHODAN_API_KEY` | Shodan API Key |
| `US_CENSYS_API_ID` | Censys API ID |
| `US_CENSYS_API_SECRET` | Censys API Secret |
| `US_SECURITYTRAILS_API_KEY` | SecurityTrails API Key |
| `PT_BINARYEDGE_API_KEY` | BinaryEdge API Key |
| `CY_NETLAS_API_KEY` | Netlas API Key |
| `FR_ONYPHE_API_KEY` | Onyphe API Key |
| `FR_LEAKIX_API_KEY` | LeakIX API Key |
| `AE_FULLHUNT_API_KEY` | FullHunt API Key |
| `KR_CRIMINALIP_API_KEY` | Criminal IP API Key |

API Key 获取入口：

- FOFA: `https://fofa.info`
- Quake: `https://quake.360.net`
- ZoomEye: `https://www.zoomeye.org`
- Hunter: `https://hunter.qianxin.com`
- DayDayMap: `https://www.daydaymap.com`
- Shodan: `https://account.shodan.io`
- Censys: `https://search.censys.io/account/api`
- SecurityTrails: `https://securitytrails.com/app/account/credentials`
- BinaryEdge: `https://app.binaryedge.io/account`
- Netlas: `https://app.netlas.io/profile/`
- Onyphe: `https://www.onyphe.io/`
- LeakIX: `https://leakix.net/`
- FullHunt: `https://fullhunt.io/`
- Criminal IP: `https://www.criminalip.io/`

## 工具列表

| 工具名称 | 所属平台 | 说明 |
| --- | --- | --- |
| `fofa_search` | FOFA | 常规资产搜索 |
| `fofa_search_next` | FOFA | 连续翻页搜索 |
| `fofa_search_stats` | FOFA | 统计聚合 |
| `fofa_host` | FOFA | Host 聚合 |
| `fofa_user_info` | FOFA | 账号信息 |
| `quake_user_info` | Quake | 用户信息 |
| `quake_filterable_fields` | Quake | 服务数据可筛选字段 |
| `quake_service_search` | Quake | 实时服务搜索 |
| `quake_service_scroll` | Quake | 深度翻页搜索 |
| `quake_search` | Quake | 兼容别名，等同于 `quake_service_scroll` |
| `quake_aggregation_fields` | Quake | 聚合字段列表 |
| `quake_service_aggregation` | Quake | 服务聚合查询 |
| `zoomeye_user_info` | ZoomEye | 用户信息、订阅信息和积分情况 |
| `zoomeye_search` | ZoomEye | 资产搜索 |
| `hunter_personal_search` | Hunter 个人版 | 资产搜索 |
| `hunter_personal_batch_create` | Hunter 个人版 | 创建批量任务 |
| `hunter_personal_batch_status` | Hunter 个人版 | 查询批量任务状态 |
| `hunter_personal_batch_download` | Hunter 个人版 | 下载批量任务结果 |
| `hunter_personal_user_info` | Hunter 个人版 | 账号信息 |
| `hunter_enterprise_search` | Hunter 企业版 | 资产搜索 |
| `hunter_enterprise_batch_create` | Hunter 企业版 | 创建批量任务 |
| `hunter_enterprise_batch_status` | Hunter 企业版 | 查询批量任务状态 |
| `hunter_enterprise_batch_download` | Hunter 企业版 | 下载批量任务结果 |
| `hunter_enterprise_batch_pull` | Hunter 企业版 | 拉取批量任务结果 JSON |
| `hunter_enterprise_user_info` | Hunter 企业版 | 账号信息 |
| `daydaymap_search` | DayDayMap | 资产搜索 |
| `shodan_search` | Shodan | 资产搜索 |
| `shodan_search_count` | Shodan | 搜索结果计数（不消耗额度） |
| `shodan_host` | Shodan | IP 主机详情 |
| `shodan_api_info` | Shodan | API 配额信息 |
| `shodan_domain` | Shodan | 域名信息（子域名+DNS 记录） |
| `shodan_dns_resolve` | Shodan | DNS 正向解析 |
| `shodan_dns_reverse` | Shodan | DNS 反向解析 |
| `censys_search` | Censys | 资产搜索 |
| `censys_aggregate` | Censys | 聚合统计（端口/国家/服务分布） |
| `censys_view_host` | Censys | IP 主机详情 |
| `censys_account` | Censys | 账号配额信息 |
| `securitytrails_domain` | SecurityTrails | 域名信息（DNS 记录+统计） |
| `securitytrails_subdomains` | SecurityTrails | 子域名枚举 |
| `binaryedge_search` | BinaryEdge | 全域资产搜索 |
| `binaryedge_subdomains` | BinaryEdge | 子域名枚举 |
| `binaryedge_account` | BinaryEdge | 账户配额信息 |
| `netlas_search` | Netlas | 互联网扫描数据搜索（banner/HTTP/SSL） |
| `netlas_domain` | Netlas | DNS 记录搜索 |
| `netlas_account` | Netlas | 账户配额信息 |
| `onyphe_search` | Onyphe | OQL 资产搜索 |
| `onyphe_summary_ip` | Onyphe | IP 资产摘要（30天全类别聚合） |
| `onyphe_summary_domain` | Onyphe | 域名资产摘要 |
| `onyphe_account` | Onyphe | 账户信息（许可证/信用额度） |
| `leakix_search` | LeakIX | YQL 资产搜索（service/leak scope） |
| `leakix_host` | LeakIX | Host 详情（Services + Leaks） |
| `leakix_subdomains` | LeakIX | 子域名发现 |
| `leakix_plugins` | LeakIX | 检测插件列表 |
| `fullhunt_domain` | FullHunt | 域名攻击面详情（主机/端口/服务/CPE/SSL/WHOIS） |
| `fullhunt_subdomains` | FullHunt | 子域名枚举 |
| `fullhunt_host` | FullHunt | 主机详情（端口/服务/产品/证书/技术栈） |
| `fullhunt_account` | FullHunt | 账户信息（计划/credits） |
| `criminalip_ip` | Criminal IP | IP 资产报告（端口/Banner/SSL/漏洞/WHOIS） |
| `criminalip_search` | Criminal IP | Banner 全网搜索 |
| `criminalip_domain` | Criminal IP | 域名情报报告 |
| `criminalip_account` | Criminal IP | 账户信息（计划/credits） |

## 请求限制

项目会对可在本地判断的参数做校验或节流。账号等级、积分额度、CSV 文件内容等仍以平台返回为准。

| 平台 | 工具 | 控制方式 |
| --- | --- | --- |
| FOFA | `fofa_search_stats` | 进程内节流，`5 秒/次` |
| FOFA | `fofa_host` | 进程内节流，`1 秒/次` |
| FOFA | `fofa_search`, `fofa_search_next` | 本地校验，返回 `body` 时 `size <= 500` |
| FOFA | `fofa_search`, `fofa_search_next` | 本地校验，返回 `cert` 或 `banner` 时 `size <= 2000` |
| Quake | `quake_service_search`, `quake_service_scroll` | 参数 schema 限制，`size <= 500` |
| Quake | `quake_service_aggregation` | 本地校验聚合字段最多 2 个，参数 schema 限制 `size <= 10000` |
| ZoomEye | `zoomeye_search` | 参数 schema 限制，`pagesize <= 10000` |
| Hunter 个人版 | 批量任务 | 工具描述提示平台限制：`all <= 10`，`ip/domain/company <= 100` |
| Hunter 企业版 | 批量任务 | 工具描述提示平台限制：`all <= 10`，`ip/domain/company <= 10000` |
| DayDayMap | `daydaymap_search` | 参数 schema 限制，`page <= 10000`、`page_size <= 10000` |
| Shodan | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Censys | 全部搜索工具 | 进程内节流，`1.1 秒/次`（满足 1 并发限制） |
| SecurityTrails | 全部搜索工具 | 进程内节流，`1 秒/次` |
| BinaryEdge | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Netlas | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Onyphe | 全部搜索工具 | 进程内节流，`1 秒/次` |
| LeakIX | 全部搜索工具 | 进程内节流，`1 秒/次` |
| FullHunt | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Criminal IP | 全部搜索工具 | 进程内节流，`1 秒/次` |

FOFA 的频率控制是单 MCP 进程内的内存节流；如果同时启动多个 MCP 进程，进程之间不会共享节流状态。

## API 文档

已整理的接口文档位于 `docs/api/`：

- `docs/api/fofa_api.md`
- `docs/api/quake_api.md`
- `docs/api/zoomeye_api.md`
- `docs/api/hunter_personal_api.md`
- `docs/api/hunter_enterprise_api.md`
- `docs/api/daydaymap_api.md`
- `docs/api/shodan_api.md`
- `docs/api/censys_api.md`
- `docs/api/securitytrails_api.md`
- `docs/api/binaryedge_api.md`
- `docs/api/netlas_api.md`
- `docs/api/onyphe_api.md`
- `docs/api/leakix_api.md`
- `docs/api/fullhunt_api.md`
- `docs/api/criminalip_api.md`

版本发布和迭代记录见 `CHANGELOG.md`。

## 项目结构

```text
src/
  surveyhub_mcp/
    server.py             # 聚合 MCP 入口
    fofa.py               # FOFA 工具
    quake.py              # Quake 工具
    zoomeye.py            # ZoomEye 工具
    hunter_personal.py    # Hunter 个人版工具
    hunter_enterprise.py  # Hunter 企业版工具
    daydaymap.py          # DayDayMap 工具
    shodan.py             # Shodan 工具
    censys.py             # Censys 工具
    securitytrails.py      # SecurityTrails 工具
    binaryedge.py          # BinaryEdge 工具
    netlas.py              # Netlas 工具
    onyphe.py              # Onyphe 工具
    leakix.py              # LeakIX 工具
    fullhunt.py            # FullHunt 工具
    criminalip.py          # Criminal IP 工具
    common.py              # 共享编码、HTTP、错误处理和节流工具
```

## 开发

```bash
uv sync
uv run python -m compileall src/surveyhub_mcp
uv build --wheel
```

## 注意

请只在合法授权范围内使用本项目，并遵守各平台的 API 服务条款和额度限制。

## 许可证

MIT License，见 `LICENSE`。
