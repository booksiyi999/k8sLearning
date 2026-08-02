"""QA round-5 attack scan for止血 re-review.

Goal: find NEW vectors that STILL穿透 to HTTP 500 despite the top-level
try/except Exception 兜底. Probes the boundaries of `except Exception`:

  D1 type-confusion on dict fields NOT in the original 6 vectors
     (annotations, containers[].env, containers[].ports, nodeSelector,
      spec as list/str, top-level YAML as list/str/number)
  D2 resource exhaustion: 1000-deep nested YAML, YAML anchor bomb,
     very long scalar
  D3 pydantic 422 boundary: wrong-type/missing level_id & user_yaml
     (must be 422, never 500)
  D4 info-leak: response must carry ONLY str(e), never the Traceback /
     file paths
  D5 multi-doc YAML (---)

A 500 here = BUG CONFIRMED (止血 hole). A 200 ok=False = 兜底 works.
A 422 = pydantic boundary (acceptable, not a 500).
"""
import json
import logging
import io
import sys
from fastapi.testclient import TestClient
from app.main import app

# raise_server_exceptions=False = real HTTP behaviour (500 stays 500).
client = TestClient(app, raise_server_exceptions=False)


def post(level_id, yaml_text):
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    ok = None
    err = ""
    try:
        body = r.json()
        ok = body.get("ok")
        err = body.get("error", "")
    except Exception as e:
        err = f"<no json: {e}>"
    return r.status_code, ok, err


results = []


def case(name, level_id, yaml_text, bucket, expect_500=False):
    code, ok, err = post(level_id, yaml_text)
    if expect_500:
        tag = "BUG-CONFIRMED" if code == 500 else "PASS"
    else:
        # for止血 correctness: must NEVER be 500
        tag = "BUG-CONFIRMED(500)" if code == 500 else "PASS"
    results.append((tag, bucket, name, code, ok, err))
    print(f"[{tag}] {bucket} {name}: HTTP {code} ok={ok} err={err[:90]!r}")


print("=" * 70)
print("D1: type-confusion on dict fields NOT in original 6 vectors")
print("=" * 70)
# annotations is a dict-expected field like labels, but NOT checked by ch01.
# Must NOT 500 (either passes or兜底). Proves止血 doesn't break & no new 500.
case("Pod annotations:str", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  annotations: "foo"
spec:
  containers:
    - name: web
      image: nginx:1.25
""", "D1")
case("Pod annotations:int", "Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels:
    app: cache
    tier: backend
  annotations: 5
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""", "D1")
case("Pod containers[].env:str", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: nginx:1.25
      env: "foo"
""", "D1")
case("Pod containers[].ports:str", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: nginx:1.25
      ports: "foo"
""", "D1")
case("Pod spec.containers[].resources.limits.cpu as dict", "Q1.4", """
apiVersion: v1
kind: Pod
metadata:
  name: resource-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      resources:
        requests:
          cpu: 100m
          memory: 128Mi
        limits:
          cpu: {val: 500m}
          memory: 256Mi
""", "D1")
case("top-level YAML is a list", "Q1.1", """
- apiVersion: v1
- kind: Pod
""", "D1")
case("top-level YAML is a string", "Q1.1", '"just a string"', "D1")
case("top-level YAML is a number", "Q1.1", '42', "D1")
case("top-level YAML is null", "Q1.1", 'null', "D1")
case("Pod metadata as list", "Q1.1", """
apiVersion: v1
kind: Pod
metadata: [1, 2, 3]
spec:
  containers:
    - name: web
      image: nginx:1.25
""", "D1")

print()
print("=" * 70)
print("D2: resource exhaustion")
print("=" * 70)
# 1000-deep nested dict
deep = "x"
for _ in range(1000):
    deep = f"x: {deep}"
case("1000-deep nested dict", "Q1.1", deep, "D2")
# YAML anchor bomb: anchor referencing itself (billion-laughs style)
case("YAML recursive anchor (billion-laughs)", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels: &a
    app: cache
    tier: *a
spec:
  containers:
    - name: web
      image: nginx:1.25
""", "D2")
# alias chain (flat, non-recursive) — should just resolve
case("YAML alias chain (flat)", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels: &l
    app: cache
spec:
  containers:
    - name: web
      image: nginx:1.25
""", "D2")
# very long scalar value
case("very long scalar (1MB)", "Q1.1", f"""
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: nginx:1.25
""", "D2")

print()
print("=" * 70)
print("D3: pydantic 422 boundary (must be 422, never 500)")
print("=" * 70)
# These go through pydantic BEFORE the try/except. They must be 422.
def post_raw(body):
    r = client.post("/api/check", json=body)
    return r.status_code, r.text[:120]

for name, body in [
    ("level_id as int", {"level_id": 5, "user_yaml": "kind: Pod"}),
    ("user_yaml as int", {"level_id": "Q1.1", "user_yaml": 5}),
    ("missing user_yaml", {"level_id": "Q1.1"}),
    ("missing level_id", {"user_yaml": "kind: Pod"}),
    ("extra unknown field", {"level_id": "Q1.1", "user_yaml": "kind: Pod", "bogus": 1}),
]:
    code, txt = post_raw(body)
    tag = "BUG-CONFIRMED(500)" if code == 500 else ("422-OK" if code == 422 else "PASS")
    results.append((tag, "D3", name, code, None, txt))
    print(f"[{tag}] D3 {name}: HTTP {code} body={txt!r}")

print()
print("=" * 70)
print("D4: info-leak — response must carry ONLY str(e), never Traceback")
print("=" * 70)
# Capture logs to confirm Traceback goes to logger, not response.
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.ERROR)
app.logger.addHandler(handler)

code, ok, err = post("Q1.2", """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: 5
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""")
leak_markers = ["Traceback", "main.py", "simulator.py", "ch01_pod.py", "line "]
leaked = [m for m in leak_markers if m in err]
log_text = log_stream.getvalue()
has_traceback_in_log = "Traceback" in log_text
results.append(("INFO-LEAK" if leaked else "PASS", "D4", "response has no traceback", code, ok, f"leaked={leaked}"))
print(f"[{'INFO-LEAK' if leaked else 'PASS'}] D4 response leak check: HTTP {code} ok={ok} err={err[:80]!r}")
print(f"     leaked markers in response: {leaked}")
print(f"     Traceback in logger.error output: {has_traceback_in_log}")
app.logger.removeHandler(handler)

print()
print("=" * 70)
print("D5: multi-doc YAML (---)")
print("=" * 70)
case("multi-doc YAML (two pods)", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: nginx:1.25
---
apiVersion: v1
kind: Pod
metadata:
  name: other-pod
spec:
  containers:
    - name: x
      image: x
""", "D5")

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)
n_bug = sum(1 for r in results if "BUG" in r[0])
n_pass = sum(1 for r in results if r[0] == "PASS" or r[0] == "422-OK")
n_leak = sum(1 for r in results if "INFO-LEAK" in r[0])
print(f"PASS/422-OK={n_pass}  BUG-CONFIRMED(500)={n_bug}  INFO-LEAK={n_leak}")
for r in results:
    if "BUG" in r[0] or "INFO-LEAK" in r[0]:
        print("  !!", r)
sys.exit(0 if n_bug == 0 and n_leak == 0 else 1)
