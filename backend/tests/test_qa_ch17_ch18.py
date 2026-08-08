"""QA 攻击性测试 - Ch17 (CRD & Operator) & Ch18 (ServiceAccount & 安全上下文)

5 维度攻击测试:
1. 边界输入测试
2. 恶意输入测试
3. 状态污染测试
4. 逻辑正确性测试
5. 模拟器一致性测试
"""
import copy
import pytest
from app.validator import get_level, CheckResult
from app.simulator import (
    ClusterState, apply_manifest, preset_state, K8sError,
)


# ========== Helper YAML fixtures ==========

VALID_CRD = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
    singular: blog
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
              author:
                type: string
"""

VALID_CRD_NO_SCHEMA = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
"""

VALID_CR = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-first-blog
spec:
  title: "Hello K8s"
  author: "dev"
"""

VALID_SA = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: app-sa
"""

VALID_OPERATOR_DEPLOY = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE
          value: ""
"""

# Q17.3: Role + RoleBinding for Operator RBAC
VALID_ROLE_ROLEBINDING = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: blog-operator-role
rules:
- apiGroups: ["blog.example.com"]
  resources: ["blogs"]
  verbs: ["get", "list", "watch", "create", "update", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
subjects:
- kind: ServiceAccount
  name: blog-operator-sa
  namespace: default
roleRef:
  kind: Role
  name: blog-operator-role
  apiGroup: rbac.authorization.k8s.io
"""

# Q17.4: CRD with status subresource + Deployment
VALID_CRD_WITH_SUBRESOURCES = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            properties:
              title:
                type: string
          status:
            type: object
            properties:
              phase:
                type: string
    subresources:
      status: {}
"""

VALID_SECURE_POD = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      runAsUser: 1000
"""

VALID_PSS_RESTRICTED_POD = """\
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  securityContext:
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
"""

VALID_LEAST_PRIV = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: secure-app-sa
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  serviceAccountName: secure-app-sa
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
"""


def _check(level_id, yaml_text):
    """Shortcut to run a level's check_fn."""
    return get_level(level_id).check_fn(yaml_text)


# =====================================================================
# 1. 边界输入测试
# =====================================================================

class TestBoundaryInputs:
    """维度 1: 边界输入测试"""

    # --- Empty / trivial YAML ---

    def test_q171_empty_string(self):
        r = _check("Q17.1", "")
        assert not r.ok

    def test_q171_only_comments(self):
        r = _check("Q17.1", "# just a comment\n")
        assert not r.ok

    def test_q171_only_separators(self):
        r = _check("Q17.1", "---\n---\n")
        assert not r.ok

    def test_q171_yaml_syntax_error(self):
        r = _check("Q17.1", "kind: Pod\n\tbad tab indent\n")
        assert not r.ok

    def test_q181_empty_string(self):
        r = _check("Q18.1", "")
        assert not r.ok

    def test_q181_only_comments(self):
        r = _check("Q18.1", "# comment only\n")
        assert not r.ok

    # --- kind / apiVersion typos ---

    def test_q171_kind_typo(self):
        yaml_bad = VALID_CRD.replace("CustomResourceDefinition", "CustomResourceDef")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_wrong_apiVersion(self):
        # BUG: Q17.1 does NOT validate apiVersion. The simulator dispatches by
        # kind only, so a CRD with apiVersion: v1 is still processed.
        # SEVERITY: P1
        yaml_bad = VALID_CRD.replace(
            "apiVersion: apiextensions.k8s.io/v1", "apiVersion: v1"
        )
        r = _check("Q17.1", yaml_bad)
        # BUG: This should fail but currently passes
        assert r.ok, (
            "BUG: Q17.1 should reject wrong apiVersion but currently accepts it"
        )

    def test_q171_wrong_apiVersion_apps(self):
        # BUG: same as above, apiVersion: apps/v1 on a CRD is accepted
        # SEVERITY: P1
        yaml_bad = VALID_CRD.replace(
            "apiVersion: apiextensions.k8s.io/v1", "apiVersion: apps/v1"
        )
        r = _check("Q17.1", yaml_bad)
        assert r.ok, "BUG: Q17.1 accepts wrong apiVersion (apps/v1)"

    # --- metadata.name validation ---

    def test_q171_bad_metadata_name(self):
        """Q17.1 now validates metadata.name format (<plural>.<group>)."""
        yaml_bad = VALID_CRD.replace(
            "name: blogs.blog.example.com", "name: foo"
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok
        assert "metadata.name" in r.error.lower() or "格式" in r.error

    def test_q171_empty_metadata_name(self):
        """Q17.1 now rejects empty metadata.name (format check fails)."""
        yaml_bad = VALID_CRD.replace(
            "name: blogs.blog.example.com", 'name: ""'
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok
        assert "metadata.name" in r.error.lower() or "格式" in r.error

    # --- CRD spec field missing ---

    def test_q171_missing_group(self):
        yaml_bad = VALID_CRD.replace("  group: blog.example.com\n", "")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok
        assert "group" in r.error.lower()

    def test_q171_missing_names(self):
        yaml_bad = VALID_CRD.replace(
            "  names:\n    kind: Blog\n    plural: blogs\n", ""
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_empty_names(self):
        yaml_bad = VALID_CRD.replace(
            "    kind: Blog\n    plural: blogs\n    singular: blog\n",
            "",
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_missing_versions(self):
        yaml_bad = VALID_CRD.replace(
            "  versions:\n  - name: v1\n    served: true\n    storage: true\n",
            "",
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_empty_versions_list(self):
        yaml_bad = VALID_CRD.replace(
            "  versions:\n  - name: v1\n    served: true\n    storage: true\n",
            "  versions: []\n",
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_missing_kind_in_names(self):
        yaml_bad = VALID_CRD.replace("    kind: Blog\n", "")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_missing_plural_in_names(self):
        yaml_bad = VALID_CRD.replace("    plural: blogs\n", "")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    # --- scope validation ---

    def test_q171_scope_cluster(self):
        yaml_cluster = VALID_CRD.replace("scope: Namespaced", "scope: Cluster")
        r = _check("Q17.1", yaml_cluster)
        assert r.ok

    def test_q171_scope_lowercase(self):
        yaml_bad = VALID_CRD.replace("scope: Namespaced", "scope: namespaced")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_scope_invalid(self):
        yaml_bad = VALID_CRD.replace("scope: Namespaced", "scope: Whatever")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_q171_scope_missing(self):
        yaml_bad = VALID_CRD.replace("  scope: Namespaced\n", "")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    # --- CRD Schema validation (Q17.2 is now CRD Schema, not CR creation) ---

    def test_q172_wrong_group_in_apiVersion(self):
        """Q17.2 is now CRD Schema validation. A CR (not CRD) should fail."""
        yaml_bad = VALID_CR.replace(
            "apiVersion: blog.example.com/v1", "apiVersion: blog.wrong.com/v1"
        )
        r = _check("Q17.2", yaml_bad)
        assert not r.ok

    def test_q172_wrong_version_in_apiVersion(self):
        """Q17.2 is now CRD Schema. A CR (not CRD) should fail."""
        yaml_bad = VALID_CR.replace(
            "apiVersion: blog.example.com/v1", "apiVersion: blog.example.com/v999"
        )
        r = _check("Q17.2", yaml_bad)
        assert not r.ok

    # --- SecurityContext edge cases ---

    def test_q183_runAsNonRoot_true_runAsUser_0(self):
        """runAsNonRoot=true + runAsUser=0 contradiction should be caught."""
        yaml_bad = VALID_SECURE_POD.replace(
            "      runAsUser: 1000",
            "      runAsNonRoot: true\n      runAsUser: 0",
        )
        # Remove duplicate runAsNonRoot
        yaml_bad = yaml_bad.replace(
            "      runAsNonRoot: true\n      runAsNonRoot: true\n      runAsUser: 0",
            "      runAsNonRoot: true\n      runAsUser: 0",
        )
        r = _check("Q18.3", yaml_bad)
        assert not r.ok
        assert "runAsUser" in r.error or "0" in r.error

    def test_q183_runAsNonRoot_true_pod_level_runAsUser_0(self):
        """Pod-level runAsNonRoot=true + pod-level runAsUser=0 contradiction."""
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 0
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      readOnlyRootFilesystem: true
"""
        r = _check("Q18.3", yaml_bad)
        assert not r.ok

    def test_q183_runAsUser_string_zero(self):
        # BUG: runAsUser: "0" (string) passes because "0" != 0 (int).
        # In real K8s, runAsUser must be an integer; string "0" is invalid.
        # SEVERITY: P1
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      runAsUser: "0"
"""
        r = _check("Q18.3", yaml_bad)
        assert not r.ok, "BUG: Q18.3 accepts runAsUser='0' (string) which equals root"

    def test_q183_runAsUser_string_value(self):
        # BUG: runAsUser: "1000" (string) passes. In real K8s it must be int.
        # SEVERITY: P2
        yaml_bad = VALID_SECURE_POD.replace(
            "runAsUser: 1000", 'runAsUser: "1000"'
        )
        r = _check("Q18.3", yaml_bad)
        assert r.ok, "BUG: Q18.3 accepts runAsUser as string instead of int"

    def test_q183_runAsNonRoot_string_true(self):
        """runAsNonRoot: "true" (string) should NOT pass (not boolean true)."""
        yaml_bad = VALID_SECURE_POD.replace(
            "runAsNonRoot: true", 'runAsNonRoot: "true"'
        )
        r = _check("Q18.3", yaml_bad)
        assert not r.ok

    def test_q183_missing_runAsUser(self):
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
"""
        r = _check("Q18.3", yaml_bad)
        assert not r.ok

    def test_q183_pod_level_sc_only(self):
        """Pod-level securityContext with runAsNonRoot + runAsUser, container
        has readOnlyRootFilesystem - should pass."""
        yaml_good = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      readOnlyRootFilesystem: true
"""
        r = _check("Q18.3", yaml_good)
        assert r.ok

    def test_q183_readOnlyRootFilesystem_pod_level_only(self):
        """readOnlyRootFilesystem is a container-level field. Setting it at
        pod level only should fail (check only looks at container_sc)."""
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    readOnlyRootFilesystem: true
  containers:
  - name: web
    image: nginx:1.25-alpine
"""
        r = _check("Q18.3", yaml_bad)
        assert not r.ok

    # --- PSS restricted edge cases ---

    def test_q184_runAsUser_string_zero(self):
        # BUG: Same as Q18.3 - runAsUser: "0" (string) passes PSS restricted
        # SEVERITY: P1
        yaml_bad = VALID_PSS_RESTRICTED_POD.replace(
            "runAsUser: 1000", 'runAsUser: "0"'
        )
        r = _check("Q18.4", yaml_bad)
        assert not r.ok, "BUG: Q18.4 PSS restricted accepts runAsUser='0' (string)"

    def test_q184_privileged_true_not_checked(self):
        # BUG: PSS restricted should reject privileged: true but the check
        # does not verify this. The lesson claims "7. 禁止 privileged 容器"
        # but the code only checks 5 items.
        # SEVERITY: P1
        yaml_bad = VALID_PSS_RESTRICTED_POD.replace(
            "      capabilities:\n        drop: [ALL]",
            "      privileged: true\n      capabilities:\n        drop: [ALL]",
        )
        r = _check("Q18.4", yaml_bad)
        assert not r.ok, "BUG: Q18.4 does not check privileged: true (PSS restricted should reject)"

    def test_q184_hostNetwork_not_checked(self):
        # BUG: PSS restricted should reject hostNetwork: true
        # SEVERITY: P1
        yaml_bad = "spec:\n  hostNetwork: true\n" + VALID_PSS_RESTRICTED_POD.split("spec:\n", 1)[1]
        # Fix: insert hostNetwork at pod spec level
        lines = VALID_PSS_RESTRICTED_POD.split("\n")
        new_lines = []
        for line in lines:
            if line.strip() == "spec:":
                new_lines.append(line)
                new_lines.append("  hostNetwork: true")
            else:
                new_lines.append(line)
        yaml_bad = "\n".join(new_lines)
        r = _check("Q18.4", yaml_bad)
        assert not r.ok, "BUG: Q18.4 does not check hostNetwork (PSS restricted should reject)"

    def test_q184_hostPID_not_checked(self):
        # BUG: PSS restricted should reject hostPID: true
        # SEVERITY: P1
        lines = VALID_PSS_RESTRICTED_POD.split("\n")
        new_lines = []
        for line in lines:
            if line.strip() == "spec:":
                new_lines.append(line)
                new_lines.append("  hostPID: true")
            else:
                new_lines.append(line)
        yaml_bad = "\n".join(new_lines)
        r = _check("Q18.4", yaml_bad)
        assert not r.ok, "BUG: Q18.4 does not check hostPID (PSS restricted should reject)"

    def test_q184_missing_allowPrivilegeEscalation(self):
        yaml_bad = VALID_PSS_RESTRICTED_POD.replace(
            "      allowPrivilegeEscalation: false\n", ""
        )
        r = _check("Q18.4", yaml_bad)
        assert not r.ok

    def test_q184_missing_seccompProfile(self):
        yaml_bad = VALID_PSS_RESTRICTED_POD.replace(
            "  securityContext:\n    seccompProfile:\n      type: RuntimeDefault\n",
            "",
        )
        r = _check("Q18.4", yaml_bad)
        assert not r.ok

    def test_q184_seccompProfile_container_level(self):
        """seccompProfile at container level should also pass."""
        yaml_good = """\
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
      seccompProfile:
        type: RuntimeDefault
"""
        r = _check("Q18.4", yaml_good)
        assert r.ok

    def test_q184_capabilities_drop_string_not_list(self):
        """capabilities.drop: ALL (string, not list) should fail."""
        yaml_bad = VALID_PSS_RESTRICTED_POD.replace(
            "        drop: [ALL]", "        drop: ALL"
        )
        r = _check("Q18.4", yaml_bad)
        assert not r.ok

    # --- SA edge cases ---

    def test_q181_missing_name(self):
        yaml_bad = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  namespace: default
"""
        r = _check("Q18.1", yaml_bad)
        assert not r.ok

    def test_q181_empty_name(self):
        yaml_bad = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ""
"""
        r = _check("Q18.1", yaml_bad)
        assert not r.ok

    def test_q181_starter_pass_true(self):
        """The starter YAML has 'pass: true' instead of name - should fail."""
        yaml_starter = get_level("Q18.1").starter_yaml
        r = _check("Q18.1", yaml_starter)
        assert not r.ok


# =====================================================================
# 2. 恶意输入测试
# =====================================================================

class TestMaliciousInputs:
    """维度 2: 恶意输入测试"""

    def test_yaml_bomb_deep_nesting(self):
        """Deeply nested YAML should not crash."""
        deep = "a: " + "\n".join(["  " * i + "b: " for i in range(1, 300)]) + "  c: val\n"
        r = _check("Q17.1", deep)
        assert not r.ok  # Should gracefully fail, not crash

    def test_yaml_anchor_recursion(self):
        """Self-referencing YAML anchor should be rejected."""
        yaml_bomb = "a: &a [*a]\n"
        r = _check("Q17.1", yaml_bomb)
        assert not r.ok

    def test_multi_doc_crd_before_cr(self):
        """Multi-doc YAML where CR appears before CRD - simulator should reject
        the CR since CRD isn't registered yet."""
        yaml_multi = VALID_CR + "---\n" + VALID_CRD_NO_SCHEMA
        state = ClusterState()
        with pytest.raises(K8sError):
            apply_manifest(state, yaml_multi)

    def test_q172_multi_doc_crd_then_cr(self):
        """Q17.2 is now CRD Schema. A CRD with schema + CR should pass
        because the CRD has the required schema."""
        yaml_multi = VALID_CRD + "---\n" + VALID_CR
        r = _check("Q17.2", yaml_multi)
        assert r.ok

    def test_crd_versions_non_dict_element(self):
        """CRD spec.versions containing a non-dict element - tests Q17.1 (CRD creation)."""
        yaml_bad = VALID_CRD.replace(
            "  - name: v1\n    served: true\n    storage: true",
            '  - "just a string"'
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_crd_schema_malicious_type(self):
        """openAPIV3Schema with non-standard type value - tests Q17.2 (CRD Schema)."""
        yaml_bad = VALID_CRD.replace(
            "        type: object\n        properties:",
            '        type: "malicious-type"\n        properties:'
        )
        r = _check("Q17.2", yaml_bad)
        assert not r.ok

    def test_q174_env_name_non_string_crash(self):
        """env[].name as non-string should not crash. Q17.4 now needs CRD+Deployment."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                '        - name: WATCH_NAMESPACE\n          value: ""',
                "        - name: 123\n          value: \"\""
            )
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_q174_env_dict_instead_of_list(self):
        """env as dict instead of list should not crash."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                "        env:\n        - name: WATCH_NAMESPACE\n          value: \"\"",
                '        env:\n          WATCH_NAMESPACE: ""'
            )
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_q174_env_null(self):
        """env: null should not crash."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                "        env:\n        - name: WATCH_NAMESPACE\n          value: \"\"",
                "        env: null"
            )
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_sa_reference_nonexistent(self):
        """Pod referencing a non-existent SA - simulator doesn't validate SA
        existence for Pod creation."""
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  serviceAccountName: nonexistent-sa
  containers:
  - name: app
    image: busybox:1.36
"""
        # Q18.2 pre-sets app-sa, but user references a different SA
        r = _check("Q18.2", yaml_bad)
        assert not r.ok
        assert "app-sa" in r.error

    def test_securityContext_unknown_fields(self):
        """SecurityContext with unknown fields should be ignored, not crash."""
        yaml_good = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-pod
spec:
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsNonRoot: true
      readOnlyRootFilesystem: true
      runAsUser: 1000
      unknownField: "should be ignored"
      anotherUnknown: 42
"""
        r = _check("Q18.3", yaml_good)
        assert r.ok


# =====================================================================
# 3. 状态污染测试
# =====================================================================

class TestStatePollution:
    """维度 3: 状态污染测试"""

    def test_check_fn_no_side_effects(self):
        """Calling check_fn should not modify any global state."""
        r1 = _check("Q17.1", VALID_CRD)
        r2 = _check("Q17.1", VALID_CRD)
        assert r1.ok == r2.ok

    def test_multiple_calls_consistent_q172(self):
        """Q17.2 is now CRD Schema. Calling multiple times should be consistent."""
        results = [_check("Q17.2", VALID_CRD).ok for _ in range(5)]
        assert all(results)

    def test_multiple_calls_consistent_q182(self):
        """Q18.2 uses preset_state - calling multiple times should be consistent."""
        yaml_pod = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
"""
        results = [_check("Q18.2", yaml_pod).ok for _ in range(5)]
        assert all(results)

    def test_crd_then_cr_in_same_state(self):
        """After CRD is created, a CR should be correctly referenced."""
        state = ClusterState()
        state = apply_manifest(state, VALID_CRD_NO_SCHEMA)
        assert len(state.customresourcedefinitions) == 1
        state = apply_manifest(state, VALID_CR)
        assert len(state.customresources) == 1

    def test_crd_does_not_pollute_preset(self):
        """preset_state should not be affected by user YAML processing."""
        state1 = ClusterState()
        state1 = preset_state(state1, VALID_CRD_NO_SCHEMA)
        crd_count_before = len(state1.customresourcedefinitions)

        # Apply user YAML that also creates a CRD
        state2 = ClusterState()
        state2 = preset_state(state2, VALID_CRD_NO_SCHEMA)
        state2 = apply_manifest(state2, VALID_CRD_NO_SCHEMA)

        # state1 should be unchanged
        assert len(state1.customresourcedefinitions) == crd_count_before

    def test_check_result_state_isolation(self):
        """The state returned in CheckResult should be independent."""
        r1 = _check("Q17.1", VALID_CRD)
        if r1.state:
            original_count = len(r1.state.customresourcedefinitions)
        r2 = _check("Q17.1", VALID_CRD)
        if r1.state:
            assert len(r1.state.customresourcedefinitions) == original_count


# =====================================================================
# 4. 逻辑正确性测试
# =====================================================================

class TestLogicCorrectness:
    """维度 4: 逻辑正确性测试"""

    # --- Q17.1 ---

    def test_q171_valid(self):
        r = _check("Q17.1", VALID_CRD)
        assert r.ok, r.error

    def test_q171_valid_minimal(self):
        """Minimal valid CRD without schema."""
        r = _check("Q17.1", VALID_CRD_NO_SCHEMA)
        assert r.ok, r.error

    # --- Q17.2 (now CRD Schema validation) ---

    def test_q172_valid(self):
        r = _check("Q17.2", VALID_CRD)
        assert r.ok, r.error

    def test_q172_no_schema_fails(self):
        r = _check("Q17.2", VALID_CRD_NO_SCHEMA)
        assert not r.ok
        assert "schema" in r.error.lower()

    def test_q172_empty_spec_properties_fails(self):
        """CRD with schema but empty spec properties should fail."""
        yaml_bad = VALID_CRD.replace(
            "              title:\n                type: string\n              author:\n                type: string",
            ""
        )
        r = _check("Q17.2", yaml_bad)
        assert not r.ok

    # --- Q17.3 (now Operator RBAC: Role + RoleBinding) ---

    def test_q173_valid(self):
        r = _check("Q17.3", VALID_ROLE_ROLEBINDING)
        assert r.ok, r.error

    def test_q173_missing_role(self):
        """Only RoleBinding, no Role."""
        yaml_bad = VALID_ROLE_ROLEBINDING.split("---", 1)[1]
        r = _check("Q17.3", yaml_bad)
        assert not r.ok

    def test_q173_empty_rules(self):
        """Role with empty rules should fail."""
        yaml_bad = VALID_ROLE_ROLEBINDING.replace("rules:\n- apiGroups:", "rules: []\n# apiGroups:")
        r = _check("Q17.3", yaml_bad)
        assert not r.ok

    def test_q173_no_sa_subject(self):
        """RoleBinding with User subject instead of ServiceAccount."""
        yaml_bad = VALID_ROLE_ROLEBINDING.replace(
            "- kind: ServiceAccount\n  name: blog-operator-sa",
            "- kind: User\n  name: admin"
        )
        r = _check("Q17.3", yaml_bad)
        assert not r.ok

    # --- Q17.4 (now Status subresource + Deployment) ---

    def test_q174_valid(self):
        yaml_valid = VALID_CRD_WITH_SUBRESOURCES + "---\n" + VALID_OPERATOR_DEPLOY
        r = _check("Q17.4", yaml_valid)
        assert r.ok, r.error

    def test_q174_missing_watch_env(self):
        yaml_no_watch = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                "        env:\n        - name: WATCH_NAMESPACE\n          value: \"\"", ""
            )
        r = _check("Q17.4", yaml_no_watch)
        assert not r.ok

    def test_q174_env_name_non_string_crash(self):
        """env[].name as non-string should not crash."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                '        - name: WATCH_NAMESPACE\n          value: ""',
                "        - name: 123\n          value: \"\""
            )
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_q174_env_dict_instead_of_list(self):
        """env as dict instead of list should not crash."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                "        env:\n        - name: WATCH_NAMESPACE\n          value: \"\"",
                '        env:\n          WATCH_NAMESPACE: ""'
            )
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_q174_env_null(self):
        """env: null should not crash."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace(
                "        env:\n        - name: WATCH_NAMESPACE\n          value: \"\"",
                "        env: null"
            )
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_q174_missing_image(self):
        """Q17.4 now checks status subresource + WATCH_NAMESPACE, not image.
        A deployment without image but with WATCH_NAMESPACE will pass.
        Test that a deployment WITHOUT WATCH_NAMESPACE fails."""
        yaml_bad = VALID_CRD_WITH_SUBRESOURCES + "---\n" + \
            VALID_OPERATOR_DEPLOY.replace("WATCH_NAMESPACE", "NOT_WATCH_NAMESPACE")
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    # --- Q17.5 ---

    def test_q175_valid(self):
        yaml_full = VALID_CRD_NO_SCHEMA + "---\n" + VALID_SA.replace(
            "app-sa", "blog-operator-sa"
        ) + "---\n" + VALID_OPERATOR_DEPLOY
        # Add serviceAccountName to the deployment template
        yaml_full = yaml_full.replace(
            "    spec:\n      containers:",
            "    spec:\n      serviceAccountName: blog-operator-sa\n      containers:"
        )
        r = _check("Q17.5", yaml_full)
        assert r.ok, r.error

    def test_q175_no_watch_env_required(self):
        """Q17.5 now checks WATCH_NAMESPACE env (previously a BUG)."""
        yaml_full = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: blog-operator-sa
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      serviceAccountName: blog-operator-sa
      containers:
      - name: operator
        image: nginx:1.25
"""
        r = _check("Q17.5", yaml_full)
        assert not r.ok
        assert "watch" in r.error.lower()

    def test_q175_no_image_required(self):
        """Q17.5 now checks Deployment image (previously a BUG)."""
        yaml_full = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    kind: Blog
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: blog-operator-sa
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: blog-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: blog-operator
  template:
    metadata:
      labels:
        app: blog-operator
    spec:
      serviceAccountName: blog-operator-sa
      containers:
      - name: operator
        env:
        - name: WATCH_NAMESPACE
          value: ""
"""
        r = _check("Q17.5", yaml_full)
        assert not r.ok
        assert "image" in r.error.lower()

    def test_q175_missing_crd(self):
        yaml_no_crd = VALID_SA.replace("app-sa", "blog-operator-sa") + "---\n" + VALID_OPERATOR_DEPLOY
        yaml_no_crd = yaml_no_crd.replace(
            "    spec:\n      containers:",
            "    spec:\n      serviceAccountName: blog-operator-sa\n      containers:"
        )
        r = _check("Q17.5", yaml_no_crd)
        assert not r.ok

    def test_q175_missing_sa(self):
        yaml_no_sa = VALID_CRD_NO_SCHEMA + "---\n" + VALID_OPERATOR_DEPLOY
        yaml_no_sa = yaml_no_sa.replace(
            "    spec:\n      containers:",
            "    spec:\n      serviceAccountName: blog-operator-sa\n      containers:"
        )
        r = _check("Q17.5", yaml_no_sa)
        assert not r.ok

    def test_q175_sa_not_matching(self):
        yaml_mismatch = VALID_CRD_NO_SCHEMA + "---\n" + \
            VALID_SA.replace("app-sa", "wrong-sa") + "---\n" + VALID_OPERATOR_DEPLOY
        yaml_mismatch = yaml_mismatch.replace(
            "    spec:\n      containers:",
            "    spec:\n      serviceAccountName: blog-operator-sa\n      containers:"
        )
        r = _check("Q17.5", yaml_mismatch)
        assert not r.ok
        assert "blog-operator-sa" in r.error or "不存在" in r.error

    # --- Q18.1 ---

    def test_q181_valid(self):
        r = _check("Q18.1", VALID_SA)
        assert r.ok, r.error

    def test_q181_wrong_apiVersion(self):
        # BUG: Q18.1 does NOT validate apiVersion (simulator dispatches by kind)
        # SEVERITY: P2
        yaml_bad = VALID_SA.replace("apiVersion: v1", "apiVersion: apps/v1")
        r = _check("Q18.1", yaml_bad)
        assert r.ok, "BUG: Q18.1 does not validate apiVersion"

    # --- Q18.2 ---

    def test_q182_valid(self):
        yaml_pod = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: busybox:1.36
    command: ["sleep", "3600"]
"""
        r = _check("Q18.2", yaml_pod)
        assert r.ok, r.error

    def test_q182_missing_serviceAccountName(self):
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  containers:
  - name: app
    image: busybox:1.36
"""
        r = _check("Q18.2", yaml_bad)
        assert not r.ok

    def test_q182_wrong_sa_name(self):
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  serviceAccountName: wrong-sa
  containers:
  - name: app
    image: busybox:1.36
"""
        r = _check("Q18.2", yaml_bad)
        assert not r.ok
        assert "app-sa" in r.error

    # --- Q18.3 ---

    def test_q183_valid(self):
        r = _check("Q18.3", VALID_SECURE_POD)
        assert r.ok, r.error

    # --- Q18.4 ---

    def test_q184_valid(self):
        r = _check("Q18.4", VALID_PSS_RESTRICTED_POD)
        assert r.ok, r.error

    def test_q184_pod_level_runAsNonRoot_only(self):
        """runAsNonRoot at pod level only, no container-level override."""
        yaml_good = """\
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
"""
        r = _check("Q18.4", yaml_good)
        assert r.ok

    def test_q184_container_overrides_pod_runAsUser_to_zero(self):
        """Pod sets runAsUser=1000, container overrides to 0 - should fail."""
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: restricted-pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      runAsUser: 0
      allowPrivilegeEscalation: false
      capabilities:
        drop: [ALL]
"""
        r = _check("Q18.4", yaml_bad)
        assert not r.ok

    # --- Q18.5 ---

    def test_q185_valid(self):
        r = _check("Q18.5", VALID_LEAST_PRIV)
        assert r.ok, r.error

    def test_q185_no_allowPrivilegeEscalation_check(self):
        # BUG: Q18.5 does NOT check allowPrivilegeEscalation: false
        # (inconsistent with Q18.4 PSS restricted). The lesson mentions it
        # as important but the check doesn't verify it.
        # SEVERITY: P1
        yaml_bad = VALID_LEAST_PRIV  # No allowPrivilegeEscalation: false
        r = _check("Q18.5", yaml_bad)
        assert r.ok, "BUG: Q18.5 does not check allowPrivilegeEscalation"

    def test_q185_no_seccompProfile_check(self):
        # BUG: Q18.5 does NOT check seccompProfile (inconsistent with Q18.4)
        # SEVERITY: P1
        r = _check("Q18.5", VALID_LEAST_PRIV)
        assert r.ok, "BUG: Q18.5 does not check seccompProfile"

    def test_q185_missing_sa(self):
        yaml_bad = """\
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
"""
        r = _check("Q18.5", yaml_bad)
        assert not r.ok

    def test_q185_sa_not_matching(self):
        yaml_bad = """\
apiVersion: v1
kind: ServiceAccount
metadata:
  name: wrong-sa
---
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  serviceAccountName: secure-app-sa
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
  containers:
  - name: web
    image: nginx:1.25-alpine
    securityContext:
      readOnlyRootFilesystem: true
      capabilities:
        drop: [ALL]
"""
        r = _check("Q18.5", yaml_bad)
        assert not r.ok


# =====================================================================
# 5. 模拟器一致性测试
# =====================================================================

class TestSimulatorConsistency:
    """维度 5: 模拟器一致性测试"""

    def test_crd_apply_and_retrieve(self):
        """CRD should be stored in state after apply."""
        state = ClusterState()
        state = apply_manifest(state, VALID_CRD)
        assert "blogs.blog.example.com" in state.customresourcedefinitions

    def test_cr_apply_after_crd(self):
        """CR should be stored after CRD is registered."""
        state = ClusterState()
        state = apply_manifest(state, VALID_CRD_NO_SCHEMA)
        state = apply_manifest(state, VALID_CR)
        assert len(state.customresources) == 1
        cr_key = next(iter(state.customresources))
        assert "my-first-blog" in cr_key

    def test_cr_before_crd_rejected(self):
        """CR before CRD should be rejected (like real K8s)."""
        state = ClusterState()
        with pytest.raises(K8sError, match="不支持的资源类型"):
            apply_manifest(state, VALID_CR)

    def test_cr_version_not_validated(self):
        # BUG: Simulator does NOT validate CR version against CRD versions.
        # apiVersion: blog.example.com/v999 matches a CRD with only v1.
        # SEVERITY: P1
        state = ClusterState()
        state = apply_manifest(state, VALID_CRD_NO_SCHEMA)
        yaml_cr_v999 = VALID_CR.replace(
            "apiVersion: blog.example.com/v1",
            "apiVersion: blog.example.com/v999",
        )
        state = apply_manifest(state, yaml_cr_v999)
        assert len(state.customresources) == 1, \
            "BUG: Simulator accepts CR with wrong version (v999 vs v1)"

    def test_cr_wrong_group_rejected(self):
        """CR with wrong group should be rejected."""
        state = ClusterState()
        state = apply_manifest(state, VALID_CRD_NO_SCHEMA)
        yaml_bad = VALID_CR.replace(
            "apiVersion: blog.example.com/v1",
            "apiVersion: wrong.example.com/v1",
        )
        with pytest.raises(K8sError):
            apply_manifest(state, yaml_bad)

    def test_sa_apply_and_pod_reference(self):
        """SA should be stored and Pod can reference it."""
        state = ClusterState()
        state = apply_manifest(state, VALID_SA)
        assert "app-sa" in state.serviceaccounts

        yaml_pod = """\
apiVersion: v1
kind: Pod
metadata:
  name: app-pod
spec:
  serviceAccountName: app-sa
  containers:
  - name: app
    image: busybox:1.36
"""
        state = apply_manifest(state, yaml_pod)
        assert "app-pod" in state.pods
        # Pod spec should reference the SA
        assert state.pods["app-pod"]["spec"]["serviceAccountName"] == "app-sa"

    def test_securityContext_stored_in_pod(self):
        """SecurityContext should be stored in the Pod spec."""
        state = ClusterState()
        state = apply_manifest(state, VALID_SECURE_POD)
        pod = state.pods["secure-pod"]
        sc = pod["spec"]["containers"][0]["securityContext"]
        assert sc["runAsNonRoot"] is True
        assert sc["readOnlyRootFilesystem"] is True
        assert sc["runAsUser"] == 1000

    def test_crd_scope_not_validated_by_simulator(self):
        # BUG: Simulator's _apply_crd does NOT validate spec.scope value.
        # A CRD with scope: "invalid" is stored without error.
        # SEVERITY: P2
        yaml_bad = VALID_CRD.replace("scope: Namespaced", "scope: InvalidScope")
        state = ClusterState()
        state = apply_manifest(state, yaml_bad)
        assert len(state.customresourcedefinitions) == 1, \
            "BUG: Simulator accepts invalid scope value"

    def test_multi_doc_crd_sa_deploy_order(self):
        """Multi-doc YAML: SA + Deployment order shouldn't matter for SA
        existence check in Q17.5 (apply processes all docs sequentially)."""
        yaml_sa_first = VALID_SA.replace("app-sa", "blog-operator-sa") + "---\n" + \
            VALID_CRD_NO_SCHEMA + "---\n" + VALID_OPERATOR_DEPLOY
        yaml_sa_first = yaml_sa_first.replace(
            "    spec:\n      containers:",
            "    spec:\n      serviceAccountName: blog-operator-sa\n      containers:"
        )
        r = _check("Q17.5", yaml_sa_first)
        assert r.ok, r.error

    def test_multi_doc_deploy_first_sa_last(self):
        """Deployment before SA in multi-doc - SA still exists when check runs."""
        yaml_deploy_first = VALID_CRD_NO_SCHEMA + "---\n" + \
            VALID_OPERATOR_DEPLOY + "---\n" + \
            VALID_SA.replace("app-sa", "blog-operator-sa")
        yaml_deploy_first = yaml_deploy_first.replace(
            "    spec:\n      containers:",
            "    spec:\n      serviceAccountName: blog-operator-sa\n      containers:"
        )
        r = _check("Q17.5", yaml_deploy_first)
        assert r.ok, r.error

    def test_crd_with_schema_stores_schema(self):
        """CRD with openAPIV3Schema should be stored with the schema."""
        state = ClusterState()
        state = apply_manifest(state, VALID_CRD)
        crd = state.customresourcedefinitions["blogs.blog.example.com"]
        versions = crd["spec"]["versions"]
        assert versions[0]["schema"]["openAPIV3Schema"]["type"] == "object"
