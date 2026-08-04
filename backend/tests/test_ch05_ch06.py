"""Chapter 5 & 6 测试"""
import pytest
from app.simulator import ClusterState, apply_manifest, preset_state, K8sError
from app.validator import get_level, list_levels


# ===== Chapter 5: Storage =====

class TestQ51CreatePV:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: /mnt/data
"""
        r = get_level("Q5.1").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_name(self):
        yaml = """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: wrong
spec:
  capacity:
    storage: 5Gi
  accessModes: [ReadWriteOnce]
  hostPath:
    path: /mnt/data
"""
        r = get_level("Q5.1").check_fn(yaml)
        assert not r.ok and "data-pv" in r.error

    def test_wrong_size(self):
        yaml = """
apiVersion: v1
kind: PersistentVolume
metadata:
  name: data-pv
spec:
  capacity:
    storage: 1Gi
  accessModes: [ReadWriteOnce]
  hostPath:
    path: /mnt/data
"""
        r = get_level("Q5.1").check_fn(yaml)
        assert not r.ok and "5Gi" in r.error


class TestQ52CreatePVC:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
"""
        r = get_level("Q5.2").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_name(self):
        yaml = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: wrong
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
"""
        r = get_level("Q5.2").check_fn(yaml)
        assert not r.ok


class TestQ53PodWithPVC:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data-pvc
"""
        r = get_level("Q5.3").check_fn(yaml)
        assert r.ok, r.error

    def test_no_pvc_ref(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      emptyDir: {}
"""
        r = get_level("Q5.3").check_fn(yaml)
        assert not r.ok and "data-pvc" in r.error


class TestQ54EmptyDir:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: shared-pod
spec:
  containers:
    - name: writer
      image: busybox
      volumeMounts:
        - name: shared
          mountPath: /shared
    - name: reader
      image: busybox
      volumeMounts:
        - name: shared
          mountPath: /shared
  volumes:
    - name: shared
      emptyDir: {}
"""
        r = get_level("Q5.4").check_fn(yaml)
        assert r.ok, r.error

    def test_no_emptydir(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: shared-pod
spec:
  containers:
    - name: writer
      image: busybox
    - name: reader
      image: busybox
"""
        r = get_level("Q5.4").check_fn(yaml)
        assert not r.ok and "emptyDir" in r.error

    def test_single_container(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: shared-pod
spec:
  containers:
    - name: solo
      image: busybox
  volumes:
    - name: shared
      emptyDir: {}
"""
        r = get_level("Q5.4").check_fn(yaml)
        assert not r.ok and "2" in r.error


# ===== Chapter 6: Scheduling =====

class TestQ61NodeSelector:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx
  nodeSelector:
    disktype: ssd
"""
        r = get_level("Q6.1").check_fn(yaml)
        assert r.ok, r.error

    def test_no_selector(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx
"""
        r = get_level("Q6.1").check_fn(yaml)
        assert not r.ok and "nodeSelector" in r.error

    def test_wrong_selector(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx
  nodeSelector:
    disktype: hdd
"""
        r = get_level("Q6.1").check_fn(yaml)
        assert not r.ok and "ssd" in r.error


class TestQ62NodeAffinity:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: ml-pod
spec:
  containers:
    - name: app
      image: tensorflow:latest
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        nodeSelectorTerms:
          - matchExpressions:
              - key: gpu
                operator: In
                values:
                  - "true"
"""
        r = get_level("Q6.2").check_fn(yaml)
        assert r.ok, r.error

    def test_no_affinity(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: ml-pod
spec:
  containers:
    - name: app
      image: tensorflow
"""
        r = get_level("Q6.2").check_fn(yaml)
        assert not r.ok and "affinity" in r.error


class TestQ63Tolerations:
    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: special-pod
spec:
  containers:
    - name: app
      image: nginx
  tolerations:
    - key: dedicated
      operator: Equal
      value: special
      effect: NoSchedule
"""
        r = get_level("Q6.3").check_fn(yaml)
        assert r.ok, r.error

    def test_no_tolerations(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: special-pod
spec:
  containers:
    - name: app
      image: nginx
"""
        r = get_level("Q6.3").check_fn(yaml)
        assert not r.ok and "tolerations" in r.error


class TestQ64ResourceLimits:
    def test_correct(self):
        yaml = """
apiVersion: v1
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
          memory: 128Mi
        limits:
          cpu: 200m
          memory: 256Mi
"""
        r = get_level("Q6.4").check_fn(yaml)
        assert r.ok, r.error

    def test_no_resources(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: limited-pod
spec:
  containers:
    - name: app
      image: nginx
"""
        r = get_level("Q6.4").check_fn(yaml)
        assert not r.ok and "resources" in r.error

    def test_only_requests(self):
        yaml = """
apiVersion: v1
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
          memory: 128Mi
"""
        r = get_level("Q6.4").check_fn(yaml)
        assert not r.ok and "limits" in r.error


# ===== Registration =====

class TestCh56Registration:
    def test_total_levels(self):
        assert len(list_levels()) == 140

    def test_ch05_exists(self):
        ch05 = [l for l in list_levels() if l["chapter"] == "ch05"]
        assert len(ch05) == 5

    def test_ch06_exists(self):
        ch06 = [l for l in list_levels() if l["chapter"] == "ch06"]
        assert len(ch06) == 5
