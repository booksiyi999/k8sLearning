"""Chapter 3: Service & 网络服务发现 测试"""
import pytest
from app.simulator import (
    ClusterState,
    apply_manifest,
    preset_state,
    resolve_service_endpoints,
    resolve_dns,
    K8sError,
)
from app.validator import get_level, list_levels


# ==================== Q3.1 ClusterIP Service ====================

class TestQ31ClusterIPService:
    def test_correct_clusterip(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  type: ClusterIP
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_without_type(self):
        """type 可省略，默认 ClusterIP"""
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_wrong_name(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: wrong-name
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "nginx-svc" in result.error

    def test_wrong_selector(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: redis
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "nginx" in result.error

    def test_wrong_port(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 443
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "80" in result.error

    def test_wrong_target_port(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 3000
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "8080" in result.error

    def test_missing_selector(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert not result.ok

    def test_wrong_type(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  type: NodePort
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "ClusterIP" in result.error


# ==================== Q3.2 NodePort Service ====================

class TestQ32NodePortService:
    def test_correct_nodeport_with_nodeport(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080
"""
        lv = get_level("Q3.2")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_nodeport_without_nodeport(self):
        """nodePort 可省略，K8s 自动分配"""
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.2")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_wrong_type(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: ClusterIP
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.2")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "NodePort" in result.error

    def test_nodeport_out_of_range(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 8080
"""
        lv = get_level("Q3.2")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "30000" in result.error

    def test_missing_selector(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: NodePort
  ports:
    - port: 80
      targetPort: 8080
"""
        lv = get_level("Q3.2")
        result = lv.check_fn(yaml)
        assert not result.ok


# ==================== Q3.3 DNS Discovery ====================

class TestQ33DNSDiscovery:
    def test_correct_with_env(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
spec:
  containers:
    - name: frontend
      image: nginx:latest
      env:
        - name: BACKEND_URL
          value: "http://backend-svc:3000"
"""
        lv = get_level("Q3.3")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_with_command(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
spec:
  containers:
    - name: frontend
      image: nginx:latest
      command: ["curl", "http://backend-svc:3000/health"]
"""
        lv = get_level("Q3.3")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_with_args(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
spec:
  containers:
    - name: frontend
      image: busybox:latest
      args: ["-backend", "backend-svc:3000"]
"""
        lv = get_level("Q3.3")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_no_dns_reference(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: frontend-pod
spec:
  containers:
    - name: frontend
      image: nginx:latest
      env:
        - name: BACKEND_URL
          value: "http://10.0.0.1:3000"
"""
        lv = get_level("Q3.3")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "backend-svc" in result.error


# ==================== Q3.4 Headless Service ====================

class TestQ34HeadlessService:
    def test_correct_headless(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  clusterIP: None
  selector:
    app: db
  ports:
    - port: 5432
      targetPort: 5432
"""
        lv = get_level("Q3.4")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_wrong_clusterip(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  clusterIP: 10.96.0.100
  selector:
    app: db
  ports:
    - port: 5432
      targetPort: 5432
"""
        lv = get_level("Q3.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "None" in result.error

    def test_missing_clusterip(self):
        """不写 clusterIP 默认分配 IP，不是 Headless"""
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  selector:
    app: db
  ports:
    - port: 5432
      targetPort: 5432
"""
        lv = get_level("Q3.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "None" in result.error

    def test_wrong_selector(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  clusterIP: None
  selector:
    app: redis
  ports:
    - port: 5432
      targetPort: 5432
"""
        lv = get_level("Q3.4")
        result = lv.check_fn(yaml)
        assert not result.ok

    def test_wrong_name(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: wrong-svc
spec:
  clusterIP: None
  selector:
    app: db
  ports:
    - port: 5432
      targetPort: 5432
"""
        lv = get_level("Q3.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "db-svc" in result.error


# ==================== Simulator 扩展测试 ====================

class TestSimulatorServiceExtensions:
    def test_resolve_service_endpoints(self):
        state = ClusterState()
        state = apply_manifest(state, """
apiVersion: v1
kind: Pod
metadata:
  name: web-0
  labels:
    app: web
spec:
  containers:
    - name: web
      image: nginx:latest
---
apiVersion: v1
kind: Pod
metadata:
  name: web-1
  labels:
    app: web
spec:
  containers:
    - name: web
      image: nginx:latest
---
apiVersion: v1
kind: Pod
metadata:
  name: db-0
  labels:
    app: db
spec:
  containers:
    - name: db
      image: postgres:15
---
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
    - port: 80
""")
        endpoints = resolve_service_endpoints(state, "web-svc")
        assert sorted(endpoints) == ["web-0", "web-1"]

    def test_resolve_service_endpoints_no_match(self):
        state = ClusterState()
        state = apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: orphan-svc
spec:
  selector:
    app: nonexistent
  ports:
    - port: 80
""")
        endpoints = resolve_service_endpoints(state, "orphan-svc")
        assert endpoints == []

    def test_resolve_dns_clusterip(self):
        state = ClusterState()
        state = apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
  clusterIP: 10.96.0.42
  selector:
    app: web
  ports:
    - port: 80
""")
        dns = resolve_dns(state, "my-svc")
        assert dns is not None
        assert dns["type"] == "ClusterIP"
        assert dns["ip"] == "10.96.0.42"

    def test_resolve_dns_headless(self):
        state = ClusterState()
        state = apply_manifest(state, """
apiVersion: v1
kind: Pod
metadata:
  name: db-0
  labels:
    app: db
spec:
  containers:
    - name: db
      image: postgres:15
---
apiVersion: v1
kind: Pod
metadata:
  name: db-1
  labels:
    app: db
spec:
  containers:
    - name: db
      image: postgres:15
---
apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  clusterIP: None
  selector:
    app: db
  ports:
    - port: 5432
""")
        dns = resolve_dns(state, "db-svc")
        assert dns is not None
        assert dns["type"] == "Headless"
        assert sorted(dns["endpoints"]) == ["db-0", "db-1"]

    def test_resolve_dns_nodeport(self):
        state = ClusterState()
        state = apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: np-svc
spec:
  type: NodePort
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
      nodePort: 30080
""")
        dns = resolve_dns(state, "np-svc")
        assert dns is not None
        assert dns["type"] == "NodePort"
        assert dns["nodePort"] == 30080

    def test_resolve_dns_not_found(self):
        state = ClusterState()
        dns = resolve_dns(state, "nonexistent")
        assert dns is None

    def test_service_validation_invalid_type(self):
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: bad-svc
spec:
  type: InvalidType
  ports:
    - port: 80
""")

    def test_service_validation_missing_ports(self):
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: bad-svc
spec:
  selector:
    app: web
""")

    def test_service_validation_non_dict_port(self):
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: bad-svc
spec:
  ports: "not-a-list"
""")

    def test_service_validation_non_int_port(self):
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: bad-svc
spec:
  ports:
    - port: "eighty"
""")

    def test_service_validation_non_dict_selector(self):
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, """
apiVersion: v1
kind: Service
metadata:
  name: bad-svc
spec:
  selector: "not-a-dict"
  ports:
    - port: 80
""")


# ==================== 关卡注册测试 ====================

class TestChapter3Registration:
    def test_list_levels_includes_ch03(self):
        levels = list_levels()
        ch03 = [lv for lv in levels if lv["chapter"] == "ch03"]
        assert len(ch03) == 5

    def test_get_level_q31(self):
        lv = get_level("Q3.1")
        assert lv is not None
        assert lv.chapter == "ch03"
        assert lv.title == "创建 ClusterIP Service"

    def test_get_level_q32(self):
        lv = get_level("Q3.2")
        assert lv is not None
        assert lv.chapter == "ch03"
        assert lv.title == "NodePort 对外暴露"

    def test_get_level_q33(self):
        lv = get_level("Q3.3")
        assert lv is not None
        assert lv.chapter == "ch03"
        assert lv.title == "Service 发现 DNS"

    def test_get_level_q34(self):
        lv = get_level("Q3.4")
        assert lv is not None
        assert lv.chapter == "ch03"
        assert lv.title == "Headless Service"

    def test_total_levels(self):
        levels = list_levels()
        assert len(levels) == 90
