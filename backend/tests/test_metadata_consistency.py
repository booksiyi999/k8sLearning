"""Metadata 一致性自动校验测试。

防止未来新增关卡时遗漏 app/metadata.py 的同步更新。

覆盖范围:
  - KNOWLEDGE_POINTS: 每个关卡必须有知识点且列表非空
  - LEVEL_XP: 每个关卡必须有 XP 且 XP > 0
  - KNOWLEDGE_DOMAINS: 知识域中 level_id 的并集必须与关卡 ID 完全一致
  - CHAPTERS_META: 每个关卡所属章节都必须有章节元数据
  - 计数一致性: list_levels() / KNOWLEDGE_POINTS / LEVEL_XP / 知识域并集 数量一致

参考:
  - app/validator.py:list_levels()  —— 关卡 ID 的唯一真实来源
  - app/metadata.py                  —— 游戏化元数据集中配置
"""
from app.validator import list_levels
from app.metadata import (
    CHAPTERS_META,
    KNOWLEDGE_DOMAINS,
    KNOWLEDGE_POINTS,
    LEVEL_XP,
)


def _level_ids() -> list[str]:
    """返回所有关卡 ID（按 list_levels() 顺序）。"""
    return [lv["id"] for lv in list_levels()]


def _domain_level_ids() -> set[str]:
    """KNOWLEDGE_DOMAINS 中所有 level_id 的并集。"""
    ids: set[str] = set()
    for level_ids in KNOWLEDGE_DOMAINS.values():
        ids.update(level_ids)
    return ids


# ---------------------------------------------------------------------------
# 1. 每个关卡都必须有知识点，且知识点列表非空
# ---------------------------------------------------------------------------
def test_all_levels_have_knowledge_points():
    ids = _level_ids()
    missing = [i for i in ids if i not in KNOWLEDGE_POINTS]
    assert not missing, (
        f"以下关卡在 KNOWLEDGE_POINTS 中缺失: {missing}；"
        f"请在 app/metadata.py 的 KNOWLEDGE_POINTS 中补充对应知识点"
    )

    empty = [i for i in ids if i in KNOWLEDGE_POINTS and not KNOWLEDGE_POINTS[i]]
    assert not empty, (
        f"以下关卡的 KNOWLEDGE_POINTS 列表为空: {empty}；"
        f"知识点列表不能为空，请补充至少一个知识点"
    )


# ---------------------------------------------------------------------------
# 2. 每个关卡都必须有 XP，且 XP > 0
# ---------------------------------------------------------------------------
def test_all_levels_have_xp():
    ids = _level_ids()
    missing = [i for i in ids if i not in LEVEL_XP]
    assert not missing, (
        f"以下关卡在 LEVEL_XP 中缺失: {missing}；"
        f"请在 app/metadata.py 的 LEVEL_XP 中补充 XP 配置"
    )

    non_positive = [i for i in ids if i in LEVEL_XP and LEVEL_XP[i] <= 0]
    assert not non_positive, (
        f"以下关卡的 LEVEL_XP 值 <= 0: {non_positive}；XP 必须为正整数"
    )


# ---------------------------------------------------------------------------
# 3. LEVEL_XP 中不应存在「幽灵」条目（即指向不存在关卡的 key）
# ---------------------------------------------------------------------------
def test_no_phantom_xp_entries():
    ids = set(_level_ids())
    phantom = [k for k in LEVEL_XP if k not in ids]
    assert not phantom, (
        f"LEVEL_XP 中存在幽灵条目（对应关卡不存在）: {phantom}；"
        f"请检查是否删除了关卡但未清理 metadata"
    )
    assert len(LEVEL_XP) == len(ids), (
        f"LEVEL_XP 条目数 ({len(LEVEL_XP)}) 与关卡数 ({len(ids)}) 不一致；"
        f"多余: {set(LEVEL_XP) - ids}，缺失: {ids - set(LEVEL_XP)}"
    )


# ---------------------------------------------------------------------------
# 4. KNOWLEDGE_POINTS 中不应存在「幽灵」条目
# ---------------------------------------------------------------------------
def test_no_phantom_kp_entries():
    ids = set(_level_ids())
    phantom = [k for k in KNOWLEDGE_POINTS if k not in ids]
    assert not phantom, (
        f"KNOWLEDGE_POINTS 中存在幽灵条目（对应关卡不存在）: {phantom}；"
        f"请检查是否删除了关卡但未清理 metadata"
    )
    assert len(KNOWLEDGE_POINTS) == len(ids), (
        f"KNOWLEDGE_POINTS 条目数 ({len(KNOWLEDGE_POINTS)}) 与关卡数 ({len(ids)}) 不一致；"
        f"多余: {set(KNOWLEDGE_POINTS) - ids}，缺失: {ids - set(KNOWLEDGE_POINTS)}"
    )


# ---------------------------------------------------------------------------
# 5. KNOWLEDGE_DOMAINS 中 level_id 的并集必须等于所有关卡 ID（无遗漏、无多余）
# ---------------------------------------------------------------------------
def test_all_levels_in_domains():
    ids = set(_level_ids())
    domain_ids = _domain_level_ids()

    missing = ids - domain_ids
    assert not missing, (
        f"以下关卡未出现在任何 KNOWLEDGE_DOMAINS 分组中: {sorted(missing)}；"
        f"请在 app/metadata.py 的 KNOWLEDGE_DOMAINS 中将其归入合适的知识域"
    )

    extra = domain_ids - ids
    assert not extra, (
        f"KNOWLEDGE_DOMAINS 中存在指向不存在关卡的 level_id: {sorted(extra)}；"
        f"请检查是否删除了关卡但未清理知识域分组"
    )


# ---------------------------------------------------------------------------
# 6. 每个关卡所属的章节都必须在 CHAPTERS_META 中，且 CHAPTERS_META 无多余条目
# ---------------------------------------------------------------------------
def test_chapters_meta_complete():
    levels = list_levels()
    chapters_used = {lv["chapter"] for lv in levels}

    missing_meta = chapters_used - set(CHAPTERS_META)
    assert not missing_meta, (
        f"以下章节被关卡引用但未在 CHAPTERS_META 中定义: {sorted(missing_meta)}；"
        f"请在 app/metadata.py 的 CHAPTERS_META 中补充章节元数据"
    )

    extra_meta = set(CHAPTERS_META) - chapters_used
    assert not extra_meta, (
        f"CHAPTERS_META 中存在未被任何关卡引用的章节: {sorted(extra_meta)}；"
        f"请检查是否删除了整章关卡但未清理 CHAPTERS_META"
    )

    assert len(CHAPTERS_META) == len(chapters_used), (
        f"CHAPTERS_META 条目数 ({len(CHAPTERS_META)}) 与实际使用的章节数 "
        f"({len(chapters_used)}) 不一致"
    )


# ---------------------------------------------------------------------------
# 7. 四处计数必须完全一致：关卡数 == 知识点数 == XP数 == 知识域并集数
# ---------------------------------------------------------------------------
def test_level_count_consistency():
    level_count = len(list_levels())
    kp_count = len(KNOWLEDGE_POINTS)
    xp_count = len(LEVEL_XP)
    domain_count = len(_domain_level_ids())

    assert level_count == kp_count == xp_count == domain_count, (
        f"计数不一致: list_levels()={level_count}, "
        f"KNOWLEDGE_POINTS={kp_count}, LEVEL_XP={xp_count}, "
        f"知识域并集={domain_count}；"
        f"新增关卡时请同步更新 metadata.py 的全部四处配置"
    )
