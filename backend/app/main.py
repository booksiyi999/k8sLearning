from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import traceback
from pydantic import BaseModel
from app.validator import get_level, list_levels, CheckResult
from app.metadata import get_all_meta, KNOWLEDGE_POINTS, LEVEL_XP, get_rank, get_next_rank, KNOWLEDGE_DOMAINS, CHAPTERS_META

logger = logging.getLogger(__name__)

app = FastAPI(title="k8s-quest", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: StaticFiles 必须挂在所有 /api/* 路由之后，否则会作为 catch-all 把 API 请求吞掉。
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"

@app.get("/api/health")
async def health():
    return {"status": "ok"}

class CheckRequest(BaseModel):
    level_id: str
    user_yaml: str

class CheckResponse(BaseModel):
    ok: bool
    error: str = ""
    hints: list[str] = []
    cluster_state: dict | None = None

@app.get("/api/levels")
async def api_list_levels():
    return {"levels": list_levels()}

@app.post("/api/check", response_model=CheckResponse)
async def api_check(req: CheckRequest):
    # 顶层 try/except 兜底: 任何未捕获异常都转为 200 ok=False, 绝不泄漏成 HTTP 500。
    # (止血: 校验/模拟器深层的非 dict 输入仍可能抛 AttributeError/TypeError, 在此统一兜底。)
    try:
        lv = get_level(req.level_id)
        if not lv:
            return CheckResponse(ok=False, error=f"找不到关卡 {req.level_id}")
        result = lv.check_fn(req.user_yaml)
        state_dict = None
        if result.state:
            state_dict = {
                "pods": result.state.pods,
                "deployments": result.state.deployments,
                "services": result.state.services,
            }
        return CheckResponse(
            ok=result.ok,
            error=result.error,
            hints=result.hints,
            cluster_state=state_dict,
        )
    except Exception as e:
        # 记录完整 stack trace 到日志, 但不暴露给用户 (响应只带 str(e))。
        logger.error("unhandled exception in /api/check (level=%s): %s\n%s",
                     req.level_id, e, traceback.format_exc())
        return CheckResponse(ok=False, error=str(e))

@app.get("/api/level/{level_id}")
async def api_get_level(level_id: str):
    lv = get_level(level_id)
    if not lv:
        return {"error": f"找不到关卡 {level_id}"}
    return {
        "id": lv.id,
        "chapter": lv.chapter,
        "title": lv.title,
        "description": lv.description,
        "starter_yaml": lv.starter_yaml,
        "knowledge_points": KNOWLEDGE_POINTS.get(lv.id, []),
        "xp": LEVEL_XP.get(lv.id, 10),
    }

@app.get("/api/meta")
async def api_get_meta():
    """返回游戏化元数据：章节信息、知识点映射、XP 配置、等级称号。"""
    return get_all_meta()

class ReportRequest(BaseModel):
    """学员进度数据（前端 localStorage 上报）。"""
    completed_levels: list[str] = []
    level_attempts: dict[str, int] = {}   # level_id -> 尝试次数
    level_first_try: list[str] = []        # 一次通过关卡列表
    level_time_spent: dict[str, int] = {}  # level_id -> 秒
    total_xp: int = 0

@app.post("/api/report")
async def api_generate_report(req: ReportRequest):
    """生成结业报告：知识掌握度、薄弱项、成绩评定。"""
    completed = set(req.completed_levels)
    total_levels = 24

    # 1. 总体完成率
    completion_rate = len(completed) / total_levels if total_levels > 0 else 0

    # 2. 知识域掌握度
    domain_stats = {}
    for domain, level_ids in KNOWLEDGE_DOMAINS.items():
        domain_completed = [lid for lid in level_ids if lid in completed]
        domain_stats[domain] = {
            "total": len(level_ids),
            "completed": len(domain_completed),
            "rate": len(domain_completed) / len(level_ids) if level_ids else 0,
            "levels": [
                {
                    "id": lid,
                    "completed": lid in completed,
                    "attempts": req.level_attempts.get(lid, 0),
                    "first_try": lid in req.level_first_try,
                    "time_spent": req.level_time_spent.get(lid, 0),
                    "knowledge_points": KNOWLEDGE_POINTS.get(lid, []),
                }
                for lid in level_ids
            ],
        }

    # 3. 薄弱项识别（尝试次数 > 2 或未完成）
    weak_areas = []
    for lid in sorted(KNOWLEDGE_POINTS.keys()):
        if lid not in completed:
            weak_areas.append({
                "level_id": lid,
                "reason": "未完成",
                "knowledge_points": KNOWLEDGE_POINTS.get(lid, []),
            })
        elif req.level_attempts.get(lid, 0) > 2:
            weak_areas.append({
                "level_id": lid,
                "reason": f"尝试 {req.level_attempts[lid]} 次",
                "knowledge_points": KNOWLEDGE_POINTS.get(lid, []),
            })

    # 4. 优势项（一次通过）
    strengths = [
        {
            "level_id": lid,
            "knowledge_points": KNOWLEDGE_POINTS.get(lid, []),
        }
        for lid in req.level_first_try if lid in completed
    ]

    # 5. 成绩评定
    if completion_rate >= 1.0 and len(req.level_first_try) >= 20:
        grade = "S"
        grade_comment = "完美通关！你已掌握 K8s 核心技能，可以挑战 CKA 认证了 👑"
    elif completion_rate >= 0.9:
        grade = "A"
        grade_comment = "优秀！大部分知识点已掌握，再补几个薄弱项就完美了 🌟"
    elif completion_rate >= 0.7:
        grade = "B"
        grade_comment = "良好！K8s 基础扎实，继续深入练习薄弱章节 💪"
    elif completion_rate >= 0.5:
        grade = "C"
        grade_comment = "及格！已掌握基础概念，建议重做未完成的关卡 📚"
    else:
        grade = "D"
        grade_comment = "起步中！K8s 学习之路才刚开始，坚持就是胜利 🌱"

    # 6. 学习建议
    recommendations = []
    for domain, stats in domain_stats.items():
        if stats["rate"] == 0:
            recommendations.append(f"尚未开始「{domain}」章节，建议从第一章开始系统学习")
        elif stats["rate"] < 0.5:
            recommendations.append(f"「{domain}」掌握度偏低 ({stats['completed']}/{stats['total']})，建议重点复习")
        elif stats["rate"] < 1.0:
            recommendations.append(f"「{domain}」即将通关 ({stats['completed']}/{stats['total']})，再完成 {stats['total'] - stats['completed']} 关即可")

    # 7. 称号
    rank = get_rank(req.total_xp)
    next_rank, xp_needed = get_next_rank(req.total_xp)

    # 8. 章节完成情况
    chapter_stats = {}
    for ch_id, ch_meta in CHAPTERS_META.items():
        ch_levels = [lid for lid in KNOWLEDGE_POINTS if lid.startswith(f"Q{ch_id[-1]}.")]
        ch_completed = [lid for lid in ch_levels if lid in completed]
        chapter_stats[ch_id] = {
            "title": ch_meta["title"],
            "icon": ch_meta["icon"],
            "total": len(ch_levels),
            "completed": len(ch_completed),
            "rate": len(ch_completed) / len(ch_levels) if ch_levels else 0,
        }

    return {
        "grade": grade,
        "grade_comment": grade_comment,
        "completion_rate": completion_rate,
        "completed_count": len(completed),
        "total_levels": total_levels,
        "total_xp": req.total_xp,
        "rank": rank,
        "next_rank": next_rank,
        "xp_to_next_rank": xp_needed,
        "first_try_count": len(req.level_first_try),
        "total_attempts": sum(req.level_attempts.values()),
        "total_time_spent": sum(req.level_time_spent.values()),
        "domain_stats": domain_stats,
        "chapter_stats": chapter_stats,
        "weak_areas": weak_areas,
        "strengths": strengths,
        "recommendations": recommendations,
    }

# 静态前端挂载放在最后，避免吞掉上面的 /api/* 路由。
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
