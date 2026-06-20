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
    all_levels = CHAPTER_1_LEVELS
    for lv in all_levels:
        if lv.id == level_id:
            return lv
    return None


def list_levels() -> list[dict]:
    from app.levels.ch01_pod import CHAPTER_1_LEVELS
    return [{"id": lv.id, "chapter": lv.chapter, "title": lv.title} for lv in CHAPTER_1_LEVELS]
