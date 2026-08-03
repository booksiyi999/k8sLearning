"""QA Attack Tests for Ch15 (PodDisruptionBudget) and Ch16 (PriorityClass).

Attack vectors tested:
- Empty/malformed YAML -> should return ok=False, NOT crash
- PDB with both minAvailable AND maxUnavailable (K8s forbids this)
- PDB minAvailable as negative number
- PDB minAvailable as string "50%" (percentage form)
- PDB selector as empty dict {} (matches all pods)
- PDB selector as non-dict (string/list)
- PriorityClass value as string "1000" instead of int
- PriorityClass value=0, value=-1
- PriorityClass with multiple globalDefault=true
- Missing required fields (no spec.selector, no spec.value)
- Type confusion attacks (bool, float)
- State pollution: call check twice

Bugs found are annotated with # BUG / # SEVERITY comments.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ==========================================================================
#  Helper
# ==========================================================================

def check(level_id: str, user_yaml: str):
    """POST to /api/check and return the JSON response dict."""
    resp = client.post("/api/check", json={"level_id": level_id, "user_yaml": user_yaml})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


# ==========================================================================
#  Valid YAML fixtures (correct baselines)
# ==========================================================================

VALID_Q151 = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: web
"""

VALID_Q152 = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: api-pdb
spec:
  minAvailable: "50%"
  selector:
    matchLabels:
      app: api
"""

VALID_Q153 = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: db-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: db
"""

VALID_Q154 = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  maxUnavailable: 1
  selector:
    matchLabels:
      app: nginx
"""

VALID_Q155 = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-dep
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
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: nginx
"""

VALID_Q161 = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: 1000000
description: "High priority for critical workloads"
"""

VALID_Q162 = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-priority
value: 1000000
description: "Critical workloads that can preempt others"
preemptionPolicy: PreemptLowerPriority
"""

VALID_Q163 = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: default-priority
value: 100000
globalDefault: true
description: "Default priority for all pods"
"""

VALID_Q164 = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: system-critical
value: 800000
description: "System critical workloads"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: user-default
value: 100000
globalDefault: true
description: "Default priority for user workloads"
"""

VALID_Q165 = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pc
value: 1000000
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: critical-pc
  containers:
  - name: nginx
    image: nginx:1.25
"""


# ==========================================================================
#  Baseline: valid YAML should pass
# ==========================================================================

class TestBaselines:
    """Verify that correct YAML passes each level."""

    def test_q151_valid(self):
        r = check("Q15.1", VALID_Q151)
        assert r["ok"] is True, f"Q15.1 baseline should pass: {r.get('error')}"

    def test_q152_valid(self):
        r = check("Q15.2", VALID_Q152)
        assert r["ok"] is True, f"Q15.2 baseline should pass: {r.get('error')}"

    def test_q153_valid(self):
        r = check("Q15.3", VALID_Q153)
        assert r["ok"] is True, f"Q15.3 baseline should pass: {r.get('error')}"

    def test_q154_valid(self):
        r = check("Q15.4", VALID_Q154)
        assert r["ok"] is True, f"Q15.4 baseline should pass: {r.get('error')}"

    def test_q155_valid(self):
        r = check("Q15.5", VALID_Q155)
        assert r["ok"] is True, f"Q15.5 baseline should pass: {r.get('error')}"

    def test_q161_valid(self):
        r = check("Q16.1", VALID_Q161)
        assert r["ok"] is True, f"Q16.1 baseline should pass: {r.get('error')}"

    def test_q162_valid(self):
        r = check("Q16.2", VALID_Q162)
        assert r["ok"] is True, f"Q16.2 baseline should pass: {r.get('error')}"

    def test_q163_valid(self):
        r = check("Q16.3", VALID_Q163)
        assert r["ok"] is True, f"Q16.3 baseline should pass: {r.get('error')}"

    def test_q164_valid(self):
        r = check("Q16.4", VALID_Q164)
        assert r["ok"] is True, f"Q16.4 baseline should pass: {r.get('error')}"

    def test_q165_valid(self):
        r = check("Q16.5", VALID_Q165)
        assert r["ok"] is True, f"Q16.5 baseline should pass: {r.get('error')}"


# ==========================================================================
#  Attack 1: Empty / malformed YAML -> must NOT crash, must return ok=False
# ==========================================================================

class TestEmptyAndMalformed:
    """Empty/malformed YAML must return ok=False without 500 errors."""

    @pytest.mark.parametrize("level_id", ["Q15.1", "Q15.2", "Q15.3", "Q15.4", "Q15.5",
                                            "Q16.1", "Q16.2", "Q16.3", "Q16.4", "Q16.5"])
    def test_empty_yaml(self, level_id):
        r = check(level_id, "")
        assert r["ok"] is False, f"{level_id}: empty YAML should fail, not pass"

    @pytest.mark.parametrize("level_id", ["Q15.1", "Q15.2", "Q15.3", "Q15.4", "Q15.5",
                                            "Q16.1", "Q16.2", "Q16.3", "Q16.4", "Q16.5"])
    def test_garbage_yaml(self, level_id):
        r = check(level_id, "this is not: valid: yaml: [")
        assert r["ok"] is False, f"{level_id}: garbage YAML should fail"

    @pytest.mark.parametrize("level_id", ["Q15.1", "Q16.1"])
    def test_yaml_string_not_dict(self, level_id):
        # YAML that parses to a bare string, not a dict
        r = check(level_id, "just a string")
        assert r["ok"] is False, f"{level_id}: bare string YAML should fail"

    @pytest.mark.parametrize("level_id", ["Q15.1", "Q16.1"])
    def test_yaml_list_not_dict(self, level_id):
        # YAML that parses to a list, not a dict
        r = check(level_id, "- item1\n- item2")
        assert r["ok"] is False, f"{level_id}: list YAML should fail"

    @pytest.mark.parametrize("level_id", ["Q15.1", "Q16.1"])
    def test_yaml_null(self, level_id):
        # YAML that is just null
        r = check(level_id, "null")
        assert r["ok"] is False, f"{level_id}: null YAML should fail"

    @pytest.mark.parametrize("level_id", ["Q15.1", "Q16.1"])
    def test_yaml_number(self, level_id):
        # YAML that is just a number
        r = check(level_id, "42")
        assert r["ok"] is False, f"{level_id}: number YAML should fail"


# ==========================================================================
#  Attack 2: PDB with both minAvailable AND maxUnavailable (K8s forbids)
# ==========================================================================

class TestPDBBothFields:
    """K8s forbids setting both minAvailable and maxUnavailable on the same PDB.
    The simulator should reject this, or at least the check functions should catch it.
    """

    PDB_BOTH = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2
  maxUnavailable: 1
  selector:
    matchLabels:
      app: web
"""

    def test_q151_both_fields_accepted(self):
        # BUG: Q15.1 accepts PDB with both minAvailable AND maxUnavailable.
        # In real K8s this is forbidden. The simulator (_apply_pdb) only checks
        # that at least one is present, not that both aren't.
        # SEVERITY: P1 - simulator-level validation gap
        r = check("Q15.1", self.PDB_BOTH)
        # This SHOULD be ok=False, but it likely passes
        if r["ok"] is True:
            pytest.fail(
                "BUG [P1]: Q15.1 accepts PDB with both minAvailable AND maxUnavailable. "
                "K8s forbids this combination. Simulator _apply_pdb only checks "
                "that at least one field exists, not that both aren't present."
            )

    def test_q152_both_fields_accepted(self):
        # BUG: Q15.2 also doesn't check for both fields.
        # SEVERITY: P2
        r = check("Q15.2", self.PDB_BOTH.replace("minAvailable: 2", 'minAvailable: "50%"'))
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.2 accepts PDB with both minAvailable AND maxUnavailable."
            )

    def test_q153_both_fields_rejected(self):
        # Q15.3 explicitly checks for both (line 396) - this should be ok=False
        r = check("Q15.3", self.PDB_BOTH)
        assert r["ok"] is False, "Q15.3 should reject PDB with both minAvailable and maxUnavailable"


# ==========================================================================
#  Attack 3: Type confusion - boolean values
# ==========================================================================

class TestBooleanTypeConfusion:
    """In Python, True == 1 and False == 0. YAML booleans should not pass as integers."""

    PDB_MAX_UNAVAIL_TRUE = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: db-pdb
spec:
  maxUnavailable: true
  selector:
    matchLabels:
      app: db
"""

    PDB_MIN_AVAIL_TRUE = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: true
  selector:
    matchLabels:
      app: web
"""

    PC_VALUE_TRUE = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
value: true
description: "test"
"""

    def test_q153_max_unavailable_true(self):
        # BUG: Q15.3 accepts maxUnavailable: true because True == 1 in Python.
        # The check `max_unavail != 1` evaluates to `True != 1` which is False,
        # so the check passes. In K8s, maxUnavailable must be int or string, not bool.
        # SEVERITY: P1
        r = check("Q15.3", self.PDB_MAX_UNAVAIL_TRUE)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P1]: Q15.3 accepts maxUnavailable: true (boolean). "
                "True == 1 in Python, so `max_unavail != 1` is False. "
                "Should check isinstance(max_unavail, bool) and reject."
            )

    def test_q154_max_unavailable_true(self):
        # BUG: Q15.4 has the same issue - maxUnavailable: true passes.
        # SEVERITY: P1
        r = check("Q15.4", self.PDB_MAX_UNAVAIL_TRUE.replace("app: db", "app: nginx").replace("name: db-pdb", "name: nginx-pdb"))
        if r["ok"] is True:
            pytest.fail(
                "BUG [P1]: Q15.4 accepts maxUnavailable: true (boolean). "
                "Same True == 1 issue as Q15.3."
            )

    def test_q151_min_available_true(self):
        # Q15.1: minAvailable: true -> True == 1 != 2 -> ok=False. This is fine.
        r = check("Q15.1", self.PDB_MIN_AVAIL_TRUE)
        assert r["ok"] is False, "Q15.1 should reject minAvailable: true (True == 1, not 2)"

    def test_q161_value_true(self):
        # Q16.1 explicitly checks isinstance(value, bool) and rejects. This is fine.
        r = check("Q16.1", self.PC_VALUE_TRUE)
        assert r["ok"] is False, "Q16.1 should reject value: true"

    def test_q162_value_true(self):
        # Q16.2 also explicitly checks isinstance(value, bool). This is fine.
        r = check("Q16.2", self.PC_VALUE_TRUE)
        assert r["ok"] is False, "Q16.2 should reject value: true"

    def test_q163_value_true(self):
        # BUG: Q16.3 does NOT check value type, only that value is not None.
        # The simulator accepts value: true (isinstance(True, int) is True),
        # and Q16.3's check only verifies `value is None` and `globalDefault is True`.
        # SEVERITY: P1
        pc_yaml = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: default-priority
value: true
globalDefault: true
description: "test"
"""
        r = check("Q16.3", pc_yaml)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P1]: Q16.3 accepts value: true (boolean) for PriorityClass. "
                "Simulator accepts it (isinstance(True, int) is True) and "
                "Q16.3 only checks `value is None`, not the type."
            )

    def test_q165_value_true(self):
        # BUG: Q16.5 does NOT check value type either.
        # SEVERITY: P2
        pc_yaml = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: critical-pc
value: true
---
apiVersion: v1
kind: Pod
metadata:
  name: critical-pod
spec:
  priorityClassName: critical-pc
  containers:
  - name: nginx
    image: nginx:1.25
"""
        r = check("Q16.5", pc_yaml)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q16.5 accepts value: true (boolean) for PriorityClass. "
                "No type validation on value field."
            )


# ==========================================================================
#  Attack 4: Type confusion - float values
# ==========================================================================

class TestFloatTypeConfusion:
    """In Python, 2.0 == 2 and 1.0 == 1. YAML floats should not pass as integers."""

    PDB_MIN_AVAIL_FLOAT = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  minAvailable: 2.0
  selector:
    matchLabels:
      app: web
"""

    PDB_MAX_UNAVAIL_FLOAT = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: db-pdb
spec:
  maxUnavailable: 1.0
  selector:
    matchLabels:
      app: db
"""

    def test_q151_min_available_float(self):
        # BUG: Q15.1 accepts minAvailable: 2.0 because 2.0 == 2 in Python.
        # SEVERITY: P2
        r = check("Q15.1", self.PDB_MIN_AVAIL_FLOAT)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.1 accepts minAvailable: 2.0 (float). "
                "2.0 == 2 in Python so `min_available != 2` is False. "
                "Should check isinstance(min_available, int) and not float."
            )

    def test_q153_max_unavailable_float(self):
        # BUG: Q15.3 accepts maxUnavailable: 1.0 because 1.0 == 1 in Python.
        # SEVERITY: P2
        r = check("Q15.3", self.PDB_MAX_UNAVAIL_FLOAT)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.3 accepts maxUnavailable: 1.0 (float). "
                "1.0 == 1 in Python so `max_unavail != 1` is False."
            )

    def test_q154_max_unavailable_float(self):
        # BUG: Q15.4 accepts maxUnavailable: 1.0 - same float issue.
        # SEVERITY: P2
        r = check("Q15.4", self.PDB_MAX_UNAVAIL_FLOAT.replace("app: db", "app: nginx").replace("name: db-pdb", "name: nginx-pdb"))
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.4 accepts maxUnavailable: 1.0 (float). "
                "Same 1.0 == 1 issue."
            )

    def test_q155_float_replicas_and_minavail(self):
        # BUG: Q15.5 accepts replicas: 3.0 and minAvailable: 2.0 (floats).
        # SEVERITY: P2
        yaml_float = VALID_Q155.replace("replicas: 3", "replicas: 3.0").replace("minAvailable: 2", "minAvailable: 2.0")
        r = check("Q15.5", yaml_float)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.5 accepts float values for replicas (3.0) and "
                "minAvailable (2.0). Python float == int comparison passes."
            )


# ==========================================================================
#  Attack 5: PDB minAvailable as percentage string edge cases
# ==========================================================================

class TestPercentageEdgeCases:
    """Q15.2 checks `isinstance(min_available, str) and "%" in min_available`.
    This accepts any string containing %, not just valid percentages.
    """

    def test_q152_valid_percentage(self):
        r = check("Q15.2", VALID_Q152)
        assert r["ok"] is True

    def test_q152_garbage_percentage(self):
        # BUG: Q15.2 accepts any string containing "%" as a valid percentage.
        # e.g. "banana%" or "%%%" or "abc%def" all pass.
        # SEVERITY: P2
        garbage_pdb = VALID_Q152.replace('"50%"', '"banana%"')
        r = check("Q15.2", garbage_pdb)
        if r["ok"] is True:
            pytest.fail(
                'BUG [P2]: Q15.2 accepts minAvailable: "banana%" as valid. '
                "Check is `isinstance(str) and '%' in str` - too permissive. "
                "Should validate format like r'^\\d+%$'."
            )

    def test_q152_double_percent(self):
        # BUG: "50%%" also passes the "%" in string check.
        # SEVERITY: P2
        double_pct = VALID_Q152.replace('"50%"', '"50%%"')
        r = check("Q15.2", double_pct)
        if r["ok"] is True:
            pytest.fail(
                'BUG [P2]: Q15.2 accepts minAvailable: "50%%" as valid percentage.'
            )

    def test_q152_empty_percent(self):
        # BUG: "%" alone passes the check.
        # SEVERITY: P2
        empty_pct = VALID_Q152.replace('"50%"', '"%"')
        r = check("Q15.2", empty_pct)
        if r["ok"] is True:
            pytest.fail(
                'BUG [P2]: Q15.2 accepts minAvailable: "%" as valid percentage.'
            )

    def test_q152_negative_percentage(self):
        # BUG: "-50%" passes the check (string contains "%").
        # SEVERITY: P2
        neg_pct = VALID_Q152.replace('"50%"', '"-50%"')
        r = check("Q15.2", neg_pct)
        if r["ok"] is True:
            pytest.fail(
                'BUG [P2]: Q15.2 accepts minAvailable: "-50%" as valid percentage.'
            )

    def test_q152_over_100_percentage(self):
        # BUG: "150%" passes the check. In K8s, percentage > 100% is invalid for minAvailable.
        # SEVERITY: P2
        over_pct = VALID_Q152.replace('"50%"', '"150%"')
        r = check("Q15.2", over_pct)
        if r["ok"] is True:
            pytest.fail(
                'BUG [P2]: Q15.2 accepts minAvailable: "150%" (> 100%).'
            )


# ==========================================================================
#  Attack 6: PDB selector edge cases
# ==========================================================================

class TestPDBSelector:
    """Test PDB selector validation edge cases."""

    def test_q154_empty_selector(self):
        # Q15.4 requires selector.matchLabels.app == "nginx".
        # Empty selector should fail.
        yaml_empty_sel = VALID_Q154.replace(
            "  selector:\n    matchLabels:\n      app: nginx",
            "  selector: {}"
        )
        r = check("Q15.4", yaml_empty_sel)
        assert r["ok"] is False, "Q15.4 should reject empty selector"

    def test_q154_missing_selector(self):
        # Q15.4 with no selector at all - spec.get("selector", {}) returns {},
        # which is a dict, then matchLabels defaults to {}, .get("app") is None != "nginx".
        yaml_no_sel = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  maxUnavailable: 1
"""
        r = check("Q15.4", yaml_no_sel)
        assert r["ok"] is False, "Q15.4 should reject missing selector"

    def test_q155_empty_selector_passes(self):
        # BUG: Q15.5 accepts PDB with empty/missing selector.
        # The selector matching logic (lines 816-826) only checks mismatch
        # when `app_label` is truthy. If matchLabels is empty or has no "app" key,
        # the check is silently skipped.
        # SEVERITY: P2
        yaml_no_selector = VALID_Q155.replace(
            "  minAvailable: 2\n  selector:\n    matchLabels:\n      app: nginx",
            "  minAvailable: 2"
        )
        r = check("Q15.5", yaml_no_selector)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.5 accepts PDB with no selector. "
                "Selector matching is skipped when matchLabels.app is falsy."
            )

    def test_q155_empty_matchlabels_passes(self):
        # BUG: Q15.5 accepts PDB with empty matchLabels: {}.
        # SEVERITY: P2
        yaml_empty_ml = VALID_Q155.replace(
            "      app: nginx\n",
            ""
        )
        # Keep selector but with empty matchLabels
        yaml_empty_ml = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-dep
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
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: nginx-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels: {}
"""
        r = check("Q15.5", yaml_empty_ml)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q15.5 accepts PDB with empty matchLabels: {}. "
                "Selector mismatch check is skipped."
            )


# ==========================================================================
#  Attack 7: PriorityClass value edge cases
# ==========================================================================

class TestPriorityClassValue:
    """Test PriorityClass value validation edge cases."""

    def test_q161_value_zero(self):
        # value: 0 is a valid int, but != 1000000, so ok=False. Fine.
        yaml_v0 = VALID_Q161.replace("value: 1000000", "value: 0")
        r = check("Q16.1", yaml_v0)
        assert r["ok"] is False, "Q16.1 should reject value: 0"

    def test_q161_value_negative(self):
        # value: -1 is a valid int, but != 1000000, so ok=False. Fine.
        yaml_neg = VALID_Q161.replace("value: 1000000", "value: -1")
        r = check("Q16.1", yaml_neg)
        assert r["ok"] is False, "Q16.1 should reject value: -1"

    def test_q161_value_string(self):
        # value: "1000000" (string) - simulator rejects (not isinstance int).
        yaml_str = VALID_Q161.replace("value: 1000000", 'value: "1000000"')
        r = check("Q16.1", yaml_str)
        assert r["ok"] is False, "Q16.1 should reject value: '1000000' (string)"

    def test_q163_value_negative(self):
        # BUG: Q16.3 accepts value: -1 (negative) with globalDefault: true.
        # Q16.3 only checks `value is None`, not the type or range.
        # In K8s, PriorityClass value must be a non-negative integer.
        # SEVERITY: P2
        yaml_neg = VALID_Q163.replace("value: 100000", "value: -1")
        r = check("Q16.3", yaml_neg)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q16.3 accepts value: -1 (negative) for PriorityClass. "
                "K8s requires value to be a non-negative integer."
            )

    def test_q163_value_zero(self):
        # value: 0 with globalDefault: true. K8s allows value: 0.
        # Q16.3 should accept this (it's technically valid in K8s).
        yaml_v0 = VALID_Q163.replace("value: 100000", "value: 0")
        r = check("Q16.3", yaml_v0)
        # This is actually valid in K8s, so ok=True is acceptable
        assert r["ok"] is True, f"Q16.3 should accept value: 0: {r.get('error')}"

    def test_q163_value_float(self):
        # BUG: Q16.3 accepts value: 100000.0 (float) because simulator
        # uses isinstance(value, int) but... actually in Python
        # isinstance(100000.0, int) is False! So simulator rejects floats.
        # This should be ok=False.
        yaml_float = VALID_Q163.replace("value: 100000", "value: 100000.0")
        r = check("Q16.3", yaml_float)
        assert r["ok"] is False, "Q16.3 should reject value: 100000.0 (float)"


# ==========================================================================
#  Attack 8: PriorityClass globalDefault edge cases
# ==========================================================================

class TestGlobalDefault:
    """Test globalDefault validation edge cases."""

    def test_q163_global_default_string_true(self):
        # globalDefault: "true" (string) should be rejected.
        # Q16.3 checks `global_default is not True` which correctly rejects strings.
        yaml_str_true = VALID_Q163.replace("globalDefault: true", 'globalDefault: "true"')
        r = check("Q16.3", yaml_str_true)
        assert r["ok"] is False, "Q16.3 should reject globalDefault: 'true' (string)"

    def test_q163_global_default_int_1(self):
        # globalDefault: 1 (int) - `1 is not True` is True (different objects),
        # so Q16.3 correctly rejects this.
        yaml_int_1 = VALID_Q163.replace("globalDefault: true", "globalDefault: 1")
        r = check("Q16.3", yaml_int_1)
        assert r["ok"] is False, "Q16.3 should reject globalDefault: 1 (int)"

    def test_q164_multiple_global_default(self):
        # BUG: Q16.4 doesn't validate that only one PriorityClass has
        # globalDefault: true. In K8s, only one PC can have globalDefault: true.
        # SEVERITY: P2
        yaml_multi_gd = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: system-critical
value: 800000
globalDefault: true
description: "System critical"
---
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: user-default
value: 100000
globalDefault: true
description: "User default"
"""
        r = check("Q16.4", yaml_multi_gd)
        if r["ok"] is True:
            pytest.fail(
                "BUG [P2]: Q16.4 accepts two PriorityClasses with globalDefault: true. "
                "K8s only allows one globalDefault: true per cluster."
            )


# ==========================================================================
#  Attack 9: Missing required fields
# ==========================================================================

class TestMissingFields:
    """Test that missing required fields are properly rejected."""

    def test_q151_no_min_available(self):
        yaml_no_ma = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
spec:
  selector:
    matchLabels:
      app: web
"""
        r = check("Q15.1", yaml_no_ma)
        assert r["ok"] is False, "Q15.1 should reject PDB without minAvailable"

    def test_q151_no_spec(self):
        yaml_no_spec = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: web-pdb
"""
        r = check("Q15.1", yaml_no_spec)
        assert r["ok"] is False, "Q15.1 should reject PDB without spec"

    def test_q161_no_value(self):
        yaml_no_val = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata:
  name: high-priority
description: "test"
"""
        r = check("Q16.1", yaml_no_val)
        assert r["ok"] is False, "Q16.1 should reject PriorityClass without value"

    def test_q161_no_metadata_name(self):
        yaml_no_name = """\
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
value: 1000000
description: "test"
"""
        r = check("Q16.1", yaml_no_name)
        assert r["ok"] is False, "Q16.1 should reject PriorityClass without metadata.name"

    def test_q153_no_max_unavailable(self):
        # Q15.3 with only minAvailable should fail (needs maxUnavailable)
        yaml_only_min = """\
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: db-pdb
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: db
"""
        r = check("Q15.3", yaml_only_min)
        assert r["ok"] is False, "Q15.3 should reject PDB without maxUnavailable"


# ==========================================================================
#  Attack 10: State pollution - call check twice
# ==========================================================================

class TestStatePollution:
    """Calling check_fn twice with the same YAML should produce identical results.
    The check functions create a new ClusterState() each time, so no pollution expected.
    """

    def test_q151_double_call(self):
        r1 = check("Q15.1", VALID_Q151)
        r2 = check("Q15.1", VALID_Q151)
        assert r1["ok"] == r2["ok"], "Q15.1: double call should produce same result"

    def test_q153_double_call(self):
        r1 = check("Q15.3", VALID_Q153)
        r2 = check("Q15.3", VALID_Q153)
        assert r1["ok"] == r2["ok"], "Q15.3: double call should produce same result"

    def test_q161_double_call(self):
        r1 = check("Q16.1", VALID_Q161)
        r2 = check("Q16.1", VALID_Q161)
        assert r1["ok"] == r2["ok"], "Q16.1: double call should produce same result"

    def test_q155_double_call(self):
        r1 = check("Q15.5", VALID_Q155)
        r2 = check("Q15.5", VALID_Q155)
        assert r1["ok"] == r2["ok"], "Q15.5: double call should produce same result"

    def test_q165_double_call(self):
        r1 = check("Q16.5", VALID_Q165)
        r2 = check("Q16.5", VALID_Q165)
        assert r1["ok"] == r2["ok"], "Q16.5: double call should produce same result"

    def test_q151_fail_then_pass(self):
        """Call with bad YAML first, then valid YAML - should still pass."""
        check("Q15.1", "garbage")
        r = check("Q15.1", VALID_Q151)
        assert r["ok"] is True, "Q15.1: state from bad call should not pollute good call"

    def test_q161_fail_then_pass(self):
        check("Q16.1", "garbage")
        r = check("Q16.1", VALID_Q161)
        assert r["ok"] is True, "Q16.1: state from bad call should not pollute good call"


# ==========================================================================
#  Attack 11: Wrong kind / unrelated resources
# ==========================================================================

class TestWrongKind:
    """Submitting the wrong kind of resource should fail gracefully."""

    def test_q151_wrong_kind_pod(self):
        yaml_pod = """\
apiVersion: v1
kind: Pod
metadata:
  name: web
spec:
  containers:
  - name: nginx
    image: nginx
"""
        r = check("Q15.1", yaml_pod)
        assert r["ok"] is False, "Q15.1 should reject Pod instead of PDB"

    def test_q161_wrong_kind_pdb(self):
        r = check("Q16.1", VALID_Q151)
        assert r["ok"] is False, "Q16.1 should reject PDB instead of PriorityClass"

    def test_q151_wrong_kind_deployment(self):
        yaml_dep = """\
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
        image: nginx
"""
        r = check("Q15.1", yaml_dep)
        assert r["ok"] is False, "Q15.1 should reject Deployment instead of PDB"


# ==========================================================================
#  Attack 12: minAvailable / maxUnavailable as wrong types
# ==========================================================================

class TestWrongTypeMinMax:
    """Test minAvailable/maxUnavailable with wrong types (list, dict, null)."""

    def test_q151_min_available_list(self):
        yaml_list = VALID_Q151.replace("minAvailable: 2", "minAvailable: [1, 2]")
        r = check("Q15.1", yaml_list)
        assert r["ok"] is False, "Q15.1 should reject minAvailable as list"

    def test_q151_min_available_dict(self):
        yaml_dict = VALID_Q151.replace("minAvailable: 2", "minAvailable:\n  count: 2")
        r = check("Q15.1", yaml_dict)
        assert r["ok"] is False, "Q15.1 should reject minAvailable as dict"

    def test_q153_max_unavailable_string(self):
        # maxUnavailable: "1" (string) - "1" != 1, so ok=False. Fine.
        yaml_str = VALID_Q153.replace("maxUnavailable: 1", 'maxUnavailable: "1"')
        r = check("Q15.3", yaml_str)
        assert r["ok"] is False, "Q15.3 should reject maxUnavailable as string '1'"

    def test_q151_min_available_null(self):
        # minAvailable: null - "minAvailable" key exists but value is None.
        # The check `if "minAvailable" not in spec` passes (key exists),
        # then `min_available != 2` -> None != 2 -> True -> ok=False. Fine.
        yaml_null = VALID_Q151.replace("minAvailable: 2", "minAvailable: null")
        r = check("Q15.1", yaml_null)
        assert r["ok"] is False, "Q15.1 should reject minAvailable: null"


# ==========================================================================
#  Attack 13: Multi-doc injection / extra resources
# ==========================================================================

class TestMultiDocInjection:
    """Test multi-document YAML with extra/unexpected resources."""

    def test_q151_with_extra_pod(self):
        # PDB + extra Pod in multi-doc YAML - should still pass if PDB is correct
        yaml_multi = VALID_Q151 + """\
---
apiVersion: v1
kind: Pod
metadata:
  name: extra
spec:
  containers:
  - name: nginx
    image: nginx
"""
        r = check("Q15.1", yaml_multi)
        assert r["ok"] is True, "Q15.1 should pass with extra Pod in multi-doc"

    def test_q161_with_extra_pod(self):
        yaml_multi = VALID_Q161 + """\
---
apiVersion: v1
kind: Pod
metadata:
  name: extra
spec:
  containers:
  - name: nginx
    image: nginx
"""
        r = check("Q16.1", yaml_multi)
        assert r["ok"] is True, "Q16.1 should pass with extra Pod in multi-doc"

    def test_q155_missing_deployment(self):
        # Q15.5 requires both Deployment and PDB - missing Deployment should fail
        yaml_only_pdb = VALID_Q155.split("---")[1]  # Just the PDB part
        r = check("Q15.5", yaml_only_pdb)
        assert r["ok"] is False, "Q15.5 should fail without Deployment"

    def test_q155_missing_pdb(self):
        # Q15.5 requires both - missing PDB should fail
        yaml_only_dep = VALID_Q155.split("---")[0]  # Just the Deployment part
        r = check("Q15.5", yaml_only_dep)
        assert r["ok"] is False, "Q15.5 should fail without PDB"

    def test_q165_missing_pod(self):
        # Q16.5 requires both PriorityClass and Pod
        yaml_only_pc = VALID_Q165.split("---")[0]
        r = check("Q16.5", yaml_only_pc)
        assert r["ok"] is False, "Q16.5 should fail without Pod"

    def test_q165_missing_priorityclass(self):
        # Q16.5 requires both - missing PriorityClass should fail
        yaml_only_pod = VALID_Q165.split("---")[1]
        r = check("Q16.5", yaml_only_pod)
        assert r["ok"] is False, "Q16.5 should fail without PriorityClass"
