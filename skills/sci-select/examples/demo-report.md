# sci-select 候选期刊报告

**方向总结**：地下水硝酸盐参考条件与水文地球化学；状态分离是研究框架，统计方法用于不确定性分析。
**论文画像**：研究对象=浅层含水层硝酸盐状态；核心问题=状态分离如何改变参考浓度估计；贡献类型=应用型方法框架
**使用边界**：以下结果用于发现值得人工复核的候选期刊；不评价稿件水平，不预测录用概率，也不声称存在唯一最优期刊。

## 快速决策表

| 期刊 | 候选状态 | 方向证据 | 期刊层级 | IF | 2025中科院 | 2026新锐 | 收录 | OA/APC | 审稿速度 | 数据状态 |
|---|---|---|---|---:|---|---|---|---|---|---|
| Journal of Hydrology | 优先核验 | 强 | 中位 | - | - | - | SCIE | - | - | 相似论文 / 指标待实时查询 |
| Hydrogeology Journal | 优先核验 | 强 | 中位 | - | - | - | SCIE | - | - | 相似论文 / 指标待实时查询 |
| Applied Geochemistry | 可选 | 中 | 中位 | - | - | - | SCIE | - | - | 相似论文 / scope待核验 |
| Water Research | 可选 | 中 | 高位 | - | - | - | SCIE | - | - | 相似论文 / scope待核验 |

## 1. Journal of Hydrology｜中位｜优先核验
**匹配理由**：近年相似论文先例 4 篇 / 覆盖 2 组检索；覆盖地下水质量与含水层过程
**近年发表先例**：列出检索获得的真实题名与年份
**官网 scope**：待核验

## 2. Hydrogeology Journal｜中位｜优先核验
**匹配理由**：近年相似论文先例 3 篇 / 覆盖 2 组检索；受众与含水层参考条件研究一致
**官网 scope**：待核验

## 3. Applied Geochemistry｜中位｜可选
**匹配理由**：水文地球化学方向相关，但需要确认论文是否强调地球化学过程而不只是阈值估计
**官网 scope**：待核验

## 4. Water Research｜高位｜可选
**匹配理由**：存在地下水硝酸盐发表先例；高位仅描述期刊层级，不表示稿件适配度或录用概率
**官网 scope**：待核验

## Full invocation example

```python
from scripts.select_journals import select_journals, format_selection_report

paper_text = """PASTE TITLE + ABSTRACT + KEYWORDS HERE"""

bundle = select_journals(
    text=paper_text,
    paper_profile={
        "direction_summary": "groundwater nitrate reference conditions; hydrochemistry is the analytical framework",
        "primary_field": "hydrogeology",
        "specialty": "groundwater nitrate reference conditions",
        "research_object": "shallow aquifer nitrate states",
        "research_question": "how status separation changes reference estimation",
        "contribution_type": "applied methodological framework",
        "target_audience": ["hydrogeologists", "groundwater-quality researchers"],
        "methods": ["hydrochemistry", "bootstrap uncertainty"],
        "exclusions": ["general analytical chemistry", "machine-learning methods"],
        "search_queries": [
            "groundwater nitrate reference condition aquifer hydrochemistry",
            "nitrate baseline status separation redox groundwater",
        ],
    },
    # Optional: strict current XinRui filter, e.g. "1区".
    # xinrui_partition="1区",
    impact_low="3",
    max_candidates=10,
)

print(format_selection_report(bundle["profile"], bundle["results"]))
```
