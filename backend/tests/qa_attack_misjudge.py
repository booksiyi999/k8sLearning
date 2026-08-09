"""QA 攻击测试：误判错答为通过（P2-1）。

针对产品体验报告 P2-1：3 关误判错答为通过（wrong_ok=3）。
测试目标：找到 check_fn 过宽的关卡，提交明显错误的 YAML 但被判 ok=True。
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestQ28KeywordBypass:
    """Q28.1 关键词绕过攻击 - 提交非命令文本但含关键词。"""

    def test_english_sentence_with_keywords(self):
        """英文句子含 kubectl/run/expose/scale 应被拒绝。"""
        r = client.post("/api/check", json={
            "level_id": "Q28.1",
            "user_yaml": "I want to kubectl run expose scale something"
        })
        assert r.status_code == 200
        assert r.json()["ok"] is False, "纯文本含关键词不应通过"

    def test_keywords_in_wrong_order(self):
        """关键词乱序排列应被拒绝。"""
        r = client.post("/api/check", json={
            "level_id": "Q28.1",
            "user_yaml": "scale expose run kubectl"
        })
        assert r.json()["ok"] is False, "关键词乱序不应通过"

    def test_keywords_without_actual_commands(self):
        """关键词作为注释应被拒绝。"""
        r = client.post("/api/check", json={
            "level_id": "Q28.1",
            "user_yaml": "# kubectl run\n# expose\n# scale\n# these are just comments"
        })
        assert r.json()["ok"] is False, "注释中的关键词不应通过"

    def test_partial_command_missing_image(self):
        """kubectl run 但缺少 --image 参数应被拒绝。"""
        r = client.post("/api/check", json={
            "level_id": "Q28.1",
            "user_yaml": "kubectl run nginx-app\nkubectl expose\nkubectl scale"
        })
        # 至少应有 --image 参数提示
        data = r.json()
        if data["ok"]:
            pytest.fail("Q28.1 接受了缺少 --image 的 kubectl run 命令")

    def test_completely_wrong_commands(self):
        """完全不相关的 kubectl 命令组合应被拒绝。"""
        r = client.post("/api/check", json={
            "level_id": "Q28.1",
            "user_yaml": "kubectl get pods\nkubectl run x\nkubectl expose y\nkubectl scale z"
        })
        data = r.json()
        # 这些命令没有实际参数，不应通过
        if data["ok"]:
            pytest.fail("Q28.1 接受了无参数的命令组合")


class TestQ251InitContainerMisjudge:
    """Q25.1 Init Container - 提交结构正确但内容完全错误的 Pod。"""

    WRONG_INIT_POD_NO_NAME_MATCH = """\
apiVersion: v1
kind: Pod
metadata:
  name: totally-wrong-name
spec:
  initContainers:
  - name: wrong-init
    image: ubuntu:latest
    command: ["echo", "wrong"]
  containers:
  - name: wrong-main
    image: redis:latest
"""

    WRONG_INIT_POD_MISSING_VOLUME = """\
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
spec:
  initContainers:
  - name: init-mysql
    image: busybox:1.36
    command: ["sh", "-c", "echo wrong"]
  containers:
  - name: web
    image: nginx:1.25
"""

    def test_wrong_pod_name_accepted_bug(self):
        """提交名称完全错误的 Pod - 当前可能误判为通过（BUG）。"""
        r = client.post("/api/check", json={
            "level_id": "Q25.1",
            "user_yaml": self.WRONG_INIT_POD_NO_NAME_MATCH
        })
        data = r.json()
        # 这是 BUG：check_fn 不验证 pod 名称
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.1 接受了名称为 'totally-wrong-name' 的 Pod，"
                "应为 'init-demo'"
            )

    def test_wrong_image_accepted_bug(self):
        """提交镜像完全错误的 Pod - 当前可能误判为通过（BUG）。"""
        r = client.post("/api/check", json={
            "level_id": "Q25.1",
            "user_yaml": self.WRONG_INIT_POD_NO_NAME_MATCH
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.1 接受了 init image=ubuntu:latest，"
                "应为 busybox:1.36"
            )

    def test_missing_volume_share_accepted_bug(self):
        """initContainer 和主容器没有共享卷 - 当前可能误判为通过（BUG）。"""
        r = client.post("/api/check", json={
            "level_id": "Q25.1",
            "user_yaml": self.WRONG_INIT_POD_MISSING_VOLUME
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.1 接受了没有共享卷的 Pod"
            )

    def test_garbage_init_command_accepted_bug(self):
        """initContainer 命令完全不符合要求 - 当前可能误判为通过。"""
        yaml_garbage = """\
apiVersion: v1
kind: Pod
metadata:
  name: init-demo
spec:
  initContainers:
  - name: init-mysql
    image: busybox:1.36
    command: ["sleep", "999999"]
  containers:
  - name: web
    image: nginx:1.25
"""
        r = client.post("/api/check", json={
            "level_id": "Q25.1",
            "user_yaml": yaml_garbage
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.1 接受了 init command=['sleep','999999']，"
                "应为写入 index.html 的命令"
            )


class TestQ252SidecarMisjudge:
    """Q25.2 Sidecar - 提交结构正确但内容错误的 Pod。"""

    WRONG_SIDECAR = """\
apiVersion: v1
kind: Pod
metadata:
  name: wrong-name
spec:
  containers:
  - name: main
    image: nginx:1.25
    volumeMounts:
    - name: shared
      mountPath: /data
  - name: helper
    image: alpine:latest
    volumeMounts:
    - name: shared
      mountPath: /data
  volumes:
  - name: shared
    emptyDir: {}
"""

    def test_wrong_pod_name_accepted_bug(self):
        """Pod名称为 'wrong-name' 而非 'sidecar-demo' - 当前可能误判为通过。"""
        r = client.post("/api/check", json={
            "level_id": "Q25.2",
            "user_yaml": self.WRONG_SIDECAR
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.2 接受了名称为 'wrong-name' 的 Pod，"
                "应为 'sidecar-demo'"
            )

    def test_wrong_container_names_accepted_bug(self):
        """容器名为 main/helper 而非 app/log-sync - 当前可能误判为通过。"""
        r = client.post("/api/check", json={
            "level_id": "Q25.2",
            "user_yaml": self.WRONG_SIDECAR
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.2 接受了容器名 main/helper，"
                "应为 app/log-sync"
            )

    def test_wrong_images_accepted_bug(self):
        """镜像为 alpine 而非 busybox - 当前可能误判为通过。"""
        r = client.post("/api/check", json={
            "level_id": "Q25.2",
            "user_yaml": self.WRONG_SIDECAR
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.2 接受了 sidecar image=alpine:latest"
            )

    def test_missing_sidecar_command_accepted_bug(self):
        """Sidecar容器缺少command - 当前可能误判为通过。"""
        yaml_no_cmd = """\
apiVersion: v1
kind: Pod
metadata:
  name: sidecar-demo
spec:
  containers:
  - name: app
    image: nginx:1.25
    volumeMounts:
    - name: shared
      mountPath: /usr/share/nginx/html
  - name: log-sync
    image: busybox:1.36
    volumeMounts:
    - name: shared
      mountPath: /var/log/app
  volumes:
  - name: shared
    emptyDir: {}
"""
        r = client.post("/api/check", json={
            "level_id": "Q25.2",
            "user_yaml": yaml_no_cmd
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                "P2-1 BUG: Q25.2 接受了没有 command 的 sidecar 容器"
            )


class TestQ28AllLevelsKeywordBypass:
    """Q28.2-Q28.5 所有关键词匹配型关卡的绕过测试。"""

    @pytest.mark.parametrize("level_id,text,description", [
        ("Q28.2", "kubectl describe logs", "缺少 pod 参数和 --previous"),
        ("Q28.3", "kubectl describe logs exec", "网络排查关键词拼凑"),
        ("Q28.4", "kubectl describe auth", "RBAC排查关键词拼凑"),
        ("Q28.5", "kubectl get create delete apply", "综合关键词拼凑"),
    ])
    def test_keyword_bypass(self, level_id, text, description):
        """所有 ch28 关卡都不应接受关键词拼凑。"""
        r = client.post("/api/check", json={
            "level_id": level_id,
            "user_yaml": text
        })
        data = r.json()
        if data["ok"]:
            pytest.fail(
                f"P2-1 BUG: {level_id} 接受了关键词拼凑: {description}"
            )
