"""止血契约测试: /api/check 顶层 try/except 兜底。

任何未捕获异常都必须被兜底为 200 ok=False，绝不能泄漏成 HTTP 500。
覆盖 QA round-4 repro 的 6 个 bucket-B 残留向量 (labels/template.metadata 各类非 dict 输入)。
"""
from fastapi.testclient import TestClient
from app.main import app

# raise_server_exceptions=False 模拟真实 HTTP 行为:
# 服务器内部异常应被 endpoint 自己兜底, 而不是冒泡成 500。
client = TestClient(app, raise_server_exceptions=False)

# 6 个原 500 向量 (来自 QA round-4 repro bucket B)
BLEEDING_VECTORS = [
    ("Q1.2 labels:str", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: "foo"
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""),
    ("Q1.2 labels:int", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: 5
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""),
    ("Q1.2 labels:null", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: null
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""),
    ("Deployment template.metadata:str", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec:
  replicas: 2
  template:
    metadata: "foo"
    spec:
      containers:
        - name: c
          image: nginx:1.25
"""),
    ("Deployment template.metadata.labels:str", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec:
  replicas: 2
  template:
    metadata:
      labels: "foo"
    spec:
      containers:
        - name: c
          image: nginx:1.25
"""),
    ("Deployment template.metadata.labels:int", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec:
  replicas: 2
  template:
    metadata:
      labels: 5
    spec:
      containers:
        - name: c
          image: nginx:1.25
"""),
]


def test_bleeding_vectors_never_500():
    """6 个原 500 向量必须全部兜底为 200 ok=False。"""
    failures = []
    for name, level_id, yaml_text in BLEEDING_VECTORS:
        r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
        body = r.json()
        if r.status_code != 200 or body.get("ok") is not False:
            failures.append(
                f"{name}: HTTP {r.status_code} ok={body.get('ok')} err={body.get('error', '')[:60]!r}"
            )
    assert not failures, "止血失败 (应全部 200 ok=False):\n  " + "\n  ".join(failures)


def test_bleeding_response_has_error_message():
    """兜底返回的 error 字段必须非空 (不能静默吞异常)。"""
    r = client.post("/api/check", json={
        "level_id": "Q1.2",
        "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: redis-pod\n  labels: 5\nspec:\n  containers:\n    - name: redis\n      image: redis:7-alpine\n",
    })
    body = r.json()
    assert r.status_code == 200
    assert body["ok"] is False
    assert body["error"], "error 字段不能为空字符串"


def test_valid_path_unaffected():
    """止血不能误伤正常路径 (Q1.1 valid Pod 仍 200 ok=True)。"""
    r = client.post("/api/check", json={
        "level_id": "Q1.1",
        "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: nginx-pod\nspec:\n  containers:\n    - name: web\n      image: nginx:1.25\n",
    })
    body = r.json()
    assert r.status_code == 200
    assert body["ok"] is True
