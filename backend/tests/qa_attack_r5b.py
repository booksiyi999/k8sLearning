"""QA round-5b: characterize the recursive-anchor 500 hole + info-leak recheck."""
import logging
import io
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

# Attach a handler to the REAL logger (app.main, not app.logger).
real_logger = logging.getLogger("app.main")
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.ERROR)
real_logger.addHandler(handler)


def post(level_id, yaml_text):
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    try:
        body = r.json()
        return r.status_code, body.get("ok"), body.get("error", "")
    except Exception as e:
        return r.status_code, None, f"<no json: {e}>"


recursive_labels = """
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels: &a
    app: cache
    tier: *a
spec:
  containers:
    - name: redis
      image: redis:7-alpine
"""

recursive_deployment_meta = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
  annotations: &a
    x: *a
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
"""

# Q1.1 recursive labels (labels not checked -> ok=True -> state returned)
c, ok, err = post("Q1.1", recursive_labels.replace("redis-pod", "nginx-pod").replace("redis:7-alpine", "nginx:1.25"))
print(f"Q1.1 recursive labels:        HTTP {c} ok={ok} err={err[:60]!r}  {'<< 500 HOLE' if c==500 else ''}")

# Q1.2 recursive labels (labels ARE checked via .get -> may still pass)
c, ok, err = post("Q1.2", recursive_labels)
print(f"Q1.2 recursive labels:        HTTP {c} ok={ok} err={err[:60]!r}  {'<< 500 HOLE' if c==500 else ''}")

# Q1.1 valid Pod with recursive annotations (annotations not checked -> ok=True)
c, ok, err = post("Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  annotations: &a
    note: *a
spec:
  containers:
    - name: web
      image: nginx:1.25
""")
print(f"Q1.1 recursive annotations:   HTTP {c} ok={ok} err={err[:60]!r}  {'<< 500 HOLE' if c==500 else ''}")

# Q1.1 recursive Deployment annotations (stored in state.deployments)
c, ok, err = post("Q1.1", recursive_deployment_meta)
print(f"Q1.1 recursive deploy anno:   HTTP {c} ok={ok} err={err[:60]!r}  {'<< 500 HOLE' if c==500 else ''}")

# --- info-leak recheck: response must carry ONLY str(e), never Traceback ---
print("\n--- info-leak recheck (labels:int triggers止血) ---")
c, ok, err = post("Q1.2", """
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
print(f"response HTTP {c} ok={ok}")
print(f"response err: {err!r}")
print(f"leaked markers in response body: {leaked}  -> {'INFO-LEAK' if leaked else 'CLEAN (str(e) only)'}")
print(f"Traceback present in logger.error output: {'yes' if 'Traceback' in log_text else 'no'}")
print(f"logger output sample: {log_text[:200]!r}")
real_logger.removeHandler(handler)
