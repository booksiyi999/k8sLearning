"""QA boundary tests for Q1.4 — probing gaps the engineer's 7 cases miss."""
import sys, traceback
sys.path.insert(0, ".")
from app.validator import get_level

lv = get_level("Q1.4")
passed, failed, crashed = [], [], []

def case(name, yaml_str, expect_ok, expect_error_contains=None):
    try:
        r = lv.check_fn(yaml_str)
        if r.ok == expect_ok:
            if expect_error_contains and expect_error_contains not in (r.error or ""):
                failed.append(f"{name}: ok={r.ok} but error '{r.error}' lacks '{expect_error_contains}'")
            else:
                passed.append(f"{name}: ok={r.ok} (expected {expect_ok}) — OK")
        else:
            failed.append(f"{name}: ok={r.ok}, expected {expect_ok}, error='{r.error}'")
    except Exception as e:
        crashed.append(f"{name}: UNHANDLED {type(e).__name__}: {e}")
        traceback.print_exc()

BASE = """\
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
          cpu: "100m"
          memory: "128Mi"
        limits:
          cpu: "500m"
          memory: "256Mi"
"""

# ---- B1: image not validated (Q1.1-Q1.3 all check image; Q1.4 skips) ----
case("B1_wrong_image_accepted", BASE.replace("nginx:1.25", "redis:latest"), True)

# ---- B2: resources is a non-dict type (string) → AttributeError risk ----
case("B2_resources_as_string", BASE.replace(
    '      resources:\n        requests:\n          cpu: "100m"\n          memory: "128Mi"\n        limits:\n          cpu: "500m"\n          memory: "256Mi"',
    '      resources: just-a-string'), False)

# ---- B3: resources is a list ----
case("B3_resources_as_list", BASE.replace(
    '      resources:\n        requests:\n          cpu: "100m"\n          memory: "128Mi"\n        limits:\n          cpu: "500m"\n          memory: "256Mi"',
    '      resources: [1, 2, 3]'), False)

# ---- B4: resources present but empty dict {} ----
case("B4_resources_empty_dict", BASE.replace(
    '      resources:\n        requests:\n          cpu: "100m"\n          memory: "128Mi"\n        limits:\n          cpu: "500m"\n          memory: "256Mi"',
    '      resources: {}'), False)

# ---- B5: requests present but empty dict ----
case("B5_requests_empty_dict", BASE.replace(
    '        requests:\n          cpu: "100m"\n          memory: "128Mi"',
    '        requests: {}'), False)

# ---- B6: numeric cpu (0.1 instead of "100m") — YAML parses as float ----
case("B6_cpu_as_float_0.1", BASE.replace('cpu: "100m"', "cpu: 0.1"), False, "requests.cpu")

# ---- B7: case sensitivity — 100M vs 100m ----
case("B7_cpu_uppercase_M", BASE.replace('cpu: "100m"', 'cpu: "100M"'), False, "requests.cpu")

# ---- B8: unquoted 100m (YAML → string "100m") ----
case("B8_unquoted_values", BASE.replace('cpu: "100m"', "cpu: 100m").replace('cpu: "500m"', "cpu: 500m"), True)

# ---- B9: extra container with no resources (only containers[0] checked) ----
case("B9_second_container_no_resources", BASE.replace(
    "      resources:\n        requests:\n          cpu: \"100m\"\n          memory: \"128Mi\"\n        limits:\n          cpu: \"500m\"\n          memory: \"256Mi\"",
    "      resources:\n        requests:\n          cpu: \"100m\"\n          memory: \"128Mi\"\n        limits:\n          cpu: \"500m\"\n          memory: \"256Mi\"\n    - name: sidecar\n      image: busybox:1.36"), True)

# ---- B10: requests present, limits present, but limits empty {} ----
case("B10_limits_empty_dict", BASE.replace(
    '        limits:\n          cpu: "500m"\n          memory: "256Mi"',
    '        limits: {}'), False)

# ---- B11: wrong pod name ----
case("B11_wrong_pod_name", BASE.replace("name: resource-pod", "name: my-pod"), False, "resource-pod")

# ---- B12: null resources value ----
case("B12_resources_null", BASE.replace(
    '      resources:\n        requests:\n          cpu: "100m"\n          memory: "128Mi"\n        limits:\n          cpu: "500m"\n          memory: "256Mi"',
    '      resources: null'), False)

print("\n" + "="*60)
print(f"PASSED:  {len(passed)}")
for p in passed: print(f"  ✓ {p}")
print(f"FAILED:  {len(failed)}")
for f in failed: print(f"  ✗ {f}")
print(f"CRASHED: {len(crashed)}")
for c in crashed: print(f"  💥 {c}")
