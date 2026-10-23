#!/usr/bin/env python3
"""Generate the complete IPD document body set from a compact catalog.

Catalog record format (one record per line, fields separated by §):
  type§id§title§path§level§owner§purpose§core§recommended§optional§extra

type:
  T = template, R = register, C = checklist, S = SOP, A = asset/spec
extra by type:
  R: fields||status_flow
  C: mandatory_items||optional_items
  S: trigger||steps||review_nodes||exceptions
  A: sections
Lists inside a field use ';' as separator.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "scripts" / "catalog"

LEVEL_LABEL = {
    "M": "强制必选",
    "C": "条件可选",
    "O": "非必要",
}
LEVEL_ICON = {"M": "🔴", "C": "🟡", "O": "⚪"}

TYPE_LABEL = {
    "T": "模板",
    "R": "台账",
    "C": "检查表",
    "S": "SOP",
    "A": "规范",
}
TYPE_ICON = {"T": "📄", "R": "📊", "C": "✅", "S": "🔄", "A": "📐"}


def level_badge(level: str) -> str:
    return f"{LEVEL_ICON.get(level, '')} {level} / {LEVEL_LABEL.get(level, level)}"


def type_badge(doc_type: str) -> str:
    return f"{TYPE_ICON.get(doc_type, '')} {TYPE_LABEL.get(doc_type, doc_type)}"


STAGE_ORDER = ["概念", "计划", "开发", "验证", "发布", "生命周期"]
GATE_BY_PHASE = {
    "概念": "CDCP + Pre-TR1",
    "计划": "PDCP + TR1 准入预审",
    "开发": "TR1~TR4 + VRR",
    "验证": "TR5 + LRR",
    "发布": "TR6 + ADCP",
    "生命周期": "PRR + LDCP/EOL",
}


def current_stage(doc: dict) -> str | None:
    phase = doc.get("phase", "")
    for stage in STAGE_ORDER:
        if stage in phase:
            return stage
    return None


def stage_strip(doc: dict) -> str:
    stage = current_stage(doc)
    if not stage:
        return "跨阶段治理（覆盖概念 → 计划 → 开发 → 验证 → 发布 → 生命周期）"
    return " → ".join(f"**{s}**" if s == stage else s for s in STAGE_ORDER)


def gate_for(doc: dict) -> str:
    stage = current_stage(doc)
    return GATE_BY_PHASE.get(stage, "按项目阶段执行")


def key_points(doc: dict) -> list[str]:
    if doc["type"] == "T":
        items = doc.get("core", [])
    elif doc["type"] == "R":
        items = doc.get("fields", [])
    elif doc["type"] == "C":
        items = doc.get("mandatory_items", [])
    elif doc["type"] == "S":
        items = doc.get("steps", [])
    elif doc["type"] == "A":
        items = doc.get("sections", [])
    else:
        items = []
    return [x for x in items if x][:5]


def visual_header(doc: dict) -> str:
    circles = "①②③④⑤"
    points = key_points(doc)
    point_text = " ｜ ".join(f"{circles[i]} {p}" for i, p in enumerate(points)) or "见正文"
    return (
        f"> **{LEVEL_ICON.get(doc['level'], '')} {doc['level']} / {LEVEL_LABEL.get(doc['level'], doc['level'])}**"
        f" ｜ **{TYPE_ICON.get(doc['type'], '')} {TYPE_LABEL.get(doc['type'], doc['type'])}**"
        f" ｜ **责任角色**：{doc['owner']}\n"
        f">\n"
        f"> **💡 一句话**：{doc['purpose']}\n"
        f">\n"
        f"> **📍 阶段位置**：{stage_strip(doc)}\n"
        f">\n"
        f"> **🚦 对应门禁**：{gate_for(doc)}\n"
        f">\n"
        f"> **🔑 重点速览**：{point_text}\n"
    )

SECTION_GUIDE = [
    ("风险", "至少列出 Top 5 风险；每项包含概率、影响、等级、应对措施、责任人、触发条件、剩余风险。不要只写“加强管理”。"),
    ("成本", "列出成本项、估算依据、关键假设、预算上限、敏感性区间；明确谁批准、超支如何升级。"),
    ("质量", "质量目标必须可度量；明确验收标准、缺陷门槛、评审/测试方式、责任人和不达标处理。"),
    ("需求", "每条需求必须有唯一 ID、来源、优先级、验收标准、假设/依赖；避免不可测试的形容词。"),
    ("验收", "验收标准必须可测试、可判定；写明验收人、验收环境、抽样/覆盖要求、不通过的处理。"),
    ("资源", "明确角色、姓名/岗位、投入比例、到位时间、技能缺口、替代方案和资源冲突升级路径。"),
    ("计划", "包含里程碑、依赖、关键路径、缓冲、责任人；计划变更必须走变更控制。"),
    ("依赖", "写明提供方、接收方、需要日期、当前状态、延迟影响和升级路径。"),
    ("合规", "写明适用法规/标准、责任人、证据、审计频率；红线项一票否决。"),
    ("知识产权", "写明专利/商标/著作权/开源/FTO 风险、布局建议、保密要求和责任人。"),
    ("供应商", "写明准入、定点、合同、交期、质量、绩效、替代和断供应急。"),
    ("制造", "写明产能、工艺、工装、良率、爬坡、质量门禁和异常处理。"),
    ("服务", "写明服务模式、SLA、备件、热线、培训、升级路径和服务成本。"),
    ("变更", "写明变更内容、原因、影响分析、备选方案、CCB 结论、实施与验证、基线更新。"),
    ("缺陷", "写明严重度定义、关闭标准、遗留缺陷审批、回归验证和升级路径。"),
    ("测试", "写明范围、层级、环境、数据、准入准出、覆盖率、缺陷门槛和资源。"),
    ("发布", "写明发布范围、时间、渠道、门禁、回退、监控和责任人。"),
    ("退市", "写明退市条件、客户迁移、库存处置、服务终止、合同/合规影响和预算。"),
    ("背景", "说明机会来源、市场/客户证据、为什么是现在；引用数据来源和时间范围，避免“拍脑袋”。"),
    ("目标", "目标必须可度量；区分业务目标、项目目标、质量目标；写明基线值、目标值、统计周期和责任人。"),
    ("范围", "明确做什么、不做什么、边界在哪里；列出关键接口、假设和排除项，防止范围蔓延。"),
    ("价值", "说明客户价值、商业价值、战略价值；尽量量化收入、成本、效率、风险降低。"),
    ("客户", "写清客户画像、使用场景、痛点、付费意愿和决策链；区分用户、决策者、采购者。"),
    ("方案", "至少给出备选方案和选择依据；写清取舍、约束和未选择方案的原因。"),
    ("里程碑", "里程碑必须有交付物、验收标准、责任人，并与 DCP/TR 节点对齐。"),
    ("审批", "明确审批人、会签顺序、授权边界；不得自己起草、自己批准。"),
    ("角色", "明确 RACI、单一责任人和备份人；跨部门角色要写投入比例。"),
    ("流程", "写清触发、输入、活动、输出、责任人、时限、评审节点和例外。"),
    ("指标", "定义指标、公式、数据源、统计频率、阈值和责任人；避免口径不一致。"),
    ("数据", "说明数据来源、口径、质量、权限、保留期限和脱敏要求。"),
    ("培训", "明确对象、内容、方式、考核和记录；关键岗位需认证上岗。"),
    ("库存", "写清数量、位置、周转、处置方式和损失；区分成品、在途、呆滞。"),
    ("合同", "写清范围、SLA、价格、付款、终止、违约和知识产权归属。"),
    ("文档", "明确版本、密级、评审、发布、归档、权限和保留期限。"),
    ("沟通", "明确对象、频率、渠道、升级路径和记录；关键决策必须书面化。"),
    ("度量", "定义度量指标、数据来源、频率、阈值和复盘机制。"),
]


PRIORITY_GUIDE = [
    ("里程碑", "里程碑必须有交付物、验收标准、责任人，并与 DCP/TR 节点对齐；写明关键依赖和缓冲。"),
    ("资源需求", "明确角色、人数/投入比例、到位时间、技能缺口、替代方案和资源冲突升级路径。"),
    ("目标客户", "写清客户画像、场景、痛点、付费意愿和决策链；区分用户、决策者、采购者。"),
    ("业务价值", "说明客户价值、商业价值、战略价值；尽量量化收入、成本、效率、风险降低。"),
    ("成功/验收", "验收标准必须可测试、可判定；写明验收人、验收环境、抽样/覆盖要求、不通过的处理。"),
    ("终止", "写明什么情况下终止/退出、谁来决策、如何收尾（资源释放、合同、客户、归档）。"),
    ("竞品", "列出直接/间接竞品、对标维度、优劣势、价格/份额、差异化机会；注明数据来源和时间。"),
    ("假设", "写明假设内容、影响、验证方式、责任人、期限；假设失效时的替代方案。"),
]


def guide_for(section: str) -> str:
    for key, text in PRIORITY_GUIDE:
        if key in section:
            return text
    for key, text in SECTION_GUIDE:
        if key in section:
            return text
    return (
        "填写时至少回答：是什么、为什么需要、谁负责、何时完成、如何验证、"
        "不满足时如何升级。避免空泛描述，所有结论要有证据或数据支撑。"
    )


def infer_phase(path: str) -> str:
    mapping = {
        "01-概念阶段": "概念阶段（Concept，CDCP）",
        "02-计划阶段": "计划阶段（Plan，PDCP）",
        "03-开发阶段": "开发阶段（Development，TR1~TR4）",
        "04-验证阶段": "验证阶段（Validation，TR5）",
        "05-发布阶段": "发布阶段（Release，TR6/ADCP）",
        "06-生命周期": "生命周期/退市阶段（Lifecycle/Retire，LDCP/EOL）",
        "07-顶层治理": "IPD/PMO 顶层治理（跨项目）",
        "08-公共模板与规范": "IPD 全流程/公共模板与规范",
        "00-总览": "IPD 全流程/总览",
    }
    for key, label in mapping.items():
        if key in path:
            return label
    return "IPD 全流程"


def split_list(value: str) -> list[str]:
    value = (value or "").strip()
    if not value:
        return []
    return [x.strip() for x in value.split(";") if x.strip()]


def parse_catalog() -> list[dict]:
    docs: list[dict] = []
    for path in sorted(CATALOG_DIR.glob("*.txt")):
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("§")
            if len(parts) < 11:
                raise ValueError(f"{path.name}:{lineno}: expected 11 fields, got {len(parts)}")
            doc_type, doc_id, title, rel_path, level, owner, purpose, core, rec, opt, extra = parts[:11]
            doc = {
                "type": doc_type.strip(),
                "id": doc_id.strip(),
                "title": title.strip(),
                "path": rel_path.strip(),
                "level": level.strip(),
                "owner": owner.strip(),
                "purpose": purpose.strip(),
                "core": split_list(core),
                "recommended": split_list(rec),
                "optional": split_list(opt),
                "extra": extra.strip(),
                "source": f"{path.name}:{lineno}",
            }
            doc["phase"] = infer_phase(doc["path"])
            if doc["type"] == "R":
                sub = doc["extra"].split("||")
                doc["fields"] = split_list(sub[0] if len(sub) > 0 else "")
                doc["status_flow"] = sub[1].strip() if len(sub) > 1 else "草稿→评审中→已批准→执行中→已关闭"
            elif doc["type"] == "C":
                sub = doc["extra"].split("||")
                doc["mandatory_items"] = split_list(sub[0] if len(sub) > 0 else "")
                doc["optional_items"] = split_list(sub[1] if len(sub) > 1 else "")
            elif doc["type"] == "S":
                sub = doc["extra"].split("||")
                doc["trigger"] = sub[0].strip() if len(sub) > 0 else ""
                doc["steps"] = split_list(sub[1] if len(sub) > 1 else "")
                doc["review_nodes"] = split_list(sub[2] if len(sub) > 2 else "")
                doc["exceptions"] = split_list(sub[3] if len(sub) > 3 else "")
            elif doc["type"] == "A":
                doc["sections"] = split_list(doc["extra"])
            docs.append(doc)
    if not docs:
        raise ValueError(f"No catalog records found under {CATALOG_DIR}")
    return docs


def frontmatter(doc: dict) -> str:
    return (
        "---\n"
        f"id: {doc['id']}\n"
        f"title: \"{doc['title']}\"\n"
        f"type: {TYPE_LABEL.get(doc['type'], doc['type'])}\n"
        f"level: {doc['level']}\n"
        f"level_label: {LEVEL_LABEL.get(doc['level'], doc['level'])}\n"
        f"owner: \"{doc['owner']}\"\n"
        f"version: v1.0\n"
        f"status: template\n"
        f"last_reviewed: 2026-10-23\n"
        "---\n\n"
    )


def control_table(doc: dict) -> str:
    return f"""## 文档控制

| 项目 | 内容 |
|---|---|
| 文档名称 | {doc['title']} |
| 文档编号 | {doc['id']} |
| 文件等级 | **{level_badge(doc['level'])}** |
| 责任角色 | {doc['owner']} |
| 适用阶段 | {doc.get('phase', 'IPD 全流程')} |
| 当前版本 | V1.0 |
| 评审方式 | 自检 + 同行评审 + PQA 复核；涉及 DCP/TR 的按对应门禁执行 |
| 归档位置 | 项目配置库对应阶段目录 |
| 密级 | 内部（按项目实际调整） |

> **使用说明**：本文件是模板正文，不是填写范例。方括号 `[ ]` 内为填写提示；不适用项写“不适用”并说明理由，不得直接删除。文件等级为 C/O 的，需在《项目裁剪表》中记录裁剪结论。
"""


def purpose_block(doc: dict) -> str:
    return f"""## 1. 🎯 目的与用途

{doc['purpose']}

本文件解决以下问题：

1. 统一本领域在 IPD 各阶段的输入、输出和评审口径；
2. 让责任人、评审人、决策人清楚“看什么、判什么、凭什么”；
3. 为 DCP/TR 提供可追溯的证据，而不是口头结论；
4. 在项目裁剪时，能够判断哪些内容必须保留、哪些可以简化。

**不适用范围**：本文件不替代项目实际数据、合同、法规文本或技术标准；引用时必须注明来源和版本。
"""


def scope_block(doc: dict) -> str:
    phase = doc.get("phase", "IPD 全流程")
    return f"""## 2. 📌 适用范围与触发条件

| 项目 | 说明 |
|---|---|
| 适用阶段 | {phase} |
| 适用项目级别 | A 类全量；B 类保留强制项；C 类可简化，但不得省略结论、责任人、验收标准 |
| 触发条件 | 进入对应阶段门禁；发生重大变更；PQA 审计/管理评审要求；客户/合规要求 |
| 输入 | 上游阶段基线、相关台账、评审意见、法规/标准、项目实际数据 |
| 输出 | 本文件批准版 + 相关台账更新 + 评审记录 |
| 时限 | 按项目计划；DCP/TR 材料原则上提前 5 个工作日提交，紧急事项按升级流程处理 |
"""


def raci_block(doc: dict) -> str:
    owner = doc["owner"]
    return f"""## 3. 👥 角色与职责（RACI）

> R=负责执行，A=最终批准，C=被咨询，I=被通知。一个事项只能有一个 A。

| 活动 | {owner} | PDT 经理 | PQA | IPMT | 相关领域 |
|---|---|---|---|---|---|
| 起草/维护本文件 | R | A | C | I | C |
| 数据/证据核实 | R | C | C | I | R |
| 评审组织 | C | R | C | I | C |
| 批准/放行 | C | A | C | A（按授权） | I |
| 变更控制 | R | A | C | I | C |
| 归档 | R | A | C | I | I |

**升级路径**：领域内无法闭环 → PDT 经理 → PQA/PMO → IPMT。涉及质量/合规红线的，直接升级，不得在项目内“消化”。
"""


def template_body(doc: dict) -> str:
    lines = ["## 4. 📝 正文结构", ""]
    lines.append("> 以下栏目按“核心必填 / 推荐填写 / 可省略”分级。核心栏目的结论缺失，DCP/TR 不得通过。")
    lines.append("")
    idx = 1
    for group, items, guide_prefix in [
        ("4.1 🔴 核心必填栏目", doc["core"], "必须填写"),
        ("4.2 🟡 推荐填写栏目", doc["recommended"], "建议填写"),
        ("4.3 ⚪ 可省略栏目", doc["optional"], "按项目复杂度决定"),
    ]:
        lines.append(f"### {group}")
        lines.append("")
        if not items:
            lines.append("_本文件无此类栏目。_")
            lines.append("")
            continue
        lines.append("| 序号 | 栏目 | 填写要求 | 责任人 | 完成状态 |")
        lines.append("|---|---|---|---|---|")
        for item in items:
            lines.append(
                f"| {idx} | **{item}** | {guide_prefix}。{guide_for(item)} | {doc['owner']} | [ ] 未开始 / [ ] 进行中 / [ ] 已完成 |"
            )
            idx += 1
        lines.append("")
    lines.append("### 4.4 ✍️ 正文填写区")
    lines.append("")
    for i, item in enumerate(doc["core"], 1):
        lines.append(f"#### 4.4.{i} {item}")
        lines.append("")
        lines.append(f"**填写要求**：{guide_for(item)}")
        lines.append("")
        lines.append("**必须回答**：")
        lines.append("")
        lines.append(f"- 现状/问题是什么？")
        lines.append(f"- 目标/结论是什么？用什么指标衡量？")
        lines.append(f"- 谁负责？什么时候完成？依赖谁？")
        lines.append(f"- 如果做不到，影响是什么？如何升级？")
        lines.append("")
        lines.append("**填写区**：")
        lines.append("")
        lines.append("> [在此填写。建议用“结论先行 + 证据 + 风险 + 下一步”的结构。]")
        lines.append("")
        lines.append("**证据/附件**：")
        lines.append("")
        lines.append("- [ ] 数据表/报告：______")
        lines.append("- [ ] 评审记录：______")
        lines.append("- [ ] 相关台账/系统链接：______")
        lines.append("")
    return "\n".join(lines)


def register_body(doc: dict) -> str:
    fields = doc.get("fields") or ["ID", "描述", "责任人", "状态", "关闭标准"]
    lines = ["## 4. 📊 台账结构与填写规则", ""]
    lines.append("> 台账是动态文件，条目持续新增、状态流转。禁止覆盖历史记录；变更留痕。")
    lines.append("")
    lines.append("### 4.1 🧾 字段定义")
    lines.append("")
    lines.append("| 字段 | 说明 | 必填 | 示例 |")
    lines.append("|---|---|---|---|")
    field_help = {
        "ID": ("唯一编号，建议 `{阶段}-{类型}-{序号}`", "CP-R-001"),
        "描述": ("事实描述，不写结论；包含触发条件/现象/影响", "关键物料交期由 8 周延长至 14 周"),
        "责任人": ("唯一责任人，写姓名/岗位，不写部门", "张三（采购经理）"),
        "状态": ("按状态流更新，不得跳级", "执行中"),
        "关闭标准": ("可验证的关闭条件，不能写“已处理”", "替代料验证通过并更新 BOM"),
        "概率": ("高/中/低或百分比", "中（40%）"),
        "影响": ("范围/进度/成本/质量/合规", "进度延迟 3 周，成本增加 8 万元"),
        "等级": ("高/中/低，按概率×影响矩阵", "高"),
        "应对": ("规避/减轻/转移/接受，写具体动作", "启动备选供应商认证"),
        "触发条件": ("什么信号出现时必须启动应对", "交期超过 10 周"),
        "优先级": ("P0/P1/P2，P0 为阻断", "P1"),
        "期限": ("目标关闭日期", "2026-11-15"),
        "关联项": ("关联需求/风险/变更/评审 ID", "CR-012, RSK-003"),
        "来源": ("会议/评审/客户/审计/系统", "TR2 评审"),
    }
    for f in fields:
        help_text, example = field_help.get(f, ("按项目实际填写；保持口径一致", "—"))
        required = "是" if any(k in f for k in ["ID", "描述", "责任人", "状态", "关闭", "概率", "影响", "等级", "应对", "期限"]) else "建议"
        lines.append(f"| {f} | {help_text} | {required} | {example} |")
    lines.append("")
    lines.append("### 4.2 🔄 状态流")
    lines.append("")
    lines.append(f"`{doc.get('status_flow', '草稿→评审中→已批准→执行中→已关闭')}`")
    lines.append("")
    lines.append("状态变更规则：")
    lines.append("")
    lines.append("- 每次变更记录日期、变更人、变更原因；")
    lines.append("- 关闭必须有证据和复核人；")
    lines.append("- 超过目标关闭日期未关闭的，自动进入升级清单；")
    lines.append("- P0/P1 条目每周复盘，P2 每两周复盘。")
    lines.append("")
    lines.append("### 4.3 📋 台账表")
    lines.append("")
    lines.append("| " + " | ".join(fields) + " |")
    lines.append("|" + "---|" * len(fields))
    lines.append("| " + " | ".join(["[填写]"] * len(fields)) + " |")
    lines.append("")
    lines.append("### 4.4 🔁 复盘与升级")
    lines.append("")
    lines.append("- 每周 PDT 例会复盘 P0/P1 条目；")
    lines.append("- 每月 PQA/PMO 抽查完整性和关闭质量；")
    lines.append("- 超期 2 周未关闭的，升级至 PDT 经理；超期 4 周的，升级至 IPMT/PMO。")
    lines.append("")
    return "\n".join(lines)


def checklist_body(doc: dict) -> str:
    mandatory = doc.get("mandatory_items") or doc["core"]
    optional = doc.get("optional_items") or doc["recommended"]
    lines = ["## 4. ✅ 检查表", ""]
    lines.append("> 结论只能填“符合 / 不符合 / 不适用”。填“不适用”必须写理由；填“不符合”必须写整改人、期限和复核人。")
    lines.append("")
    lines.append("### 4.1 🔴 强制检查项（不通过则门禁不通过）")
    lines.append("")
    lines.append("| 序号 | 检查项 | 判定标准 | 证据/附件 | 结论 | 整改人 | 期限 | 复核人 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, item in enumerate(mandatory, 1):
        lines.append(
            f"| M{i} | **{item}** | 有明确结论、责任人、数据/证据支撑；无红线项 | [ ] | [ ] 符合 / [ ] 不符合 / [ ] 不适用 |  |  |  |"
        )
    lines.append("")
    lines.append("### 4.2 🟡 可选补充检查项（按项目级别/风险选用）")
    lines.append("")
    lines.append("| 序号 | 检查项 | 判定标准 | 证据/附件 | 结论 | 备注 |")
    lines.append("|---|---|---|---|---|---|")
    for i, item in enumerate(optional, 1):
        lines.append(f"| O{i} | {item} | 有则加分，无则说明理由 | [ ] | [ ] 符合 / [ ] 不符合 / [ ] 不适用 |  |")
    lines.append("")
    lines.append("### 4.3 🚦 检查结论")
    lines.append("")
    lines.append("| 项目 | 结论 |")
    lines.append("|---|---|")
    lines.append("| 强制项通过数/总数 | ___ / ___ |")
    lines.append("| 不符合项数 | ___ |")
    lines.append("| 红线项 | [ ] 无 / [ ] 有（说明：______） |")
    lines.append("| 总体结论 | [ ] 通过 / [ ] 有条件通过 / [ ] 不通过 |")
    lines.append("| 条件/整改要求 | ______ |")
    lines.append("| 检查人/日期 | ______ |")
    lines.append("| 复核人/日期 | ______ |")
    lines.append("")
    lines.append("> **有条件通过**必须同时满足：无红线项、不符合项有明确整改计划、整改完成前有替代控制措施、批准人书面同意。")
    lines.append("")
    return "\n".join(lines)


def sop_body(doc: dict) -> str:
    trigger = doc.get("trigger") or "进入对应阶段门禁；发生重大变更；管理评审/审计要求"
    steps = doc.get("steps") or ["启动", "分析", "评审", "执行", "验证", "关闭"]
    if len(steps) == 1 and "→" in steps[0]:
        steps = [s.strip() for s in steps[0].split("→") if s.strip()]
    review = doc.get("review_nodes") or ["阶段评审", "PQA 复核"]
    exceptions = doc.get("exceptions") or ["紧急事项可先执行后补批，须 24 小时内补齐记录", "超出授权范围的，升级至 IPMT/PMO"]
    lines = ["## 4. 🔄 流程说明", ""]
    lines.append("### 4.1 ⚡ 触发条件")
    lines.append("")
    lines.append(trigger)
    lines.append("")
    lines.append("### 4.2 🪜 流程步骤")
    lines.append("")
    lines.append("| 步骤 | 输入 | 活动 | 输出 | 责任人 | 时限 |")
    lines.append("|---|---|---|---|---|---|")
    for i, step in enumerate(steps, 1):
        lines.append(
            f"| {i}. {step} | 上游基线/台账/申请 | 执行「{step}」：明确输入、责任人、完成标准；形成记录；关键结论需评审 | 《{step}》记录/更新后的台账 | {doc['owner']} | 按项目计划 |"
        )
    lines.append("")
    lines.append("### 4.3 🚦 评审与决策节点")
    lines.append("")
    for node in review:
        lines.append(f"- **{node}**：检查输入完整性、结论是否有证据、风险/例外是否闭合；输出评审记录和明确结论。")
    lines.append("")
    lines.append("### 4.4 ⚠️ 例外场景与兜底")
    lines.append("")
    lines.append("| 例外场景 | 处理方式 | 批准人 | 记录要求 |")
    lines.append("|---|---|---|---|")
    for ex in exceptions:
        lines.append(f"| {ex} | 先控制风险，再补流程；不得跳过质量/合规红线 | PDT 经理/PMO（按授权） | 例外审批表 + 风险登记册 |")
    lines.append("")
    lines.append("### 4.5 ⏱️ 时限与 SLA")
    lines.append("")
    lines.append("| 事项 | 时限 | 超时处理 |")
    lines.append("|---|---|---|")
    lines.append("| 常规申请 | 2 个工作日内受理 | 升级至 PDT 经理 |")
    lines.append("| 评审 | 5 个工作日内完成 | 升级至 PMO |")
    lines.append("| 紧急事项 | 24 小时内响应 | 直接升级至 IPMT 授权代表 |")
    lines.append("")
    lines.append("### 4.6 📈 度量与审计")
    lines.append("")
    lines.append("- 流程遵从率、按时完成率、例外率、返工率；")
    lines.append("- PQA 每季度抽查；")
    lines.append("- 重大偏差纳入项目健康度和 IPMT 报告。")
    lines.append("")
    return "\n".join(lines)


def asset_body(doc: dict) -> str:
    sections = doc.get("sections") or doc["core"]
    lines = ["## 4. 📐 规范正文", ""]
    for i, sec in enumerate(sections, 1):
        lines.append(f"### 4.{i} {sec}")
        lines.append("")
        lines.append(f"**要求**：{guide_for(sec)}")
        lines.append("")
        lines.append("**执行要点**：")
        lines.append("")
        lines.append("- 明确适用范围和责任人；")
        lines.append("- 明确输入、输出、评审节点和记录；")
        lines.append("- 明确例外场景和升级路径；")
        lines.append("- 每季度复核一次，法规/组织变化时即时更新。")
        lines.append("")
        lines.append("**记录/模板**：")
        lines.append("")
        lines.append("> [在此补充表格、字段或检查清单。]")
        lines.append("")
    return "\n".join(lines)


def common_tail(doc: dict) -> str:
    return """## 5. ⚠️ 风险、依赖与常见失败模式

| 类别 | 常见问题 | 预防/兜底 |
|---|---|---|
| 风险 | 只列风险不写应对；概率影响拍脑袋；风险长期不更新 | Top 风险必须有责任人、触发条件、应对和复盘节奏 |
| 质量 | 结论无证据；验收标准模糊；评审走过场 | 每个结论附证据；验收标准可测试；评审意见必须闭环 |
| 依赖 | 外部依赖未确认；接口人变更；交期假设未验证 | 依赖台账 + 需要日期 + 升级路径 |
| 进度 | 无缓冲；关键路径不清；变更未评估 | 关键路径/缓冲可见；变更走 CCB |
| 成本 | 漏项；估算无依据；超支不升级 | 成本项清单 + 敏感性 + 偏差阈值 |
| 合规 | 法规识别不全；证据缺失；红线被“特批” | 合规清单 + 一票否决 + 审计 |
| 组织 | 责任人不唯一；跨部门不协同；升级路径不清 | RACI 明确 + 单一责任人 + 升级 SOP |

## 6. ✅ 验收标准

本文件满足以下条件方可判为“完成”：

1. 核心必填栏目全部有结论，且结论有数据/证据支撑；
2. 风险、依赖、假设均已识别，并有责任人和应对；
3. 验收标准可测试、可判定，验收人明确；
4. 相关台账已更新，ID 可追溯；
5. 评审意见已闭环，遗留问题有责任人和期限；
6. 文件已按命名规范归档，版本/密级/审批完整。

## 7. 🧾 评审与审批

| 角色 | 职责 | 签字/日期 |
|---|---|---|
| 起草人 | 保证内容完整、数据真实、结论可追溯 | |
| 领域评审人 | 检查专业正确性和可执行性 | |
| PQA | 检查流程符合性、分级/裁剪是否合规 | |
| 批准人 | 对结论和资源承诺负责 | |

> 评审不通过时，必须写明“不通过原因 + 整改项 + 复核时间”，不得只写“原则同意”。

## 8. 🔄 变更记录

| 版本 | 日期 | 变更内容 | 变更人 | 审批人 |
|---|---|---|---|---|
| V1.0 | 2026-10-23 | 初始模板发布 | PMO | IPMT/PMO |

## 9. 📎 附录与参考

- [ ] 上游阶段基线/评审记录
- [ ] 相关台账/系统链接
- [ ] 法规/标准/合同引用
- [ ] 会议纪要/决策记录
- [ ] 其他附件：______

> **模板维护**：本文件由 PMO 归口维护，每季度复核一次；项目使用时不得删除“核心必填”栏目，可在《项目裁剪表》中记录简化理由。
"""


def render(doc: dict) -> str:
    body = [frontmatter(doc)]
    body.append(f"# {doc['title']}\n")
    body.append(visual_header(doc))
    body.append("")
    body.append(control_table(doc))
    body.append("")
    body.append(purpose_block(doc))
    body.append("")
    body.append(scope_block(doc))
    body.append("")
    body.append(raci_block(doc))
    body.append("")
    if doc["type"] == "T":
        body.append(template_body(doc))
    elif doc["type"] == "R":
        body.append(register_body(doc))
    elif doc["type"] == "C":
        body.append(checklist_body(doc))
    elif doc["type"] == "S":
        body.append(sop_body(doc))
    elif doc["type"] == "A":
        body.append(asset_body(doc))
    else:
        raise ValueError(f"Unknown type {doc['type']} for {doc['id']}")
    body.append("")
    body.append(common_tail(doc))
    return "\n".join(body)


def main() -> int:
    docs = parse_catalog()
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for doc in docs:
        if doc["id"] in seen_ids:
            raise ValueError(f"Duplicate id: {doc['id']} ({doc['source']})")
        if doc["path"] in seen_paths:
            raise ValueError(f"Duplicate path: {doc['path']} ({doc['source']})")
        seen_ids.add(doc["id"])
        seen_paths.add(doc["path"])
        target = ROOT / doc["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(doc), encoding="utf-8", newline="\n")
    print(f"Generated {len(docs)} documents under {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
