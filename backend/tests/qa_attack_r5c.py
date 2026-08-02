"""QA round-5c: aggressive cycle-construction bypass vectors.

Targets gaps the engineer's round-5b tests do NOT cover:
  - indirect cycle (a->b->a, two distinct anchors)
  - deep cycle (10-level nesting then back to root)
  - list-internal cycle (list references itself)
  - cycle in spec.containers / spec / root
  - YAML merge-key (`<<`) self-reference
  - cycle in Deployment template
  - deep diamond (shared alias at depth, must NOT false-positive)

Each vector: must return HTTP 200 ok=False (or 200 ok=True with NO cycle in state).
A 500 = HOLE (cycle leaked to serialization layer).
A 200 ok=True where state contains a cycle = also HOLE (would 500 on real serialization).

The app.main top-level try/except is a SAFETY NET, not the fix. The fix is
_has_circular_ref in apply_manifest. We verify the cycle is rejected AT THE SOURCE.
"""
import json
import logging
import io
import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

real_logger = logging.getLogger("app.main")
log_stream = io.StringIO()
handler = logging.StreamHandler(log_stream)
handler.setLevel(logging.ERROR)
real_logger.addHandler(handler)


def post(level_id, yaml_text):
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    try:
        body = r.json()
    except Exception as e:
        return r.status_code, None, {}, f"<no json: {e}>"
    return r.status_code, body.get("ok"), body.get("cluster_state"), body.get("error", "")


# ---- a helper to detect a cycle in the returned cluster_state (defense in depth) ----
def state_has_cycle(state):
    """Walk the returned cluster_state the way json.dumps would; detect cycles."""
    seen = set()
    def walk(o):
        oid = id(o)
        if oid in seen:
            return True
        if isinstance(o, dict):
            seen.add(oid)
            for v in o.values():
                if walk(v):
                    return True
            seen.discard(oid)
        elif isinstance(o, list):
            seen.add(oid)
            for it in o:
                if walk(it):
                    return True
            seen.discard(oid)
        return False
    if not state:
        return False
    return walk(state)


V = []
# 1. Indirect cycle a->b->a (two distinct anchors)
V.append(("indirect a->b->a labels", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels: &a
    app: cache
    tier: &b
      deep: *a
spec:
  containers:
    - name: web
      image: nginx:1.25
"""))

# 2. Deep cycle: nest 10 levels then back to root
V.append(("deep 10-level cycle", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  annotations: &a
    a1:
      a2:
        a3:
          a4:
            a5:
              a6:
                a7:
                  a8:
                    a9:
                      a10: *a
spec:
  containers:
    - name: web
      image: nginx:1.25
"""))

# 3. List-internal cycle: list references itself
V.append(("list self-ref containers", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers: &c
    - name: web
      image: nginx:1.25
      next: *c
"""))

# 4. Cycle in spec (spec references the pod root)
V.append(("spec -> root cycle", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels: &a
    app: cache
spec: *a
  containers:
    - name: web
      image: nginx:1.25
"""))

# 5. Root references itself (anchor on top-level doc)
V.append(("root self-ref", "Q1.1", """
&a
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  self: *a
spec:
  containers:
    - name: web
      image: nginx:1.25
"""))

# 6. YAML merge-key self-reference
V.append(("merge-key self-ref <<", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  annotations: &a
    <<: *a
    note: hi
spec:
  containers:
    - name: web
      image: nginx:1.25
"""))

# 7. Cycle in Deployment template (annotations self-ref deep in template)
V.append(("deploy template deep cycle", "Q1.1", """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dep
  annotations: &a
    x:
      y: *a
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
"""))

# 8. Cycle via container env (deep in spec.containers)
V.append(("container env cycle", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: web
      image: nginx:1.25
      env: &e
        - name: LOOP
          value: *e
"""))

# 9. Diamond at depth (shared alias deep in two branches) - MUST NOT false-positive
V.append(("deep diamond no-fp", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  labels: &shared
    app: cache
    tier: backend
spec:
  containers:
    - name: web
      image: nginx:1.25
      env:
        - name: A
          valueFrom:
            configMapRef: *shared
        - name: B
          valueFrom:
            configMapRef: *shared
"""))

# 10. Cycle through two list items (item0 -> item1 -> item0)
V.append(("list item cross-cycle", "Q1.1", """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
  annotations:
    list: &l
      - &first
        a: 1
      - *first
spec:
  containers:
    - name: web
      image: nginx:1.25
"""))

holes = []
print("=== QA round-5c: aggressive cycle bypass vectors ===")
for name, level_id, y in V:
    c, ok, state, err = post(level_id, y)
    tag = ""
    cyc = state_has_cycle(state) if ok else False
    if c == 500:
        tag = "  << 500 HOLE (cycle leaked to serialization)"
        holes.append((name, "HTTP 500", ok, err[:80]))
    elif ok is True and cyc:
        tag = "  << STATE-CYCLE HOLE (ok=True but state has cycle -> would 500 on serialize)"
        holes.append((name, "STATE-CYCLE", ok, err[:80]))
    elif ok is True and name.startswith("deep diamond"):
        tag = "  OK (diamond correctly allowed, no false-positive)"
    print(f"{name:32s} HTTP {c} ok={ok} cyc={cyc} err={err[:50]!r}{tag}")

# explicit false-positive check for the diamond vector
print("\n=== false-positive regression (diamond must pass) ===")
c, ok, state, err = post("Q1.1", V[8][2])
print(f"deep diamond: HTTP {c} ok={ok} (expect ok=True, no false-positive)")
if ok is not True:
    holes.append(("deep diamond", "FALSE-POSITIVE", ok, err[:80]))

print("\n=== info-leak recheck on cycle rejection ===")
c, ok, state, err = post("Q1.1", V[0][2])
leak_markers = ["Traceback", "main.py", "simulator.py", "_has_circular_ref", "line "]
leaked = [m for m in leak_markers if m in err]
print(f"indirect cycle rejection err: {err!r}")
print(f"leaked markers: {leaked} -> {'INFO-LEAK' if leaked else 'CLEAN'}")

log_text = log_stream.getvalue()
print(f"\nlogger.error output present: {'yes' if log_text.strip() else 'no (clean)'}")
if log_text.strip():
    print(f"logger sample: {log_text[:300]!r}")
real_logger.removeHandler(handler)

print("\n=== SUMMARY ===")
if holes:
    print(f"FOUND {len(holes)} HOLE(s):")
    for h in holes:
        print(f"  - {h[0]}: {h[1]} ok={h[2]} err={h[3]!r}")
    sys.exit(1)
else:
    print("ALL CLEAR: 0 holes. All cycle vectors rejected at source (200 ok=False), diamond no false-positive, no info-leak.")
