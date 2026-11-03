# 收录数据与接口契约

## 输入

脚本接受 JSON 数组或只含 `entries` 字段的对象。`dryRun` 由命令模式决定，不能通过输入文件开启写入。服务端请求为 `{"dryRun":true,"entries":[...]}`；不传 dryRun 也只做预检。

| 字段 | 要求 |
| --- | --- |
| `name` | 必填，GitHub `owner/repo`；owner ≤39、repo ≤100，整体 ≤140 字符 |
| `url` | 必填，与 name 对应的 HTTPS github.com 仓库 URL，≤300 字符 |
| `domain` | 必填，下表中的一级领域 |
| `sub` | 必填，已有或准确描述用途的小写字母/数字/连字符 slug，≤80 字符 |
| `one_liner` | 必填，1–240 字符；简短说明项目是什么及核心用途 |
| `public.scenario` | 必填，1–4000 字符；面向访客的适用场景 |
| `public.diff` | 可选，≤4000 字符；有依据的差异，不编造比较 |
| `highlights` | 可选，≤4000 字符；具体能力，允许换行 |
| `scenario` | 可选，≤8000 字符；策展内部判断，公开 API 不直接返回 |
| `domainCn` / `lang` | 可选，各 ≤80 字符；领域中文名可由服务端补齐 |
| `stars` | 可选，≤32 字符的非负数字串，可带小数与 k/m；数值不得超过 10 亿 |
| `pushed` | 可选，≤40 字符；ISO 日期/时间或 YYYY-MM；未知可省略 |
| `tags` | 可选，最多 20 个不重复的非空字符串，各 ≤80 字符 |

未知字段、非法类型、控制字符或超长值会被拒绝；服务端不静默截断。服务端会修剪字符串首尾空白，正文允许换行/制表符；客户端提前拒绝 name/domain/sub 身份字段中的首尾空白，避免回执匹配含糊。整批最多 20 条、UTF-8 JSON 请求体不超过 128 KiB。上传脚本先检查基本形状，字段语义以服务端校验为准。

| domain | 含义 |
| --- | --- |
| frontend | 前端 |
| backend | 后端 |
| ai-agents | AI 与 Agent |
| design | 设计 |
| devtools | 开发工具 |
| mobile | 移动端 |
| data | 数据 |
| media | 多媒体 |
| systems | 系统与底层 |
| app | 应用与产品 |
| resource | 资源与导航 |

子方向优先取目标站 `/api/catalog/stats` 的现有值；确需新增时用简明 slug。tags 以领域、子方向和有检索价值的技术/用途为主。多领域分别写完整条目，同仓 name 大小写、url、lang、stars、pushed 保持一致；不要为增加曝光而重复分类。

## 写入语义

API：`POST /api/ingest/projects`。客户端通过 `NB_PROJECT_INGEST_TOKEN` 提供专用 Bearer 凭证，服务端使用 `CATALOG_INGEST_TOKEN` 校验。服务端未配置时拒绝写入；管理员 Cookie 与本地 bypass 均不能替代此凭证。

客户端每次请求都发送 `User-Agent: nb-project-upload/1.0` 与 `Accept: application/json`，明确真实产品身份并兼容站点 HTTP 入口对客户端标识的要求。

一批写入事务化；任一语句失败整批回滚。同仓身份不区分大小写，同仓/领域/子方向为条目身份。重复提交返回 `exists`，不覆盖现有条目；新领域可以追加到已有仓库。已有元数据和评分不被本次上传替换，新仓初始评分由服务端计算。

响应示意（合成）：

```json
{
  "ok": true,
  "dryRun": false,
  "summary": {"projectsCreated": 1, "entriesCreated": 1, "entriesSkipped": 0},
  "items": [{"name": "example-org/sample-tool", "domain": "devtools", "sub": "cli", "status": "created"}]
}
```

dry-run 的待新增状态为 `would_create`，数量为预计值。apply 的 `created` 和数量来自实际写入结果。两种模式都用 `exists` 表示已有条目。Python 脚本额外输出 `target` 与 `verified`；后者只在 apply 后全部条目回读存在时为 true。

## 配置和证据边界

- `NB_PROJECT_URL`：目标站 origin，不含路径、查询参数或凭据。
- `NB_PROJECT_INGEST_TOKEN`：仅环境/受控密钥源注入；不支持 token 命令参数。使用站点维护者配置的专用随机凭证，建议至少 32 字符，不自行改用其他平台 token。
- 服务端部署与 secret 配置由目标站维护者完成，本 Skill 不操作 Cloudflare。
- 预检成功只能证明契约与当前存在性；写入确认、受保护回读、公开 API 可读和浏览器展示分别记录。
- D1 中新增条目不自动写回仓库的策展 Markdown；需要 Git 备份时由目标项目另行使用现有导出流程。
## 候选草稿（独立于旧 entries 数组）

```json
{
  "expectedVersion": 1,
  "draft": {
    "title": "示例资源名称",
    "one_liner": "以明确任务为入口组织工具与文档，帮助开发者复用已有的工程操作流程。",
    "public": {"scenario": "团队需要把重复工程操作整理为可审阅步骤时使用。", "diff": ""},
    "highlights": "显式任务边界；提供可复核的步骤说明",
    "domain": "ai-agents", "sub": "agent-skill",
    "tags": ["ai-agents", "agent-skill", "skill/coding"],
    "evidence": [{"url": "https://example.invalid/official-doc", "excerpt": "替换成真实官方来源的准确摘录"}]
  }
}
```

上例仅说明结构，不得直接提交为真实资源。先 GET 当前候选获得 `expectedVersion`。API 保存后 version 加 1；只有管理员审核可以发布。简介上限 240 字符、场景/差异/亮点各 4000；标签最多 20 个，证据 1–20 条。建议长度和语言为编辑提示，不能凭长度判断语义质量。
