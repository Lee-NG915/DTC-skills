# 数据契约 v0.2

这是数据结构约定，不是已经实现的自动提取器或 JSON Schema 校验器。提取时保持字段稳定；新增不兼容结构需要升级 schema_version。

## 顶层结构

| 字段 | 内容 |
| --- | --- |
| schema_version / spec_id / revision / previous_revision | 数据格式版本、设计区域稳定标识、本次和上次提取版本 |
| source | file_key、url、branch、figma_version、retrieved_at；不可取得的值用 null |
| frames[] | 节点 ID、链接、设计画板尺寸、角色 desktop/mobile/unknown、状态、变量 mode；画板尺寸不等于已确认浏览器断点 |
| evidence[] | id、kind、原始文件路径、内容哈希（可取得时）、工具/接口、提取时间、范围、是否截断；不保存凭证 |
| components[] | 稳定 id、建议名称、责任、parent_id、映射 node_ids、原子/组合/业务类型、复用边界、确认状态 |
| nodes[] | 实际节点 id、parent_id、类型、名称、链接、对应组件、frame、visibility、extraction_status、缺失项/排除理由 |
| properties[] | 下述逐属性行；混合文本和实例差异独立记录 |
| proposals[] | CSS/布局映射、响应式策略、组件接口、空值规则、有限变体建议、理由、相关 row_ids、Review 状态 |
| asset_reviews[] | 素材源尺寸/可见边界/显示目标、质量疑点和证据、影响、解决/补交要求、负责人及状态 |
| decisions[] | 业务与期限约束、候选方案、成本与风险、推荐条件、开发者实际选定方案及确认记录 |
| visual_targets[] / implementation_targets[] | 经确认的视觉基线及环境；选中方案的实现/资源目标，与原始属性差异的理由及 decision_id |
| assertions[] | 下述验收契约，不能把未运行的断言标为通过 |
| review / coverage / changes[] | 确认记录、覆盖统计、与上版逐行差异 |

## 每一个属性都带来源

每行包含：`id`、`component_id`、`node_id`、`frame_id`、`state`、`property`、`value`、`unit`、`origin`、`evidence_refs`、`source_path`、`derivation`、`review`。

- `origin`：`figma-read`（结构化原始节点属性读取）、`context-reference`（工具生成的参考代码，待原始属性核对）、`user-supplied`（用户粘贴文本）、`screenshot-annotation`（图中明确标注）、`derived`（有公式的换算）、`estimated`（视觉估计）、`unknown`、`not-applicable`。建议实现放 proposals，不混入设计事实。工具成功、JSON 可解析不代表属性来源正确或完整。
- `value: null` 表示未知/不适用，结合 origin 和理由判断；0、false、空字符串保留原义。
- `evidence_refs` 指向证据清单；`source_path` 精确到返回字段/文本分段，不能只写“来自 Figma”。
- `derivation` 包括 input row IDs、公式、适用条件/坐标系；换算另外生成一行，不覆盖原始值。
- `review`：pending / approved / needs-clarification / rejected，附用户确实确认的记录。来源可信度和是否批准是两件事。
- 字体、渐变或变量等复杂值可使用对象，但保持原始单位与结构，不将对象压成丢失信息的字符串。

字段形状示例（用户提供信息，不是假造 Figma 提取）：

```json
{
  "id": "example-hero.title.font-size.desktop",
  "component_id": "page-example-hero.title",
  "node_id": null,
  "frame_id": null,
  "state": "default",
  "property": "typography.fontSize",
  "value": 40,
  "unit": "px",
  "origin": "user-supplied",
  "evidence_refs": ["user-typography-example"],
  "source_path": "user message: font-size",
  "derivation": null,
  "review": {"status": "pending"}
}
```

## 容易测错的字段

### 文字

- 保留文本内容、大小写属性、字体 family/style name、weight、italic、font size、line-height 的原始模式和单位、letter-spacing、对齐、装饰、段落间距、文本框 resize/截断/行数约束。
- 混合文字按字符范围读取样式；不能只读取第一个字符并代表整段。变体字体轴与字体可用性也需要记录。
- `SemiBold` 是字体样式名称，不是合法 CSS `font-style` 值。数值 weight 与斜体状态单独确认，不凭名字无条件推导。
- `line-height: 100%` 保留百分比。字号 40px 时可另记条件换算 40px；不能据此把文本框高度 44 改成 40。
- `leading-trim: NONE` 保留原始设计语义，不自动写进生产 CSS。所用 Figma 接口未暴露字段时记录 unknown。
- 渐变记录类型、色标（颜色空间/alpha/位置）、变换/方向、节点 opacity，而不只截取一个绿色色号。
- 变量记录绑定 ID/名称、collection、mode、alias 和当前 resolved value；有绑定不等于所有 mode 值都相同。未绑定不等于开发必须创建 token。

### 尺寸、间距和布局

- 分开记录局部 size、绝对包围盒、实际绘制边界、坐标变换。阴影/描边/旋转可令它们不同，不用截图显示像素替换设计单位。
- Auto Layout：方向、padding 四边、itemSpacing、对齐、wrap、sizing（fixed/hug/fill）、min/max、布局定位。约束值和当前呈现尺寸都保留。
- 额外距离记录 from/to 节点及各自边（或 baseline）、同一参照坐标系、距离、计算方法。例如 A.bottom→B.top 与 parent.top→A.top 是不同数据。
- 只有同坐标系、无未处理变换时，才可用 `B.y - (A.y + A.height)` 推导垂直 gap。旋转/遮罩等需说明测量边界。
- 测得空白不是 CSS margin/padding 的证明。居中 1200 宽容器与左右 360 的观测，不意味着要硬编码 margin 360。
- 间距必须按设备与布局变体分行：Desktop、Mobile，以及同一设备下的列数/卡片宽度变体（如 1 列/2 列）各自读取。相邻元素对（价格与划线价、标题与卖点、卖点与优惠码等）逐对审查，值相同也要写“已分别读取且一致”；不得把一端间距填到另一端，也不得用常见 token 或参考组件猜测。
- 设计固定宽度不直接等于 CSS 固定宽度或 max-width；需要结合 sizing、父级、其他画板和开发决策。
- 图像的边框盒、可见裁切和素材内留白分别记录。只把素材作为图片实现是建议边界，不能掩盖其本应可编辑的文字。

## 方案决策与目标

`decisions[]` 每项至少包含 id、component_ids、source_node_ids、已确认的 business_requirements、deadline/assumptions、候选 options（资源边界、编辑能力、开发/设计等待/测试/维护成本、风险）、recommended_option_id、recommendation_conditions、selected_option_id、status、实际确认记录。未确认时 selected_option_id 为 null，不默认使用推荐项。

`visual_targets[]` 记录视觉参考的 evidence_id/version、区域、目标视口/状态、构图/清晰度要求及 review；`implementation_targets[]` 记录 decision_id、相关 property/asset IDs、目标值和单位、与原始值的差异理由/依据、Review 状态。目标可为布局行为或资产契约，不必都是数字。原始 properties 保留不改；资源质量问题的修正不能静默替换证据。

确认扁平化后 components 保留 source_node_ids 和 asset_id 映射；内部不再要求 DOM 属性断言。coverage 分别记录节点取证覆盖及选定方案资产/接口/验收覆盖。旧 v0.1 数据仍是历史草稿，不因新增字段自动升级或批准。

## 验收契约

每条 assertion 包含 `id`、`row_ids`、`component_id`、`viewport`、`state`、`fixture`、`implementation_selector`、`measurement`、`expected`、`tolerance`、`priority`、`review_status`。

`expected` 引用已批准的 visual_target / implementation_target ID（关联 decision_id）；经核对并明确采用的原始/派生 row ID 也可使用，不能自动把所有节点尺寸变为生产断言。截图估计不能作为精确数值验收基线，除非用户明确接受其误差及用途。tolerance 按测量类型确认，不能默认所有差异容忍 2px 或全部零容差；未确认就留空并说明不可用于自动判定。

整图断言比较指定区域的视觉、内容完整性、清晰度、显示比例/裁切及外部布局，不要求内部字重/字体 DOM 值。图文分离增加实际字体/文字位置和长文案双端测试。视觉一致与业务编辑能力都需满足，不能互相替代。

运行结果另存 `test-results.json`：spec revision、实现版本、浏览器/视口/DPR、字体加载、数据状态、参数变化序列、实际值、差值、证据、pass/fail/blocked/not-run。缺少字体、selector、数据或环境时不能记 pass。
