from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from dataclasses import fields as dataclass_fields
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import traceback
from pydantic import BaseModel
from app.validator import get_level, list_levels, CheckResult, Lesson
from app.simulator import ClusterState
from app.metadata import get_all_meta, KNOWLEDGE_POINTS, LEVEL_XP, CHAPTER_BONUS_XP, get_rank, get_next_rank, KNOWLEDGE_DOMAINS, CHAPTERS_META
from app.cluster import ClusterManager


def _build_cluster_state(state: ClusterState | None) -> dict | None:
    """动态构建 cluster_state: 遍历 ClusterState 的所有字段, 只返回非空 dict 字段。

    替代之前硬编码 pods/deployments/services 三种资源的做法,
    确保 ConfigMap/Secret/PV/Ingress/NetworkPolicy/CRD 等 28 种资源
    都能被前端看到。
    """
    if state is None:
        return None
    result: dict = {}
    for f in dataclass_fields(state):
        value = getattr(state, f.name)
        if isinstance(value, dict) and value:
            result[f.name] = value
    return result if result else None

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

@app.get("/api/admin/all-levels")
async def api_admin_all_levels():
    """后门模式：返回所有关卡完整信息（题目/模板/教学内容）。"""
    all_data = []
    for ch_id in sorted(CHAPTERS_META.keys()):
        ch_meta = CHAPTERS_META[ch_id]
        ch_levels = list_levels(ch_id)
        chapter_data = {
            "chapter": ch_id,
            "title": ch_meta["title"],
            "icon": ch_meta["icon"],
            "color": ch_meta["color"],
            "description": ch_meta["description"],
            "difficulty": ch_meta["difficulty"],
            "levels": []
        }
        for lv_info in ch_levels:
            lv = get_level(lv_info["id"])
            if not lv:
                continue
            level_data = {
                "id": lv.id,
                "title": lv.title,
                "description": lv.description,
                "starter_yaml": lv.starter_yaml,
                "knowledge_points": KNOWLEDGE_POINTS.get(lv.id, []),
                "xp": LEVEL_XP.get(lv.id, 10),
                "lesson": None,
            }
            if lv.lesson:
                level_data["lesson"] = {
                    "concept": lv.lesson.concept,
                    "key_fields": lv.lesson.key_fields,
                    "diagram": lv.lesson.diagram,
                    "example_yaml": lv.lesson.example_yaml,
                    "common_errors": lv.lesson.common_errors,
                    "tips": lv.lesson.tips,
                }
            chapter_data["levels"].append(level_data)
        all_data.append(chapter_data)
    return {"chapters": all_data, "total_levels": sum(len(ch["levels"]) for ch in all_data)}

@app.post("/api/check", response_model=CheckResponse)
async def api_check(req: CheckRequest):
    # 顶层 try/except 兜底: 任何未捕获异常都转为 200 ok=False, 绝不泄漏成 HTTP 500。
    # (止血: 校验/模拟器深层的非 dict 输入仍可能抛 AttributeError/TypeError, 在此统一兜底。)
    try:
        lv = get_level(req.level_id)
        if not lv:
            return CheckResponse(ok=False, error=f"找不到关卡 {req.level_id}")

        # ══ 双轨制: Ch28 集群模式接入真实 kubectl 执行验证 ══
        # Ch28 (实战级) 在集群模式下，执行真实 kubectl 命令并验证结果
        # 其他章节 (认知级/基础级) 继续使用模拟器 check_fn
        if CLUSTER_MGR.enabled and lv.chapter == "ch28":
            cluster_result = await CLUSTER_MGR.verify_ch28(req.level_id, req.user_yaml)
            return CheckResponse(
                ok=cluster_result["ok"],
                error=cluster_result.get("error", ""),
                hints=cluster_result.get("hints", []),
                cluster_state=None,  # 真实集群状态通过 /api/resources 获取
            )

        # 模拟器模式 (认知级/基础级): 使用 check_fn 校验
        result = lv.check_fn(req.user_yaml)
        state_dict = _build_cluster_state(result.state)
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
    # 获取章节 track (关卡 track 优先，否则继承章节 track)
    ch_meta = CHAPTERS_META.get(lv.chapter, {})
    track = lv.track or ch_meta.get("track", "基础级")
    return {
        "id": lv.id,
        "chapter": lv.chapter,
        "title": lv.title,
        "description": lv.description,
        "starter_yaml": lv.starter_yaml,
        "knowledge_points": KNOWLEDGE_POINTS.get(lv.id, []),
        "xp": LEVEL_XP.get(lv.id, 10),
        "track": track,
        "supports_cluster_verify": ch_meta.get("supports_cluster_verify", False),
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
    total_levels = len(KNOWLEDGE_POINTS)

    # ── 服务端重新计算 total_xp（安全：不信任客户端提交的值）──
    client_xp = req.total_xp
    server_xp = sum(LEVEL_XP.get(lid, 10) for lid in completed)
    # 章节通关奖励：检查每章是否全部完成
    for ch_id in CHAPTERS_META:
        ch_num = int(ch_id[2:])
        ch_levels = [lid for lid in KNOWLEDGE_POINTS if lid.startswith(f"Q{ch_num}.")]
        if ch_levels and all(lid in completed for lid in ch_levels):
            server_xp += CHAPTER_BONUS_XP.get(ch_id, 0)

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

    # 7. 称号（基于服务端计算的 XP）
    rank = get_rank(server_xp)
    next_rank, xp_needed = get_next_rank(server_xp)

    # 8. 章节完成情况
    chapter_stats = {}
    for ch_id, ch_meta in CHAPTERS_META.items():
        ch_num = int(ch_id[2:])
        ch_levels = [lid for lid in KNOWLEDGE_POINTS if lid.startswith(f"Q{ch_num}.")]
        ch_completed = [lid for lid in ch_levels if lid in completed]
        chapter_stats[ch_id] = {
            "title": ch_meta["title"],
            "icon": ch_meta["icon"],
            "total": len(ch_levels),
            "completed": len(ch_completed),
            "rate": len(ch_completed) / len(ch_levels) if ch_levels else 0,
        }

    result = {
        "grade": grade,
        "grade_comment": grade_comment,
        "completion_rate": completion_rate,
        "completed_count": len(completed),
        "total_levels": total_levels,
        "total_xp": server_xp,
        "server_calculated_xp": server_xp,
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
    if client_xp != server_xp:
        result["warning"] = (
            f"客户端提交的 total_xp({client_xp})与服务端计算值({server_xp})不一致，已使用服务端计算值"
        )
    return result

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
        state_dict = _build_cluster_state(result.state)
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
    """获取集群连接状态，包含双轨制信息。"""
    status = CLUSTER_MGR.get_status()
    # 附加双轨制信息
    status["ch28_cluster_verify"] = CLUSTER_MGR.enabled  # Ch28 集群验证是否可用
    return status


# ═══ v2.3 新增: Ch28 集群验证详细结果端点 ═══

class ClusterCheckRequest(BaseModel):
    level_id: str
    user_input: str


@app.post("/api/check/cluster")
async def api_check_cluster(req: ClusterCheckRequest):
    """Ch28 集群模式验证：返回详细的命令执行结果。

    与 /api/check 的区别：
    - /api/check 返回简化的 CheckResponse (ok/error/hints)
    - /api/check/cluster 返回完整的执行结果 (含每条命令的输出)

    仅在集群模式下有效，否则返回模拟器模式提示。
    """
    lv = get_level(req.level_id)
    if not lv:
        return {"ok": False, "error": f"找不到关卡 {req.level_id}"}
    if lv.chapter != "ch28":
        return {"ok": False, "error": "此端点仅支持 Ch28 关卡"}
    if not CLUSTER_MGR.enabled:
        return {
            "ok": False,
            "mode": "simulator",
            "error": "集群模式未启用。当前为认知级模式（文本模式匹配）。",
            "hints": ["设置 K8S_QUEST_MODE=cluster 并配置 KUBECONFIG 以启用实战级验证"],
        }
    result = await CLUSTER_MGR.verify_ch28(req.level_id, req.user_input)
    return result


# ═══ v2.0 新增: 交互式 Kubectl 终端 ═══

class KubectlRequest(BaseModel):
    command: str
    force: bool = False  # 确认执行危险命令


@app.post("/api/kubectl")
async def api_kubectl(req: KubectlRequest):
    """执行 kubectl 命令（经过安全验证）。

    - 模拟器模式：返回提示信息
    - 集群模式：执行命令并返回输出
    - 危险命令（delete/scale/rollout等）需要 force=true
    """
    result = await CLUSTER_MGR.kubectl_exec(req.command, force=req.force)
    return result


@app.get("/api/kubectl/whitelist")
async def api_kubectl_whitelist():
    """返回允许的 kubectl 子命令列表（供前端自动补全）。"""
    return {
        "allowed": sorted(ClusterManager.ALLOWED_SUBCOMMANDS),
        "dangerous": sorted(ClusterManager.DANGEROUS_SUBCOMMANDS),
        "namespace": CLUSTER_MGR.namespace,
        "mode": "cluster" if CLUSTER_MGR.enabled else "simulator",
    }


# ═══ v2.2 新增: 进度导入导出 API ═══

# 校验密钥（可通过环境变量覆盖，防止客户端篡改导出数据）
PROGRESS_SECRET = os.getenv("K8S_QUEST_PROGRESS_SECRET", "k8s-quest-progress-2024")


def _calculate_server_xp(completed_levels: list[str]) -> int:
    """服务端重新计算 total_xp（不信任客户端提交的值）。

    逻辑与 /api/report 完全一致：
    1. 每个已完成关卡 +LEVEL_XP
    2. 章节全部完成 +CHAPTER_BONUS_XP
    """
    completed = set(completed_levels)
    server_xp = sum(LEVEL_XP.get(lid, 10) for lid in completed)
    for ch_id in CHAPTERS_META:
        ch_num = int(ch_id[2:])
        ch_levels = [lid for lid in KNOWLEDGE_POINTS if lid.startswith(f"Q{ch_num}.")]
        if ch_levels and all(lid in completed for lid in ch_levels):
            server_xp += CHAPTER_BONUS_XP.get(ch_id, 0)
    return server_xp


def _calculate_checksum(completed_levels: list[str]) -> str:
    """根据 completed_levels + 服务端密钥生成 SHA-256 校验码。

    用于防止客户端篡改导出的进度数据。
    """
    data = json.dumps(sorted(completed_levels), sort_keys=True)
    return hashlib.sha256((data + PROGRESS_SECRET).encode()).hexdigest()


@app.post("/api/progress/export")
async def api_progress_export(req: ReportRequest):
    """导出进度：接收学员进度数据，服务端重算 XP，返回带签名的完整 JSON。

    返回字段：
    - completed_levels / level_attempts / level_first_try / level_time_spent: 原样回传
    - total_xp: 服务端重新计算（不信任客户端值）
    - exported_at: 导出时间（ISO 8601）
    - level_count: 已完成关卡数
    - completion_rate: 完成率 (0.0 ~ 1.0)
    - checksum: 防篡改签名
    """
    server_xp = _calculate_server_xp(req.completed_levels)
    total_levels = len(KNOWLEDGE_POINTS)
    completion_rate = len(req.completed_levels) / total_levels if total_levels > 0 else 0
    checksum = _calculate_checksum(req.completed_levels)

    return {
        "completed_levels": req.completed_levels,
        "level_attempts": req.level_attempts,
        "level_first_try": req.level_first_try,
        "level_time_spent": req.level_time_spent,
        "total_xp": server_xp,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "level_count": len(req.completed_levels),
        "completion_rate": completion_rate,
        "checksum": checksum,
    }


class ImportRequest(BaseModel):
    """导入进度数据（与导出 JSON 结构一致）。"""
    completed_levels: list[str] = []
    level_attempts: dict[str, int] = {}
    level_first_try: list[str] = []
    level_time_spent: dict[str, int] = {}
    total_xp: int = 0
    exported_at: str = ""
    level_count: int = 0
    completion_rate: float = 0.0
    checksum: str = ""


@app.post("/api/progress/import")
async def api_progress_import(req: ImportRequest):
    """导入进度：验证 checksum，返回验证结果。

    - 验证通过: 返回 valid=True + 服务端重算的统计信息
    - 验证失败: 返回 valid=False
    - 不存储到服务端（个人工具，仅验证）
    """
    expected_checksum = _calculate_checksum(req.completed_levels)
    valid = req.checksum == expected_checksum

    if valid:
        server_xp = _calculate_server_xp(req.completed_levels)
        total_levels = len(KNOWLEDGE_POINTS)
        completion_rate = len(req.completed_levels) / total_levels if total_levels > 0 else 0
    else:
        server_xp = 0
        completion_rate = 0.0

    return {
        "valid": valid,
        "total_xp": server_xp,
        "completion_rate": completion_rate,
        "level_count": len(req.completed_levels),
    }


# ═══ v2.2 新增: 实操模块（YAML 存文件 + 用户自主 kubectl apply） ═══

class PlaygroundSaveRequest(BaseModel):
    level_id: str
    yaml_content: str


@app.post("/api/playground/save")
async def api_playground_save(req: PlaygroundSaveRequest):
    """保存用户 YAML 到文件，供终端手动 kubectl apply 使用。

    不是自动部署——用户自己在终端中执行 kubectl apply -f <filepath>。
    """
    import os

    save_dir = "/tmp/k8s-quest"
    os.makedirs(save_dir, exist_ok=True)

    # 文件名: Q1_1.yaml
    safe_name = req.level_id.replace(".", "_")
    filename = f"{safe_name}.yaml"
    filepath = os.path.join(save_dir, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(req.yaml_content)
    except Exception as e:
        return {"ok": False, "error": f"保存失败: {e}"}

    return {
        "ok": True,
        "filepath": filepath,
        "filename": filename,
        "hint": f"YAML 已保存到 {filepath}",
        "apply_command": f"kubectl apply -f {filepath}",
        "verify_command": f"kubectl get all",
    }


@app.get("/api/playground/levels")
async def api_playground_levels():
    """返回支持实操模块的关卡列表。"""
    from app.metadata import CHAPTERS_META
    # 关键关卡：需要用户直接与 K8s 交互的章节
    playground_levels = {
        "Q0.1", "Q0.3",           # 架构总览：创建Node/Pod+Service
        "Q1.1", "Q1.6",           # Pod基础：第一个Pod + 探针
        "Q2.1", "Q2.3",           # Deployment：创建 + 滚动更新
        "Q3.1",                   # Service：创建并测试连通性
        "Q6.1",                   # 调度：nodeSelector
        "Q9.5",                   # RBAC实战：验证权限
        "Q12.5",                  # NetworkPolicy实战：验证流量隔离
        "Q13.1",                  # DaemonSet：每个节点一个
        "Q17.1",                  # CRD：创建自定义资源
        "Q22.1",                  # 故障排查：CrashLoopBackOff
        "Q28.1", "Q28.2", "Q28.5", # CKA：kubectl操作挑战
    }
    return {
        "levels": sorted(playground_levels),
        "save_dir": "/tmp/k8s-quest",
    }


# 静态前端挂载放在最后，避免吞掉上面的 /api/* 路由。
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
