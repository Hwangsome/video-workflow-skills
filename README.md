# 电商短视频编导 / 脚本策划

统一使用 [`ecommerce-video-director/SKILL.md`](ecommerce-video-director/SKILL.md)。该文件夹是一个可独立使用的技能，支持创意方向、演示/口播/剧情脚本、局部改稿与内容资产沉淀。

默认交互：首次只说“写一个脚本”且方向未定时，先交具体编号创意、推荐和取舍，等用户选择再展开。已选、已指定方向或明确说“你来定，直接写”时直接完成；局部改稿不重新选题。执行契约见 [方向选择能力卡](ecommerce-video-director/references/direction-selection.md)。

- 什么时候用、如何选择流程和使用边界：技能入口。
- 创意机制与剧情方法：`references/creative-methods.md`。
- 分镜与执行交付：`references/deliverables.md`。
- 分类型编导、叙事、制作与评审：`references/direction-playbooks.md`、`story-engine.md`、`production.md`、`review.md`。
- 五种方向的完整脚本练习：`references/worked-example.md`。
- 事实、创意机制、复盘资产：`references/asset-workflow.md`。
- 原仓库25张能力卡的改编去向及官方行业参考：`references/source-map.md`。
- 本地资产工具：`scripts/asset_store.py`，提供新版本保存、品牌内搜索、派生索引与时间线检查，仅依赖Python 3.10+标准库。
- 行为回归场景：`evals/scenarios.json`，提供验收预期，不代表已执行模型测试。

例如：“用这个技能，根据商品资料给我几个不同的创意方向，我选定后再展开30秒脚本。”也可明确授权：“方向你来定，直接写一条单人可拍的30秒脚本，并保存待验证资产。”

原 `script-director/` 和 `save-the-cat-screenwriting/` 已由统一技能替代，来源仍可在[原始提交 cbbc441](https://github.com/Hwangsome/video-workflow-skills/tree/cbbc44115b8f4d07e2f57acb42bc31823b7073e0)中查阅。安装或使用完整的 `ecommerce-video-director/` 文件夹即可，无需同时安装原有两个技能。本仓库不包含实际项目的 `outputs/` 和 `content-assets/`，技能内的示例属于虚构练习。
