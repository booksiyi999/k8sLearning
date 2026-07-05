"""QA E2E boundary scan for round-4 re-review.

Tests three buckets via real FastAPI TestClient on /api/check:
  A) Engineer's 5 fixed vectors  -> expect 200 ok=False (regression check)
  B) QA's NEW suspected residuals -> expect 500 if bug present (the 5th-round finding)
  C) Valid Pod Q1.1               -> expect 200 ok=True (no regression)
"""
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

def post(level_id, yaml_text):
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    ok = None
    err = ""
    try:
        body = r.json()
        ok = body.get("ok")
        err = body.get("error", "")[:80]
    except Exception as e:
        err = f"<no json: {e}>"
    return r.status_code, ok, err

results = []

def case(name, level_id, yaml_text, expect_status, expect_ok=None, bucket=""):
    code, ok, err = post(level_id, yaml_text)
    status_tag = "PASS" if code == expect_status and (expect_ok is None or ok == expect_ok) else "FAIL"
    if bucket == "B" and code == 500:
        status_tag = "BUG-CONFIRMED"  # for bucket B, 500 is the finding, not a pass
    results.append((status_tag, bucket, name, code, ok, err))
    print(f"[{status_tag}] {bucket} {name}: HTTP {code} ok={ok} err={err!r}")

# ---------- A) Engineer's 5 fixed vectors (regression: must be 200 ok=False) ----------
print("=== A) Regression: 5 fixed vectors -> expect 200 ok=False ===")
case("R2 containers:5", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers: 5
""", 200, False, "A")

case("R1 template:foo", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec:
  replicas: 2
  template: foo
""", 200, False, "A")

case("Pod metadata:namefoo (substring bypass)", "Q1.1", """
apiVersion: v1
kind: Pod
metadata: namefoo
spec:
  containers:
    - name: c
      image: nginx:1.25
""", 200, False, "A")

case("Deployment spec:foo", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec: foo
""", 200, False, "A")

case("Deployment replicas:foo", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec:
  replicas: foo
  template: foo
""", 200, False, "A")

# ---------- B) QA NEW suspected residuals (5th-round) ----------
print("\n=== B) NEW suspected residuals -> 500 means BUG CONFIRMED ===")
# B1: _check_02 labels non-dict -> labels.get(k) AttributeError
case("B1 Q1.2 labels:str", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: "foo"
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""", 200, False, "B")

case("B1b Q1.2 labels:int", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: 5
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""", 200, False, "B")

case("B1c Q1.2 labels:null", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: null
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""", 200, False, "B")

# B2: _apply_deployment template.metadata non-dict -> setdefault AttributeError
case("B2 Deployment template.metadata:str", "Q1.1", """
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
""", 200, False, "B")

# B3: template.metadata.labels non-dict -> item assignment TypeError
case("B3 Deployment template.metadata.labels:str", "Q1.1", """
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
""", 200, False, "B")

# B4: template.metadata.labels:int -> dict(labels) ValueError
case("B4 Deployment template.metadata.labels:int", "Q1.1", """
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
""", 200, False, "B")

# ---------- C) Valid path regression ----------
print("\n=== C) Valid Pod Q1.1 -> expect 200 ok=True ===")
case("C valid Q1.1", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: nginx:1.25
""", 200, True, "C")

case("C valid Q1.2", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels:
    app: cache
    tier: backend
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""", 200, True, "C")

case("C valid Deployment", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
spec:
  replicas: 2
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: c
          image: nginx:1.25
""", 200, None, "C")

print("\n=== SUMMARY ===")
n_pass = sum(1 for r in results if r[0] == "PASS")
n_bug = sum(1 for r in results if r[0] == "BUG-CONFIRMED")
n_fail = sum(1 for r in results if r[0] == "FAIL")
print(f"PASS={n_pass} BUG-CONFIRMED(500)={n_bug} FAIL(unexpected)={n_fail}")
for r in results:
    if r[0] != "PASS":
        print("  !!", r)
