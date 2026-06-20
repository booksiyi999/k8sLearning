from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel
from app.validator import get_level, list_levels, CheckResult

app = FastAPI(title="k8s-quest", version="0.1.0")

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
    }

# 静态前端挂载放在最后，避免吞掉上面的 /api/* 路由。
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
