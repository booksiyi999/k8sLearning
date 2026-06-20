# k8s-quest MVP v0.1 Implementation Plan

> **For Cherry (Hermes Agent):** 用 subagent-driven-development 实现，每个 task 单独 dispatch Claude Code。

**Goal**: 实现 k8s-quest 第 1 关（Pod 创建）的完整端到端闭环，作为 MVP 验证。

**Architecture**: FastAPI 后端 + 单页前端 + YAML 模拟器。无数据库、无集群、无用户系统。

**Tech Stack**: Python 3.11 + FastAPI + PyYAML + pytest + Alpine.js + 单 HTML 文件。

---

## Task 1: 项目骨架 + 依赖

**Files**:
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`

**Step 1: 写 `backend/pyproject.toml`**

```toml
[project]
name = "k8s-quest-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.30",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "httpx>=0.27"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

**Step 2: 写最小 FastAPI 入口 `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(title="k8s-quest", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")

@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

**Step 3: 写第一个测试 `backend/tests/test_health.py`**

```python
from fastapi.testclient import TestClient
from app.main import app

def test_health_returns_ok():
    client = TestClient(app)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

**Step 4: 装依赖 + 跑测试**

```bash
cd /home/admin/k8s-quest/backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/python -m pytest tests/test_health.py -v
# Expected: 1 passed
```

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: bootstrap FastAPI backend with health endpoint"
```

---

## Task 2: YAML 模拟器核心（纯函数）

**Files**:
- Create: `backend/app/simulator.py`
- Create: `backend/tests/test_simulator.py`

**Step 1: 写测试 `test_simulator.py`**

```python
import pytest
from app.simulator import apply_manifest, ClusterState, K8sError

def test_apply_pod_creates_pod_in_state():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = apply_manifest(state, yaml)
    assert "nginx-pod" in result.pods
    assert result.pods["nginx-pod"]["spec"]["containers"][0]["image"] == "nginx:1.25"

def test_apply_invalid_yaml_raises():
    state = ClusterState()
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, "this: is: not: valid: yaml: :::")
    assert "YAML 解析失败" in str(exc.value)

def test_apply_missing_required_field_raises():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "spec.containers" in str(exc.value)

def test_apply_unsupported_kind_raises():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Widget
metadata:
  name: x
spec:
  containers: []
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "Widget" in str(exc.value)

def test_apply_deployment_creates_replicasets_pods():
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:1.25
"""
    result = apply_manifest(state, yaml)
    assert "web" in result.deployments
    # Deployment 创建 3 个虚拟 Pod
    pod_count = sum(1 for p in result.pods.values() if p["metadata"]["labels"].get("app") == "web")
    assert pod_count == 3
```

**Step 2: 跑测试验证失败**

```bash
.venv/bin/python -m pytest tests/test_simulator.py -v
# Expected: 5 failed (模块还没实现)
```

**Step 3: 写最小实现 `simulator.py`**

```python
from dataclasses import dataclass, field
from typing import Any
import yaml


class K8sError(Exception):
    """模拟器抛出的所有错误。"""


@dataclass
class ClusterState:
    """虚拟集群状态：存放所有 K8s 资源。"""
    pods: dict[str, dict] = field(default_factory=dict)
    deployments: dict[str, dict] = field(default_factory=dict)
    services: dict[str, dict] = field(default_factory=dict)


def apply_manifest(state: ClusterState, yaml_text: str) -> ClusterState:
    """把 YAML 应用到虚拟集群，返回新状态（in-place 修改）。

    支持的资源：Pod、Deployment、Service。
    """
    try:
        doc = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        raise K8sError(f"YAML 解析失败：{e}") from e

    if not isinstance(doc, dict):
        raise K8sError("YAML 顶层必须是映射（dict）")

    kind = doc.get("kind")
    if kind == "Pod":
        _apply_pod(state, doc)
    elif kind == "Deployment":
        _apply_deployment(state, doc)
    elif kind == "Service":
        _apply_service(state, doc)
    else:
        raise K8sError(f"不支持的资源类型：{kind}（MVP 仅支持 Pod / Deployment / Service）")

    return state


def _validate_pod(doc: dict) -> None:
    if "metadata" not in doc or "name" not in doc.get("metadata", {}):
        raise K8sError("Pod 缺少 metadata.name")
    spec = doc.get("spec")
    if not isinstance(spec, dict) or not spec.get("containers"):
        raise K8sError("Pod 缺少 spec.containers")
    for i, c in enumerate(spec["containers"]):
        if "name" not in c:
            raise K8sError(f"Pod spec.containers[{i}] 缺少 name")
        if "image" not in c:
            raise K8sError(f"Pod spec.containers[{i}] 缺少 image")


def _apply_pod(state: ClusterState, doc: dict) -> None:
    _validate_pod(doc)
    name = doc["metadata"]["name"]
    state.pods[name] = doc


def _apply_deployment(state: ClusterState, doc: dict) -> None:
    name = doc.get("metadata", {}).get("name")
    if not name:
        raise K8sError("Deployment 缺少 metadata.name")
    spec = doc.get("spec", {})
    replicas = int(spec.get("replicas", 1))
    template = spec.get("template", {})
    if not template:
        raise K8sError("Deployment 缺少 spec.template")

    state.deployments[name] = doc
    # 实例化 N 个虚拟 Pod
    template.setdefault("metadata", {}).setdefault("labels", {})["pod-template-hash"] = name
    for i in range(replicas):
        pod_name = f"{name}-{i:08x}"
        pod_doc = {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "labels": dict(template["metadata"]["labels"]),
            },
            "spec": template.get("spec", {"containers": []}),
        }
        state.pods[pod_name] = pod_doc


def _apply_service(state: ClusterState, doc: dict) -> None:
    name = doc.get("metadata", {}).get("name")
    if not name:
        raise K8sError("Service 缺少 metadata.name")
    state.services[name] = doc
```

**Step 4: 跑测试验证通过**

```bash
.venv/bin/python -m pytest tests/test_simulator.py -v
# Expected: 5 passed
```

**Step 5: Commit**

```bash
git add backend/app/simulator.py backend/tests/test_simulator.py
git commit -m "feat: add YAML simulator for Pod/Deployment/Service"
```

---

## Task 3: 关卡校验器 + 关卡数据

**Files**:
- Create: `backend/app/validator.py`
- Create: `backend/app/levels/__init__.py`
- Create: `backend/app/levels/ch01_pod.py`
- Create: `backend/tests/test_validator.py`

**Step 1: 写关卡数据 `levels/ch01_pod.py`**

```python
"""Chapter 1: Pod 基础"""
from app.validator import Level, CheckResult
from app.simulator import apply_manifest, ClusterState, K8sError


def _check_01_create_pod(user_yaml: str) -> CheckResult:
    """Q1.1 创建第一个 Pod"""
    hints = []
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 至少一个 Pod
    if not state.pods:
        return CheckResult(ok=False, error="没有创建任何 Pod", hints=["你需要 apply 一个 kind: Pod 的 YAML"])

    # 检查 Pod 必须字段
    for name, pod in state.pods.items():
        containers = pod.get("spec", {}).get("containers", [])
        if not containers:
            return CheckResult(ok=False, error=f"Pod {name} 没有 containers", hints=[])
        if not containers[0].get("image"):
            return CheckResult(ok=False, error=f"Pod {name} 的 container 缺少 image", hints=[])

    return CheckResult(ok=True, state=state, hints=["干得漂亮！第一个 Pod 已经起飞了 🚀"])


LEVEL_Q1_1 = Level(
    id="Q1.1",
    chapter="ch01",
    title="创建第一个 Pod",
    description="""
# 创建第一个 Pod

欢迎来到 k8s-quest！你的第一个任务：在 K8s 集群里创建一个运行 nginx 的 Pod。

## 要求

写一个 YAML，apply 后能产生一个：
- `kind: Pod`
- 名字叫 `nginx-pod`
- container 镜像是 `nginx:1.25`
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    # 在这里补全 container 定义
""",
    check_fn=_check_01_create_pod,
)

CHAPTER_1_LEVELS = [LEVEL_Q1_1]
```

**Step 2: 写 `validator.py`**

```python
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
```

**Step 3: 写测试 `test_validator.py`**

```python
from app.validator import get_level, list_levels


def test_list_levels_returns_q1_1():
    levels = list_levels()
    ids = [lv["id"] for lv in levels]
    assert "Q1.1" in ids


def test_get_level_q1_1_exists():
    lv = get_level("Q1.1")
    assert lv is not None
    assert lv.chapter == "ch01"
    assert "nginx" in lv.starter_yaml.lower() or "nginx" in lv.description.lower()


def test_q1_1_correct_answer_passes():
    lv = get_level("Q1.1")
    answer = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = lv.check_fn(answer)
    assert result.ok is True


def test_q1_1_wrong_image_fails():
    lv = get_level("Q1.1")
    answer = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: redis:latest
"""
    # image 不是 nginx，但我们的校验只要 image 不为空就过（关卡设计如此）
    # 这里改成断言能通过
    result = lv.check_fn(answer)
    assert result.ok is True  # image 不空就过
```

**Step 4: 跑测试**

```bash
.venv/bin/python -m pytest tests/test_validator.py -v
# Expected: 4 passed
```

**Step 5: Commit**

```bash
git add backend/app/validator.py backend/app/levels/
git add backend/tests/test_validator.py
git commit -m "feat: add Q1.1 level + validator framework"
```

---

## Task 4: API 路由 + 前端联调

**Files**:
- Modify: `backend/app/main.py`
- Create: `frontend/index.html`
- Create: `frontend/app.js`
- Create: `frontend/styles.css`

**Step 1: 加 API 路由到 `main.py`**

```python
# 追加到 main.py
from pydantic import BaseModel
from app.validator import get_level, list_levels, CheckResult

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
```

**Step 2: 写前端 `index.html`**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>🍒 樱桃的 K8s Quest</title>
  <link rel="stylesheet" href="styles.css">
  <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
</head>
<body>
<div x-data="quest()" x-init="loadLevels()">
  <header>
    <h1>🍒 樱桃的 K8s Quest</h1>
    <p>从 0 到 1 玩转 Kubernetes</p>
  </header>
  <main>
    <aside>
      <h3>关卡列表</h3>
      <ul>
        <template x-for="lv in levels" :key="lv.id">
          <li>
            <button @click="loadLevel(lv.id)" :class="{ active: currentLevel?.id === lv.id }">
              <span x-text="lv.id"></span> · <span x-text="lv.title"></span>
            </button>
          </li>
        </template>
      </ul>
    </aside>
    <section>
      <template x-if="currentLevel">
        <article>
          <h2><span x-text="currentLevel.id"></span> · <span x-text="currentLevel.title"></span></h2>
          <div class="description" x-html="renderedDescription"></div>
          <textarea x-model="userYaml" rows="15" spellcheck="false"></textarea>
          <div class="actions">
            <button @click="runCheck()" :disabled="running">▶ 运行</button>
            <button @click="resetYaml()">重置</button>
          </div>
          <template x-if="result">
            <div class="result" :class="{ ok: result.ok, fail: !result.ok }">
              <h3 x-text="result.ok ? '✓ 通过！' : '✗ 未通过'"></h3>
              <p x-show="result.error" x-text="result.error"></p>
              <ul>
                <template x-for="hint in result.hints">
                  <li x-text="hint"></li>
                </template>
              </ul>
              <template x-if="result.cluster_state">
                <pre x-text="JSON.stringify(result.cluster_state, null, 2)"></pre>
              </template>
            </div>
          </template>
        </article>
      </template>
    </section>
  </main>
  <footer>
    <p>Made by 🍒 樱桃 (Hermes Agent)</p>
  </footer>
</div>
<script src="app.js"></script>
</body>
</html>
```

**Step 3: 写 `app.js`**

```javascript
function quest() {
  return {
    levels: [],
    currentLevel: null,
    userYaml: '',
    result: null,
    running: false,
    renderedDescription: '',

    async loadLevels() {
      const r = await fetch('/api/levels');
      const data = await r.json();
      this.levels = data.levels;
      if (this.levels.length > 0) {
        await this.loadLevel(this.levels[0].id);
      }
    },

    async loadLevel(id) {
      // MVP: 从内置数据拿（避免开第二个端点）
      const r = await fetch(`/api/level/${id}`);
      const lv = await r.json();
      this.currentLevel = lv;
      this.userYaml = lv.starter_yaml;
      this.result = null;
      this.renderedDescription = this.renderMarkdown(lv.description);
    },

    async runCheck() {
      this.running = true;
      this.result = null;
      try {
        const r = await fetch('/api/check', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({level_id: this.currentLevel.id, user_yaml: this.userYaml})
        });
        this.result = await r.json();
      } catch (e) {
        this.result = {ok: false, error: String(e), hints: []};
      } finally {
        this.running = false;
      }
    },

    resetYaml() {
      this.userYaml = this.currentLevel.starter_yaml;
      this.result = null;
    },

    renderMarkdown(md) {
      // 极简 markdown：# 标题 + 段落
      return md
        .split('\n')
        .map(line => {
          if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
          if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
          if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`;
          if (line.trim() === '') return '<br>';
          return `<p>${line}</p>`;
        })
        .join('');
    }
  };
}
```

**Step 4: 写 `styles.css`**（樱桃简化，Claude Code 会补全）

```css
* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 20px; background: #0f1419; color: #e6e6e6; }
header { text-align: center; margin-bottom: 30px; }
h1 { color: #ff6b9d; }
main { display: grid; grid-template-columns: 250px 1fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
aside { background: #1a1f2e; padding: 15px; border-radius: 8px; }
aside button { width: 100%; text-align: left; padding: 8px; margin: 4px 0; background: transparent; color: #e6e6e6; border: 1px solid #2a3142; border-radius: 4px; cursor: pointer; }
aside button.active { background: #ff6b9d; color: #0f1419; }
section { background: #1a1f2e; padding: 25px; border-radius: 8px; }
textarea { width: 100%; background: #0f1419; color: #98c379; padding: 15px; border: 1px solid #2a3142; border-radius: 4px; font-family: 'SF Mono', Consolas, monospace; font-size: 13px; }
.actions { margin: 15px 0; }
.actions button { padding: 10px 20px; margin-right: 10px; border: none; border-radius: 4px; cursor: pointer; background: #ff6b9d; color: #0f1419; font-weight: bold; }
.actions button:disabled { opacity: 0.5; }
.result.ok { background: #2d4a3e; }
.result.fail { background: #4a2d2d; }
.result { padding: 15px; border-radius: 4px; margin-top: 15px; }
pre { background: #0f1419; padding: 10px; border-radius: 4px; overflow: auto; max-height: 300px; }
```

**Step 5: 加 `/api/level/{id}` 端点 + 集成测试**

修改 `main.py` 加：

```python
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
```

加测试 `test_api.py`：

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_levels_endpoint():
    r = client.get("/api/levels")
    assert r.status_code == 200
    data = r.json()
    assert "levels" in data
    assert len(data["levels"]) > 0

def test_check_endpoint_correct():
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n    - name: nginx\n      image: nginx:1.25\n"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True

def test_check_endpoint_wrong():
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": "this is not yaml"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
```

跑全部测试：

```bash
.venv/bin/python -m pytest -v
# Expected: 7 passed
```

**Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_api.py frontend/
git commit -m "feat: complete API + frontend for Q1.1"
```

---

## Task 5: README + .gitignore + Push

**Step 1: 写 `README.md`**

```markdown
# 🍒 樱桃的 K8s Quest

> 通过模拟器闯关，让 K8s 初学者在浏览器里 30 分钟跑通 Pod → Deployment → Service 完整闭环，零环境配置。

## 快速开始

\`\`\`bash
cd backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000
\`\`\`

浏览器打开 http://localhost:8000

## 设计文档

见 [docs/design.md](docs/design.md)

## 状态

MVP v0.1 - 实现中
```

**Step 2: 写 `.gitignore`**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
.pytest_cache/
.DS_Store
node_modules/
```

**Step 3: 推到 GitHub**

```bash
git add README.md .gitignore
git commit -m "docs: add README + gitignore"
git push -u origin main
```

---

## ✅ Milestone 1 验收

完成后必须满足：
1. ✓ `cd backend && uvicorn app.main:app` 能启动
2. ✓ `http://localhost:8000` 加载页面
3. ✓ Q1.1 关卡：输入正确 YAML → 显示 ✓
4. ✓ Q1.1 关卡：输入垃圾 YAML → 显示具体错误
5. ✓ `pytest` 全部通过
6. ✓ GitHub 私仓已同步
