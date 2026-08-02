from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging
import os
import traceback
from pydantic import BaseModel
from app.validator import get_level, list_levels, CheckResult, Lesson
from app.metadata import get_all_meta, KNOWLEDGE_POINTS, LEVEL_XP, get_rank, get_next_rank, KNOWLEDGE_DOMAINS, CHAPTERS_META
from app.cluster import ClusterManager

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

# ── 集群管理器（真实 K8s 模式可选） ──
_DEPLOY_MODE = os.getenv("K8S_QUEST_MODE", "simulator")
_KUBECONFIG = os.getenv("KUBECONFIG") or str(Path.home() / ".kube" / "config")
CLUSTER_MGR = ClusterManager(kubeconfig_path=_KUBECONFIG if _DEPLOY_MODE == "cluster" else None)

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

# ═══ v0.4 新增: 教学 + 集群 API ═══

@app.get("/api/lesson/{level_id}")
async def api_get_lesson(level_id: str):
    """获取关卡教学文档。"""
    lv = get_level(level_id)
    if not lv:
        return {"error": f"找不到关卡 {level_id}"}
    if not lv.lesson:
        return {"error": f"关卡 {level_id} 暂无教学文档", "has_lesson": False}
    lesson = lv.lesson
    return {
        "has_lesson": True,
        "level_id": lv.id,
        "concept": lesson.concept,
        "key_fields": lesson.key_fields,
        "diagram": lesson.diagram,
        "example_yaml": lesson.example_yaml,
        "common_errors": lesson.common_errors,
        "tips": lesson.tips,
    }


class DeployRequest(BaseModel):
    level_id: str
    user_yaml: str


@app.post("/api/deploy")
async def api_deploy(req: DeployRequest):
    """部署 YAML — 双模式：模拟器 or 真实集群。"""
    lv = get_level(req.level_id)
    if not lv:
        return {"ok": False, "error": f"找不到关卡 {req.level_id}"}

    # 真实集群模式
    if CLUSTER_MGR.enabled:
        deploy_result = await CLUSTER_MGR.apply(req.user_yaml)
        if not deploy_result["success"]:
            return {"ok": False, "mode": "cluster", "error": deploy_result["error"]}
        # 获取部署后的资源列表
        resources = await CLUSTER_MGR.get_resources("all")
        return {
            "ok": True,
            "mode": "cluster",
            "deploy_output": deploy_result["output"],
            "resources": resources,
        }

    # 模拟器模式（保持现有逻辑）
    try:
        result = lv.check_fn(req.user_yaml)
        state_dict = None
        if result.state:
            state_dict = {
                "pods": result.state.pods,
                "deployments": result.state.deployments,
                "services": result.state.services,
            }
        return {
            "ok": result.ok,
            "mode": "simulator",
            "error": result.error,
            "hints": result.hints,
            "cluster_state": state_dict,
        }
    except Exception as e:
        logger.error("deploy error (level=%s): %s\n%s", req.level_id, e, traceback.format_exc())
        return {"ok": False, "mode": "simulator", "error": str(e)}


@app.get("/api/resources")
async def api_get_resources(resource_type: str = "all"):
    """获取集群资源列表（仅集群模式）。"""
    if not CLUSTER_MGR.enabled:
        return {"mode": "simulator", "resources": [], "error": "未启用集群模式"}
    resources = await CLUSTER_MGR.get_resources(resource_type)
    return {"mode": "cluster", "resources": resources}


@app.get("/api/logs/{pod_name}")
async def api_get_logs(pod_name: str, tail: int = 50):
    """获取 Pod 日志（仅集群模式）。"""
    if not CLUSTER_MGR.enabled:
        return {"mode": "simulator", "logs": "", "error": "未启用集群模式"}
    logs = await CLUSTER_MGR.get_logs(pod_name, tail)
    return {"mode": "cluster", "logs": logs, "pod_name": pod_name}


class ConnectivityRequest(BaseModel):
    service_name: str
    port: int = 80


@app.post("/api/test-connectivity")
async def api_test_connectivity(req: ConnectivityRequest):
    """测试 Service 连通性（仅集群模式）。"""
    if not CLUSTER_MGR.enabled:
        return {"mode": "simulator", "reachable": False, "error": "未启用集群模式"}
    result = await CLUSTER_MGR.test_connectivity(req.service_name, req.port)
    return {"mode": "cluster", **result}


@app.get("/api/cluster/status")
async def api_cluster_status():
    """获取集群连接状态。"""
    return CLUSTER_MGR.get_status()


# 静态前端挂载放在最后，避免吞掉上面的 /api/* 路由。
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
