"""Tests for the rewritten Q22.3, Q22.4, and Q27.1 check functions.

These levels were rewritten to fix 'false positive' issues identified in
Claude Code review:

- Q22.3: Was keyword-search on text input; now validates a fixed Pod YAML
  (CrashLoopBackOff scenario with broken args).
- Q22.4: Was keyword-search on text input; now validates a fixed Pod YAML
  (Pending scenario with excessive resource requests).
- Q27.1: Was checking Deployment name contains 'istio'; now checks for
  sidecar injection labels (istio-injection=enabled) or Istio CRD structure
  (VirtualService/Gateway with networking.istio.io/v1beta1).
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def check(level_id, yaml_text):
    """POST to /api/check and return the JSON response."""
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    assert r.status_code == 200, f"{level_id} returned HTTP {r.status_code}"
    return r.json()


# ════════════════════════════════════════════════════════════════════
# Q22.3 - CrashLoopBackOff 故障排查 (rewritten)
# ════════════════════════════════════════════════════════════════════

class TestQ223CorrectAnswers:
    """Valid fixes for the CrashLoopBackOff scenario should pass."""

    def test_fix_with_nginx_command(self):
        """Fix: replace broken args with correct nginx command."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["nginx", "-g", "daemon off;"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_fix_by_removing_command_args(self):
        """Fix: remove broken command/args, let nginx use default entrypoint."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_fix_with_sleep_command(self):
        """Fix: use sleep command to keep container running."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_fix_with_correct_args(self):
        """Fix: replace broken args with valid application args."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["/bin/sh", "-c"]
    args: ["nginx -g 'daemon off;'"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"


class TestQ223WrongAnswers:
    """Invalid or unfixed YAML should be rejected."""

    def test_still_has_exit_1_in_args(self):
        """The original broken YAML should still fail."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["/bin/sh", "-c"]
    args: ["echo starting && exit 1"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is False, "Should reject YAML with 'exit 1' in args"

    def test_command_false(self):
        """command: ['false'] should be rejected."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["false"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is False, "Should reject command 'false'"

    def test_command_exit(self):
        """command: ['exit'] should be rejected."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: nginx:1.25
    command: ["exit"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is False, "Should reject command 'exit'"

    def test_empty_input(self):
        d = check("Q22.3", "")
        assert d["ok"] is False

    def test_garbage(self):
        d = check("Q22.3", "this is not yaml {{{")
        assert d["ok"] is False

    def test_service_not_pod(self):
        """A Service is the wrong kind for this level."""
        yaml_text = """\
apiVersion: v1
kind: Service
metadata:
  name: wrong
spec:
  selector:
    app: x
  ports:
  - port: 80
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is False

    def test_no_image(self):
        """Pod without image should fail."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    command: ["sleep", "3600"]
"""
        d = check("Q22.3", yaml_text)
        assert d["ok"] is False

    def test_keyword_search_no_longer_works(self):
        """The old keyword-based approach (typing commands) should NOT pass."""
        d = check("Q22.3", "kubectl describe pod app-pod\nkubectl logs app-pod")
        assert d["ok"] is False, "Keyword search should no longer pass - YAML fix required"


# ════════════════════════════════════════════════════════════════════
# Q22.4 - Pending Pod 故障排查 (rewritten)
# ════════════════════════════════════════════════════════════════════

class TestQ224CorrectAnswers:
    """Valid fixes for the Pending Pod scenario should pass."""

    def test_fix_with_reasonable_resources(self):
        """Fix: reduce resource requests to reasonable values."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "1"
        memory: "1Gi"
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_fix_by_removing_resources(self):
        """Fix: remove resources entirely, let scheduler decide."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_fix_with_nodeSelector(self):
        """Fix: add nodeSelector (alternative strategy for scheduling)."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  nodeSelector:
    disktype: ssd
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_fix_with_small_resources(self):
        """Fix: use very small resource requests."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "100m"
        memory: "64Mi"
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"


class TestQ224WrongAnswers:
    """Invalid or unfixed YAML should be rejected."""

    def test_original_excessive_cpu(self):
        """The original broken YAML (100 CPU) should fail."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "100"
        memory: "512Mi"
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is False, "Should reject CPU request of 100 cores"

    def test_original_excessive_memory(self):
        """The original broken YAML (512Gi memory) should fail."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "500m"
        memory: "512Gi"
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is False, "Should reject memory request of 512Gi"

    def test_both_excessive(self):
        """Both CPU and memory excessive should fail."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: worker
spec:
  containers:
  - name: worker
    image: busybox:1.36
    command: ["sleep", "3600"]
    resources:
      requests:
        cpu: "100"
        memory: "512Gi"
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is False

    def test_empty_input(self):
        d = check("Q22.4", "")
        assert d["ok"] is False

    def test_garbage(self):
        d = check("Q22.4", "not yaml {{{")
        assert d["ok"] is False

    def test_service_not_pod(self):
        """A Service is the wrong kind for this level."""
        yaml_text = """\
apiVersion: v1
kind: Service
metadata:
  name: wrong
spec:
  selector:
    app: x
  ports:
  - port: 80
"""
        d = check("Q22.4", yaml_text)
        assert d["ok"] is False

    def test_keyword_search_no_longer_works(self):
        """The old keyword-based approach (typing commands) should NOT pass."""
        d = check("Q22.4", "kubectl get pods -n kube-system\nkubectl get componentstatuses")
        assert d["ok"] is False, "Keyword search should no longer pass - YAML fix required"


# ════════════════════════════════════════════════════════════════════
# Q27.1 - Istio 架构概念 (rewritten)
# ════════════════════════════════════════════════════════════════════

class TestQ271CorrectAnswers:
    """Valid Istio Service Mesh configurations should pass."""

    def test_sidecar_injection_namespace(self):
        """Namespace with istio-injection=enabled + Deployment should pass."""
        yaml_text = """\
---
apiVersion: v1
kind: Namespace
metadata:
  name: my-istio-app
  labels:
    istio-injection: enabled
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-istio-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: nginx:1.25
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_virtualservice(self):
        """VirtualService with correct apiVersion should pass."""
        yaml_text = """\
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app-vs
spec:
  hosts:
  - my-app
  http:
  - route:
    - destination:
        host: my-app
        subset: v1
      weight: 80
    - destination:
        host: my-app
        subset: v2
      weight: 20
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_gateway(self):
        """Gateway with correct apiVersion should pass."""
        yaml_text = """\
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
spec:
  servers:
  - port:
      number: 80
      name: http
      protocol: HTTP
    hosts:
    - "*"
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"

    def test_virtualservice_v1_api(self):
        """VirtualService with v1 (not v1beta1) apiVersion should also pass."""
        yaml_text = """\
apiVersion: networking.istio.io/v1
kind: VirtualService
metadata:
  name: my-app-vs
spec:
  hosts:
  - my-app
  http:
  - route:
    - destination:
        host: my-app
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is True, f"Expected ok=True, got error: {d.get('error', '')}"


class TestQ271WrongAnswers:
    """Invalid configurations should be rejected."""

    def test_deployment_named_istio_without_injection(self):
        """The OLD false positive: Deployment named 'istiod' without sidecar injection.

        This was the bug - name containing 'istio' passed the old check.
        The new check should reject it.
        """
        yaml_text = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: istiod
  namespace: istio-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: istiod
  template:
    metadata:
      labels:
        app: istiod
    spec:
      containers:
      - name: istiod
        image: istio/pilot:1.21.0
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False, (
            "Deployment named 'istiod' should NOT pass - "
            "name-based keyword matching was the false positive being fixed"
        )

    def test_namespace_without_injection_label(self):
        """Namespace without istio-injection=enabled should not pass."""
        yaml_text = """\
---
apiVersion: v1
kind: Namespace
metadata:
  name: my-app
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: my-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: nginx:1.25
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False, "Namespace without istio-injection=enabled should fail"

    def test_injection_namespace_without_deployment(self):
        """Namespace with injection label but no Deployment should fail."""
        yaml_text = """\
apiVersion: v1
kind: Namespace
metadata:
  name: my-istio-app
  labels:
    istio-injection: enabled
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False, "Namespace with injection label but no Deployment should fail"

    def test_injection_namespace_deployment_wrong_namespace(self):
        """Deployment not in the injection-enabled namespace should fail."""
        yaml_text = """\
---
apiVersion: v1
kind: Namespace
metadata:
  name: my-istio-app
  labels:
    istio-injection: enabled
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: nginx:1.25
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False, "Deployment in wrong namespace should fail"

    def test_virtualservice_wrong_api_version(self):
        """VirtualService with wrong apiVersion should fail."""
        yaml_text = """\
apiVersion: v1
kind: VirtualService
metadata:
  name: my-app-vs
spec:
  hosts:
  - my-app
  http:
  - route:
    - destination:
        host: my-app
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False, "VirtualService with apiVersion: v1 should fail"

    def test_virtualservice_missing_hosts(self):
        """VirtualService without hosts should fail."""
        yaml_text = """\
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app-vs
spec:
  http:
  - route:
    - destination:
        host: my-app
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False

    def test_virtualservice_missing_http(self):
        """VirtualService without http routes should fail."""
        yaml_text = """\
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: my-app-vs
spec:
  hosts:
  - my-app
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False

    def test_gateway_missing_servers(self):
        """Gateway without servers should fail."""
        yaml_text = """\
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: my-gateway
spec:
  selector:
    istio: ingressgateway
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False

    def test_empty_input(self):
        d = check("Q27.1", "")
        assert d["ok"] is False

    def test_garbage(self):
        d = check("Q27.1", "not yaml {{{")
        assert d["ok"] is False

    def test_just_a_pod(self):
        """A plain Pod is not a valid Istio configuration."""
        yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: x
spec:
  containers:
  - name: x
    image: nginx
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False

    def test_just_a_deployment(self):
        """A plain Deployment without injection is not valid Istio config."""
        yaml_text = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-app
  template:
    metadata:
      labels:
        app: my-app
    spec:
      containers:
      - name: my-app
        image: nginx:1.25
"""
        d = check("Q27.1", yaml_text)
        assert d["ok"] is False
