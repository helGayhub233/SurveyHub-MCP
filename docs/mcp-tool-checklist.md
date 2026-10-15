# MCP 工具检查表

> **当前设计整改（2026-10-15）**：以下原始基线与附录 A/B 保留为历史记录，不代表当前实现。代码已统一业务错误、记录计数、分页与执行回执；增加 64 KiB 输出预算、凭证隔离缓存、FOFA 账号/端点原子协调与六平台本机共享节流；Hunter 下载默认禁止覆盖并采用原子提交。此次验证为离线回归和 Schema 检查，未重跑上游实测。
>
> 评审分层：协议约定（Schema、isError、工具发现）、Agent 接口设计（语义、输出预算、分页组合）与服务治理（凭证、限流、配额）分别判定。OpenViking 是参考实现，业务特有的文件操作约定不视为所有 MCP 的强制规范。

> **用途**：对 SurveyHub-MCP（及同构自研 MCP 服务）的工具实现做例行审查，覆盖两类问题：
> 1. **请求限流与配额治理**——来源：2026-10-15 FOFA 审查发现的 3 个低风险缺口（附录 A）；
> 2. **工具设计范式**——参照：OpenViking MCP 服务端工具范式（附录 C）。
>
> **基线**：2026-10-15。限流现状为静态代码核查 + `note/check_fofa_rate.py` 实测；OpenViking 范式来自其官方仓库文档与运行时工具 Schema。
>
> **用法**：逐项勾选（`[ ]` → `[x]`）；不满足的记录整改，接受例外的记录理由与日期。同一检查表适用于任意平台工具集（FOFA / Quake / ZoomEye / DayDayMap / Hunter 个人 / Hunter 企业）。
>
> - 「基线」栏是 2026-10-15 的核查结果，仅作对照，不代表永久结论。
> - 涉及行号只写符号名或函数名，避免行号漂移。

## 本次协议整改闭环（2026-10-15，SDK 2.3.0）

验证命令：`.venv/bin/python -m unittest discover -s tests -v`，89 项通过，其中新增协议回归 12 项。新增 `tests/test_mcp_protocol_contracts.py`，使用真实 SDK 客户端/服务端和内存传输，三个版本各建独立连接；另以独立子进程逐一重跑三个版本的 stdio 握手、目录和错误路径，全部通过。上游 API 仍为离线验证，未消耗供应商配额。

- [x] **审查 P1**：`fofa_search` 缺参、`quake_search size=99999`、类型错误、多余参数及未知工具均有 `structuredContent`；与文本 JSON 相等，并通过声明的输出 Schema。预期失败/意外异常分别返回 `tool_error`/`internal_error`；协议错误与取消继续透传。
- [x] **审查 P2**：六个可缓存方法均提供正 TTL。工具目录及发现结果为 5 分钟 `private`；静态目录为 5 分钟 `public`，参考读取为 1 小时 `public`。SDK 客户端连续读取两次只产生一次请求，显式刷新仍会发送请求。
- [x] **Schema 体量**：32 工具目录从约 404 KB 降至 247 KB；单份输出 Schema 从 10,537 字节降至 5,575 字节（JSON 默认序列化口径）。仅删除说明性注释，逐工具保留校验约束和本地 `$defs`；完整说明在 `surveyhub://reference/response-schema`。不使用依赖客户端跨工具解析的外部引用。
- [x] **审查 P3**：`2026-07-28` 发现结果省略 `logging`；旧版仍宣告并支持 `logging/setLevel`。现代请求按公开 `_meta` 筛选日志，不依赖 `_allowed_log_levels`；未启用日志的请求不会收到日志。
- [x] **入口一致性**：FOFA 5 / Quake 13 / ZoomEye 2 / DayDayMap 1 / Hunter Personal 5 / Hunter Enterprise 6，均继承错误信封、缓存和现代能力修复。
- [x] **次要项**：32 工具均声明并执行 `additionalProperties=false`；无凭证启动 instructions 从 7,305 压缩至 4,844 字符，修复重复词；补充 `website_url`。

缓存提示和作用域依据 [SDK caching 文档](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/client/caching.md)。保留 `private` 是因为工具可见性及启动说明依赖当前进程凭证配置，正 TTL 仍允许同一调用方复用。Tasks、HTTP transport 和 icons 是后续特性，不作为本次协议修复的完成条件。下面未勾选项保留待复核状态，尤其上游官方限额与全量文档一致性不能由离线测试代替。

## 一、请求限流与配额

### 1.1 端点覆盖

**R1 所有外呼调用点都经过限流评估**
- [x] 检查方法：`rg -n 'request_json\(|rate_limiter=' src/surveyhub_mcp/`，逐点确认是否传 `rate_limiter` 或有豁免说明
- 通过标准：每个调用点要么传入限流器，要么在代码注释或 API 文档中注明"不耗配额、无频率要求"的豁免理由
- 基线：FOFA `get_fofa_user_info()` 未传 `rate_limiter` → 缺口①：单次调用无影响，连续批量调用无频率兜底
- 复查：六平台外呼均传入按凭证协调的限流器，FOFA `user_info` 也进入账号桶。

**R2 信息类端点（user_info 等）同样纳入兜底**
- [x] 检查方法：对照 R1 清单，确认 user_info / 字段查询类端点的覆盖情况
- 通过标准：信息类端点与搜索端点同等对待，或显式说明豁免
- 基线：Hunter `userInfo` 已套 1 秒限流（正面样板）；FOFA `fofa_user_info` 未限流（缺口①）

### 1.2 账号级统一节流

**R3 同一凭证的多端点不存在可超限的并发交错**
- [x] 检查方法：列出该平台全部限流器实例与间隔，模拟最坏交错场景（如 search 1.67 次/秒与 host 1 次/秒同时进行），核对瞬时合计速率
- 通过标准：账号级与端点级限制均覆盖实际调用，包括并发及顺序交替；不能用"正常 MCP 顺序调用"替代共享约束。接受部署例外时须明确凭证使用范围及外部协调责任。
- 基线：FOFA 的 search / host / stats 是三个独立限流器实例 → 缺口②：交错并发瞬时合计可超 2/s；正常 MCP 顺序调用流程不触发，但没有账号级统一节流
- 复查：账号与端点桶由同一 SQLite 事务预留；`SharedRateLimitTests` 覆盖交错预留。本次未重跑真实多进程并发压测。

### 1.3 跨进程协调

**R4 按凭证实际使用范围设置跨进程协调**
- [x] 检查方法：检查各平台 `AsyncRateLimiter(...)` 构造参数是否传 `namespace` 与 `identity_provider`
- 通过标准：共用凭证的进程在正确的限流范围内共享状态；SQLite/namespace/identity_provider 是本项目的实现方式，不是协议要求。单进程、跨用户、多主机及外部调用方的边界分别说明。
- 基线：FOFA 三个限流器与 Quake 限流器均未传 → 缺口③：多进程各自独立节流；Hunter 个人/企业已设置（正面样板）
- 复查：六平台均配置，Hunter 同 Key 共享账号桶；协调边界仍为同机、同用户、同状态目录。

**R5 未做跨进程协调时，文档写明"单进程内存节流"边界**
- [x] 检查方法：检查 `docs/api/<平台>_api.md` 的"本地 MCP 请求控制"（或等价章节）
- 通过标准：跨进程协调的适用范围、共享机制与不适用范围均须显式写入平台文档。
- 基线：`fofa_api.md` 已写明 ✓；其余平台文档待确认
- 复查（2026-10-15）：六平台均在文档头部写明"相同凭证共享 SQLite 节流，限同机、同用户且共用状态目录的进程"。该说明位于 MCP 本地预算提示之后的等价章节，非独立 `### 本地 MCP 请求控制` 标题；`fofa` / `daydaymap` 保留了该标题，其余四平台改用头部说明块。多机、跨用户及直接调用上游的客户端明确不在协调范围内。

### 1.4 参数与上游依据

**R6 限流间隔与上游官方要求一致或更保守，并注明依据**
- [x] 检查方法：对照各平台官方文档的"使用限制"，核对代码中的间隔常数
- 通过标准：每个间隔常数都能指向上游依据，或明确标注为本地保护值而非上游声明。
- 基线：FOFA search/next `0.6 秒/次`（官方建议 <2/s）、stats `5 秒/次`、host `1 秒/次` ✓；Quake `5 秒/次`、Hunter `1 秒/次` 待逐平台核对上游一致性
- 复查（2026-10-15）：FOFA 三档间隔均可对应上游「使用限制」（建议 <2/s、stats 5 秒/次、host 1 秒/次），本地取值等于或更保守 ✓。Quake `5 秒/次`、Hunter `1 秒/次`、ZoomEye `1 秒/次`、DayDayMap `1 秒/次` 属**本地保护值**：上游未声明请求频率上限。已在四份文档补注该性质及真实限速反馈渠道（Quake `q3005`、Hunter HTTP/业务码 429）。

### 1.5 文档同步

**R7 限流信息四处一致：代码常数 ↔ 工具 description ↔ API 文档 ↔ CHANGELOG**
- [x] 检查方法：改动限流后逐处对照四出处
- 通过标准：四处数值一致；仅作说明性描述的出处不构成不一致。
- 基线：FOFA `0.6 秒/次` 节流曾只记录于工具 description 与 CHANGELOG，`docs/api/fofa_api.md` 未收录（文档差异④，已于 2026-10-15 补记）
- 复查（2026-10-15）：代码常数（0.6/1/5 秒与各 1 秒）与工具 description 逐工具核对一致；六平台 API 文档头部均含对应间隔；CHANGELOG「Unreleased」记录了账号级协调与本地一秒保护的变更。四处无冲突。

## 二、工具设计范式（OpenViking 参照）

> 参照对象：OpenViking MCP 服务端工具。核心范式：目录以运行时为准、参数一致、写操作安全、异步透明、回显规范化。依据见附录 C。

### 2.1 工具目录与命名

**P1 文档声明"工具以运行时 tools/list 为准"**
- [x] 检查方法：README / server instructions 是否有等价声明；本地文档与运行时 Schema 冲突时的口径
- OpenViking 依据："实际可用工具以所连接服务的 `tools/list` 响应为准"

**P2 工具命名动作导向、能力不混用**
- [x] 检查方法：同一工具不同时承担发现/执行/变更；名称可预测
- 基线：SurveyHub 平台前缀（`fofa_search` / `fofa_host` / `fofa_user_info`）+ 单一职责 ✓

### 2.2 参数 Schema

**P3 同类参数跨工具同名同义**
- [x] 检查方法：跨工具比对 size / page / next / fields 等的命名与语义
- OpenViking 依据：`limit` / `offset` / `node_limit` / `level_limit` 语义区分明确
- 复查（2026-10-15）：命名随各上游 provider 语法，不做跨平台统一——FOFA/Quake 用 `size`、Hunter/DayDayMap 用 `page_size`、ZoomEye 用 `pagesize`，均为上游字段名原样暴露，保证查询语句与官方文档 1:1 对应。同平台内 `size` 的语义按端点区分且描述已显式限定：搜索/翻页为「Results per page」，聚合工具为「Aggregation bucket count per field」；跨平台的 `page` / `fields` / `query` / `start_time` / `end_time` / `retry_mode` / `force_retry` 语义一致。
- 例外：Quake 的 `size` 在搜索端点表示记录数、在聚合端点表示桶数，与上游同名同形，重命名会破坏与官方文档的对应关系，接受为例外并依赖 description 消歧。

**P4 同类工具默认值一致；不一致须有理由**
- [x] 检查方法：比对同平台工具（如 `fofa_search` 与 `fofa_search_next`）的同类参数默认值
- 待复核（2026-10-15 静态初查）：`fofa_search` 默认 `fields=host,ip,port,domain,icp,icon_hash,cert`，`fofa_search_next` 默认 `fields=host,ip,port,domain,title`。如为有意设计，建议在描述或文档注明理由
- 当前实现：两个 MCP 搜索工具及底层函数均使用 `FOFA_CORRELATION_FIELDS`。

**P5 约束显式（ge / le / enum / pattern）**
- [x] 检查方法：检查参数是否用 JSON Schema 约束表达范围
- 基线：`fofa_search.size` 为 `ge=1, le=1000`、`retry_mode` 为枚举 ✓

### 2.3 返回与分页

**P6 返回体量可控**
- [x] 检查方法：是否存在 fields / size / detail 等裁剪参数；大字段（body / cert / banner）有独立上限
- 历史基线：FOFA `size` 上限 1000，请求 `body` 时最多 500 条、`cert` / `banner` 时上游最多 2000 条；这些是记录数，不能证明字符串或 token 体量可控。
- 当前实现：公开 JSON 负载 ≤64 KiB，长数据字符串保留前 4096 字符并标记；裁剪返回 `meta.output` 和 `next_action=refine_query`，不得直接翻页跳过本页省略记录。

**P7 分页有界且游标明确**
- [x] 检查方法：分页上限、游标（`next_id`）是否显式返回并可直接复用
- 基线：`fofa_search_next` 的 `next` 游标 ✓
- 当前实现：`pagination` 统一总量、关系、游标及续页参数；Hunter `arr`、FOFA `size` 已适配，Quake 下界总量和未知游标偏移不推断为完整。顶层及 `meta.execution.completeness` 保持一致。

**P8 MCP 侧上限与上游上限的差异有说明**
- [x] 检查方法：`docs/api/*.md` 是否注明"MCP 单次上限"与"上游文档上限"的差异
- 通过标准：凡本地收紧上游上限之处均须标注两个口径，或说明上游未公开该上限。
- 基线：`fofa_api.md` 已注明（MCP 1000 vs 上游 10,000）✓
- 复查（2026-10-15）：六平台文档均含 MCP 侧上限声明。`fofa` / `quake` / `zoomeye` / `daydaymap` 在头部预算块标注页码与负载上限并给出「上游 API 上限不代表 MCP 可请求上限」；Hunter 两份文档头部标注 CSV 5 MiB / 100 行，本轮补记了搜索端点 `page_size` 的 MCP 上限 `100`（枚举 `10/50/100`）；企业版批量拉取的 `page_size` 枚举 `100/200/500/1000` 本就是上游口径，两处已可区分。

### 2.4 失败与边界语义

**P9 错误可行动**
- [x] 检查方法：missing_key / 认证失败 / 配额不足 / 语法错误是否给出下一步（配置指引、语法重写、参考文档）
- OpenViking 依据：失败显式，边界写入工具描述（如 write 到 skills 子树被拒绝）
- 当前实现：各平台业务码/标志在缓存与执行回执前归一；HTTP 200 的业务失败同样设置 `ok=false` / `isError=true`，不进入成功缓存。
- 复查：SDK 参数校验失败及未知工具也进入统一信封，`error.type` 可直接解析；非法参数值不进入错误文本。

**P10 注解（annotations）准确反映副作用**
- [x] 检查方法：`READ_ONLY_REMOTE_TOOL` / `METERED_READ_ONLY_REMOTE_TOOL` 与实际行为一致
- 注解仅为提示；规范中 `idempotentHint` 只在 `readOnlyHint=false` 时有意义，不能作为只读工具的标准计费标志。配额保护应核对实际请求账本、`meta.metered` 与 `meta.execution`；未知扣费不能用 HTTP 尝试次数代替。
- 复查（2026-10-15）：32 个工具的注解经运行时 `tools/list` 逐一核对。只读远端查询（搜索、聚合、翻页、字段表、user_info、batch_status/pull）为 `readOnlyHint=true`；`batch_create` 为 `readOnlyHint=false`（有远程副作用）；`batch_download` 为 `readOnlyHint=false, destructiveHint=true`（写本地文件并可覆盖）。所有工具 `openWorldHint=true`，符合访问外部服务的事实。计费工具统一使用 `METERED_READ_ONLY_TOOL` 并把配额风险写在 description（`safe_only` / `force_retry` 语义），未把 `idempotentHint` 当作计费标志。

**P11 工具描述写明"何时用 / 何时不用"与工具间路由**
- [x] 检查方法：每个工具 description 是否说明与相邻工具的关系（何时用 `fofa_search_next`、何时用 `fofa_host`）
- OpenViking 依据：find / search、list / tree / glob 的描述互相路由
- 复查（2026-10-15）：32 个工具中 30 个显式引用了同族工具名，形成双向路由（如 `fofa_search` ↔ `fofa_search_next` / `fofa_host` / `fofa_search_stats`，Hunter batch 四件套互相指引，Quake host/service 系列互相指向）。两项不引用同族工具是有意设计：`daydaymap_search` 是本平台唯一工具（无同族可路由），`quake_user_info` 已写明「Use this before searches when permissions or credits are uncertain; do not use it for asset discovery」，即覆盖「何时用 / 何时不用」而无需点名其他工具。

### 2.5 写操作安全（Hunter 批次创建及本地下载已存在副作用）

**P12 覆盖前先读取；局部修改用编辑而非整文件重写**
- OpenViking 依据：write 工具"覆盖前请先用 read 查看当前内容；只改文件局部时优先用 edit"
- 该要求适用于文件编辑业务；本项目导出工具按覆盖策略检查：默认拒绝已有路径，仅 `overwrite=true` 允许替换，无需为下载而读完整旧文件。

**P13 编辑失败时不改变目标（原子性）**
- OpenViking 依据：edit 在 `old_string` 找不到或多处匹配且未开启 `replace_all` 时失败且文件保持不变
- 当前下载实现：同目录临时文件写入/刷盘后原子提交，失败保留旧目标；默认模式同时防止提交时目标被其他调用创建的竞争。

**P14 删除需显式递归标志与确认**
- OpenViking 依据：forget 删除目录需 `recursive=true`
- 当前项目无删除工具，此项不适用。

### 2.6 异步任务

**P15 异步结果返回任务标识与查询方式；不承诺必然产出**
- [x] 检查方法：检查 Hunter 企业版批次（batch → task 查询 → download）类流程
- OpenViking 依据：remember 立即返回 `task_id`，提取结果可能什么都不保留
- 当前创建→状态→拉取/下载闭环保留；创建请求按凭证及文件内容去重，未知结果不盲目重发。跨调用总预算属于客户端编排，不能把提示文本视为服务端已执行的约束。

### 2.7 规范化回显

**P16 响应回显规范化后的输入 / 标识，可直接复用为后续入参**
- [x] 检查方法：`original_query` / `executed_query` / `next` 游标 / 规范化 URI 等
- OpenViking 依据：响应始终回显展开后的 canonical URI，可直接作为工具入参

## 三、复查流程

1. 修改任何平台的限流器后：重跑 `note/check_fofa_rate.py`（FOFA）或按同构脚本验证实际间隔与并发串行化；
2. 按 R7 对照四处文档同步；
3. 对目标平台逐项勾选本表；未通过项登记整改，例外项记录理由与日期；
4. 新平台接入时（如新增数据源），按本表全量过一遍。

## 附录 A：FOFA 缺口清单（2026-10-15 审查结论）

| 编号 | 位置 | 内容 | 风险 | 备注 |
|------|------|------|------|------|
| ① | `fofa.py` `get_fofa_user_info()` | 调用 `request_json` 未传 `rate_limiter` | 低 | 端点不耗查询额度，单次无影响；连续批量调用无频率兜底 |
| ② | `fofa.py` 模块级限流器 | search / host / stats 三个独立实例，无账号级联动 | 低 | 交错并发瞬时合计可超 2/s；正常顺序调用不触发 |
| ③ | `fofa.py` 模块级限流器 | 未传 `namespace` / `identity_provider` | 低 | 多 MCP 进程用同一 KEY 时各自独立节流；Hunter 有 SQLite 跨进程协调 |
| ④ | `docs/api/fofa_api.md` | "本地 MCP 请求控制"曾漏记 search 的 0.6 秒节流 | 文档 | 该信息曾仅在工具 description 与 CHANGELOG；已于 2026-10-15 补记 |

实测证据：`note/check_fofa_rate.py` 输出 search/next `0.601s`、host `1.001s`、stats `5.001s`，3 路并发 search 被串行化（间隔约 0.6s）。

## 附录 B：六平台限流现状盘点（2026-10-15 静态初查）

| 平台 | 限流器 | 间隔 | namespace | 端点覆盖 | 初评 |
|------|--------|------|-----------|----------|------|
| FOFA | 3 个独立 | 0.6 / 1 / 5 秒 | 无 | `user_info` 未覆盖 | ⚠️ 缺口①②③ |
| Quake | 1 个 | 5 秒 | 无 | 全端点（含 user/info、filterable） | ⚠️ 缺口③同构 |
| ZoomEye | 无 | — | — | 0/2（userinfo、search 均未限流） | ⚠️ 待确认是否符合上游要求 |
| DayDayMap | 无 | — | — | 0/1（search 未限流） | ⚠️ 待确认是否符合上游要求 |
| Hunter 个人 | 1 个 | 1 秒 | hunter-personal | 全端点 | ✅ 模式样板 |
| Hunter 企业 | 1 个 | 1 秒 | hunter-enterprise | 全端点 | ✅ 模式样板 |

> ZoomEye / DayDayMap 是否属有意豁免（如上游无明确速率要求、按积分/次数计费）需结合官方文档确认后再定性；静态初查结果，未经运行时验证。

## 附录 C：OpenViking 范式依据

- 仓库：`github.com/volcengine/OpenViking`（核对于 2026-10-15，HEAD `2290984`）
- 关键文档：
  - `docs/zh/guides/06-mcp-integration.md`——MCP 工具表与参数语义；"实际可用工具以所连接服务的 tools/list 响应为准"；write 的 read-before-overwrite、edit 原子性、forget 的 recursive；remember 的 `task_id` 与"结果可能什么都不保留"；canonical URI 回显
  - `docs/zh/agent-integrations/16-capability-reference.md`——服务端工具目录与集成行为
- 运行时核对：本机 openviking MCP 工具 Schema（read 的 `uris` 数组与 `offset` 从 0 开始；search 的 `mode` / `detail` / `max_tokens` / `exclude_uris`；find 的 `read_content`；glob / grep 的 `node_limit`）
