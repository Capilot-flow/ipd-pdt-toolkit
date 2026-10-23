# 生成脚本说明

本目录用“目录数据（catalog）+ 渲染器”的方式维护 278 份交付物正文，避免手工复制导致格式漂移。

---

## 1. 文件

| 文件 | 用途 |
|---|---|
| `catalog/01_common_governance.txt` | 公共模板、公共规范、顶层治理 |
| `catalog/02_concept_plan.txt` | 概念阶段、计划阶段 |
| `catalog/03_development_validation.txt` | 开发阶段、验证阶段 |
| `catalog/04_release_lifecycle.txt` | 发布阶段、生命周期/退市 |
| `generate_docs.py` | 读取 catalog，生成 278 份 Markdown 正文 |
| `generate_index.py` | 生成全量索引和各目录 README |

---

## 2. catalog 记录格式

每行一条记录，字段用 `§` 分隔：

```text
type§id§title§path§level§owner§purpose§core§recommended§optional§extra
```

| 字段 | 说明 |
|---|---|
| type | `T` 模板、`R` 台账、`C` Checklist、`S` SOP、`A` 规范 |
| id | 唯一编号，如 `CP-T-01` |
| title | 中文名称 |
| path | 相对仓库根目录的路径 |
| level | `M` / `C` / `O` |
| owner | 责任角色 |
| purpose | 用途说明 |
| core | 核心必填栏目，`;` 分隔 |
| recommended | 推荐栏目，`;` 分隔 |
| optional | 可省略栏目，`;` 分隔 |
| extra | 按类型不同，见下 |

### 2.1 extra 字段

| 类型 | extra 格式 |
|---|---|
| T | 空 |
| R | `字段1;字段2||状态流` |
| C | `强制检查项1;强制检查项2||可选检查项1;可选检查项2` |
| S | `触发条件||步骤1→步骤2→...||评审节点1;评审节点2||例外1;例外2` |
| A | `章节1;章节2;...` |

> 注意：`§` 是字段分隔符，正文中不要使用；列表内部用 `;`，SOP 步骤用 `→`，SOP 的四个部分用 `||`。

---

## 3. 常用命令

```bash
# 生成全部正文
python scripts/generate_docs.py

# 生成索引和目录 README
python scripts/generate_index.py

# 校验（示例）
python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'scripts')
from generate_docs import parse_catalog
for d in parse_catalog():
    assert Path(d['path']).exists(), d
print('ok')
PY
```

---

## 4. 新增一份交付物

1. 在对应 `catalog/*.txt` 增加一行；
2. 运行 `python scripts/generate_docs.py`；
3. 运行 `python scripts/generate_index.py`；
4. 检查生成的正文，补充必要的领域内容；
5. 提交 PR，说明文件等级和核心栏目。

---

## 5. 修改生成规则

- 文档通用骨架：`generate_docs.py` 中的 `template_body`、`register_body`、`checklist_body`、`sop_body`、`asset_body`；
- 栏目填写提示：`SECTION_GUIDE` 和 `PRIORITY_GUIDE`；
- 阶段推断：`infer_phase`；
- 索引分组：`generate_index.py` 中的 `GROUPS` 和 `PHASE_TEXT`。

修改后请重新生成并检查 diff，避免批量格式漂移。
