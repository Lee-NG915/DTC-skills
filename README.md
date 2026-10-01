# DTC-skills

面向 DTC/Web 开发和技术分享的可组合技能仓库。每个环节独立使用；已有有效产物直接复用，不要求从需求到发布串行执行全部技能。

## 结构与格式

```text
DTC-skills/
├── LICENSE                 # 保留既有 MIT 许可
├── README.md
├── .env.example            # 当前无必需变量
├── .gitignore
├── schemas/
│   └── skill.schema.json   # 本仓库扩展元数据契约
├── targets/
│   ├── README.md           # 目标项目适配档案契约
│   └── <target>.md         # 项目技术栈、边界与验证能力
├── scripts/
│   └── validate.rb         # 本地结构、引用及元数据一致性校验
└── skills/
    ├── catalog.json        # 轻量索引
    └── <skill-name>/
        ├── SKILL.md        # 标准入口，包含 name / description
        ├── skill.json      # 本仓库扩展：版本、输入、输出、关联技能
        ├── references/     # 有详细分支时再创建
        ├── scripts/        # 有实际可执行逻辑时再创建
        └── assets/         # 有模板、fixture 等资源时再创建
```

遵循 [Agent Skills 目录规范](https://agentskills.io/specification)。标准识别入口是 `SKILL.md`；`skill.json` 不是该标准要求的文件，是本仓库自定义扩展，其结构由 `schemas/skill.schema.json` 描述。`inputs` / `outputs` 是自然语言交接契约，不是可调用 API 参数；`relatedSkills` 表示按需协作，不是必跑依赖。当前没有调度器、环境加载器或远端执行器。

## 开发环节

| Skill | 何时使用 | 交接内容 |
| --- | --- | --- |
| [dtc-ci-monitor](skills/dtc-ci-monitor/SKILL.md) | 检查或跟进指定提交的 CI，定位失败并审阅自动修复建议；按授权执行有界重试，不自动推送或修改服务端设置。 | 终态或最后观察状态、失败分类及修复评估、候选绑定的验证记录 |
| [dtc-context](skills/dtc-context/SKILL.md) | 建立产品、仓库、目标环境、范围和授权上下文，避免串用错误项目或历史身份。 | 最小上下文摘要（可复用现有任务记录）、目标、授权及待确认项 |
| [dtc-data-tracking](skills/dtc-data-tracking/SKILL.md) | 为埋点、许可、分析映射和监控变化选择场景范围，保证事件语义、排除条件、降级行为和下游边界可验证。 | tracking contract、scenario scope、unit/browser results、downstream acceptance gaps |
| [dtc-delivery](skills/dtc-delivery/SKILL.md) | 生成跨环境可交付候选，核对构建身份、目标漂移、写入/回读和发布交接。 | candidate、delivery plan、write/readback receipt、handoff status |
| [dtc-design-evidence](skills/dtc-design-evidence/SKILL.md) | 从设计稿、运行页面、旧组件和配置中提取可追溯证据，明确组件映射、素材边界、响应式差异和未知项。 | source map、design facts、implementation decisions、visual and behavior targets |
| [dtc-page-decomposition](skills/dtc-page-decomposition/SKILL.md) | 将页面拆成区域、组合组件、页面状态和数据边界。 | 页面组件树、区域图、状态矩阵 |
| [dtc-atomic-decomposition](skills/dtc-atomic-decomposition/SKILL.md) | 将复杂组件拆成原子组件、组合组件和适配边界。 | 原子组件树、组件契约、变体矩阵 |
| [dtc-technical-design](skills/dtc-technical-design/SKILL.md) | 评估复用、扩展、新建及技术边界。 | 技术契约、方案决定与风险 |
| [dtc-ui-spec](skills/dtc-ui-spec/SKILL.md) | 将适用 UI 参数与行为/配置契约冻结为逐项规格。 | UI 规格、Review、验证断言 |
| [dtc-evidence-log](skills/dtc-evidence-log/SKILL.md) | 维护跨需求、设计、实现、测试、交付和复盘的一份可追溯记录，保存候选身份、失败闭环和证据取回方式。 | timeline、evidence manifest、handoff summary、open issues |
| [dtc-exception-handling](skills/dtc-exception-handling/SKILL.md) | 处理目标不明、需求变化、证据缺失、动态数据异常、远端漂移、CI 失败、部分写入和紧急故障等特殊流程。 | decision record、stop/retry condition、recovery plan、handoff boundary |
| [dtc-implementation](skills/dtc-implementation/SKILL.md) | 消费页面/组件契约，实现跨技术栈的组合、状态、资源、运行时入口和真实预览。 | source changes、build output、preview fixtures、implementation notes |
| [dtc-component-testing](skills/dtc-component-testing/SKILL.md) | 为页面和组件设计分层测试与状态 fixture。 | 测试矩阵、场景、结果和缺口 |
| [dtc-visual-validation](skills/dtc-visual-validation/SKILL.md) | 用同视口、内容和状态校验视觉一致性。 | 视觉对照、差异和状态 |
| [dtc-privacy-redaction](skills/dtc-privacy-redaction/SKILL.md) | 在日志、截图、代码片段、录屏和公开示例进入分享仓库前擦除秘密、个人信息、内部定位和商业敏感信息。 | 脱敏素材、redaction-report.md、脱敏后哈希（可选） |
| [dtc-recording-analysis](skills/dtc-recording-analysis/SKILL.md) | 把脱敏后的真实开发证据整理成适合小红书等公开渠道的录屏、旁白、字幕和发布前检查。 | recording outline、shot list、voiceover/captions、publication checklist |
| [dtc-requirements-analysis](skills/dtc-requirements-analysis/SKILL.md) | 把想法、会议材料、缺陷或配置请求整理成范围清晰、可验收、可交接的需求记录。 | 需求记录、AC 验收标准、待确认项、下游影响 |
| [dtc-scoped-validation](skills/dtc-scoped-validation/SKILL.md) | 根据真实 diff、消费者和失败代价选择最小可靠验证范围，分别记录逻辑、视觉、构建、远端和业务验收层级。 | validation plan、commands and results、untested scope、failure loop |
| [dtc-workflow-review](skills/dtc-workflow-review/SKILL.md) | 在预览交接后或用户要求复盘时评估流程问题，区分执行遗漏、规则不足、需求变化与证据缺口，提出有边界的技能改进。 | 经验分类和置信度、改进建议与适用边界、后续观察条件 |
| [dtc-optimization](skills/dtc-optimization/SKILL.md) | 基于测量优化组件性能、架构、可维护性和反馈回路。 | 优化假设、前后测量、回归结果、后续观察 |

## 跨技术栈原则

技能只规定问题边界、证据、输入输出和验收语义，不规定 React、Vue、Svelte、原生视图、服务端模板、CSS-in-JS 或某个构建器。`dtc-context/references/stack-adapter.md` 用项目实际能力映射组件输入、生命周期、预览、测试、构建和视觉对照。没有 DOM 时使用平台等价的布局/绘制/状态证据；没有 Storybook 时使用已有 preview/harness；没有自动化工具时保留可复现手工步骤和缺口。

## 目标项目适配

通用 skill 不复制到目标项目中。目标项目在根目录提供 `.dtc/target-profile.md`
软链，指向本仓库 `targets/<target>.md`；DTC skills 通过 `dtc-context` 先读取档案，
再把技术栈、领域边界、命令、预览能力和交付限制交给后续阶段。目标项目可以把
适配档案作为本地分支的一部分修改，修改会直接作用于本地 DTC-skills 源文件。

目标档案只描述能力和规则，不授予远端写入、发布、发消息或业务验收权限。目标项目
自身的 Hard Rules 优先于档案；没有档案时保留通用流程并显式记录技术栈和命令未知。

## 如何组合

- 新页面/组件：context → requirements-analysis → design-evidence → page-decomposition → atomic-decomposition → technical-design → ui-spec → implementation → component-testing → visual-validation → scoped-validation → optimization → delivery。页面拆分、原子拆分和 UI 规格是三个不同产物；首次实现必须先冻结适用 UI 规格，视觉验证不能被参数或功能测试替代。
- 局部样式：context → ui-spec（增量）→ implementation → visual-validation → component-testing → scoped-validation；只补改动影响的规格、视觉区域和状态。
- 埋点：context → data-tracking（先定义场景与 Review）→ implementation → scoped-validation → data-tracking（下游验收）。
- CI 跟进：ci-monitor；失败时接 exception-handling，修复后复核对应提交的新 attempt。
- 优化：component-testing/visual-validation → optimization → scoped-validation；任何优化都要有前后测量和回归结果。
- 复盘与内容：evidence-log → workflow-review → privacy-redaction → recording-analysis。

以上省略 `dtc-` 前缀。evidence-log 贯穿阶段，exception-handling 按异常触发。privacy-redaction 用于复制、交接或公开材料，不是每次本地编码都要重跑的门禁。技能明确的授权边界仍须遵守；已有授权不重复申请。

## 使用与扩展

在支持技能的客户端中，将所需目录放入该客户端支持的技能位置，或让助手读取指定 `skills/<name>/SKILL.md`。客户端扫描目录的行为不同，不假设 clone 后自动安装。

单独使用一个技能时，只需提供它所需的已有输入；引用的协作技能未安装时说明缺口，不假装已调用。经常组合使用时一起安装相关目录，保持同级相对路径。纯 UI 工具、平台 CLI、真实部署权限由调用环境提供。

新增其他场景时创建独立 `skills/<name>/`，添加必需入口和元数据，登记 catalog；不需要沿用 `dtc-` 前缀，也不预建空目录。共性语义放负责该环节的技能，平台特例放该技能的 references，并在入口注明何时读取；不新增主题同步、商家后台或单一框架专用流程到通用目录。版本变更同步 `skill.json`，关联索引只记录位置，避免重复维护依赖图。

运行 `ruby scripts/validate.rb` 检查结构、字段约束、目录/元数据命名、目录索引和相对链接；无需安装项目依赖。这是本仓库轻量校验，不替代完整 JSON Schema 引擎或真实任务行为验证。

## 公开范围

保留流程判断，移除真实店铺、客户资料、凭据、私有链接和业务案例身份。原始日志与录屏不进入分享仓库；录屏需检查画面、声音、字幕、缩略图与通知。秘密扫描不能证明全部内容安全，发布前仍需检查实际展示材料。

当前是从开发实践抽象的第一版技能，尚未在其他项目完成端到端验证。仓库只提供技能指令和结构检查，没有复制某个项目的构建、上传、部署或 CI 自动修复执行器；这些由具体技术栈适配器提供。
