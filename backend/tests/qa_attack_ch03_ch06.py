"""QA 攻击性测试：Chapter 3-6 check_fn 与 simulator 异常输入处理。

5 个攻击维度：
1. 类型混淆攻击（数字/列表/null 作为顶层 YAML）
2. 资源耗尽攻击（超大 YAML、深度嵌套）
3. 注入越权攻击（hostPath/privileged 等危险字段）
4. 校验绕过攻击（大小写混用、单位混淆、字段重复）
5. 边界值攻击（空字符串、port=0、replicas=0、nodePort 边界）
"""
import pytest
import yaml
from app.simulator import apply_manifest, preset_state, ClusterState, K8sError
from app.validator import CheckResult
from app.levels.ch03_service import (
    _check_01_clusterip_service,
    _check_02_nodeport_service,
    _check_03_dns_discovery,
    _check_04_headless_service,
)
from app.levels.ch04_configmap import (
    _check_01_create_configmap,
    _check_02_configmap_env,
    _check_03_configmap_volume,
    _check_04_secret,
)
from app.levels.ch05_storage import (
    _check_01_create_pv,
    _check_02_create_pvc,
    _check_03_pod_with_pvc,
    _check_04_emptydir,
)
from app.levels.ch06_scheduling import (
    _check_01_node_selector,
    _check_02_node_affinity,
    _check_03_taints_tolerations,
    _check_04_resource_limits,
)


# ===========================================================================
# 辅助函数
# ===========================================================================

def _run_check_safely(check_fn, user_yaml: str) -> CheckResult:
    """运行 check_fn，确保不抛未捕获异常（应返回 CheckResult）。"""
    return check_fn(user_yaml)


# ===========================================================================
# 维度 1：类型混淆攻击
# ===========================================================================

class TestTypeConfusionAttack:
    """传非标准 YAML（数字/列表/null 作为顶层）给各 check_fn。"""

    @pytest.mark.parametrize("check_fn", [
        _check_01_clusterip_service,
        _check_02_nodeport_service,
        _check_03_dns_discovery,
        _check_04_headless_service,
        _check_01_create_configmap,
        _check_02_configmap_env,
        _check_03_configmap_volume,
        _check_04_secret,
        _check_01_create_pv,
        _check_02_create_pvc,
        _check_03_pod_with_pvc,
        _check_04_emptydir,
        _check_01_node_selector,
        _check_02_node_affinity,
        _check_03_taints_tolerations,
        _check_04_resource_limits,
    ])
    def test_top_level_integer(self, check_fn):
        """顶层 YAML 是一个整数。"""
        result = _run_check_safely(check_fn, "42")
        assert isinstance(result, CheckResult)
        assert result.ok is False  # 应拒绝

    @pytest.mark.parametrize("check_fn", [
        _check_01_clusterip_service,
        _check_01_create_configmap,
        _check_01_create_pv,
        _check_01_node_selector,
    ])
    def test_top_level_list(self, check_fn):
        """顶层 YAML 是一个列表。"""
        result = _run_check_safely(check_fn, "- item1\n- item2")
        assert isinstance(result, CheckResult)
        assert result.ok is False

    @pytest.mark.parametrize("check_fn", [
        _check_01_clusterip_service,
        _check_01_create_configmap,
        _check_01_create_pv,
    ])
    def test_top_level_null(self, check_fn):
        """顶层 YAML 是 null。"""
        result = _run_check_safely(check_fn, "null")
        assert isinstance(result, CheckResult)
        assert result.ok is False

    @pytest.mark.parametrize("check_fn", [
        _check_01_clusterip_service,
        _check_01_create_configmap,
    ])
    def test_top_level_string(self, check_fn):
        """顶层 YAML 是一个裸字符串。"""
        result = _run_check_safely(check_fn, "just a string")
        assert isinstance(result, CheckResult)
        assert result.ok is False

    @pytest.mark.parametrize("check_fn", [
        _check_01_clusterip_service,
        _check_01_create_pv,
    ])
    def test_top_level_boolean(self, check_fn):
        """顶层 YAML 是一个布尔值。"""
        result = _run_check_safely(check_fn, "true")
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_empty_yaml_string(self):
        """空字符串 YAML。"""
        result = _check_01_clusterip_service("")
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_only_comments(self):
        """只有注释的 YAML。"""
        result = _check_01_create_configmap("# just a comment\n# another")
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_only_separator(self):
        """只有 --- 分隔符的 YAML。"""
        result = _check_01_create_pv("---\n---\n---")
        assert isinstance(result, CheckResult)
        assert result.ok is False


# ===========================================================================
# 维度 2：资源耗尽攻击
# ===========================================================================

class TestResourceExhaustionAttack:
    """超大 YAML、深度嵌套、循环引用。"""

    def test_huge_yaml_string(self):
        """超大 YAML 字符串（10000 行注释 + 1 个有效文档）。"""
        huge = "\n".join(f"# comment line {i}" for i in range(10000))
        huge += "\napiVersion: v1\nkind: Service\nmetadata:\n  name: nginx-svc\nspec:\n  selector:\n    app: nginx\n  ports:\n    - port: 80\n      targetPort: 8080"
        result = _check_01_clusterip_service(huge)
        assert isinstance(result, CheckResult)
        # 应能处理，不崩溃

    def test_deeply_nested_yaml(self):
        """深度嵌套的 YAML（500 层）。"""
        depth = 500
        lines = ["a:" * 0]
        indent = ""
        for i in range(depth):
            indent += "  "
            lines.append(f"{indent}b{i}:")
        lines.append(f"{indent}  val: end")
        yaml_text = "\n".join(lines)
        # 这种 YAML 不是合法 K8s manifest，应被拒绝
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)

    def test_many_ports_in_service(self):
        """Service 中塞入大量端口（1000个）。"""
        ports = "\n".join(f"    - port: {i}\n      targetPort: {i}" for i in range(1000))
        yaml_text = f"""apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
{ports}
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)

    def test_many_configmap_keys(self):
        """ConfigMap 中塞入大量 key（5000个）。"""
        entries = "\n".join(f"  KEY_{i}: value_{i}" for i in range(5000))
        yaml_text = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
{entries}
"""
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)

    def test_many_documents(self):
        """多文档 YAML（500 个 --- 分隔的文档）。"""
        docs = []
        for i in range(500):
            docs.append(f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: cm-{i}
data:
  key: value""")
        yaml_text = "\n---\n".join(docs)
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)

    def test_circular_ref_yaml(self):
        """YAML 自引用 anchor（循环引用）。"""
        yaml_text = """a: &anchor
  b: *anchor
"""
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, yaml_text)

    def test_extremely_long_string_value(self):
        """超长字符串值（1MB）。"""
        long_val = "x" * (1024 * 1024)
        yaml_text = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
  BIG: "{long_val}"
"""
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)


# ===========================================================================
# 维度 3：注入越权攻击
# ===========================================================================

class TestInjectionAttack:
    """YAML 里塞 hostPath/privileged 等危险字段。"""

    def test_pod_with_hostpath(self):
        """Pod 挂载 hostPath。simulator 应接受但不崩溃。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: evil-pod
spec:
  containers:
    - name: evil
      image: alpine
      securityContext:
        privileged: true
      volumeMounts:
        - name: host
          mountPath: /host
  volumes:
    - name: host
      hostPath:
        path: /
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        assert "evil-pod" in state.pods

    def test_pv_with_hostpath_injection(self):
        """PV 中 hostPath 注入。check_fn 应正确验证。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /etc/shadow
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # path 不是 /mnt/data

    def test_pod_with_privileged_container(self):
        """Pod 里有 privileged: true 容器。simulator 不应崩溃。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: priv-pod
spec:
  containers:
    - name: priv
      image: alpine
      securityContext:
        privileged: true
        runAsUser: 0
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        assert "priv-pod" in state.pods

    def test_pod_with_host_network(self):
        """Pod 使用 hostNetwork。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: hostnet-pod
spec:
  hostNetwork: true
  containers:
    - name: app
      image: nginx
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        assert "hostnet-pod" in state.pods

    def test_secret_with_plain_text_password(self):
        """Secret 使用 stringData 而非 data。"""
        yaml_text = """apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
stringData:
  password: mypassword123
---
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
    - name: client
      image: postgres:15
      env:
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
"""
        result = _check_04_secret(yaml_text)
        assert isinstance(result, CheckResult)

    def test_yaml_with_special_chars_in_name(self):
        """metadata.name 含特殊字符。"""
        yaml_text = """apiVersion: v1
kind: ConfigMap
metadata:
  name: "../../etc/passwd"
data:
  APP_MODE: production
  LOG_LEVEL: info
"""
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # 名字不是 app-config


# ===========================================================================
# 维度 4：校验绕过攻击
# ===========================================================================

class TestBypassAttack:
    """大小写混用、单位混淆、字段重复。"""

    def test_service_type_case_mismatch(self):
        """Service type 大小写混用：clusterip vs ClusterIP。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  type: clusterip
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # 小写 clusterip 应被拒绝

    def test_service_type_nodeport_lowercase(self):
        """NodePort 用小写 nodeport。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  type: nodeport
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
"""
        result = _check_02_nodeport_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pv_storage_unit_case(self):
        """PV storage 用小写 5gi 而非 5Gi。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # 5gi != 5Gi

    def test_pv_accessmode_case(self):
        """accessModes 用小写 readwriteonce。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - readwriteonce
  hostPath:
    path: /mnt/data
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_headless_clusterip_lowercase_none(self):
        """Headless Service clusterIP 用小写 none。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: db-svc
spec:
  clusterIP: none
  selector:
    app: db
  ports:
    - port: 5432
"""
        result = _check_04_headless_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # "none" != "None"

    def test_duplicate_yaml_keys(self):
        """YAML 中重复 key（PyYAML 默认后者覆盖前者）。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
  name: nginx-svc-override
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        # PyYAML 默认后者覆盖，所以 name=nginx-svc-override, 找不到 nginx-svc
        assert result.ok is False

    def test_duplicate_port_key(self):
        """ports[0] 中重复 port 字段。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 9999
      port: 80
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)

    def test_duplicate_storage_key(self):
        """PV 中重复 capacity.storage 字段。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 1Gi
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)

    def test_secret_type_case_mismatch(self):
        """Secret type 用小写 opaque。"""
        yaml_text = """apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: opaque
data:
  password: cGFzcw==
---
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
    - name: client
      image: postgres:15
      env:
        - name: PWD
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: password
"""
        result = _check_04_secret(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # opaque != Opaque


# ===========================================================================
# 维度 5：边界值攻击
# ===========================================================================

class TestBoundaryAttack:
    """空字符串、空端口、port=0、replicas=0、nodePort 边界。"""

    def test_port_zero(self):
        """Service port=0。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 0
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # port 0 != 80

    def test_targetport_zero(self):
        """targetPort=0。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 0
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # targetPort 0 != 8080

    def test_nodeport_below_range(self):
        """nodePort=29999（低于范围 30000）。"""
        yaml_text = """apiVersion: v1
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
      nodePort: 29999
"""
        result = _check_02_nodeport_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_nodeport_above_range(self):
        """nodePort=32768（高于范围 32767）。"""
        yaml_text = """apiVersion: v1
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
      nodePort: 32768
"""
        result = _check_02_nodeport_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_nodeport_boundary_30000(self):
        """nodePort=30000（恰好下界）。"""
        yaml_text = """apiVersion: v1
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
      nodePort: 30000
"""
        result = _check_02_nodeport_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is True  # 30000 在范围内

    def test_nodeport_boundary_32767(self):
        """nodePort=32767（恰好上界）。"""
        yaml_text = """apiVersion: v1
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
      nodePort: 32767
"""
        result = _check_02_nodeport_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is True  # 32767 在范围内

    def test_empty_selector_value(self):
        """selector.app 为空字符串。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: ""
  ports:
    - port: 80
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # "" != "nginx"

    def test_empty_port_list(self):
        """ports 为空列表。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports: []
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_empty_string_as_yaml(self):
        """空字符串作为 YAML。"""
        for fn in [_check_01_clusterip_service, _check_01_create_configmap, _check_01_create_pv]:
            result = fn("")
            assert isinstance(result, CheckResult)
            assert result.ok is False

    def test_port_negative(self):
        """port 为负数。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: -1
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)

    def test_port_as_string(self):
        """port 是字符串而非整数。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: "80"
      targetPort: "8080"
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        # "80" != 80 (int), 应失败
        assert result.ok is False

    def test_port_as_float(self):
        """port 是浮点数。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 80.0
      targetPort: 8080.0
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)

    def test_configmap_empty_data(self):
        """ConfigMap data 为空字典。"""
        yaml_text = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data: {}
"""
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_configmap_null_data(self):
        """ConfigMap data 为 null。"""
        yaml_text = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data: null
"""
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pv_zero_storage(self):
        """PV storage=0。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: "0"
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pv_empty_accessmodes(self):
        """PV accessModes 为空列表。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes: []
  hostPath:
    path: /mnt/data
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # [] != [ReadWriteOnce]

    def test_pod_no_containers(self):
        """Pod 没有 containers。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: empty-pod
spec:
  containers: []
"""
        result = _check_03_dns_discovery(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_resource_limits_zero_cpu(self):
        """resources 中 cpu=0。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: limited-pod
spec:
  containers:
    - name: app
      image: nginx
      resources:
        requests:
          cpu: 0
          memory: 0
        limits:
          cpu: 0
          memory: 0
"""
        result = _check_04_resource_limits(yaml_text)
        assert isinstance(result, CheckResult)
        # 0 是有效值，check_fn 不校验范围，应通过
        # 但这可能是 bug：真实 K8s 不允许 cpu=0

    def test_resource_limits_negative_memory(self):
        """resources 中 memory 为负数。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: limited-pod
spec:
  containers:
    - name: app
      image: nginx
      resources:
        requests:
          cpu: 100m
          memory: -128Mi
        limits:
          cpu: 200m
          memory: -256Mi
"""
        result = _check_04_resource_limits(yaml_text)
        assert isinstance(result, CheckResult)
        # 负数 memory 应该是无效的，但 check_fn 可能不校验

    def test_emptydir_with_empty_containers(self):
        """emptyDir 但只有一个容器。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: shared-pod
spec:
  containers:
    - name: writer
      image: busybox
  volumes:
    - name: shared
      emptyDir: {}
"""
        result = _check_04_emptydir(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False  # 需要至少 2 个容器

    def test_tolerations_empty_list(self):
        """tolerations 为空列表。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: special-pod
spec:
  containers:
    - name: app
      image: nginx
  tolerations: []
"""
        result = _check_03_taints_tolerations(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_node_selector_empty_dict(self):
        """nodeSelector 为空字典。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx
  nodeSelector: {}
"""
        result = _check_01_node_selector(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_port_very_large(self):
        """port 为超大整数。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - port: 999999999999
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)

    def test_configmap_with_integer_value(self):
        """ConfigMap data 值为整数而非字符串。"""
        yaml_text = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
  PORT: 8080
"""
        result = _check_01_create_configmap(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is True  # 整数值不阻止通过

    def test_pod_metadata_name_integer(self):
        """metadata.name 为整数。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: 12345
spec:
  containers:
    - name: app
      image: nginx
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        # name=12345 (int), 不崩溃即可

    def test_service_without_spec(self):
        """Service 没有 spec。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_service_without_metadata(self):
        """Service 没有 metadata。"""
        yaml_text = """apiVersion: v1
kind: Service
spec:
  selector:
    app: nginx
  ports:
    - port: 80
      targetPort: 8080
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pod_spec_not_dict(self):
        """Pod spec 是字符串而非 dict。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec: "not a dict"
"""
        result = _check_03_dns_discovery(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_containers_not_list(self):
        """containers 是字符串而非 list。"""
        yaml_text = """apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers: "not a list"
"""
        result = _check_03_dns_discovery(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_service_port_not_dict(self):
        """ports[0] 是字符串而非 dict。"""
        yaml_text = """apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  selector:
    app: nginx
  ports:
    - "not a dict"
"""
        result = _check_01_clusterip_service(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pv_capacity_not_dict(self):
        """capacity 是字符串而非 dict — BUG: check_fn 崩溃 AttributeError。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity: "broken"
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
"""
        # BUG-001: spec.get("capacity", {}).get("storage") 当 capacity 是
        # truthy 非 dict (str/int/list) 时, .get() 在 str/int 上抛
        # AttributeError, 绕过 K8sError 异常处理, 导致 HTTP 500。
        # 同一 pattern 也影响 hostPath 字段。
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pv_capacity_integer(self):
        """capacity 是整数 — BUG-001 变体。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity: 42
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pv_hostpath_not_dict(self):
        """hostPath 是字符串而非 dict — BUG-001 变体。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath: "broken"
"""
        result = _check_01_create_pv(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pvc_resources_not_dict(self):
        """resources 是字符串 — BUG-002: check_fn 崩溃 AttributeError。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources: "broken"
"""
        # BUG-002: spec.get("resources", {}).get("requests", {}).get("storage")
        # 当 resources 是 truthy 非 dict 时, .get() 在 str 上抛 AttributeError。
        result = _check_02_create_pvc(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_pvc_requests_not_dict(self):
        """requests 是字符串 — BUG-002 变体。"""
        yaml_text = """apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests: "broken"
"""
        result = _check_02_create_pvc(yaml_text)
        assert isinstance(result, CheckResult)
        assert result.ok is False

    def test_deployment_replicas_zero(self):
        """Deployment replicas=0。"""
        yaml_text = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: zero-deploy
spec:
  replicas: 0
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
        - name: app
          image: nginx
"""
        state = ClusterState()
        state = apply_manifest(state, yaml_text)
        # replicas=0 合法，不应创建 Pod
        deploy_pods = [n for n in state.pods if n.startswith("zero-deploy")]
        assert len(deploy_pods) == 0
