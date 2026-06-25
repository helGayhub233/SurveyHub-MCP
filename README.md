<h1 align="center">SurveyHub-MCP</h1>

<p align="center">基于 <code>FastMCP</code> 编写的空间测绘 MCP Server，聚合查询 FOFA、Quake、Hunter、ZoomEye、DayDayMap</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/surveyhub-mcp?label=PyPI&color=3775A9" alt="PyPI 版本"/>
  <img src="https://img.shields.io/badge/Python-%3E%3D3.10-3776AB" alt="Python >=3.10"/>
  <img src="https://img.shields.io/github/stars/helGayhub233/SurveyHub-MCP?style=flat&label=Stars&color=181717" alt="GitHub Stars"/>
  <img src="https://img.shields.io/pypi/dm/surveyhub-mcp?label=Downloads&color=2EA44F" alt="PyPI 下载量"/>
  <img src="https://img.shields.io/github/license/helGayhub233/SurveyHub-MCP?label=License&color=blue" alt="许可证"/>
</p>

## 支持平台

| 平台 | 能力 |
| --- | --- |
| FOFA | 资产搜索、连续翻页、统计聚合、Host 聚合、账号信息 |
| 360 Quake | 服务搜索、深度翻页、聚合查询、字段查询、账号信息 |
| Hunter  | 资产搜索、批量任务、任务状态、结果下载、账号信息 |
| ZoomEye | 资产搜索、账号信息 |
| DayDayMap | 资产搜索 |

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
        "CN_DAYDAYMAP_API_KEY": "your_daydaymap_api_key"
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
hunter-personal-mcp //个人版
hunter-enterprise-mcp //企业版
daydaymap-mcp
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
        "CN_DAYDAYMAP_API_KEY": "your_daydaymap_api_key"
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

`mcp.json.example` 和 `.env.example` 提供了可直接修改的示例。

## 环境变量

环境变量使用 `CN_` 前缀命名规范。

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

API Key 获取入口：

- FOFA: `https://fofa.info`
- Quake: `https://quake.360.net`
- ZoomEye: `https://www.zoomeye.org`
- Hunter: `https://hunter.qianxin.com`
- DayDayMap: `https://www.daydaymap.com`

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

## 请求限制

项目会对可在本地判断的参数做校验或节流。账号等级、积分额度、CSV 文件内容等仍以平台返回为准。

| 平台 | 工具 | 控制方式 |
| --- | --- | --- |
| FOFA | `fofa_search_stats` | 进程内节流，`5 秒/次` |
| FOFA | `fofa_host` | 进程内节流，`1 秒/次` |
| FOFA | `fofa_search`, `fofa_search_next` | 本地校验，返回 `body` 时 `size <= 500` |
| FOFA | `fofa_search`, `fofa_search_next` | 本地校验，返回 `cert` 或 `banner` 时 `size <= 2000` |
| Quake | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Quake | `quake_service_search`, `quake_service_scroll` | 参数 schema 限制，`size <= 500` |
| Quake | `quake_service_aggregation` | 本地校验聚合字段最多 2 个，参数 schema 限制 `size <= 10000` |
| ZoomEye | `zoomeye_search` | 参数 schema 限制，`pagesize <= 10000` |
| Hunter 个人版 | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Hunter 个人版 | 批量任务 | 工具描述提示平台限制：`all <= 10`，`ip/domain/company <= 100` |
| Hunter 企业版 | 全部搜索工具 | 进程内节流，`1 秒/次` |
| Hunter 企业版 | 批量任务 | 工具描述提示平台限制：`all <= 10`，`ip/domain/company <= 10000` |
| DayDayMap | `daydaymap_search` | 参数 schema 限制，`page <= 10000`、`page_size <= 10000` |
| 全部平台 | 全部 HTTP 请求 | 进程内熔断保护，连续 2 次可恢复失败后暂停 15 秒 |

FOFA、Quake、Hunter 的频率控制和全部平台的熔断状态是单 MCP 进程内的内存状态；如果同时启动多个 MCP 进程，进程之间不会共享这些状态。

## API 文档

已整理的接口文档位于 `docs/api/`：

- `docs/api/fofa_api.md`
- `docs/api/quake_api.md`
- `docs/api/zoomeye_api.md`
- `docs/api/hunter_personal_api.md`
- `docs/api/hunter_enterprise_api.md`
- `docs/api/daydaymap_api.md`

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
    common.py             # 共享编码、HTTP、错误处理和节流工具
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
