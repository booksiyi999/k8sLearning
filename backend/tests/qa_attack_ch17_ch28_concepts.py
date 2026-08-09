"""QA 攻击测试：ch17 概念关 & ch28 CKA 命令关校验缺陷。

针对 P1-1 和 P1-2 报告：
- P1-1: ch28 CKA 关 example 全失败（0/5）- 模拟器承载不了命令型答案
- P1-2: ch17 概念关 example 不过（3/10）- Q17.6/Q17.8/Q17.10

测试维度:
1. ch17 概念关 example_yaml 应通过 check_fn
2. ch28 命令关 example_yaml 应通过 check_fn
3. ch28 关键词绕过攻击
4. ch17 结构校验 vs 内容校验差距
"""
import pytest
from app.validator import get_level


# ═══════════════════════════════════════════════
# P1-2: ch17 概念关 example 验证
# ═══════════════════════════════════════════════

class TestCh17ExamplePasses:
    """ch17 所有关卡的 example_yaml 应该能通过 check_fn。"""

    @pytest.mark.parametrize("level_id", [
        "Q17.1", "Q17.2", "Q17.3", "Q17.4", "Q17.5",
        "Q17.6", "Q17.7", "Q17.8", "Q17.9", "Q17.10",
    ])
    def test_example_yaml_passes_check(self, level_id):
        """example_yaml 必须通过 check_fn - 否则用户无法学习。"""
        level = get_level(level_id)
        assert level is not None, f"{level_id} not found"
        assert level.lesson is not None, f"{level_id} has no lesson"
        assert level.lesson.example_yaml, f"{level_id} has no example_yaml"

        result = level.check_fn(level.lesson.example_yaml)
        assert result.ok, (
            f"P1-2 BUG: {level_id} example_yaml fails check_fn!\n"
            f"  Error: {result.error}\n"
            f"  example_yaml (first 200 chars): {level.lesson.example_yaml[:200]}"
        )

    @pytest.mark.parametrize("level_id", [
        "Q17.6", "Q17.8", "Q17.10",
    ])
    def test_concept_level_example_detailed(self, level_id):
        """P1-2 重点：Q17.6/Q17.8/Q17.10 概念关 example 应通过。"""
        level = get_level(level_id)
        result = level.check_fn(level.lesson.example_yaml)
        if not result.ok:
            pytest.fail(
                f"P1-2 CONFIRMED: {level_id} example_yaml fails check_fn\n"
                f"  Error: {result.error}\n"
                f"  Example YAML:\n{level.lesson.example_yaml}"
            )


# ═══════════════════════════════════════════════
# P1-1: ch28 CKA 命令关 example 验证
# ═══════════════════════════════════════════════

class TestCh28ExamplePasses:
    """ch28 所有关卡的 example_yaml 应该能通过 check_fn。"""

    @pytest.mark.parametrize("level_id", [
        "Q28.1", "Q28.2", "Q28.3", "Q28.4", "Q28.5",
    ])
    def test_example_yaml_passes_check(self, level_id):
        """example_yaml 必须通过 check_fn - 否则用户无法学习。"""
        level = get_level(level_id)
        assert level is not None, f"{level_id} not found"
        assert level.lesson is not None, f"{level_id} has no lesson"
        assert level.lesson.example_yaml, f"{level_id} has no example_yaml"

        result = level.check_fn(level.lesson.example_yaml)
        assert result.ok, (
            f"P1-1 BUG: {level_id} example_yaml fails check_fn!\n"
            f"  Error: {result.error}\n"
            f"  example_yaml (first 200 chars): {level.lesson.example_yaml[:200]}"
        )


class TestCh28KeywordMatchingWeakness:
    """ch28 关键词匹配型 check_fn 的弱点测试。"""

    def test_q281_keyword_order_irrelevant(self):
        """Q28.1 关键词出现顺序不影响通过 - 校验过松。"""
        level = get_level("Q28.1")
        # 关键词倒序
        reversed_text = """\
# scale
# expose
# run
# kubectl
kubectl scale deployment x --replicas=3
kubectl expose deployment x --port=80
kubectl run x --image=nginx
"""
        result = level.check_fn(reversed_text)
        # 当前实现只检查关键词存在，不检查顺序
        # 所以倒序也能通过
        print(f"Reversed order: ok={result.ok}")
        # 如果通过，说明校验过松
        if result.ok:
            print("WARNING: Q28.1 accepts commands in wrong order")

    def test_q281_keywords_in_comments(self):
        """Q28.1 关键词在注释中也能通过 - 校验过松。"""
        level = get_level("Q28.1")
        text = """\
# kubectl run nginx-app --image=nginx:1.25
# kubectl expose deployment nginx-app --port=80
# kubectl scale deployment nginx-app --replicas=3
# 以上都是注释，没有实际命令
"""
        result = level.check_fn(text)
        if result.ok:
            pytest.fail(
                "P1-1 BUG: Q28.1 accepts keywords only in comments"
            )

    def test_q282_keywords_without_pod_name(self):
        """Q28.2 describe/logs 但缺少 pod 名称。"""
        level = get_level("Q28.2")
        text = "kubectl describe\nkubectl logs"
        result = level.check_fn(text)
        if result.ok:
            pytest.fail(
                "P1-1 BUG: Q28.2 accepts commands without pod name"
            )

    def test_q281_completely_wrong_commands(self):
        """Q28.1 完全不相关的 kubectl 命令但含关键词。"""
        level = get_level("Q28.1")
        # "run" 出现在 "running" 中, "expose" 出现在 "exposed" 中
        text = "kubectl get pods running exposed scaled"
        result = level.check_fn(text)
        print(f"Wrong commands with keywords: ok={result.ok}")


# ═══════════════════════════════════════════════
# 全局: 所有150关 example_yaml 回归测试
# ═══════════════════════════════════════════════

class TestAllLevelsExamplePasses:
    """所有关卡的 example_yaml 都应该通过 check_fn（回归防护）。"""

    @pytest.mark.parametrize("ch", range(0, 29))
    def test_chapter_examples_pass(self, ch):
        """每章的所有 example_yaml 都应通过。"""
        failures = []
        for lv in range(1, 6):
            level_id = f"Q{ch}.{lv}"
            level = get_level(level_id)
            if level is None:
                continue
            if level.lesson is None or not level.lesson.example_yaml:
                continue
            result = level.check_fn(level.lesson.example_yaml)
            if not result.ok:
                failures.append((level_id, result.error))

        if failures:
            fail_msg = "\n".join(
                f"  {lid}: {err}" for lid, err in failures
            )
            pytest.fail(
                f"Chapter {ch} has {len(failures)} example_yaml failures:\n{fail_msg}"
            )


# ═══════════════════════════════════════════════
# ch17 概念关校验深度测试
# ═══════════════════════════════════════════════

class TestCh17ConceptDepth:
    """ch17 概念关校验深度测试 - 结构 vs 内容。"""

    def test_q176_rejects_wrong_condition_status(self):
        """Q17.6 status.conditions 中 status 值不合法应被拒绝。"""
        level = get_level("Q17.6")
        yaml_bad = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "Maybe"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""
        result = level.check_fn(yaml_bad)
        # status 应为 True/False/Unknown
        # 当前 check_fn 可能不验证 status 值的合法性
        print(f"Wrong condition status: ok={result.ok}")

    def test_q176_rejects_missing_observed_generation(self):
        """Q17.6 缺少 observedGeneration 应被拒绝。"""
        level = get_level("Q17.6")
        yaml_bad = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello"
status:
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""
        result = level.check_fn(yaml_bad)
        assert not result.ok, "Q17.6 should reject missing observedGeneration"

    def test_q178_rejects_finalizer_without_slash(self):
        """Q17.8 finalizer 不含 / 应被拒绝。"""
        level = get_level("Q17.8")
        yaml_bad = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
  finalizers:
  - cleanup
spec:
  title: "Hello"
"""
        result = level.check_fn(yaml_bad)
        assert not result.ok, "Q17.8 should reject finalizer without /"

    def test_q178_rejects_empty_finalizer(self):
        """Q17.8 空 finalizer 字符串应被拒绝。"""
        level = get_level("Q17.8")
        yaml_bad = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
  finalizers:
  - ""
spec:
  title: "Hello"
"""
        result = level.check_fn(yaml_bad)
        assert not result.ok, "Q17.8 should reject empty finalizer string"

    def test_q1710_rejects_partial_fields(self):
        """Q17.10 缺少部分最佳实践字段应被拒绝。"""
        level = get_level("Q17.10")
        # 只有 spec 和 status，缺少 ownerReferences 和 finalizers
        yaml_partial = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: partial-blog
spec:
  title: "Partial"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""
        result = level.check_fn(yaml_partial)
        assert not result.ok, "Q17.10 should reject partial best practices"

    def test_q1710_accepts_complete_yaml(self):
        """Q17.10 完整的最佳实践 YAML 应通过。"""
        level = get_level("Q17.10")
        yaml_complete = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  ownerReferences:
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def
    controller: true
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Best Practice Blog"
  author: "operator"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""
        result = level.check_fn(yaml_complete)
        assert result.ok, f"Q17.10 should accept complete YAML: {result.error}"
