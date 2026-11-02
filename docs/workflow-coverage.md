# 流程覆盖与公开版组织

整理日期：2026-11-02。按目录逐项核对的来源是 **15 个维护中的根技能**、**6 个工作区工具技能**和 **1 个生成镜像入口**。应用内冻结的历史快照不作为现行来源；客户端镜像不重复维护。公开仓库保留已有 20 个技能并新增 3 个，共 **23 个**。

这是按能力合并的公开版，不是私有仓库镜像。平台名称 Shopify、Figma、Nx、GTM/GA4 是必要技术语境；公司/客户品牌、真实商店、内部定位与历史业务事实不进入公开包。

| 来源能力/入口 | 公开入口与资料 |
| --- | --- |
| monorepo-app-context | [上下文](../skills/dtc-context/SKILL.md)、[多应用工程](../skills/dtc-monorepo-workflow/SKILL.md) |
| requirements-analysis-agent | [需求梳理](../skills/dtc-requirements-analysis/SKILL.md) |
| product-design-tech-spec | [技术方案](../skills/dtc-technical-design/SKILL.md) |
| component-development-contract | [UI 规格](../skills/dtc-ui-spec/SKILL.md)、[组件契约](../skills/dtc-atomic-decomposition/references/component-contract.md)、[测试](../skills/dtc-component-testing/SKILL.md) |
| figma-delivery-contract | [Figma 数据契约](../skills/dtc-design-evidence/references/figma-data-contract.md)，保留格式语义，不重新批准历史记录 |
| figma-design-spec | [设计取证](../skills/dtc-design-evidence/SKILL.md)、[分端间距](../skills/dtc-ui-spec/references/device-spacing.md)、[视觉验证](../skills/dtc-visual-validation/SKILL.md) |
| shopify-theme-design-development | [实现](../skills/dtc-implementation/SKILL.md)、[主题适配](../skills/dtc-implementation/references/shopify-theme.md)、[浏览器证据](../skills/dtc-component-testing/references/browser-evidence.md) |
| shopify-live-theme-sync | [Live 回填](../skills/dtc-delivery/references/shopify-live-sync.md) |
| shopify-draft-delivery | [Draft 交付](../skills/dtc-delivery/references/shopify-draft.md)、[生产候选](../skills/dtc-delivery/references/production-candidate.md) |
| tracking-scene-workflow | [追踪场景](../skills/dtc-data-tracking/SKILL.md)、[GTM/GA4 保护与配置](../skills/dtc-data-tracking/references/gtm-ga4.md) |
| operations-review | [业务 Review](../skills/dtc-operations-review/SKILL.md)、[分析验收](../skills/dtc-operations-review/references/analytics.md) |
| web-interface-audit | [Web 界面静态审计](../skills/dtc-web-interface-audit/SKILL.md) |
| requirement-change-log | [证据记录](../skills/dtc-evidence-log/SKILL.md)、[记录与恢复](../skills/dtc-evidence-log/references/records-and-handoff.md) |
| shopify-theme-self-iteration | [流程复盘](../skills/dtc-workflow-review/SKILL.md) |
| monitor-ci 及其生成镜像 | [CI 跟进](../skills/dtc-ci-monitor/SKILL.md)，不携带宿主专用工具名、模型选择或自愈脚本 |
| nx-workspace / nx-run-tasks / nx-generate / nx-plugins / nx-import / link-workspace-packages | [多应用工程](../skills/dtc-monorepo-workflow/SKILL.md) 与 [Nx 适配](../skills/dtc-monorepo-workflow/references/nx.md)，归纳能力，未打包供应商技能副本 |

机器索引为 [workflow-coverage.json](workflow-coverage.json)。页拆分、原子拆分、异常处理、录屏、隐私、优化等既有公开技能继续保留；相同规则放一处，通过引用复用。

## 被替换的依赖

- 私有 context resolver、merge/reconcile、任务登记、追踪配置、候选检查和日志工具：替换为清楚的输入/输出、停止条件和目标项目适配义务，不保留无法执行的命令。
- 业务实例、真实设计/商品/报表 ID、内部文档、固定视口与人物偏好：删除或改为明确的合成示例/当前项目配置。
- 历史上传授权、固定 reviewer、自动更新 skill 的长期授权、上线状态：删除，改为当前任务证据和授权。
- 原始日志、截图、环境文件、依赖、源码包、冻结迁移及内部哈希清单：未导入。

源文件级清点和私有匹配词用于本地核对，不加入公开仓库。公开检查只证明本次检查范围；不声称私有执行器已开源、所有平台已验证或历史 Git 内容已被擦除。
