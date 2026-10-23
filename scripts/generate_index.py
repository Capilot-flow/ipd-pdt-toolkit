#!/usr/bin/env python3
"""Generate the deliverable index and phase README files from the catalog."""
from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

from generate_docs import LEVEL_ICON, LEVEL_LABEL, TYPE_ICON, TYPE_LABEL, parse_catalog

ROOT = Path(__file__).resolve().parents[1]

GROUPS = [
    ("01-概念阶段-CDCP", "01. 概念阶段（CDCP）", "01-概念阶段-CDCP"),
    ("02-计划阶段-PDCP", "02. 计划阶段（PDCP）", "02-计划阶段-PDCP"),
    ("03-开发阶段-TR1-TR4", "03. 开发阶段（TR1~TR4）", "03-开发阶段-TR1-TR4"),
    ("04-验证阶段-TR5", "04. 验证阶段（TR5）", "04-验证阶段-TR5"),
    ("05-发布阶段-TR6-ADCP", "05. 发布阶段（TR6/ADCP）", "05-发布阶段-TR6-ADCP"),
    ("06-生命周期与退市", "06. 生命周期与退市（LDCP/EOL）", "06-生命周期与退市"),
    ("07-顶层治理", "07. 顶层治理（跨项目）", "07-顶层治理"),
    ("08-公共模板与规范", "08. 公共模板与规范", "08-公共模板与规范"),
]

PHASE_TEXT = {
    "01-概念阶段-CDCP": {
        "goal": "把机会点转化为可立项的产品概念，回答“值不值得做、大致做什么”，通过 CDCP 获得计划阶段授权。",
        "gate": "CDCP（商业决策）+ Pre-TR1（概念技术预审）",
        "entry": "机会点初筛完成、战略/路标匹配、PDT 经理候选人指定、初步客户/市场证据、合规初筛无红线。",
        "exit": "商业价值成立、目标客户/场景清晰、技术可行、风险可控、资源可承诺、合规无红线、立项申请书获批。",
        "focus": ["商业论证与市场证据", "初始需求与概念方案", "技术可行性", "初始风险/合规/IP/成本", "PDT 组建与授权"],
    },
    "02-计划阶段-PDCP": {
        "goal": "把概念转化为可执行的项目计划，完成需求/架构基线和预算/资源承诺，通过 PDCP 签署项目任务书。",
        "gate": "PDCP（商业决策）+ TR1 准入预审",
        "entry": "CDCP Go、立项申请书/商业论证获批、PDT 核心团队到位、初始需求/概念方案基线、预算框架预沟通。",
        "exit": "需求/架构基线冻结、计划闭合、预算/资源获批、供应/制造/服务可行、Top 风险有应对、任务书签署。",
        "focus": ["需求基线与架构", "WBS/进度/资源/预算", "质量/测试计划", "供应/制造/服务计划", "变更/风险/配置机制"],
    },
    "03-开发阶段-TR1-TR4": {
        "goal": "按基线完成系统/详细设计、开发、集成，通过 TR1~TR4 逐级确认技术成熟度，形成可验证版本/样机。",
        "gate": "TR1~TR4（技术评审）+ VRR（验证准入，管理决策）",
        "entry": "PDCP Go、需求/架构基线冻结、开发环境/工具链就绪、开发资源到位、变更/配置管理生效。",
        "exit": "设计完成、集成通过、阻断缺陷清零、版本/文档受控、验证资源就绪。",
        "focus": ["系统/详细设计", "接口与集成", "DFMEA/DFM/DFT/DFS", "单元/集成测试", "样机/BOM/工艺", "设计变更与缺陷闭环"],
    },
    "04-验证阶段-TR5": {
        "goal": "验证产品满足需求、质量、可靠性、安全、合规要求，缺陷收敛到发布门槛，通过 TR5 进入发布准备。",
        "gate": "TR5（技术评审）+ LRR（发布准入预审）",
        "entry": "TR4 通过、候选版本/样机冻结、测试环境/数据就绪、认证/试产条件就绪、缺陷门槛定义。",
        "exit": "测试覆盖达标、阻断/严重缺陷清零、性能/可靠性/安全/合规通过、试产良率达标、服务/文档/培训就绪、剩余风险接受。",
        "focus": ["系统/性能/可靠性/安全测试", "UAT/Beta/试点", "认证/安规/EMC", "试产/小批量", "缺陷收敛与质量度量", "服务/文档验证"],
    },
    "05-发布阶段-TR6-ADCP": {
        "goal": "完成上市/量产/交付/服务准备，通过 TR6 和 ADCP 获得上市授权，建立发布后监控与回退机制。",
        "gate": "TR6（技术评审）+ ADCP（商业决策）",
        "entry": "TR5 通过、发布包/版本冻结、量产/交付就绪、市场/销售/定价就绪、服务/培训就绪、认证完成、回退方案批准。",
        "exit": "发布门禁全过、首单/首台可交付、支持团队就绪、监控/回退就绪、剩余风险接受。",
        "focus": ["发布计划/市场/定价", "量产/供应/交付", "服务/培训/文档", "回退方案", "ADCP 决策", "发布后监控"],
    },
    "06-生命周期与退市": {
        "goal": "监控产品绩效、质量、成本和客户满意度，持续优化，评估并执行退市，完成客户迁移、服务终止和知识沉淀。",
        "gate": "PRR（上市后复盘）+ LDCP/EOL DCP（退市决策）",
        "entry": "ADCP Go/产品上市、绩效指标/责任人/预算明确、退市触发条件定义、服务/合同/库存台账建立。",
        "exit": "绩效达标或退市条件成立、客户迁移可行、库存/服务/合同风险可控、财务影响可接受。",
        "focus": ["绩效/满意度/质量监控", "版本迭代/降本", "EOL 评估", "客户迁移", "库存/服务终止", "复盘与归档"],
    },
}

PHASE_VISUAL = {
    "01-概念阶段-CDCP": {
        "mermaid": """flowchart LR
    A["机会点"] --> B["概念/需求/商业论证"]
    B --> C{"Pre-TR1"}
    C -->|通过| D{"CDCP"}
    D -->|Go| E["进入计划"]
    D -->|Rework| B
    D -->|No-Go| F["关闭/观察"]""",
        "must": ["商业价值成立", "目标客户/场景清晰", "技术可行", "风险可控", "资源可承诺"],
        "leak": ["只有市场故事，没有客户证据", "成本/风险漏项", "合规/IP 红线未识别"],
        "signal": ["CDCP 反复 Rework", "关键假设没有验证计划", "PDT 核心成员不到位"],
    },
    "02-计划阶段-PDCP": {
        "mermaid": """flowchart LR
    A["需求/架构基线"] --> B["WBS/进度/预算"]
    B --> C{"TR1 预审"}
    C -->|通过| D{"PDCP"}
    D -->|Go| E["进入开发"]
    D -->|Rework| B
    D -->|No-Go| F["调整/终止"]""",
        "must": ["需求/架构冻结", "计划闭合", "预算/资源获批", "供应/制造/服务可行", "Top 风险有应对"],
        "leak": ["WBS 漏项", "资源只写部门不写人", "关键路径没有缓冲"],
        "signal": ["计划反复改基线", "预算/资源缺口靠“后面再说”", "供应/制造未介入"],
    },
    "03-开发阶段-TR1-TR4": {
        "mermaid": """flowchart LR
    A["TR1 需求/方案"] --> B["TR2 系统/接口"]
    B --> C["TR3 详细设计"]
    C --> D["TR4 开发/集成"]
    D --> E{"VRR 验证准入"}
    E -->|Go| F["进入验证"]
    E -->|Rework| D""",
        "must": ["需求可追溯", "接口闭合", "设计可制造/可测试", "阻断缺陷清零", "版本受控"],
        "leak": ["接口只写“待定”", "DFM/DFT/DFS 后置", "变更不走 CCB"],
        "signal": ["TR 开成汇报会", "缺陷越修越多", "样机问题重复出现"],
    },
    "04-验证阶段-TR5": {
        "mermaid": """flowchart LR
    A["TR5 验证"] --> B{"缺陷收敛"}
    B -->|是| C{"LRR 发布准入"}
    B -->|否| D["回炉修复"]
    C -->|Go| E["进入发布"]
    C -->|Rework| D""",
        "must": ["测试覆盖达标", "阻断/严重缺陷清零", "认证/合规通过", "试产良率达标", "服务/文档就绪"],
        "leak": ["只测正常路径", "认证样品/周期没预留", "遗留缺陷没有接受人"],
        "signal": ["TR5 前还在改需求", "缺陷关闭率突然“变好”", "试产问题没有根因"],
    },
    "05-发布阶段-TR6-ADCP": {
        "mermaid": """flowchart LR
    A["TR6 发布/量产"] --> B{"ADCP"}
    B -->|Go| C["上市/交付"]
    B -->|Rework| D["整改/分阶段"]
    B -->|No-Go| E["延迟/取消"]
    C --> F["发布后监控"]""",
        "must": ["发布门禁全过", "首单/首台可交付", "供应/服务就绪", "回退方案可执行", "剩余风险接受"],
        "leak": ["只盯质量，漏供应/服务", "回退方案没演练", "渠道/培训未就绪"],
        "signal": ["ADCP 前还在补认证", "首单交付靠“特事特办”", "发布后问题无人接"],
    },
    "06-生命周期与退市": {
        "mermaid": """flowchart LR
    A["绩效/质量/客户监控"] --> B{"继续经营"}
    B -->|是| C["迭代/降本"]
    B -->|否| D{"EOL 评估"}
    D -->|Go| E["退市执行"]
    D -->|Rework| F["补迁移/库存方案"]
    D -->|No-Go| C""",
        "must": ["绩效/质量达标", "退市条件成立", "客户迁移可行", "库存/服务风险可控", "财务影响可接受"],
        "leak": ["只算库存，不算客户流失", "服务合同未到期", "数据/知识未归档"],
        "signal": ["绩效持续下滑", "客户投诉集中", "备件/服务成本失控"],
    },
}

TYPE_ORDER = {"T": 0, "R": 1, "C": 2, "S": 3, "A": 4}


def group_docs(docs):
    grouped = defaultdict(list)
    for doc in docs:
        for key, _label, prefix in GROUPS:
            if doc["path"].startswith(prefix + "/"):
                grouped[key].append(doc)
                break
    return grouped


def rel_link(from_file: Path, target_file: Path) -> str:
    return os.path.relpath(target_file, from_file.parent).replace("\\", "/")


def write_index(docs):
    grouped = group_docs(docs)
    index_path = ROOT / "00-总览与使用说明" / "全量交付物索引.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# 全量交付物索引",
        "",
        "> 本索引由 `scripts/generate_index.py` 从 `scripts/catalog/*.txt` 自动生成。共 **%d** 份交付物。" % len(docs),
        "",
        "## 统计",
        "",
        "| 板块 | 模板 | 台账 | Checklist | SOP | 规范 | 小计 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label, _prefix in GROUPS:
        items = grouped.get(key, [])
        counts = {t: sum(1 for d in items if d["type"] == t) for t in "TRCSA"}
        lines.append(
            f"| {label} | {counts['T']} | {counts['R']} | {counts['C']} | {counts['S']} | {counts['A']} | {len(items)} |"
        )
    lines += ["", "## 目录", ""]
    for key, label, _prefix in GROUPS:
        if grouped.get(key):
            lines.append(f"- [{label}](#{key})")
    lines.append("")
    for key, label, prefix in GROUPS:
        items = sorted(grouped.get(key, []), key=lambda d: (TYPE_ORDER.get(d["type"], 9), d["id"]))
        if not items:
            continue
        lines += [f'<a id="{key}"></a>', "", f"## {label}", ""]
        lines += ["| 编号 | 交付物 | 类型 | 等级 | 责任角色 | 用途 | 文件 |", "|---|---|---|---|---|---|---|"]
        for doc in items:
            link = rel_link(index_path, ROOT / doc["path"])
            lines.append(
                f"| {doc['id']} | {doc['title']} | {TYPE_ICON.get(doc['type'], '')} {TYPE_LABEL.get(doc['type'], doc['type'])} | "
                f"{LEVEL_ICON.get(doc['level'], '')} {doc['level']} / {LEVEL_LABEL.get(doc['level'], doc['level'])} | {doc['owner']} | "
                f"{doc['purpose']} | [{Path(doc['path']).name}]({link}) |"
            )
        lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {index_path.relative_to(ROOT)} ({len(docs)} documents)")


def write_phase_readme(key: str, label: str, prefix: str, docs):
    info = PHASE_TEXT[key]
    visual = PHASE_VISUAL[key]
    items = sorted(docs, key=lambda d: (TYPE_ORDER.get(d["type"], 9), d["id"]))
    counts = {t: sum(1 for d in items if d["type"] == t) for t in "TRCSA"}
    lines = [
        f"# {label}",
        "",
        f"> {info['goal']}",
        "",
        "## 0. 一图看懂",
        "",
        "```mermaid",
        visual["mermaid"],
        "```",
        "",
        "## 1. 阶段门禁",
        "",
        f"- **门禁**：{info['gate']}",
        f"- **准入**：{info['entry']}",
        f"- **准出**：{info['exit']}",
        "",
        "## 2. 重点抓什么",
        "",
        f"**本阶段重点**：{'、'.join(info['focus'])}",
        "",
        "| 必须抓住 | 容易漏掉 | 失败信号 |",
        "|---|---|---|",
        f"| {'<br>'.join('✅ ' + x for x in visual['must'])} | {'<br>'.join('⚠️ ' + x for x in visual['leak'])} | {'<br>'.join('🚨 ' + x for x in visual['signal'])} |",
        "",
        "## 3. 本阶段物料",
        "",
        f"📄 模板 {counts['T']} ｜ 📊 台账 {counts['R']} ｜ ✅ 检查表 {counts['C']} ｜ 🔄 SOP {counts['S']} ｜ 合计 {len(items)}",
        "",
        "| 编号 | 交付物 | 类型 | 等级 | 责任角色 | 用途 | 文件 |",
        "|---|---|---|---|---|---|---|",
    ]
    for doc in items:
        rel = doc["path"][len(prefix) + 1:]
        lines.append(
            f"| {doc['id']} | {doc['title']} | {TYPE_ICON.get(doc['type'], '')} {TYPE_LABEL.get(doc['type'], doc['type'])} | "
            f"{LEVEL_ICON.get(doc['level'], '')} {doc['level']} / {LEVEL_LABEL.get(doc['level'], doc['level'])} | {doc['owner']} | "
            f"{doc['purpose']} | [{rel}]({rel}) |"
        )
    lines += [
        "",
        "## 4. 使用提示",
        "",
        "- 先读 `00-总览与使用说明/IPD流程总览.md` 和 `DCP与TR时序.md`；",
        "- 用 `08-公共模板与规范/模板/CM-T-18-项目裁剪表.md` 做裁剪；",
        "- 每份模板的“核心必填”栏目不得整体省略；",
        "- DCP/TR 前用对应 `检查表/` 自检，问题闭环后再上会。",
        "",
    ]
    target = ROOT / prefix / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {target.relative_to(ROOT)}")


def write_section_readme(key: str, label: str, prefix: str, docs):
    items = sorted(docs, key=lambda d: (TYPE_ORDER.get(d["type"], 9), d["id"]))
    counts = {t: sum(1 for d in items if d["type"] == t) for t in "TRCSA"}
    target = ROOT / prefix / "README.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {label}",
        "",
        f"> 共 {len(items)} 份：📄 模板 {counts['T']} ｜ 📊 台账 {counts['R']} ｜ ✅ 检查表 {counts['C']} ｜ 🔄 SOP {counts['S']} ｜ 📐 规范 {counts['A']}",
        "",
        "| 编号 | 交付物 | 类型 | 等级 | 责任角色 | 用途 | 文件 |",
        "|---|---|---|---|---|---|---|",
    ]
    for doc in items:
        link = rel_link(target, ROOT / doc["path"])
        lines.append(
            f"| {doc['id']} | {doc['title']} | {TYPE_ICON.get(doc['type'], '')} {TYPE_LABEL.get(doc['type'], doc['type'])} | "
            f"{LEVEL_ICON.get(doc['level'], '')} {doc['level']} / {LEVEL_LABEL.get(doc['level'], doc['level'])} | {doc['owner']} | "
            f"{doc['purpose']} | [{Path(doc['path']).name}]({link}) |"
        )
    lines += ["", "> 总索引见 `00-总览与使用说明/全量交付物索引.md`。", ""]
    target.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"Wrote {target.relative_to(ROOT)}")


def main():
    docs = parse_catalog()
    write_index(docs)
    grouped = group_docs(docs)
    for key, label, prefix in GROUPS:
        if key in PHASE_TEXT:
            write_phase_readme(key, label, prefix, grouped.get(key, []))
        else:
            write_section_readme(key, label, prefix, grouped.get(key, []))


if __name__ == "__main__":
    main()
