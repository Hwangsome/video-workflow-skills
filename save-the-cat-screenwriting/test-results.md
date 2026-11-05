# 阶段 4 压力测试结果 — save-the-cat-screenwriting

- **测试日期**: 2026-11-05
- **测试方式**: 独立 sub-agent 盲测（干净上下文，未提供 `type` / `expected_behavior` / `notes`，只给 SKILL.md + 请求列表）
- **用例集**: `test-prompts.json`（10 条：5 should_trigger / 3 should_not_trigger / 2 edge_case）
- **产物校验**: `validate_skill_pack.py` → 0 errors, 0 warnings

## 通过率

| 指标 | 结果 |
|---|---|
| 总用例 | 10 |
| 通过 | **10** |
| 通过率 | **100%** |
| 诱饵容错 | 3/3（容错要求 0） |
| 路由精度（命中正确能力卡/参考文件） | 7/7 条应触发用例全部命中 |

## 逐条结果

| # | 用例 id | 预期 | 盲测判定 | 结论 |
|---|---|---|---|---|
| 1 | should-trigger-01 | 激活 → bad-idea-warnings | yes → bad-idea-warnings.md | ✅ |
| 2 | should-trigger-02 | 激活 → beat-sheet-bs2 / three-structural-ailments | yes → beat-sheet-bs2.md | ✅ |
| 3 | should-trigger-03 | 激活 → story-diagnosis-checklist | yes → story-diagnosis-checklist.md | ✅ |
| 4 | should-trigger-04 | 激活 → beat-sheet-bs2 | yes → beat-sheet-bs2.md | ✅ |
| 5 | should-trigger-05 | 激活 → protagonist-antagonist | yes → protagonist-antagonist.md | ✅ |
| 6 | should-not-trigger-01 | 不激活（技术查询） | no → none | ✅ |
| 7 | should-not-trigger-02 | 不激活（合规文本） | no → none | ✅ |
| 8 | should-not-trigger-03 | 不激活（艺术价值/影评） | no → none | ✅ |
| 9 | edge-01 | 激活入口 → glossary.md（不加载能力卡） | yes → references/glossary.md | ✅ |
| 10 | edge-02 | 激活 + 拒承诺 | yes → beat-sheet-bs2.md，并说明拒绝"保证票房" | ✅ |

## 观察与说明

1. **case 2 的判定正确但路由取了"结构"而非"归病"**：请求里同时含"中段全废戏"（枝蔓）与"结构塌了"（节拍缺格）。按 SKILL.md 的"一次只加载 1 张卡"规则取 `beat-sheet-bs2` 合理；实际使用时若用户在追问"到底是哪种病"，应补 `three-structural-ailments`。已在 cards 的 `also_read` 中互相指向，无需改 trigger。
2. **case 10 是唯一涉及 stop_conditions 的用例**：盲测者主动引用了"拒绝保证"这条边界，说明 SKILL.md 的"边界与判停"段落在真实调用路径上可见、可执行，不是装饰。
3. **跨 skill 混淆测试在 single 模式下退化为跨"目标文件"混淆**：single 只产 1 个入口，同书能力不互相抢调用；真正的误触发风险来自"电影/写作"字面诱饵（case 8）与"写作但文体相反"（case 7），两者均未被误触发。

## 结论

**通过，无需回炉。** 产物可进入阶段 5 交付。若后续改成 pack（7 个晋级 Skill + router），需补一轮 pack 级盲测：把 8 个入口的 name+description 一起交给 sub-agent 做"该激活哪一个"的选择题。
