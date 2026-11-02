# Git 与协作记录

先读取目标仓库当前贡献规则及默认分支；以下是可采用的工作流，不假设所有项目都使用相同 Issue/MR 门禁。

## 分支和工作区

核对 `git status --short`、当前分支及 upstream；已有改动归属不明时保留并隔离本次内容。整仓审计可读 `git worktree list --porcelain` 与 `git for-each-ref --format='%(refname:short)|%(upstream:short)' refs/heads`，必要时核对分支 remote/merge 配置，避免上游引用已消失而漏报。

创建开发分支/工作树时显式 `--no-track`，例如 `git switch --no-track -c <branch> <base>`。默认分支是比较基线，不应成为开发分支的 upstream。发现错误跟踪先报告，停止依赖它的 pull/push；只在授权范围修正配置，不 reset/rebase 来掩盖问题。无 upstream 或 gone 不自动绑定默认分支。

仅在当前任务已授权推送时，用明确远端及开发分支 refspec 推送。按路径暂存并审阅 staged diff，避免把其他应用、凭据、原始证据或并行任务改动带入。

## Issue、PR/MR

仓库要求 Issue First 时，先查重并绑定有负责人的 Issue。记录背景、范围、依赖、可验证验收和文档；已有描述的进展使用追加评论，不覆盖原始要求。评论或外部写入需有用户请求或所调用工作流的明确授权。

跨仓任务区分总目标和本仓工作项，并使用平台实际支持的关联。新分支可含工作项编号，已有 PR/MR 分支保持连续性。描述提供具体背景、变更、已推送文档链接、验证、风险和未验收层级；回读目标分支及关联关系。

若目标 GitLab 项目要求机器可读绑定，可分别独立成行使用 `Work Item: <完整 URL>` 与 `Root Issue: <完整 URL>`，每项一次，并按其实际规则指定 reviewer、核验 related merge requests。GitHub 或其他仓库沿用自己的机制；本仓库不提供服务端门禁，也不强制私有平台的 URL、审批人或 CI 作业名。
