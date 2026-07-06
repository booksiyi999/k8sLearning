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


# ===========================================================================
# Chapter 2 扩展: Preset 机制 + Rollout History + Rollback
# 这些测试验证 simulator 为 Q2.3 (滚动更新) 和 Q2.4 (回滚) 提供的基础设施。
# ===========================================================================

from app.simulator import preset_state, rollback_deployment  # noqa: E402


# --- Preset 机制 ---

def test_preset_state_creates_deployment_and_pods():
    """preset_state 应用 YAML 后, deployment 和对应 pods 应存在"""
    state = ClusterState()
    yaml_text = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    state = preset_state(state, yaml_text)
    assert "web-deploy" in state.deployments
    # 3 个虚拟 Pod
    web_pods = [p for p in state.pods.values()
                if p["metadata"]["labels"].get("app") == "web"]
    assert len(web_pods) == 3


def test_preset_state_then_apply_upgrade():
    """preset v1 后 apply v2 (玩家升级), deployment 应反映新 image"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
    state = preset_state(state, v1)
    state = apply_manifest(state, v2)  # 玩家提交升级
    deploy = state.deployments["web-deploy"]
    image = deploy["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "nginx:1.25"


def test_preset_state_invalid_yaml_raises():
    """preset_state 传入非法 YAML 应抛 K8sError"""
    state = ClusterState()
    with pytest.raises(K8sError):
        preset_state(state, "this: is: not: valid: yaml: :::")


# --- Rollout History (revisions) ---

def test_revisions_empty_by_default():
    """新 ClusterState 的 revisions 应为空 dict"""
    state = ClusterState()
    assert state.revisions == {}


def test_first_deployment_apply_creates_revision_1():
    """首次 apply Deployment 应创建 revision 1"""
    state = ClusterState()
    yaml_text = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    apply_manifest(state, yaml_text)
    assert "web-deploy" in state.revisions
    assert len(state.revisions["web-deploy"]) == 1
    rev = state.revisions["web-deploy"][0]
    assert rev["revision"] == 1
    assert rev["image"] == "nginx:1.24"
    assert rev["replicas"] == 3


def test_deployment_update_creates_revision_2():
    """同一 deployment 第二次 apply (更新 image) 应创建 revision 2"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:1.25")
    apply_manifest(state, v1)
    apply_manifest(state, v2)
    assert len(state.revisions["web-deploy"]) == 2
    assert state.revisions["web-deploy"][0]["image"] == "nginx:1.24"
    assert state.revisions["web-deploy"][1]["image"] == "nginx:1.25"


def test_rollout_history_tracks_replica_changes():
    """replica 变更也应记录在 revision history 中"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deploy
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: app
          image: python:3.11-slim
"""
    v2 = v1.replace("replicas: 3", "replicas: 5")
    apply_manifest(state, v1)
    apply_manifest(state, v2)
    assert state.revisions["api-deploy"][0]["replicas"] == 3
    assert state.revisions["api-deploy"][1]["replicas"] == 5


def test_revision_doc_is_deep_copy_not_reference():
    """revision 中存储的 doc 应是深拷贝, 不应被后续 apply 原地修改"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:1.25")
    apply_manifest(state, v1)
    rev1_doc = state.revisions["web-deploy"][0]["doc"]
    apply_manifest(state, v2)
    # rev1_doc 不应被第二次 apply 修改
    img = rev1_doc["spec"]["template"]["spec"]["containers"][0]["image"]
    assert img == "nginx:1.24"


# --- Rollback ---

def test_rollback_restores_old_image():
    """apply v1, apply v2, rollback → deployment image 回到 v1"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:broken")
    apply_manifest(state, v1)
    apply_manifest(state, v2)
    rollback_deployment(state, "web-deploy")
    deploy = state.deployments["web-deploy"]
    image = deploy["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "nginx:1.24"


def test_rollback_creates_new_revision():
    """rollback 后, revisions 应有 3 个条目 (rollback = 新 revision)"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:broken")
    apply_manifest(state, v1)
    apply_manifest(state, v2)
    assert len(state.revisions["web-deploy"]) == 2
    rollback_deployment(state, "web-deploy")
    assert len(state.revisions["web-deploy"]) == 3
    # 回滚后的 revision 应与 revision 1 的 image 一致
    assert state.revisions["web-deploy"][2]["image"] == "nginx:1.24"


def test_rollback_updates_pods_to_old_image():
    """rollback 后, pods 的 image 应反映回滚后的版本"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
spec:
  replicas: 2
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:1.25")
    apply_manifest(state, v1)
    apply_manifest(state, v2)
    # 确认 v2 的 pods 是 1.25
    web_pods = [p for p in state.pods.values()
                if p["metadata"]["labels"].get("app") == "web"]
    assert all(p["spec"]["containers"][0]["image"] == "nginx:1.25" for p in web_pods)
    rollback_deployment(state, "web-deploy")
    # 回滚后 pods 应是 1.24
    web_pods = [p for p in state.pods.values()
                if p["metadata"]["labels"].get("app") == "web"]
    assert all(p["spec"]["containers"][0]["image"] == "nginx:1.24" for p in web_pods)


def test_rollback_no_history_raises():
    """只有 1 个 revision 的 deployment 无法回滚 → K8sError"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    apply_manifest(state, v1)
    with pytest.raises(K8sError) as exc:
        rollback_deployment(state, "web-deploy")
    assert "回滚" in str(exc.value) or "rollback" in str(exc.value).lower()


def test_rollback_nonexistent_deployment_raises():
    """回滚不存在的 deployment → K8sError"""
    state = ClusterState()
    with pytest.raises(K8sError) as exc:
        rollback_deployment(state, "nonexistent")
    assert "nonexistent" in str(exc.value)


def test_rollback_specific_revision():
    """回滚到指定 revision (跳过上一版, 回到更早的版本)"""
    state = ClusterState()
    base = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:{ver}
"""
    apply_manifest(state, base.format(ver="1.24"))   # rev 1
    apply_manifest(state, base.format(ver="1.25"))   # rev 2
    apply_manifest(state, base.format(ver="1.26"))   # rev 3
    # 回滚到 revision 1 (nginx:1.24), 跳过 revision 2
    rollback_deployment(state, "web-deploy", to_revision=1)
    deploy = state.deployments["web-deploy"]
    image = deploy["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "nginx:1.24"


def test_rollback_nonexistent_revision_raises():
    """回滚到不存在的 revision number → K8sError"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:1.25")
    apply_manifest(state, v1)
    apply_manifest(state, v2)
    with pytest.raises(K8sError) as exc:
        rollback_deployment(state, "web-deploy", to_revision=99)
    assert "99" in str(exc.value)


# --- Rollback via annotation (apply_manifest 集成) ---

def test_rollback_annotation_triggers_in_apply_manifest():
    """玩家提交带 k8s-quest/rollback: true annotation 的 YAML → 触发回滚"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    v2 = v1.replace("nginx:1.24", "nginx:broken")
    apply_manifest(state, v1)
    apply_manifest(state, v2)

    rollback_yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    k8s-quest/rollback: "true"
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
    apply_manifest(state, rollback_yaml)
    deploy = state.deployments["web-deploy"]
    image = deploy["spec"]["template"]["spec"]["containers"][0]["image"]
    assert image == "nginx:1.24"  # 回滚到上一版


def test_rollback_annotation_on_no_history_raises():
    """带 rollback annotation 的 YAML 应用到只有 1 个 revision 的 deployment → K8sError"""
    state = ClusterState()
    v1 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
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
          image: nginx:1.24
"""
    apply_manifest(state, v1)
    rollback_yaml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    k8s-quest/rollback: "true"
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
    with pytest.raises(K8sError):
        apply_manifest(state, rollback_yaml)


# --- 向后兼容: Pod/Service 不受 revisions 影响 ---

def test_pod_apply_does_not_create_revisions():
    """apply Pod 不应在 revisions 中产生条目"""
    state = ClusterState()
    yaml_text = """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
"""
    apply_manifest(state, yaml_text)
    assert state.revisions == {}


def test_service_apply_does_not_create_revisions():
    """apply Service 不应在 revisions 中产生条目"""
    state = ClusterState()
    yaml_text = """\
apiVersion: v1
kind: Service
metadata:
  name: web-svc
spec:
  selector:
    app: web
  ports:
    - port: 80
      targetPort: 8080
"""
    apply_manifest(state, yaml_text)
    assert state.revisions == {}
