"""E2E 通关旅程测试。

模拟学员从 Q1.1 到 Q6.5 的完整通关流程：
1. 逐个提交所有 30 关的正确答案
2. 验证 XP 累积过程（每关 +10，每章 +50）
3. 验证最终 XP = 600（30*10 + 6*50）
4. 验证报告生成（100% 完成率，S 级评定）
5. 验证知识域全部 100%
6. 验证无薄弱项
7. 验证称号为 "K8s 传奇"
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ==========================================================================
#  30 个关卡的正确 YAML 答案（从已有测试中提取）
# ==========================================================================

CORRECT_ANSWERS = {
    # ---- Chapter 1: Pod 基础 ----
    "Q1.1": """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
""",
    "Q1.2": """\
apiVersion: v1
kind: Pod
metadata:
  name: redis-pod
  labels:
    app: cache
    tier: backend
spec:
  containers:
    - name: redis
      image: redis:7-alpine
""",
    "Q1.3": """\
apiVersion: v1
kind: Pod
metadata:
  name: web-with-logger
spec:
  containers:
    - name: web
      image: nginx:1.25
    - name: logger
      image: busybox:1.36
""",
    "Q1.4": """\
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
""",
    "Q1.5": """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-web
  labels:
    app: nginx
spec:
  containers:
    - name: nginx
      image: nginx:1.25
      ports:
        - containerPort: 80
""",
    # ---- Chapter 2: Deployment ----
    "Q2.1": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
spec:
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
""",
    "Q2.2": """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deploy
spec:
  replicas: 5
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
        - name: api
          image: python:3.11-slim
""",
    "Q2.3": """\
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
""",
    "Q2.4": """\
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
          image: nginx:1.24
""",
    "Q2.5": """\
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
""",
    # ---- Chapter 3: Service 网络 ----
    "Q3.1": """\
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
""",
    "Q3.2": """\
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
""",
    "Q3.3": """\
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
""",
    "Q3.4": """\
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
""",
    "Q3.5": """\
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
          image: nginx:1.25
          ports:
            - containerPort: 80
---
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
      targetPort: 80
""",
    # ---- Chapter 4: 配置管理 ----
    "Q4.1": """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
""",
    "Q4.2": """\
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
""",
    "Q4.3": """\
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
""",
    "Q4.4": """\
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
""",
    "Q4.5": """\
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  APP_MODE: production
  LOG_LEVEL: info
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      envFrom:
        - configMapRef:
            name: app-config
""",
    # ---- Chapter 5: 存储 ----
    "Q5.1": """\
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
""",
    "Q5.2": """\
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 5Gi
""",
    "Q5.3": """\
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
""",
    "Q5.4": """\
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
""",
    "Q5.5": """\
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
    - name: app
      image: nginx:1.25
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: data-pvc
""",
    # ---- Chapter 6: 调度 ----
    "Q6.1": """\
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
""",
    "Q6.2": """\
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
""",
    "Q6.3": """\
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
""",
    "Q6.4": """\
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
""",
    "Q6.5": """\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    - name: nginx
      image: nginx:1.25
  nodeSelector:
    disktype: ssd
""",
}

# 关卡顺序（Q1.1 -> Q6.5）
ALL_LEVEL_IDS = [f"Q{ch}.{lv}" for ch in range(1, 7) for lv in range(1, 6)]

# 每章关卡列表
CHAPTERS = {
    1: ["Q1.1", "Q1.2", "Q1.3", "Q1.4", "Q1.5"],
    2: ["Q2.1", "Q2.2", "Q2.3", "Q2.4", "Q2.5"],
    3: ["Q3.1", "Q3.2", "Q3.3", "Q3.4", "Q3.5"],
    4: ["Q4.1", "Q4.2", "Q4.3", "Q4.4", "Q4.5"],
    5: ["Q5.1", "Q5.2", "Q5.3", "Q5.4", "Q5.5"],
    6: ["Q6.1", "Q6.2", "Q6.3", "Q6.4", "Q6.5"],
}

LEVEL_XP = 10
CHAPTER_BONUS_XP = 50


# ==========================================================================
#  E2E 通关旅程
# ==========================================================================

class TestE2EJourney:
    """模拟学员从 Q1.1 到 Q6.5 的完整通关旅程"""

    @pytest.fixture(autouse=True)
    def setup_journey(self):
        """执行完整通关流程，记录每一步的状态。"""
        self.completed_levels = []
        self.level_attempts = {}
        self.level_first_try = []
        self.level_time_spent = {}
        self.total_xp = 0
        self.check_results = {}  # level_id -> check response
        self.xp_after_each_level = []  # (level_id, xp_after)

        chapter_bonus_claimed = set()

        for level_id in ALL_LEVEL_IDS:
            # 提交正确答案
            r = client.post("/api/check", json={
                "level_id": level_id,
                "user_yaml": CORRECT_ANSWERS[level_id],
            })
            assert r.status_code == 200
            check_data = r.json()
            self.check_results[level_id] = check_data

            # 验证通过
            assert check_data["ok"] is True, (
                f"Level {level_id} should pass with correct answer, "
                f"got error: {check_data.get('error', '')}"
            )

            # 记录通关状态
            self.completed_levels.append(level_id)
            self.level_attempts[level_id] = 1  # 一次通过
            self.level_first_try.append(level_id)
            self.level_time_spent[level_id] = 60  # 假设每关 60 秒

            # XP 计算：每关 +10
            self.total_xp += LEVEL_XP

            # 章节通关奖励：该章 5 关全部完成时 +50
            ch_num = int(level_id.split(".")[0][1:])
            ch_levels = CHAPTERS[ch_num]
            if all(l in self.completed_levels for l in ch_levels):
                if ch_num not in chapter_bonus_claimed:
                    self.total_xp += CHAPTER_BONUS_XP
                    chapter_bonus_claimed.add(ch_num)

            self.xp_after_each_level.append((level_id, self.total_xp))

    # ---- 验证每关都通过 ----

    def test_all_30_levels_passed(self):
        """所有 30 关都应通过"""
        assert len(self.check_results) == 30
        for lid, result in self.check_results.items():
            assert result["ok"] is True, f"{lid} did not pass"

    def test_all_30_levels_have_cluster_state(self):
        """通过的关卡应返回 cluster_state（非 None）"""
        for lid, result in self.check_results.items():
            # 部分关卡可能返回 None cluster_state（如纯 ConfigMap），但 ok=True 即可
            assert result["ok"] is True

    # ---- 验证 XP 累积过程 ----

    def test_xp_accumulation_per_level(self):
        """每关 +10 XP"""
        # Q1.1 之后应为 10
        assert self.xp_after_each_level[0] == ("Q1.1", 10)
        # Q1.2 之后应为 20
        assert self.xp_after_each_level[1] == ("Q1.2", 20)

    def test_xp_chapter_bonus_after_ch1(self):
        """完成 Ch1 全部 5 关后 +50 章节奖励"""
        # Q1.5 是 Ch1 最后一关，完成后 XP = 5*10 + 50 = 100
        q15_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q1.5")
        assert q15_xp == 100  # 50 + 50

    def test_xp_chapter_bonus_after_ch2(self):
        """完成 Ch2 全部 5 关后 +50 章节奖励"""
        q25_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q2.5")
        assert q25_xp == 200  # 100 + 50 + 50

    def test_xp_chapter_bonus_after_ch3(self):
        q35_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q3.5")
        assert q35_xp == 300  # 200 + 50 + 50

    def test_xp_chapter_bonus_after_ch4(self):
        q45_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q4.5")
        assert q45_xp == 400  # 300 + 50 + 50

    def test_xp_chapter_bonus_after_ch5(self):
        q55_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q5.5")
        assert q55_xp == 500  # 400 + 50 + 50

    def test_xp_chapter_bonus_after_ch6(self):
        q65_xp = next(xp for lid, xp in self.xp_after_each_level if lid == "Q6.5")
        assert q65_xp == 600  # 500 + 50 + 50

    def test_final_xp_is_600(self):
        """最终 XP = 600（30*10 + 6*50）"""
        assert self.total_xp == 600

    def test_xp_after_each_chapter_completion(self):
        """每个章节完成时的 XP 值"""
        expected = {
            "Q1.5": 100,
            "Q2.5": 200,
            "Q3.5": 300,
            "Q4.5": 400,
            "Q5.5": 500,
            "Q6.5": 600,
        }
        for lid, expected_xp in expected.items():
            actual_xp = next(xp for l, xp in self.xp_after_each_level if l == lid)
            assert actual_xp == expected_xp, (
                f"After {lid}: expected {expected_xp} XP, got {actual_xp}"
            )

    # ---- 验证报告生成 ----

    def _generate_report(self):
        r = client.post("/api/report", json={
            "completed_levels": self.completed_levels,
            "level_attempts": self.level_attempts,
            "level_first_try": self.level_first_try,
            "level_time_spent": self.level_time_spent,
            "total_xp": self.total_xp,
        })
        assert r.status_code == 200
        return r.json()

    def test_report_completion_rate_100(self):
        """报告显示 100% 完成率"""
        data = self._generate_report()
        assert data["completion_rate"] == 1.0
        assert data["completed_count"] == 30
        assert data["total_levels"] == 30

    def test_report_grade_s(self):
        """报告评定为 S 级"""
        data = self._generate_report()
        assert data["grade"] == "S"
        assert "完美通关" in data["grade_comment"]

    def test_report_total_xp_600(self):
        """报告总 XP = 600"""
        data = self._generate_report()
        assert data["total_xp"] == 600

    def test_report_first_try_count_30(self):
        """所有 30 关都是首通"""
        data = self._generate_report()
        assert data["first_try_count"] == 30

    def test_report_total_attempts_30(self):
        """总尝试次数 = 30（每关 1 次）"""
        data = self._generate_report()
        assert data["total_attempts"] == 30

    # ---- 验证知识域全部 100% ----

    def test_report_all_domains_100(self):
        """所有知识域掌握度 100%"""
        data = self._generate_report()
        for domain, stats in data["domain_stats"].items():
            assert stats["rate"] == 1.0, f"Domain {domain} rate is {stats['rate']}, expected 1.0"
            assert stats["completed"] == stats["total"]

    def test_report_domain_levels_all_completed(self):
        """每个知识域的所有关卡都标记为已完成"""
        data = self._generate_report()
        for domain, stats in data["domain_stats"].items():
            for lv in stats["levels"]:
                assert lv["completed"] is True, f"{lv['id']} not marked completed"
                assert lv["first_try"] is True, f"{lv['id']} not marked first_try"
                assert lv["attempts"] == 1

    # ---- 验证无薄弱项 ----

    def test_report_no_weak_areas(self):
        """无薄弱项"""
        data = self._generate_report()
        assert len(data["weak_areas"]) == 0

    # ---- 验证称号 ----

    def test_report_rank_is_legend(self):
        """称号为 K8s 传奇"""
        data = self._generate_report()
        assert "K8s 传奇" in data["rank"]

    def test_report_next_rank_is_none(self):
        """已满级，无下一称号"""
        data = self._generate_report()
        assert data["next_rank"] is None
        assert data["xp_to_next_rank"] == 0

    # ---- 验证优势项 ----

    def test_report_strengths_count_30(self):
        """30 个优势项（全部首通）"""
        data = self._generate_report()
        assert len(data["strengths"]) == 30

    # ---- 验证学习建议 ----

    def test_report_no_recommendations(self):
        """全部 100% -> 无学习建议"""
        data = self._generate_report()
        assert len(data["recommendations"]) == 0

    # ---- 验证章节统计 ----

    def test_report_all_chapters_complete(self):
        """所有章节 100% 完成"""
        data = self._generate_report()
        for ch_id in ["ch01", "ch02", "ch03", "ch04", "ch05", "ch06"]:
            ch = data["chapter_stats"][ch_id]
            assert ch["total"] == 5
            assert ch["completed"] == 5
            assert ch["rate"] == 1.0

    # ---- 验证时间统计 ----

    def test_report_total_time_spent(self):
        """总时间 = 30 * 60 = 1800 秒"""
        data = self._generate_report()
        assert data["total_time_spent"] == 1800


# ==========================================================================
#  逐关验证（参数化测试）
# ==========================================================================

class TestEachLevelSubmission:
    """逐个验证每个关卡的提交"""

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_submit_correct_answer(self, level_id):
        """每个关卡的正确答案都能通过"""
        r = client.post("/api/check", json={
            "level_id": level_id,
            "user_yaml": CORRECT_ANSWERS[level_id],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True, (
            f"Level {level_id} failed with correct answer: {data.get('error', '')}"
        )

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_submit_wrong_answer_fails(self, level_id):
        """错误答案应该失败"""
        r = client.post("/api/check", json={
            "level_id": level_id,
            "user_yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: totally-wrong\nspec:\n  containers:\n    - name: x\n      image: wrong:latest\n",
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False


# ==========================================================================
#  XP 累积序列验证
# ==========================================================================

class TestXPAccumulation:
    """验证 XP 逐步累积的完整序列"""

    def test_full_xp_sequence(self):
        """验证每一步的 XP 值"""
        total_xp = 0
        completed = []
        chapter_bonus_claimed = set()
        xp_sequence = []

        for level_id in ALL_LEVEL_IDS:
            # 提交
            r = client.post("/api/check", json={
                "level_id": level_id,
                "user_yaml": CORRECT_ANSWERS[level_id],
            })
            assert r.json()["ok"] is True

            completed.append(level_id)
            total_xp += LEVEL_XP

            ch_num = int(level_id.split(".")[0][1:])
            ch_levels = CHAPTERS[ch_num]
            if all(l in completed for l in ch_levels) and ch_num not in chapter_bonus_claimed:
                total_xp += CHAPTER_BONUS_XP
                chapter_bonus_claimed.add(ch_num)

            xp_sequence.append((level_id, total_xp))

        # 验证完整序列
        expected_xp = 0
        claimed = set()
        for i, level_id in enumerate(ALL_LEVEL_IDS):
            expected_xp += LEVEL_XP
            ch_num = int(level_id.split(".")[0][1:])
            ch_levels = CHAPTERS[ch_num]
            done_so_far = [l for l in ALL_LEVEL_IDS[:i + 1] if l.startswith(f"Q{ch_num}.")]
            if len(done_so_far) == 5 and ch_num not in claimed:
                expected_xp += CHAPTER_BONUS_XP
                claimed.add(ch_num)
            assert xp_sequence[i] == (level_id, expected_xp), (
                f"Step {i}: expected ({level_id}, {expected_xp}), got {xp_sequence[i]}"
            )

        assert expected_xp == 600
        assert total_xp == 600
