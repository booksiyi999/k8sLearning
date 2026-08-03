"""Chapter 4: ConfigMap & Secret 测试"""
import pytest
from app.simulator import ClusterState, apply_manifest, preset_state, K8sError
from app.validator import get_level, list_levels


class TestQ41CreateConfigMap:
    def test_correct_configmap(self):
        yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
"""
        lv = get_level("Q4.1")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_wrong_name(self):
        yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: wrong-name
data:
  APP_MODE: production
  LOG_LEVEL: info
"""
        lv = get_level("Q4.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "app-config" in result.error

    def test_missing_app_mode(self):
        yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  LOG_LEVEL: info
"""
        lv = get_level("Q4.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "APP_MODE" in result.error

    def test_wrong_app_mode(self):
        yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: development
  LOG_LEVEL: info
"""
        lv = get_level("Q4.1")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "production" in result.error

    def test_missing_data(self):
        yaml = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
"""
        lv = get_level("Q4.1")
        result = lv.check_fn(yaml)
        assert not result.ok


class TestQ42ConfigMapEnv:
    def test_correct_env_configmapkeyref(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      env:
        - name: APP_MODE
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: APP_MODE
"""
        lv = get_level("Q4.2")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_envfrom(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      envFrom:
        - configMapRef:
            name: app-config
"""
        lv = get_level("Q4.2")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_no_configmap_ref(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      env:
        - name: APP_MODE
          value: production
"""
        lv = get_level("Q4.2")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "app-config" in result.error


class TestQ43ConfigMapVolume:
    def test_correct_volume_mount(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      volumeMounts:
        - name: config-vol
          mountPath: /etc/config
  volumes:
    - name: config-vol
      configMap:
        name: app-config
"""
        lv = get_level("Q4.3")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_no_volume(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
    - name: app
      image: nginx:latest
"""
        lv = get_level("Q4.3")
        result = lv.check_fn(yaml)
        assert not result.ok

    def test_wrong_configmap_name(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
    - name: app
      image: nginx:latest
      volumeMounts:
        - name: config-vol
          mountPath: /etc/config
  volumes:
    - name: config-vol
      configMap:
        name: wrong-name
"""
        lv = get_level("Q4.3")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "app-config" in result.error

    def test_no_volume_mounts(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: config-pod
spec:
  containers:
    - name: app
      image: nginx:latest
  volumes:
    - name: config-vol
      configMap:
        name: app-config
"""
        lv = get_level("Q4.3")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "volumeMounts" in result.error


class TestQ44Secret:
    def test_correct_secret_with_env(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
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
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_secret_with_envfrom(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
---
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
    - name: client
      image: postgres:15
      envFrom:
        - secretRef:
            name: db-secret
"""
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_correct_secret_with_volume(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
---
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
    - name: client
      image: postgres:15
      volumeMounts:
        - name: secret-vol
          mountPath: /etc/secret
  volumes:
    - name: secret-vol
      secret:
        secretName: db-secret
"""
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert result.ok, f"Expected ok, got error: {result.error}"

    def test_wrong_secret_name(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: wrong-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
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
              name: wrong-secret
              key: password
"""
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "db-secret" in result.error

    def test_missing_password(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  username: YWRtaW4=
---
apiVersion: v1
kind: Pod
metadata:
  name: db-client
spec:
  containers:
    - name: client
      image: postgres:15
      envFrom:
        - secretRef:
            name: db-secret
"""
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "password" in result.error

    def test_no_pod(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
"""
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "Pod" in result.error

    def test_pod_not_referencing_secret(self):
        yaml = """
apiVersion: v1
kind: Secret
metadata:
  name: db-secret
type: Opaque
data:
  password: cGFzc3dvcmQxMjM=
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
          value: hardcoded
"""
        lv = get_level("Q4.4")
        result = lv.check_fn(yaml)
        assert not result.ok
        assert "db-secret" in result.error


class TestChapter4Registration:
    def test_list_levels_includes_ch04(self):
        levels = list_levels()
        ch04 = [lv for lv in levels if lv["chapter"] == "ch04"]
        assert len(ch04) == 5

    def test_get_level_q41(self):
        lv = get_level("Q4.1")
        assert lv is not None
        assert lv.chapter == "ch04"
        assert lv.title == "创建 ConfigMap"

    def test_get_level_q44(self):
        lv = get_level("Q4.4")
        assert lv is not None
        assert lv.chapter == "ch04"
        assert lv.title == "创建 Secret 并使用"

    def test_total_levels(self):
        levels = list_levels()
        assert len(levels) == 60
