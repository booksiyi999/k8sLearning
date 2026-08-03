"""QA Attack Tests for Ch13 (DaemonSet) and Ch14 (Namespace & ResourceQuota).

Tests attack vectors:
- Empty/malformed YAML
- Wrong kind / missing fields
- Multi-doc YAML injection
- Type confusion
- Negative resource values
- default < defaultRequest in LimitRange
- State pollution
- Non-string image causing AttributeError

Bugs found are annotated with # BUG / # SEVERITY comments.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ==========================================================================
#  Helper: call /api/check
# ==========================================================================

def check(level_id: str, user_yaml: str):
    """POST to /api/check and return the JSON response dict."""
    resp = client.post("/api/check", json={"level_id": level_id, "user_yaml": user_yaml})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


# ==========================================================================
#  Valid YAML fixtures (correct answers) for baseline passes
# ==========================================================================

VALID_Q131 = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25
"""

VALID_Q132 = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ssd-monitor
spec:
  selector:
    matchLabels:
      app: ssd-monitor
  template:
    metadata:
      labels:
        app: ssd-monitor
    spec:
      nodeSelector:
        disktype: ssd
      containers:
      - name: nginx
        image: nginx:1.25
"""

VALID_Q133 = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: rolling-ds
spec:
  selector:
    matchLabels:
      app: rolling
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
  template:
    metadata:
      labels:
        app: rolling
    spec:
      containers:
      - name: nginx
        image: nginx:1.26
"""

VALID_Q134 = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: node-exporter
spec:
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      hostNetwork: true
      containers:
      - name: node-exporter
        image: prom/node-exporter
"""

VALID_Q135 = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit
        volumeMounts:
        - name: varlog
          mountPath: /var/log
        - name: varlibdocker
          mountPath: /var/lib/docker/containers
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
      - name: varlibdocker
        hostPath:
          path: /var/lib/docker/containers
"""

VALID_Q141 = """\
apiVersion: v1
kind: Namespace
metadata:
  name: dev-team
"""

VALID_Q142 = """\
apiVersion: v1
kind: Namespace
metadata:
  name: dev-team
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: dev-team
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

VALID_Q143 = """\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: default
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    pods: "10"
"""

VALID_Q144 = """\
apiVersion: v1
kind: LimitRange
metadata:
  name: cpu-limits
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
"""

VALID_Q145 = """\
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: team-a-quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    limits.cpu: "8"
    limits.memory: "16Gi"
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: team-a-limits
  namespace: team-a
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
"""


# ==========================================================================
#  Ch13 Tests
# ==========================================================================

class TestQ131CreateDaemonSet:
    """Q13.1 - Create first DaemonSet."""

    def test_valid_passes(self):
        r = check("Q13.1", VALID_Q131)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_empty_yaml(self):
        r = check("Q13.1", "")
        assert r["ok"] is False
        assert "DaemonSet" in r["error"] or "没有创建" in r["error"]

    def test_malformed_yaml(self):
        r = check("Q13.1", "kind: DaemonSet\n  bad: : :")
        assert r["ok"] is False

    def test_wrong_kind_pod(self):
        r = check("Q13.1", """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
  - name: nginx
    image: nginx:1.25
""")
        assert r["ok"] is False
        assert "DaemonSet" in r["error"]

    def test_missing_spec_template(self):
        r = check("Q13.1", """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon
spec:
  selector:
    matchLabels:
      app: nginx
""")
        assert r["ok"] is False
        assert "template" in r["error"].lower()

    def test_missing_containers(self):
        r = check("Q13.1", """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec: {}
""")
        assert r["ok"] is False
        assert "containers" in r["error"].lower()

    def test_type_confusion_containers_as_string(self):
        """containers as a string instead of list."""
        r = check("Q13.1", """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: nginx-daemon
spec:
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers: "nginx"
""")
        assert r["ok"] is False
        assert "containers" in r["error"].lower()

    def test_multi_doc_injection(self):
        # BUG: When a valid DaemonSet + extra Pod (without metadata.labels) is
        #   submitted, the check function crashes with KeyError: 'labels'.
        #   Line 92: `p["metadata"]["labels"].get("daemonset")` assumes all pods
        #   have metadata.labels, but the injected Pod doesn't.
        #   The `isinstance(p.get("metadata", {}).get("labels", {}), dict)` check
        #   on line 91 returns True for missing labels (default {}), but then
        #   line 92 directly accesses p["metadata"]["labels"] which raises KeyError.
        # SEVERITY: P0 (crash on valid multi-doc YAML)
        r = check("Q13.1", VALID_Q131 + """\
---
apiVersion: v1
kind: Pod
metadata:
  name: injected-pod
spec:
  containers:
  - name: evil
    image: evil:latest
""")
        # Should pass (valid DS + extra Pod is legitimate multi-doc YAML),
        # but currently crashes with KeyError:
        assert r["ok"] is True, \
            f"BUG: Multi-doc with valid DS + label-less Pod crashes: {r.get('error')}"

    def test_state_pollution(self):
        """Call check twice; second call should be independent."""
        r1 = check("Q13.1", VALID_Q131)
        r2 = check("Q13.1", VALID_Q131)
        assert r1["ok"] is True
        assert r2["ok"] is True
        # Verify no extra pods leaked (should be exactly 3)
        if r2.get("cluster_state"):
            pods = r2["cluster_state"].get("pods", {})
            ds_pods = [k for k, v in pods.items()
                       if isinstance(v.get("metadata", {}).get("labels", {}), dict)
                       and v.get("metadata", {}).get("labels", {}).get("daemonset") == "nginx-daemon"]
            assert len(ds_pods) == 3, f"Expected 3 DS pods, got {len(ds_pods)}"


class TestQ132NodeSelector:
    """Q13.2 - DaemonSet with nodeSelector."""

    def test_valid_passes(self):
        r = check("Q13.2", VALID_Q132)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_no_node_selector(self):
        r = check("Q13.2", VALID_Q131)  # No nodeSelector
        assert r["ok"] is False
        assert "nodeSelector" in r["error"]

    def test_wrong_selector_value(self):
        yaml_str = VALID_Q132.replace("disktype: ssd", "disktype: hdd")
        r = check("Q13.2", yaml_str)
        assert r["ok"] is False
        assert "ssd" in r["error"]

    def test_selector_matching_no_nodes(self):
        """nodeSelector with non-existent label -> 0 pods."""
        yaml_str = VALID_Q132.replace("disktype: ssd", "disktype: nvme")
        r = check("Q13.2", yaml_str)
        # BUG: check expects disktype == 'ssd', so wrong value is caught first.
        # But if we add an extra label, the selector matches 0 nodes:
        assert r["ok"] is False

    def test_selector_matching_no_nodes_extra_label(self):
        """nodeSelector with extra label that no node has -> 0 pods created."""
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ssd-monitor
spec:
  selector:
    matchLabels:
      app: ssd-monitor
  template:
    metadata:
      labels:
        app: ssd-monitor
    spec:
      nodeSelector:
        disktype: ssd
        nonexistent: label
      containers:
      - name: nginx
        image: nginx:1.25
"""
        r = check("Q13.2", yaml_str)
        # disktype is correct, but extra label means 0 nodes match -> 0 pods
        assert r["ok"] is False
        assert "0" in r["error"] or "节点" in r["error"]

    def test_nodeSelector_as_string(self):
        """Type confusion: nodeSelector as string instead of dict."""
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: ssd-monitor
spec:
  selector:
    matchLabels:
      app: ssd-monitor
  template:
    metadata:
      labels:
        app: ssd-monitor
    spec:
      nodeSelector: ssd
      containers:
      - name: nginx
        image: nginx:1.25
"""
        r = check("Q13.2", yaml_str)
        assert r["ok"] is False
        assert "nodeSelector" in r["error"]


class TestQ133RollingUpdate:
    """Q13.3 - DaemonSet RollingUpdate."""

    def test_valid_passes(self):
        r = check("Q13.3", VALID_Q133)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_missing_update_strategy(self):
        r = check("Q13.3", VALID_Q131)
        assert r["ok"] is False
        assert "updateStrategy" in r["error"]

    def test_wrong_strategy_type(self):
        yaml_str = VALID_Q133.replace("RollingUpdate", "OnDelete")
        r = check("Q13.3", yaml_str)
        assert r["ok"] is False
        assert "RollingUpdate" in r["error"]

    def test_missing_maxUnavailable(self):
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: rolling-ds
spec:
  selector:
    matchLabels:
      app: rolling
  updateStrategy:
    type: RollingUpdate
    rollingUpdate: {}
  template:
    metadata:
      labels:
        app: rolling
    spec:
      containers:
      - name: nginx
        image: nginx:1.26
"""
        r = check("Q13.3", yaml_str)
        assert r["ok"] is False
        assert "maxUnavailable" in r["error"]


    # NOTE: The same KeyError: 'labels' bug exists in Q13.2 (line 334)
    # and Q13.5 (line 1135) - they use the identical pattern:
    #   p["metadata"]["labels"].get("daemonset")
    # instead of the safe:
    #   p.get("metadata", {}).get("labels", {}).get("daemonset")


class TestQ134DaemonSetVsDeployment:
    """Q13.4 - DaemonSet vs Deployment."""

    def test_valid_daemonset_passes(self):
        r = check("Q13.4", VALID_Q134)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_deployment_should_fail(self):
        deploy_yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: node-exporter
spec:
  replicas: 2
  selector:
    matchLabels:
      app: node-exporter
  template:
    metadata:
      labels:
        app: node-exporter
    spec:
      containers:
      - name: node-exporter
        image: prom/node-exporter
"""
        r = check("Q13.4", deploy_yaml)
        assert r["ok"] is False
        assert "DaemonSet" in r["error"]
        assert "Deployment" in r["error"]

    def test_empty_yaml(self):
        r = check("Q13.4", "")
        assert r["ok"] is False


class TestQ135FluentBit:
    """Q13.5 - Fluent Bit DaemonSet."""

    def test_valid_passes(self):
        r = check("Q13.5", VALID_Q135)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_wrong_image(self):
        yaml_str = VALID_Q135.replace("fluent/fluent-bit", "nginx:1.25")
        r = check("Q13.5", yaml_str)
        assert r["ok"] is False
        assert "fluent" in r["error"].lower() or "日志" in r["error"]

    def test_missing_volumeMounts(self):
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
"""
        r = check("Q13.5", yaml_str)
        assert r["ok"] is False
        assert "volumeMounts" in r["error"]

    def test_missing_var_log_mount(self):
        """volumeMounts present but no /var/log."""
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: fluent/fluent-bit
        volumeMounts:
        - name: tmp
          mountPath: /tmp
      volumes:
      - name: tmp
        hostPath:
          path: /tmp
"""
        r = check("Q13.5", yaml_str)
        assert r["ok"] is False
        assert "/var/log" in r["error"]

    def test_non_string_image_int(self):
        # BUG: image: 123 (integer) is truthy, passes `if not image` check,
        #   then image.lower() raises AttributeError.
        #   The check_fn's try/except only catches K8sError, not AttributeError.
        #   The API endpoint's top-level handler catches it, returning ok=False
        #   with a cryptic error message instead of a meaningful validation error.
        # SEVERITY: P1
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: 123
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
"""
        r = check("Q13.5", yaml_str)
        assert r["ok"] is False
        # Should return a user-friendly error about image, not AttributeError
        assert "image" in r["error"].lower() or "镜像" in r["error"], \
            f"Expected user-friendly image error, got: {r['error']}"

    def test_non_string_image_list(self):
        # BUG: image as list passes truthiness check, then .lower() crashes.
        # SEVERITY: P1
        yaml_str = """\
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: fluent-bit
spec:
  selector:
    matchLabels:
      app: fluent-bit
  template:
    metadata:
      labels:
        app: fluent-bit
    spec:
      containers:
      - name: fluent-bit
        image: ["fluent/fluent-bit"]
        volumeMounts:
        - name: varlog
          mountPath: /var/log
      volumes:
      - name: varlog
        hostPath:
          path: /var/log
"""
        r = check("Q13.5", yaml_str)
        assert r["ok"] is False
        assert "image" in r["error"].lower() or "镜像" in r["error"], \
            f"Expected user-friendly image error, got: {r['error']}"


# ==========================================================================
#  Ch14 Tests
# ==========================================================================

class TestQ141CreateNamespace:
    """Q14.1 - Create Namespace."""

    def test_valid_passes(self):
        r = check("Q14.1", VALID_Q141)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_empty_yaml(self):
        r = check("Q14.1", "")
        assert r["ok"] is False
        assert "Namespace" in r["error"]

    def test_wrong_kind(self):
        r = check("Q14.1", VALID_Q131)  # DaemonSet
        assert r["ok"] is False
        assert "Namespace" in r["error"]

    def test_missing_name(self):
        r = check("Q14.1", """\
apiVersion: v1
kind: Namespace
metadata: {}
""")
        assert r["ok"] is False

    def test_wrong_apiVersion(self):
        r = check("Q14.1", """\
apiVersion: apps/v1
kind: Namespace
metadata:
  name: dev-team
""")
        assert r["ok"] is False
        assert "apiVersion" in r["error"] or "v1" in r["error"]

    def test_malformed_yaml(self):
        r = check("Q14.1", "::: not yaml :::")
        assert r["ok"] is False


class TestQ142DeployInNamespace:
    """Q14.2 - Deploy in Namespace."""

    def test_valid_passes(self):
        r = check("Q14.2", VALID_Q142)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_missing_namespace(self):
        yaml_str = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
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
        r = check("Q14.2", yaml_str)
        assert r["ok"] is False
        assert "Namespace" in r["error"]

    def test_deployment_without_namespace_field(self):
        """Namespace created but Deployment has no namespace."""
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: dev-team
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
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
        r = check("Q14.2", yaml_str)
        assert r["ok"] is False
        assert "namespace" in r["error"].lower()

    def test_deployment_namespace_not_created(self):
        """Deployment references namespace that was never created."""
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: dev-team
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-app
  namespace: non-existent
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
        r = check("Q14.2", yaml_str)
        assert r["ok"] is False
        assert "namespace" in r["error"].lower() or "不存在" in r["error"]


class TestQ143ResourceQuota:
    """Q14.3 - Create ResourceQuota."""

    def test_valid_passes(self):
        r = check("Q14.3", VALID_Q143)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_empty_yaml(self):
        r = check("Q14.3", "")
        assert r["ok"] is False
        assert "ResourceQuota" in r["error"]

    def test_missing_hard(self):
        r = check("Q14.3", """\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
spec: {}
""")
        assert r["ok"] is False
        assert "hard" in r["error"].lower()

    def test_missing_cpu(self):
        r = check("Q14.3", """\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
spec:
  hard:
    requests.memory: "8Gi"
    pods: "10"
""")
        assert r["ok"] is False
        assert "CPU" in r["error"] or "cpu" in r["error"].lower()

    def test_negative_values_pass(self):
        # BUG: ResourceQuota with negative resource values passes validation.
        #   The check only verifies key presence (cpu/memory/pods in key names)
        #   but never validates the values. Negative quotas are invalid in K8s.
        # SEVERITY: P1
        yaml_str = """\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: bad-quota
spec:
  hard:
    requests.cpu: "-999"
    requests.memory: "-1Gi"
    limits.cpu: "-100"
    limits.memory: "-1Gi"
    pods: "-5"
"""
        r = check("Q14.3", yaml_str)
        # Bug fixed: negative resource quota values are now rejected
        assert r["ok"] is False, \
            f"Negative resource quota values should be rejected. Error: {r.get('error')}"
        assert "负数" in r["error"] or "negative" in r["error"].lower(), \
            f"Expected negative value error, got: {r['error']}"

    def test_loose_key_matching(self):
        # BUG: The check uses `any("cpu" in str(k).lower() for k in hard.keys())`
        #   which matches ANY key containing the substring "cpu", "memory", or "pod".
        #   So `mycpu`, `mymemory`, `mypod` would pass, even though the task
        #   requires specific keys like requests.cpu, limits.cpu, etc.
        # SEVERITY: P2
        yaml_str = """\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: loose-quota
spec:
  hard:
    mycpu: "4"
    mymemory: "8Gi"
    mypod: "10"
"""
        r = check("Q14.3", yaml_str)
        # Bug fixed: loose key matching replaced with exact key matching
        assert r["ok"] is False, \
            f"Loose key matching should be rejected; exact keys required. Error: {r.get('error')}"
        assert "CPU" in r["error"] or "cpu" in r["error"].lower(), \
            f"Expected CPU missing error, got: {r['error']}"

    def test_single_cpu_key_instead_of_requests_and_limits(self):
        # BUG: A single `cpu` key passes the check even though both
        #   requests.cpu AND limits.cpu are required.
        # SEVERITY: P2
        yaml_str = """\
apiVersion: v1
kind: ResourceQuota
metadata:
  name: minimal-quota
spec:
  hard:
    cpu: "4"
    memory: "8Gi"
    pods: "10"
"""
        r = check("Q14.3", yaml_str)
        # Bug fixed: exact key matching now requires requests.cpu + limits.cpu
        assert r["ok"] is False, \
            f"Single 'cpu' key should be rejected; requests.cpu + limits.cpu required. Error: {r.get('error')}"
        assert "CPU" in r["error"] or "cpu" in r["error"].lower(), \
            f"Expected CPU missing error, got: {r['error']}"


class TestQ144LimitRange:
    """Q14.4 - Create LimitRange."""

    def test_valid_passes(self):
        r = check("Q14.4", VALID_Q144)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_empty_yaml(self):
        r = check("Q14.4", "")
        assert r["ok"] is False
        assert "LimitRange" in r["error"]

    def test_missing_limits(self):
        r = check("Q14.4", """\
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
spec: {}
""")
        assert r["ok"] is False
        assert "limits" in r["error"].lower()

    def test_wrong_type(self):
        yaml_str = VALID_Q144.replace("type: Container", "type: Pod")
        r = check("Q14.4", yaml_str)
        assert r["ok"] is False
        assert "Container" in r["error"]

    def test_missing_default(self):
        yaml_str = """\
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
spec:
  limits:
  - type: Container
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
"""
        r = check("Q14.4", yaml_str)
        assert r["ok"] is False
        assert "default" in r["error"].lower()

    def test_default_less_than_defaultRequest(self):
        # BUG: LimitRange where default (limits) < defaultRequest (requests) passes.
        #   In K8s, limits must always be >= requests. The check function
        #   validates presence of cpu/memory in both default and defaultRequest
        #   but never compares their values.
        # SEVERITY: P1
        yaml_str = """\
apiVersion: v1
kind: LimitRange
metadata:
  name: inverted-limits
spec:
  limits:
  - type: Container
    default:
      cpu: "10m"
      memory: "10Mi"
    defaultRequest:
      cpu: "1000m"
      memory: "1000Mi"
"""
        r = check("Q14.4", yaml_str)
        # Bug fixed: default < defaultRequest is now rejected
        assert r["ok"] is False, \
            f"default < defaultRequest should be rejected. Error: {r.get('error')}"
        assert "default" in r["error"].lower() or "requests" in r["error"].lower(), \
            f"Expected default vs defaultRequest error, got: {r['error']}"

    def test_default_missing_cpu(self):
        yaml_str = """\
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
spec:
  limits:
  - type: Container
    default:
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
      memory: "128Mi"
"""
        r = check("Q14.4", yaml_str)
        assert r["ok"] is False
        assert "cpu" in r["error"].lower() or "default" in r["error"].lower()

    def test_defaultRequest_missing_memory(self):
        yaml_str = """\
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "512Mi"
    defaultRequest:
      cpu: "100m"
"""
        r = check("Q14.4", yaml_str)
        assert r["ok"] is False
        assert "memory" in r["error"].lower() or "defaultRequest" in r["error"].lower()


class TestQ145MultiTeam:
    """Q14.5 - Multi-team resource isolation."""

    def test_valid_passes(self):
        r = check("Q14.5", VALID_Q145)
        assert r["ok"] is True, f"Valid YAML should pass: {r.get('error')}"

    def test_missing_namespace(self):
        r = check("Q14.5", VALID_Q143)  # Only ResourceQuota
        assert r["ok"] is False
        assert "Namespace" in r["error"]

    def test_missing_resourcequota(self):
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
  namespace: team-a
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "512Mi"
"""
        r = check("Q14.5", yaml_str)
        assert r["ok"] is False
        assert "ResourceQuota" in r["error"]

    def test_missing_limitrange(self):
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    pods: "10"
"""
        r = check("Q14.5", yaml_str)
        assert r["ok"] is False
        assert "LimitRange" in r["error"]

    def test_limitrange_empty_limits_rejected(self):
        """Empty limits[] is correctly rejected by the simulator's _apply_limitrange."""
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: empty-limits
  namespace: team-a
spec:
  limits: []
"""
        r = check("Q14.5", yaml_str)
        assert r["ok"] is False, "Empty limits[] should be rejected"

    def test_limitrange_non_dict_limits_passes(self):
        # BUG: Q14.5 check for LimitRange default is inside
        #   `if isinstance(limits, list) and limits and isinstance(limits[0], dict):`
        #   When limits[0] is a non-dict (e.g. a string), the condition is False,
        #   the check is skipped entirely, and the function returns ok=True.
        #   The simulator's _apply_limitrange only checks that limits is a non-empty
        #   list, not that items are dicts. So `limits: ["not-a-dict"]` passes.
        # SEVERITY: P1
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
  namespace: team-a
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: bad-limits
  namespace: team-a
spec:
  limits:
  - "not-a-dict"
"""
        r = check("Q14.5", yaml_str)
        # Bug fixed: non-dict limits[0] is now rejected
        assert r["ok"] is False, \
            f"LimitRange with non-dict limits[0] should be rejected. Error: {r.get('error')}"
        assert "limits" in r["error"].lower() or "字典" in r["error"], \
            f"Expected limits format error, got: {r['error']}"

    def test_resourcequota_wrong_namespace(self):
        yaml_str = """\
apiVersion: v1
kind: Namespace
metadata:
  name: team-a
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: quota
  namespace: team-b
spec:
  hard:
    requests.cpu: "4"
    requests.memory: "8Gi"
    pods: "10"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: limits
  namespace: team-b
spec:
  limits:
  - type: Container
    default:
      cpu: "500m"
      memory: "512Mi"
"""
        r = check("Q14.5", yaml_str)
        assert r["ok"] is False
        assert "namespace" in r["error"].lower() or "不存在" in r["error"]


# ==========================================================================
#  Cross-cutting: state pollution across all levels
# ==========================================================================

class TestStatePollution:
    """Verify calling check_fn multiple times has no side effects."""

    @pytest.mark.parametrize("level_id,yaml_str", [
        ("Q13.1", VALID_Q131),
        ("Q13.2", VALID_Q132),
        ("Q13.3", VALID_Q133),
        ("Q13.4", VALID_Q134),
        ("Q13.5", VALID_Q135),
        ("Q14.1", VALID_Q141),
        ("Q14.2", VALID_Q142),
        ("Q14.3", VALID_Q143),
        ("Q14.4", VALID_Q144),
        ("Q14.5", VALID_Q145),
    ])
    def test_idempotent(self, level_id, yaml_str):
        r1 = check(level_id, yaml_str)
        r2 = check(level_id, yaml_str)
        assert r1["ok"] is True, f"First call failed for {level_id}: {r1.get('error')}"
        assert r2["ok"] is True, f"Second call failed for {level_id}: {r2.get('error')}"
        # Both should return same ok status
        assert r1["ok"] == r2["ok"]


# ==========================================================================
#  Cross-cutting: crash resistance
# ==========================================================================

class TestCrashResistance:
    """All check functions should return ok=False, never raise/crash."""

    @pytest.mark.parametrize("level_id", [
        "Q13.1", "Q13.2", "Q13.3", "Q13.4", "Q13.5",
        "Q14.1", "Q14.2", "Q14.3", "Q14.4", "Q14.5",
    ])
    def test_empty_string(self, level_id):
        r = check(level_id, "")
        assert r["ok"] is False
        assert r["error"]  # Non-empty error message

    @pytest.mark.parametrize("level_id", [
        "Q13.1", "Q13.2", "Q13.3", "Q13.4", "Q13.5",
        "Q14.1", "Q14.2", "Q14.3", "Q14.4", "Q14.5",
    ])
    def test_random_garbage(self, level_id):
        r = check(level_id, "this is not yaml at all {{{")
        assert r["ok"] is False
        assert r["error"]

    @pytest.mark.parametrize("level_id", [
        "Q13.1", "Q13.2", "Q13.3", "Q13.4", "Q13.5",
        "Q14.1", "Q14.2", "Q14.3", "Q14.4", "Q14.5",
    ])
    def test_null_yaml(self, level_id):
        """YAML that parses to None (e.g., just '---')."""
        r = check(level_id, "---")
        assert r["ok"] is False
        assert r["error"]

    @pytest.mark.parametrize("level_id", [
        "Q13.1", "Q13.2", "Q13.3", "Q13.4", "Q13.5",
        "Q14.1", "Q14.2", "Q14.3", "Q14.4", "Q14.5",
    ])
    def test_yaml_list_instead_of_dict(self, level_id):
        """YAML that parses to a list instead of a dict."""
        r = check(level_id, "- item1\n- item2")
        assert r["ok"] is False
        assert r["error"]

    @pytest.mark.parametrize("level_id", [
        "Q13.1", "Q13.2", "Q13.3", "Q13.4", "Q13.5",
        "Q14.1", "Q14.2", "Q14.3", "Q14.4", "Q14.5",
    ])
    def test_yaml_scalar(self, level_id):
        """YAML that parses to a scalar string."""
        r = check(level_id, "just a string")
        assert r["ok"] is False
        assert r["error"]
