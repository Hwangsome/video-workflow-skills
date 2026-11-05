# 编剧 / 文案：视听脚本交付契约

承接上游策划与核查，将“为什么拍、讲什么”变成“事情如何发生、人物如何说、观众如何理解”。不重新替用户选方向，不将DE等风格组合拆成多片。验收标准：下游无需重新猜故事，就能开始分镜和拍摄准备。

## 六项交付，同一份数据

1. **一句话故事与核心承诺**：谁在什么处境、想做什么、通过什么动作改变局面；观众得到什么信息/体验。非叙事展示可以没有人物冲突，不强凑人物弧线。
2. **完整视听脚本（主交付）**：时间段、场景、人物、可观察动作、画面内容、完整角色台词、旁白、关键声音/停顿、屏幕文字。用“起身准备离开→听到声音停住→低头看刷子”，不用“很无奈”“高级感”等抽象描述代替行为。
3. **叙事与情绪节奏**：每段的叙事功能、信息/情绪起止、揭示与回收。可按开场/推进/揭示/高潮/结尾组织，但氛围/演示内容不强造冲突。
4. **文案备选**：开场、关键卖点表达、结尾各给有实质区别的备选，说明适用条件、与主稿的差异和替换影响。默认各一条足够，不堆同义句；无法成立则说明不适用理由，不发明卖点。备选不进入主稿时长，不自动生成多条完整成片。
5. **制作交接说明**：必须保留、可以调整、必要道具、事实待核实项、简化拍法与对叙事的影响。关键画面属编剧表达，具体景别、机位、运动交给导演/分镜；不另起制片排期或器材清单。
6. **脚本自检**：时长、台词试读、实际操作时间、动作可拍性、承诺兑现与主张依据逐项给检查方式、结果、具体段号和未完成项。文字估算不冒充真实朗读，时间表相加正确不等于动作来得及。

所有配套内容只服务完整视听脚本，不默认写成长篇创作复盘。标题/封面是发布备选，不替代脚本。产品能力未知，明确其影响段落，删改确定性广告承诺；不能把未知主张原样放进口播并只在末尾免责声明。

## 文件和上游关联

在 `outputs/<项目>/<脚本ID>/v01/` 默认生成三个文件：

- `script.json`：该角色的内容事实源，含全部六项、上游策划引用与版本。
- `script.md`：由JSON生成，编导与演员可读。
- `report.html`：同源阅读/打印报告，视听脚本是视觉主体，备选/交接/自检紧随其后。

策划与调研仍是完整三角色交付的上游产物，默认已有方案MD/HTML可保留并链接。仅编剧任务不重复生成上游长报告，也不把上游大段复制成剧本。JSON是这次正式交付，不是仅供内部检索的可选项；旧版MD渲染路径可兼容，但新编剧任务优先用结构化构建。

`asset_id`与`version`标识当前脚本；`planning_ref`含上游`asset_id`、整数`version`、已选`concept_id`和可定位的`source`（相对路径/链接及章节）。这些必须来自实际策划记录；合成示例的引用明确标记为演练，真实任务不能编造已存在的上游ID。没有ID的已有策划，先建立最小上游记录并保留出处，再关联；上游修改后明确当前脚本沿用旧版还是同步新版。段落人物包括画外发声者，台词必须对应明确角色；旁白单列，不挤进角色对白。

## 数据约定与构建

结构示例见 [script.json](../examples/07-script-package/script.json)。执行：

```bash
python3 <技能目录>/scripts/build_script_report.py <项目目录>/script.json
```

默认在JSON同目录生成`script.md`与`report.html`，已有产物不覆盖；确认均为同源派生文件后用`--overwrite`。可用`--planning <上游策划.json>`核对上游asset_id、version与concept_id（上游概念列表为`concepts:[{concept_id:...}]`）。未提供该文件时只检查引用结构，不声称已验证上游记录存在。

核心字段：

- `asset_id, version, title, status, planning_ref, target_duration, story`；story含`one_sentence,promise`。
- `segments`：每项`id,start,end,location,characters,action,visual,dialogue,voiceover,sound,screen_text,beat,emotion`；dialogue是`[{character,text}]`，其他声音/字幕/人物为字符串列表，其余为文字。`claim_ids`列本段涉及主张，没主张为空。
- `claim_checks`：`[{id,statement,source,status,scope}]`，source为可定位依据，status标已支持/待核实/已删除。待核实和已删除的主张不得通过claim_ids进入正式主稿；可在交接中列待补证，补证后修订版本。
- `alternatives`含openings、key_claims、endings三组，元素含`text,when_to_use,difference,impact`；为空时在`alternative_notes`对应类别解释原因。impact说明时间、衔接或依据变化，不能静默替换后仍用原时长。
- `handoff`含must_keep、can_change、props、pending_facts、simplified_version五项字符串列表。无待核实项可为空，其他项至少说明实际决定或不适用理由。
- `self_check`含readthrough、action_timing、shootability、promise_payoff、claims五个对象，各含`status,method,result`；状态明确未执行/已执行/需改等，不能仅填“通过”。

工具校验引用形状、时间连续、字段完整和主张关联，按原数据生成MD/HTML；不能判断台词是否自然、动作是否可拍、来源是否可信、试读是否真的发生。结构通过后仍做人工内容核对和实际浏览器检查。多个版本使用不同目录，保留历史JSON及派生文件，不单改HTML台词。
