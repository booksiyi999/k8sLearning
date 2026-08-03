"""Chapter 7 (Job/CronJob) & Chapter 8 (StatefulSet) 测试"""
import pytest
from app.simulator import ClusterState, apply_manifest, preset_state, K8sError
from app.validator import get_level, list_levels


# ===== Chapter 7: Job / CronJob =====

class TestQ71CreateJob:
    """Q7.1 创建第一个 Job"""

    def test_correct(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.38
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
"""
        r = get_level("Q7.1").check_fn(yaml)
        assert r.ok, r.error

    def test_creates_pod(self):
        """Job 创建后 pods 中有对应 Pod"""
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.38
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
"""
        r = get_level("Q7.1").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        assert "pi-pod" in r.state.pods

    def test_empty_yaml(self):
        r = get_level("Q7.1").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: pi
spec:
  containers:
  - name: pi
    image: perl:5.38
    command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
"""
        r = get_level("Q7.1").check_fn(yaml)
        assert not r.ok
        assert "Job" in r.error

    def test_missing_command(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  template:
    spec:
      containers:
      - name: pi
        image: perl:5.38
      restartPolicy: Never
"""
        r = get_level("Q7.1").check_fn(yaml)
        assert not r.ok
        assert "command" in r.error

    def test_missing_template(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: pi
spec:
  backoffLimit: 4
"""
        r = get_level("Q7.1").check_fn(yaml)
        assert not r.ok


class TestQ72ParallelJob:
    """Q7.2 Job 并行执行"""

    def test_correct(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  parallelism: 3
  completions: 6
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.36
        command: ["echo", "hello"]
      restartPolicy: Never
"""
        r = get_level("Q7.2").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_parallelism(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  parallelism: 2
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.36
        command: ["echo", "hello"]
      restartPolicy: Never
"""
        r = get_level("Q7.2").check_fn(yaml)
        assert not r.ok
        assert "3" in r.error

    def test_missing_parallelism(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: parallel-job
spec:
  completions: 6
  template:
    spec:
      containers:
      - name: worker
        image: busybox:1.36
        command: ["echo", "hello"]
      restartPolicy: Never
"""
        r = get_level("Q7.2").check_fn(yaml)
        assert not r.ok
        assert "parallelism" in r.error

    def test_empty_yaml(self):
        r = get_level("Q7.2").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: parallel-job
spec:
  containers:
  - name: worker
    image: busybox:1.36
"""
        r = get_level("Q7.2").check_fn(yaml)
        assert not r.ok


class TestQ73CreateCronJob:
    """Q7.3 创建 CronJob"""

    def test_correct(self):
        yaml = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello-cron
spec:
  schedule: "*/1 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.36
            command: ["echo", "hello from cron"]
          restartPolicy: Never
"""
        r = get_level("Q7.3").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_schedule(self):
        yaml = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello-cron
spec:
  schedule: "0 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.36
            command: ["echo", "hello"]
          restartPolicy: Never
"""
        r = get_level("Q7.3").check_fn(yaml)
        assert not r.ok
        assert "*/1 * * * *" in r.error

    def test_missing_schedule(self):
        yaml = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hello-cron
spec:
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: hello
            image: busybox:1.36
            command: ["echo", "hello"]
          restartPolicy: Never
"""
        r = get_level("Q7.3").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q7.3").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: hello-cron
spec:
  template:
    spec:
      containers:
      - name: hello
        image: busybox:1.36
        command: ["echo", "hello"]
      restartPolicy: Never
"""
        r = get_level("Q7.3").check_fn(yaml)
        assert not r.ok


class TestQ74ConcurrencyPolicy:
    """Q7.4 CronJob 并发策略"""

    def test_correct(self):
        yaml = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: forbid-cron
spec:
  schedule: "*/1 * * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: task
            image: busybox:1.36
            command: ["sleep", "30"]
          restartPolicy: Never
"""
        r = get_level("Q7.4").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_policy(self):
        yaml = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: forbid-cron
spec:
  schedule: "*/1 * * * *"
  concurrencyPolicy: Allow
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: task
            image: busybox:1.36
            command: ["sleep", "30"]
          restartPolicy: Never
"""
        r = get_level("Q7.4").check_fn(yaml)
        assert not r.ok
        assert "Forbid" in r.error

    def test_missing_policy(self):
        yaml = """
apiVersion: batch/v1
kind: CronJob
metadata:
  name: forbid-cron
spec:
  schedule: "*/1 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: task
            image: busybox:1.36
            command: ["sleep", "30"]
          restartPolicy: Never
"""
        r = get_level("Q7.4").check_fn(yaml)
        assert not r.ok
        assert "concurrencyPolicy" in r.error

    def test_empty_yaml(self):
        r = get_level("Q7.4").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: forbid-cron
spec:
  containers:
  - name: task
    image: busybox:1.36
"""
        r = get_level("Q7.4").check_fn(yaml)
        assert not r.ok


class TestQ75DeployJob:
    """Q7.5 集群实战 - 部署 Job"""

    def test_correct(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: compute-job
spec:
  template:
    spec:
      containers:
      - name: compute
        image: perl:5.38
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Never
"""
        r = get_level("Q7.5").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_restart_policy(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: compute-job
spec:
  template:
    spec:
      containers:
      - name: compute
        image: perl:5.38
        command: ["perl", "-Mbignum=bpi", "-wle", "print bpi(2000)"]
      restartPolicy: Always
"""
        r = get_level("Q7.5").check_fn(yaml)
        assert not r.ok
        assert "restartPolicy" in r.error

    def test_missing_image(self):
        yaml = """
apiVersion: batch/v1
kind: Job
metadata:
  name: compute-job
spec:
  template:
    spec:
      containers:
      - name: compute
        command: ["echo", "hello"]
      restartPolicy: Never
"""
        r = get_level("Q7.5").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q7.5").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: v1
kind: Pod
metadata:
  name: compute-job
spec:
  containers:
  - name: compute
    image: perl:5.38
"""
        r = get_level("Q7.5").check_fn(yaml)
        assert not r.ok


# ===== Chapter 8: StatefulSet =====

class TestQ81CreateStatefulSet:
    """Q8.1 创建 StatefulSet"""

    def test_correct(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
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
        r = get_level("Q8.1").check_fn(yaml)
        assert r.ok, r.error

    def test_pods_count(self):
        """StatefulSet 创建后 pods 数量正确"""
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
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
        r = get_level("Q8.1").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        # 验证有序 Pod 存在
        assert "web-0" in r.state.pods
        assert "web-1" in r.state.pods
        assert "web-2" in r.state.pods
        assert len([p for p in r.state.pods if p.startswith("web-")]) == 3

    def test_wrong_replicas(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
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
        image: nginx:1.25
"""
        r = get_level("Q8.1").check_fn(yaml)
        assert not r.ok
        assert "3" in r.error

    def test_missing_service_name(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
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
        # 模拟器会拒绝没有 serviceName 的 StatefulSet
        r = get_level("Q8.1").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q8.1").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
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
        r = get_level("Q8.1").check_fn(yaml)
        assert not r.ok


class TestQ82ScaleStatefulSet:
    """Q8.2 StatefulSet 扩缩容"""

    def test_correct(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
  replicas: 5
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
        r = get_level("Q8.2").check_fn(yaml)
        assert r.ok, r.error

    def test_pods_count_after_scale(self):
        """扩容后 pods 数量正确"""
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
  replicas: 5
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
        r = get_level("Q8.2").check_fn(yaml)
        assert r.ok, r.error
        assert r.state is not None
        sts_pods = [p for p in r.state.pods if p.startswith("web-")]
        assert len(sts_pods) == 5

    def test_not_scaled(self):
        """replicas 仍为 3，未扩容"""
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: web
spec:
  serviceName: web
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
        r = get_level("Q8.2").check_fn(yaml)
        assert not r.ok
        assert "5" in r.error

    def test_empty_yaml(self):
        r = get_level("Q8.2").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 5
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
        r = get_level("Q8.2").check_fn(yaml)
        assert not r.ok


class TestQ83HeadlessService:
    """Q8.3 Headless Service + StatefulSet"""

    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None
  selector:
    app: nginx
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx
spec:
  serviceName: nginx
  replicas: 3
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
        r = get_level("Q8.3").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_headless_service(self):
        """没有 Headless Service（clusterIP 不为 None）"""
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  selector:
    app: nginx
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx
spec:
  serviceName: nginx
  replicas: 3
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
        r = get_level("Q8.3").check_fn(yaml)
        assert not r.ok
        assert "Headless" in r.error or "None" in r.error

    def test_missing_statefulset(self):
        """只有 Headless Service 没有 StatefulSet"""
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx
spec:
  clusterIP: None
  selector:
    app: nginx
  ports:
  - port: 80
"""
        r = get_level("Q8.3").check_fn(yaml)
        assert not r.ok
        assert "StatefulSet" in r.error

    def test_service_name_mismatch(self):
        """serviceName 与 Headless Service 名称不匹配"""
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: nginx-svc
spec:
  clusterIP: None
  selector:
    app: nginx
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: nginx
spec:
  serviceName: wrong-name
  replicas: 3
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
        r = get_level("Q8.3").check_fn(yaml)
        assert not r.ok

    def test_empty_yaml(self):
        r = get_level("Q8.3").check_fn("")
        assert not r.ok


class TestQ84PersistentStorage:
    """Q8.4 StatefulSet 持久化"""

    def test_correct(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: data-app
spec:
  serviceName: data-app
  replicas: 3
  selector:
    matchLabels:
      app: data-app
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ReadWriteOnce]
      resources:
        requests:
          storage: 1Gi
  template:
    metadata:
      labels:
        app: data-app
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
        volumeMounts:
        - name: data
          mountPath: /data
"""
        r = get_level("Q8.4").check_fn(yaml)
        assert r.ok, r.error

    def test_missing_volume_claim_templates(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: data-app
spec:
  serviceName: data-app
  replicas: 3
  selector:
    matchLabels:
      app: data-app
  template:
    metadata:
      labels:
        app: data-app
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
"""
        r = get_level("Q8.4").check_fn(yaml)
        assert not r.ok
        assert "volumeClaimTemplates" in r.error

    def test_missing_storage_request(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: data-app
spec:
  serviceName: data-app
  replicas: 3
  selector:
    matchLabels:
      app: data-app
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: [ReadWriteOnce]
  template:
    metadata:
      labels:
        app: data-app
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
"""
        r = get_level("Q8.4").check_fn(yaml)
        assert not r.ok
        assert "storage" in r.error

    def test_missing_access_modes(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: data-app
spec:
  serviceName: data-app
  replicas: 3
  selector:
    matchLabels:
      app: data-app
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      resources:
        requests:
          storage: 1Gi
  template:
    metadata:
      labels:
        app: data-app
    spec:
      containers:
      - name: app
        image: busybox:1.36
        command: ["sleep", "3600"]
"""
        r = get_level("Q8.4").check_fn(yaml)
        assert not r.ok
        assert "accessModes" in r.error

    def test_empty_yaml(self):
        r = get_level("Q8.4").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-app
  template:
    metadata:
      labels:
        app: data-app
    spec:
      containers:
      - name: app
        image: busybox:1.36
"""
        r = get_level("Q8.4").check_fn(yaml)
        assert not r.ok


class TestQ85DeployMySQL:
    """Q8.5 集群实战 - 部署 MySQL StatefulSet"""

    def test_correct(self):
        yaml = """
apiVersion: v1
kind: Service
metadata:
  name: mysql
spec:
  clusterIP: None
  selector:
    app: mysql
  ports:
  - port: 3306
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "password123"
        ports:
        - containerPort: 3306
"""
        r = get_level("Q8.5").check_fn(yaml)
        assert r.ok, r.error

    def test_wrong_image(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: nginx:1.25
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "password123"
"""
        r = get_level("Q8.5").check_fn(yaml)
        assert not r.ok
        assert "mysql" in r.error.lower()

    def test_missing_image(self):
        yaml = """
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
spec:
  serviceName: mysql
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        env:
        - name: MYSQL_ROOT_PASSWORD
          value: "password123"
"""
        r = get_level("Q8.5").check_fn(yaml)
        assert not r.ok
        assert "image" in r.error

    def test_empty_yaml(self):
        r = get_level("Q8.5").check_fn("")
        assert not r.ok

    def test_wrong_kind(self):
        yaml = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mysql
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
"""
        r = get_level("Q8.5").check_fn(yaml)
        assert not r.ok


# ===== Level Registration =====

class TestLevelRegistration:
    """验证关卡注册正确"""

    def test_all_ch07_levels_registered(self):
        levels = list_levels("ch07")
        ids = [lv["id"] for lv in levels]
        assert "Q7.1" in ids
        assert "Q7.2" in ids
        assert "Q7.3" in ids
        assert "Q7.4" in ids
        assert "Q7.5" in ids
        assert len(levels) == 5

    def test_all_ch08_levels_registered(self):
        levels = list_levels("ch08")
        ids = [lv["id"] for lv in levels]
        assert "Q8.1" in ids
        assert "Q8.2" in ids
        assert "Q8.3" in ids
        assert "Q8.4" in ids
        assert "Q8.5" in ids
        assert len(levels) == 5

    def test_get_level_returns_lesson(self):
        for level_id in ["Q7.1", "Q7.2", "Q7.3", "Q7.4", "Q7.5",
                         "Q8.1", "Q8.2", "Q8.3", "Q8.4", "Q8.5"]:
            lv = get_level(level_id)
            assert lv is not None, f"{level_id} not found"
            assert lv.lesson is not None, f"{level_id} missing lesson"
            assert lv.lesson.concept, f"{level_id} lesson.concept is empty"
            assert lv.lesson.key_fields, f"{level_id} lesson.key_fields is empty"
            assert lv.lesson.diagram, f"{level_id} lesson.diagram is empty"
            assert lv.lesson.example_yaml, f"{level_id} lesson.example_yaml is empty"
            assert lv.lesson.common_errors, f"{level_id} lesson.common_errors is empty"
            assert lv.lesson.tips, f"{level_id} lesson.tips is empty"
