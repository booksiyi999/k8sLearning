from dataclasses import dataclass, field
from typing import Any, Callable
from app.simulator import ClusterState


@dataclass
class CheckResult:
    ok: bool
    state: ClusterState | None = None
    error: str = ""
    hints: list[str] = field(default_factory=list)


@dataclass
class Level:
    id: str
    chapter: str
    title: str
    description: str
    starter_yaml: str
    check_fn: Callable[[str], CheckResult]


def get_level(level_id: str) -> Level | None:
    """根据 id 查找关卡。"""
    from app.levels.ch01_pod import CHAPTER_1_LEVELS
    from app.levels.ch02_deployment import CHAPTER_2_LEVELS
    from app.levels.ch03_service import CHAPTER_3_LEVELS
    all_levels = CHAPTER_1_LEVELS + CHAPTER_2_LEVELS + CHAPTER_3_LEVELS
    for lv in all_levels:
        if lv.id == level_id:
            return lv
    return None


def list_levels(chapter: str | None = None) -> list[dict]:
    """列出关卡。chapter=None 返回全部，否则按 chapter 过滤。"""
    from app.levels.ch01_pod import CHAPTER_1_LEVELS
    from app.levels.ch02_deployment import CHAPTER_2_LEVELS
    from app.levels.ch03_service import CHAPTER_3_LEVELS
    all_levels = CHAPTER_1_LEVELS + CHAPTER_2_LEVELS + CHAPTER_3_LEVELS
    if chapter is not None:
        all_levels = [lv for lv in all_levels if lv.chapter == chapter]
    return [{"id": lv.id, "chapter": lv.chapter, "title": lv.title} for lv in all_levels]
