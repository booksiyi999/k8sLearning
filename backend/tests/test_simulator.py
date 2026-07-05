import pytest
from app.simulator import apply_manifest, ClusterState, K8sError

def test_apply_pod_creates_pod_in_state():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    result = apply_manifest(state, yaml)
    assert "nginx-pod" in result.pods
    assert result.pods["nginx-pod"]["spec"]["containers"][0]["image"] == "nginx:1.25"

def test_apply_invalid_yaml_raises():
    state = ClusterState()
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, "this: is: not: valid: yaml: :::")
    assert "YAML 解析失败" in str(exc.value)

def test_apply_missing_required_field_raises():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    # spec 整体缺失 → 更精确的 "缺少 spec" 文案（而非笼统 spec.containers）
    assert "spec" in str(exc.value)

def test_apply_unsupported_kind_raises():
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Widget
metadata:
  name: x
spec:
  containers: []
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "Widget" in str(exc.value)

def test_apply_deployment_creates_replicasets_pods():
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
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
    result = apply_manifest(state, yaml)
    assert "web" in result.deployments
    # Deployment 创建 3 个虚拟 Pod
    pod_count = sum(1 for p in result.pods.values() if p["metadata"]["labels"].get("app") == "web")
    assert pod_count == 3


def test_validate_pod_rejects_string_container_element():
    """containers 元素是字符串（恰好含 name/image 子串）→ 必须拒绝，不得绕过校验（B8）

    若只做 ``"name" in c`` 子串判断，字符串 "name-image" 会被误判为合法容器，
    随后在关卡校验里调用 c.get(...) 触发 AttributeError → /api/check HTTP 500。
    """
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers:
    - "name-image"
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "containers" in str(exc.value)


# ---------------------------------------------------------------------------
# R2 (第 4 轮): Pod spec.containers 集合层 falsy-only guard
# truthy 非 list（int/dict/str）绕过 `not spec.get("containers")` 后，
# enumerate/索引访问崩溃 → /api/check HTTP 500。守卫必须用 isinstance(list)。
# ---------------------------------------------------------------------------
def test_validate_pod_rejects_int_containers():
    """containers: 5（truthy int）→ 必须拒绝，不得在 enumerate 时崩溃（R2）"""
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers: 5
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "containers" in str(exc.value)


def test_validate_pod_rejects_dict_containers():
    """containers: {}（truthy dict，可迭代但语义错误）→ 必须拒绝（isinstance list 覆盖）"""
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers: {}
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "containers" in str(exc.value)


def test_validate_pod_rejects_string_containers():
    """containers: foo（truthy str，可迭代字符但语义错误）→ 必须拒绝（isinstance list 覆盖）"""
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: bad-pod
spec:
  containers: foo
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "containers" in str(exc.value)


# ---------------------------------------------------------------------------
# R1 (第 4 轮): Deployment spec.template falsy-only guard
# truthy 非 dict（str/int）绕过 `if not template:` 后，template.setdefault 崩溃
# → /api/check HTTP 500。守卫必须用 isinstance(dict)。
# ---------------------------------------------------------------------------
def test_apply_deployment_rejects_string_template():
    """spec.template: foo（truthy str）→ 必须拒绝，不得 setdefault 崩溃（R1）"""
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  template: foo
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "template" in str(exc.value)


def test_apply_deployment_rejects_int_template():
    """spec.template: 5（truthy int）→ 必须拒绝（isinstance dict 覆盖）"""
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  template: 5
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "template" in str(exc.value)


# ---------------------------------------------------------------------------
# 一次性扫清：simulator 其余 falsy-only / 缺类型守卫（同类残留，防第 5 轮）
# metadata 非 dict → .get("name") 崩溃；spec 非 dict → .get 崩溃；
# replicas 非 int → int() 崩溃；metadata.name 含 "name" 子串绕过子串判断。
# ---------------------------------------------------------------------------
def test_validate_pod_rejects_string_metadata_with_name_substring():
    """metadata: namefoo（str 含 'name' 子串）绕过子串判断 → 不得崩溃，必须 K8sError"""
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Pod
metadata: namefoo
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "metadata" in str(exc.value)


def test_apply_deployment_rejects_non_dict_metadata():
    """Deployment metadata: foo（str）→ .get('name') 崩溃 → 必须返回 K8sError"""
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata: foo
spec:
  template: {}
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "metadata" in str(exc.value)


def test_apply_deployment_rejects_non_dict_spec():
    """Deployment spec: foo（str）→ .get 崩溃 → 必须返回 K8sError"""
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: d
spec: foo
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "spec" in str(exc.value)


def test_apply_deployment_rejects_non_int_replicas():
    """Deployment replicas: foo（str）→ int() 崩溃 → 必须返回 K8sError"""
    state = ClusterState()
    yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: d
spec:
  replicas: foo
  template: {}
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "replicas" in str(exc.value)


def test_apply_service_rejects_non_dict_metadata():
    """Service metadata: foo（str）→ .get('name') 崩溃 → 必须返回 K8sError"""
    state = ClusterState()
    yaml = """
apiVersion: v1
kind: Service
metadata: foo
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "metadata" in str(exc.value)


# ---------------------------------------------------------------------------
# 循环引用检测 (攻击维度 #3): yaml.safe_load 对自引用 anchor (&a / *a) 不报错,
# 直接构造循环引用 Python dict。若存入 state, FastAPI 序列化 json.dumps 抛
# ValueError (中间件层, try/except 之外) → HTTP 500。parse 后检测并拒绝。
# ---------------------------------------------------------------------------
def test_apply_rejects_recursive_yaml_anchor_labels():
    """自引用 anchor 在 labels (&a / *a) → 必须拒绝, 不得存入 state"""
    state = ClusterState()
    yaml = """
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
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "循环引用" in str(exc.value)
    # 确保循环结构没有存入 state
    assert "nginx-pod" not in state.pods


def test_apply_rejects_recursive_yaml_anchor_annotations():
    """自引用 anchor 在 annotations → 必须拒绝"""
    state = ClusterState()
    yaml = """
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
"""
    with pytest.raises(K8sError) as exc:
        apply_manifest(state, yaml)
    assert "循环引用" in str(exc.value)


def test_apply_allows_flat_yaml_alias_no_false_positive():
    """合法的 flat alias (非自引用, diamond 共享) → 不得误报为循环引用"""
    state = ClusterState()
    yaml = """
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
"""
    # 不应抛异常 — flat alias 是合法 YAML, 无循环
    result = apply_manifest(state, yaml)
    assert "nginx-pod" in result.pods
