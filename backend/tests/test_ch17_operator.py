"""Ch17 CRD & Operator 章节测试（10 关）

每关测试:
1. 正确 YAML 通过
2. 错误 YAML 失败
"""
import pytest
from app.validator import get_level, CheckResult


def _check(level_id, yaml_text):
    """Shortcut to run a level's check_fn."""
    return get_level(level_id).check_fn(yaml_text)


# =====================================================================
# Q17.1 创建 CRD - metadata.name 格式校验
# =====================================================================

VALID_Q171 = """\
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

INVALID_Q171_BAD_NAME = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: wrong-name
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

INVALID_Q171_MISSING_KIND = """\
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: blogs.blog.example.com
spec:
  group: blog.example.com
  names:
    plural: blogs
  scope: Namespaced
  versions:
  - name: v1
    served: true
    storage: true
"""


class TestQ171CreateCRD:
    def test_valid_passes(self):
        r = _check("Q17.1", VALID_Q171)
        assert r.ok, f"Valid CRD should pass: {r.error}"

    def test_bad_metadata_name_fails(self):
        r = _check("Q17.1", INVALID_Q171_BAD_NAME)
        assert not r.ok
        assert "metadata.name" in r.error.lower() or "格式" in r.error

    def test_missing_kind_fails(self):
        r = _check("Q17.1", INVALID_Q171_MISSING_KIND)
        assert not r.ok
        assert "kind" in r.error.lower()

    def test_empty_yaml_fails(self):
        r = _check("Q17.1", "")
        assert not r.ok

    def test_missing_group_fails(self):
        yaml_bad = VALID_Q171.replace("  group: blog.example.com\n", "")
        r = _check("Q17.1", yaml_bad)
        assert not r.ok
        assert "group" in r.error.lower()

    def test_missing_versions_fails(self):
        yaml_bad = VALID_Q171.replace(
            "  versions:\n  - name: v1\n    served: true\n    storage: true\n", ""
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok

    def test_name_plural_mismatch_fails(self):
        """metadata.name 的 plural 部分与 spec.names.plural 不一致"""
        yaml_bad = VALID_Q171.replace(
            "name: blogs.blog.example.com", "name: posts.blog.example.com"
        )
        r = _check("Q17.1", yaml_bad)
        assert not r.ok
        assert "格式" in r.error or "metadata.name" in r.error.lower()

    def test_scope_cluster_passes(self):
        yaml_cluster = VALID_Q171.replace("scope: Namespaced", "scope: Cluster")
        r = _check("Q17.1", yaml_cluster)
        assert r.ok


# =====================================================================
# Q17.2 CRD Schema 验证
# =====================================================================

VALID_Q172 = """\
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
            required: [title]
"""

INVALID_Q172_NO_SCHEMA = """\
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

INVALID_Q172_NO_PROPERTIES = """\
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
"""


class TestQ172CRDSchema:
    def test_valid_passes(self):
        r = _check("Q17.2", VALID_Q172)
        assert r.ok, f"Valid CRD with schema should pass: {r.error}"

    def test_no_schema_fails(self):
        r = _check("Q17.2", INVALID_Q172_NO_SCHEMA)
        assert not r.ok
        assert "schema" in r.error.lower()

    def test_no_properties_fails(self):
        r = _check("Q17.2", INVALID_Q172_NO_PROPERTIES)
        assert not r.ok
        assert "properties" in r.error.lower()

    def test_wrong_type_fails(self):
        yaml_bad = VALID_Q172.replace("type: object\n        properties:", "type: string\n        properties:")
        r = _check("Q17.2", yaml_bad)
        assert not r.ok
        assert "type" in r.error.lower()

    def test_empty_spec_properties_fails(self):
        yaml_bad = VALID_Q172.replace(
            "              title:\n                type: string\n            required: [title]",
            ""
        )
        r = _check("Q17.2", yaml_bad)
        assert not r.ok
        assert "properties" in r.error.lower()


# =====================================================================
# Q17.3 Operator RBAC - Role + RoleBinding
# =====================================================================

VALID_Q173 = """\
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

INVALID_Q173_NO_ROLE = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
subjects:
- kind: ServiceAccount
  name: blog-operator-sa
roleRef:
  kind: Role
  name: blog-operator-role
  apiGroup: rbac.authorization.k8s.io
"""

INVALID_Q173_EMPTY_RULES = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: blog-operator-role
rules: []
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
subjects:
- kind: ServiceAccount
  name: blog-operator-sa
roleRef:
  kind: Role
  name: blog-operator-role
  apiGroup: rbac.authorization.k8s.io
"""

INVALID_Q173_NO_SA_SUBJECT = """\
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: blog-operator-role
rules:
- apiGroups: ["blog.example.com"]
  resources: ["blogs"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: blog-operator-binding
subjects:
- kind: User
  name: admin
roleRef:
  kind: Role
  name: blog-operator-role
  apiGroup: rbac.authorization.k8s.io
"""


class TestQ173OperatorRBAC:
    def test_valid_passes(self):
        r = _check("Q17.3", VALID_Q173)
        assert r.ok, f"Valid Role+RoleBinding should pass: {r.error}"

    def test_no_role_fails(self):
        r = _check("Q17.3", INVALID_Q173_NO_ROLE)
        assert not r.ok
        assert "role" in r.error.lower()

    def test_no_rolebinding_fails(self):
        yaml_bad = VALID_Q173.split("---")[0]
        r = _check("Q17.3", yaml_bad)
        assert not r.ok
        assert "rolebinding" in r.error.lower()

    def test_empty_rules_fails(self):
        r = _check("Q17.3", INVALID_Q173_EMPTY_RULES)
        assert not r.ok
        assert "rules" in r.error.lower()

    def test_no_sa_subject_fails(self):
        r = _check("Q17.3", INVALID_Q173_NO_SA_SUBJECT)
        assert not r.ok
        assert "serviceaccount" in r.error.lower() or "subjects" in r.error.lower()

    def test_missing_verbs_fails(self):
        yaml_bad = VALID_Q173.replace(
            '  verbs: ["get", "list", "watch", "create", "update", "delete"]',
            ""
        )
        r = _check("Q17.3", yaml_bad)
        assert not r.ok
        assert "verbs" in r.error.lower()


# =====================================================================
# Q17.4 Status 子资源 + Deployment WATCH
# =====================================================================

VALID_Q174 = """\
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
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE
          value: ""
"""

INVALID_Q174_NO_SUBRESOURCES = """\
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
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE
          value: ""
"""

INVALID_Q174_NO_WATCH_ENV = """\
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
    subresources:
      status: {}
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
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
"""


class TestQ174StatusSubresource:
    def test_valid_passes(self):
        r = _check("Q17.4", VALID_Q174)
        assert r.ok, f"Valid CRD with status subresource + Deployment should pass: {r.error}"

    def test_no_subresources_fails(self):
        r = _check("Q17.4", INVALID_Q174_NO_SUBRESOURCES)
        assert not r.ok
        assert "subresources" in r.error.lower() or "status" in r.error.lower()

    def test_no_watch_env_fails(self):
        r = _check("Q17.4", INVALID_Q174_NO_WATCH_ENV)
        assert not r.ok
        assert "watch" in r.error.lower() or "subresources" in r.error.lower() or "status" in r.error.lower()

    def test_no_crd_fails(self):
        yaml_bad = VALID_Q174.split("---")[1]  # Only Deployment
        r = _check("Q17.4", yaml_bad)
        assert not r.ok

    def test_no_deployment_fails(self):
        # Only CRD part (split on first ---)
        parts = VALID_Q174.split("---", 1)
        r = _check("Q17.4", parts[0])
        assert not r.ok
        assert "deployment" in r.error.lower()


# =====================================================================
# Q17.5 Operator Deployment 完整校验
# =====================================================================

VALID_Q175 = """\
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
            required: [title]
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
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE
          value: ""
"""

INVALID_Q175_NO_SA = """\
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
      containers:
      - name: operator
        image: operator-sdk/example-operator:v1
        env:
        - name: WATCH_NAMESPACE
          value: ""
"""

INVALID_Q175_WRONG_REPLICAS = VALID_Q175.replace("  replicas: 1", "  replicas: 3")

INVALID_Q175_NO_SA_REF = VALID_Q175.replace(
    "      serviceAccountName: blog-operator-sa\n", ""
)

INVALID_Q175_NO_WATCH = VALID_Q175.replace(
    """        env:
        - name: WATCH_NAMESPACE
          value: ""\n""",
    ""
)


class TestQ175DeployOperator:
    def test_valid_passes(self):
        r = _check("Q17.5", VALID_Q175)
        assert r.ok, f"Valid operator stack should pass: {r.error}"

    def test_no_sa_fails(self):
        r = _check("Q17.5", INVALID_Q175_NO_SA)
        assert not r.ok
        assert "serviceaccount" in r.error.lower()

    def test_wrong_replicas_fails(self):
        r = _check("Q17.5", INVALID_Q175_WRONG_REPLICAS)
        assert not r.ok
        assert "replicas" in r.error.lower()

    def test_no_sa_ref_fails(self):
        r = _check("Q17.5", INVALID_Q175_NO_SA_REF)
        assert not r.ok
        assert "serviceaccount" in r.error.lower() or "serviceaccountname" in r.error.lower()

    def test_no_watch_env_fails(self):
        r = _check("Q17.5", INVALID_Q175_NO_WATCH)
        assert not r.ok
        assert "watch" in r.error.lower()

    def test_no_crd_fails(self):
        yaml_bad = VALID_Q175.split("---", 1)[1]  # Skip CRD
        r = _check("Q17.5", yaml_bad)
        assert not r.ok

    def test_sa_name_mismatch_fails(self):
        yaml_bad = VALID_Q175.replace(
            "      serviceAccountName: blog-operator-sa",
            "      serviceAccountName: wrong-sa",
        )
        r = _check("Q17.5", yaml_bad)
        assert not r.ok


# =====================================================================
# Q17.6 Reconcile 循环骨架 - YAML 结构校验
# =====================================================================

VALID_Q176 = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""

INVALID_Q176_NO_STATUS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
"""

INVALID_Q176_NO_CONDITIONS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
status:
  observedGeneration: 1
"""

INVALID_Q176_NO_OBSERVED_GEN = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
status:
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""

INVALID_Q176_CONDITION_MISSING_FIELD = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
"""

INVALID_Q176_EMPTY_CONDITIONS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: my-blog
spec:
  title: "Hello Blog"
status:
  observedGeneration: 1
  conditions: []
"""


class TestQ176ReconcileLoop:
    def test_valid_passes(self):
        r = _check("Q17.6", VALID_Q176)
        assert r.ok, f"Valid CR with status fields should pass: {r.error}"

    def test_no_status_fails(self):
        r = _check("Q17.6", INVALID_Q176_NO_STATUS)
        assert not r.ok
        assert "status" in r.error.lower()

    def test_no_conditions_fails(self):
        r = _check("Q17.6", INVALID_Q176_NO_CONDITIONS)
        assert not r.ok
        assert "conditions" in r.error.lower()

    def test_no_observed_generation_fails(self):
        r = _check("Q17.6", INVALID_Q176_NO_OBSERVED_GEN)
        assert not r.ok
        assert "observedgeneration" in r.error.lower()

    def test_condition_missing_field_fails(self):
        r = _check("Q17.6", INVALID_Q176_CONDITION_MISSING_FIELD)
        assert not r.ok
        assert "lasttransitiontime" in r.error.lower()

    def test_empty_conditions_fails(self):
        r = _check("Q17.6", INVALID_Q176_EMPTY_CONDITIONS)
        assert not r.ok

    def test_empty_yaml_fails(self):
        r = _check("Q17.6", "")
        assert not r.ok

    def test_keyword_only_text_fails(self):
        """关键词文本不应通过（不再是关键词匹配）"""
        r = _check("Q17.6", "The operator will watch and compare things.")
        assert not r.ok


# =====================================================================
# Q17.7 OwnerReference 与级联删除
# =====================================================================

VALID_Q177 = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: owned-blog
  ownerReferences:
  - apiVersion: apps/v1
    kind: Deployment
    name: blog-operator
    uid: abc-123-def-456
    controller: true
spec:
  title: "Owned Blog"
"""

INVALID_Q177_NO_UID = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: owned-blog
  ownerReferences:
  - apiVersion: apps/v1
    kind: Deployment
    name: blog-operator
spec:
  title: "Owned Blog"
"""

INVALID_Q177_NO_OWNER_REFS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: owned-blog
spec:
  title: "Owned Blog"
"""


class TestQ177OwnerReference:
    def test_valid_passes(self):
        r = _check("Q17.7", VALID_Q177)
        assert r.ok, f"Valid ownerReferences should pass: {r.error}"

    def test_missing_uid_fails(self):
        r = _check("Q17.7", INVALID_Q177_NO_UID)
        assert not r.ok
        assert "uid" in r.error.lower()

    def test_no_owner_refs_fails(self):
        r = _check("Q17.7", INVALID_Q177_NO_OWNER_REFS)
        assert not r.ok

    def test_empty_owner_refs_fails(self):
        yaml_bad = VALID_Q177.replace(
            "  - apiVersion: apps/v1\n    kind: Deployment\n    name: blog-operator\n    uid: abc-123-def-456\n    controller: true",
            ""
        )
        r = _check("Q17.7", yaml_bad)
        assert not r.ok

    def test_missing_kind_fails(self):
        yaml_bad = VALID_Q177.replace("    kind: Deployment\n", "")
        r = _check("Q17.7", yaml_bad)
        assert not r.ok
        assert "kind" in r.error.lower()

    def test_missing_name_fails(self):
        yaml_bad = VALID_Q177.replace("    name: blog-operator\n", "")
        r = _check("Q17.7", yaml_bad)
        assert not r.ok
        assert "name" in r.error.lower()

    def test_empty_apiversion_fails(self):
        """apiVersion 为空字符串应失败"""
        yaml_bad = VALID_Q177.replace("  - apiVersion: apps/v1", '  - apiVersion: ""')
        r = _check("Q17.7", yaml_bad)
        assert not r.ok
        assert "apiversion" in r.error.lower()

    def test_empty_name_fails(self):
        """name 为空字符串应失败"""
        yaml_bad = VALID_Q177.replace("    name: blog-operator", '    name: ""')
        r = _check("Q17.7", yaml_bad)
        assert not r.ok
        assert "name" in r.error.lower()


# =====================================================================
# Q17.8 Finalizer 概念
# =====================================================================

VALID_Q178 = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: protected-blog
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Protected Blog"
"""

INVALID_Q178_NO_FINALIZERS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: protected-blog
spec:
  title: "Protected Blog"
"""

INVALID_Q178_EMPTY_FINALIZERS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: protected-blog
  finalizers: []
spec:
  title: "Protected Blog"
"""


class TestQ178Finalizer:
    def test_valid_passes(self):
        r = _check("Q17.8", VALID_Q178)
        assert r.ok, f"Valid finalizers should pass: {r.error}"

    def test_no_finalizers_fails(self):
        r = _check("Q17.8", INVALID_Q178_NO_FINALIZERS)
        assert not r.ok

    def test_empty_finalizers_fails(self):
        r = _check("Q17.8", INVALID_Q178_EMPTY_FINALIZERS)
        assert not r.ok

    def test_multiple_finalizers_passes(self):
        yaml_good = VALID_Q178.replace(
            "  - blog.example.com/cleanup",
            "  - blog.example.com/cleanup\n  - blog.example.com/notify",
        )
        r = _check("Q17.8", yaml_good)
        assert r.ok

    def test_empty_string_finalizer_fails(self):
        yaml_bad = VALID_Q178.replace(
            "  - blog.example.com/cleanup", '  - ""'
        )
        r = _check("Q17.8", yaml_bad)
        assert not r.ok

    def test_finalizer_without_slash_fails(self):
        """finalizer 名称不包含 '/' 应失败"""
        yaml_bad = VALID_Q178.replace(
            "  - blog.example.com/cleanup", "  - cleanup"
        )
        r = _check("Q17.8", yaml_bad)
        assert not r.ok
        assert "/" in r.error or "格式" in r.error

    def test_finalizer_string_not_list_fails(self):
        """finalizers 是单个字符串而非列表应失败"""
        yaml_bad = VALID_Q178.replace(
            "  finalizers:\n  - blog.example.com/cleanup",
            '  finalizers: blog.example.com/cleanup'
        )
        r = _check("Q17.8", yaml_bad)
        assert not r.ok


# =====================================================================
# Q17.9 Conditions 状态管理
# =====================================================================

VALID_Q179 = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
status:
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: DeploymentReady
    message: "Blog deployment is running"
"""

INVALID_Q179_NO_CONDITIONS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
status: {}
"""

INVALID_Q179_MISSING_TYPE = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
status:
  conditions:
  - status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
"""

INVALID_Q179_MISSING_LAST_TRANSITION = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
status:
  conditions:
  - type: Ready
    status: "True"
"""

INVALID_Q179_EMPTY_CONDITIONS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: status-blog
spec:
  title: "Status Blog"
status:
  conditions: []
"""


class TestQ179Conditions:
    def test_valid_passes(self):
        r = _check("Q17.9", VALID_Q179)
        assert r.ok, f"Valid conditions should pass: {r.error}"

    def test_no_conditions_fails(self):
        r = _check("Q17.9", INVALID_Q179_NO_CONDITIONS)
        assert not r.ok

    def test_missing_type_fails(self):
        r = _check("Q17.9", INVALID_Q179_MISSING_TYPE)
        assert not r.ok
        assert "type" in r.error.lower()

    def test_missing_last_transition_fails(self):
        r = _check("Q17.9", INVALID_Q179_MISSING_LAST_TRANSITION)
        assert not r.ok
        assert "lasttransitiontime" in r.error.lower()

    def test_empty_conditions_fails(self):
        r = _check("Q17.9", INVALID_Q179_EMPTY_CONDITIONS)
        assert not r.ok

    def test_multiple_conditions_passes(self):
        yaml_good = VALID_Q179.replace(
            '    message: "Blog deployment is running"',
            '    message: "Blog deployment is running"\n'
            '  - type: Available\n'
            '    status: "True"\n'
            '    lastTransitionTime: "2024-01-01T00:00:00Z"\n'
            '    reason: ServiceAvailable',
        )
        r = _check("Q17.9", yaml_good)
        assert r.ok

    def test_missing_status_fails(self):
        yaml_bad = VALID_Q179.replace('    status: "True"\n', "")
        r = _check("Q17.9", yaml_bad)
        assert not r.ok
        assert "status" in r.error.lower()

    def test_invalid_status_lowercase_fails(self):
        """status 为小写 'true' 应失败"""
        yaml_bad = VALID_Q179.replace('status: "True"', 'status: "true"')
        r = _check("Q17.9", yaml_bad)
        assert not r.ok
        assert "status" in r.error.lower()

    def test_invalid_status_value_fails(self):
        """status 不是 True/False/Unknown 应失败"""
        yaml_bad = VALID_Q179.replace('status: "True"', 'status: "Running"')
        r = _check("Q17.9", yaml_bad)
        assert not r.ok
        assert "status" in r.error.lower()

    def test_status_unknown_passes(self):
        """status 为 'Unknown' 应通过"""
        yaml_good = VALID_Q179.replace('status: "True"', 'status: "Unknown"')
        r = _check("Q17.9", yaml_good)
        assert r.ok

    def test_missing_reason_fails(self):
        """缺少 reason 字段应失败"""
        yaml_bad = VALID_Q179.replace("    reason: DeploymentReady\n", "")
        r = _check("Q17.9", yaml_bad)
        assert not r.ok
        assert "reason" in r.error.lower()

    def test_empty_type_fails(self):
        """type 为空字符串应失败"""
        yaml_bad = VALID_Q179.replace("type: Ready", 'type: ""')
        r = _check("Q17.9", yaml_bad)
        assert not r.ok
        assert "type" in r.error.lower()


# =====================================================================
# Q17.10 Operator 最佳实践总结 - YAML 综合校验
# =====================================================================

VALID_Q1710_ALL = """\
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
    reason: DeploymentReady
    message: "Blog deployment is running"
"""

INVALID_Q1710_NO_SPEC = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  ownerReferences:
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def
  finalizers:
  - blog.example.com/cleanup
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: DeploymentReady
"""

INVALID_Q1710_NO_STATUS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  ownerReferences:
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Best Practice Blog"
"""

INVALID_Q1710_NO_OWNER_REFS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Best Practice Blog"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: DeploymentReady
"""

INVALID_Q1710_NO_FINALIZERS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  ownerReferences:
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def
spec:
  title: "Best Practice Blog"
status:
  observedGeneration: 1
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2024-01-01T00:00:00Z"
    reason: DeploymentReady
"""

INVALID_Q1710_NO_CONDITIONS = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: best-practice-blog
  ownerReferences:
  - apiVersion: blog.example.com/v1
    kind: Blog
    name: parent-blog
    uid: abc-123-def
  finalizers:
  - blog.example.com/cleanup
spec:
  title: "Best Practice Blog"
status:
  observedGeneration: 1
"""

INVALID_Q1710_MINIMAL = """\
apiVersion: blog.example.com/v1
kind: Blog
metadata:
  name: minimal-blog
spec:
  title: "Minimal Blog"
"""


class TestQ1710BestPractices:
    def test_all_fields_passes(self):
        r = _check("Q17.10", VALID_Q1710_ALL)
        assert r.ok, f"CR with all best practice fields should pass: {r.error}"

    def test_no_spec_fails(self):
        r = _check("Q17.10", INVALID_Q1710_NO_SPEC)
        assert not r.ok
        assert "spec" in r.error.lower()

    def test_no_status_fails(self):
        r = _check("Q17.10", INVALID_Q1710_NO_STATUS)
        assert not r.ok
        assert "status" in r.error.lower()

    def test_no_owner_refs_fails(self):
        r = _check("Q17.10", INVALID_Q1710_NO_OWNER_REFS)
        assert not r.ok
        assert "ownerreferences" in r.error.lower()

    def test_no_finalizers_fails(self):
        r = _check("Q17.10", INVALID_Q1710_NO_FINALIZERS)
        assert not r.ok
        assert "finalizers" in r.error.lower()

    def test_no_conditions_fails(self):
        r = _check("Q17.10", INVALID_Q1710_NO_CONDITIONS)
        assert not r.ok
        assert "conditions" in r.error.lower()

    def test_minimal_cr_fails(self):
        r = _check("Q17.10", INVALID_Q1710_MINIMAL)
        assert not r.ok

    def test_empty_fails(self):
        r = _check("Q17.10", "")
        assert not r.ok

    def test_keyword_text_fails(self):
        """关键词文本不应通过（不再是关键词匹配）"""
        text = (
            "Operator should be 幂等 meaning reconcile produces the same result. "
            "Errors trigger a requeue for retry. "
            "Use finalizer for cleanup before deletion."
        )
        r = _check("Q17.10", text)
        assert not r.ok


# =====================================================================
# 章节完整性测试
# =====================================================================

class TestChapter17Integrity:
    """测试章节完整性"""

    def test_chapter_has_10_levels(self):
        from app.validator import list_levels
        levels = list_levels("ch17")
        assert len(levels) == 10, f"Ch17 should have 10 levels, got {len(levels)}"

    def test_all_level_ids_present(self):
        from app.validator import list_levels
        levels = list_levels("ch17")
        ids = [lv["id"] for lv in levels]
        expected = [f"Q17.{i}" for i in range(1, 11)]
        assert ids == expected, f"Level IDs mismatch: {ids} vs {expected}"

    def test_all_levels_have_lessons(self):
        from app.validator import get_level
        for i in range(1, 11):
            lv = get_level(f"Q17.{i}")
            assert lv is not None, f"Q17.{i} not found"
            assert lv.lesson is not None, f"Q17.{i} has no lesson"
            assert lv.lesson.concept, f"Q17.{i} lesson has no concept"
            assert lv.lesson.key_fields, f"Q17.{i} lesson has no key_fields"
            assert lv.lesson.diagram, f"Q17.{i} lesson has no diagram"
            assert lv.lesson.example_yaml, f"Q17.{i} lesson has no example_yaml"
            assert lv.lesson.common_errors, f"Q17.{i} lesson has no common_errors"
            assert lv.lesson.tips, f"Q17.{i} lesson has no tips"

    def test_all_levels_have_knowledge_points(self):
        from app.metadata import KNOWLEDGE_POINTS
        for i in range(1, 11):
            lid = f"Q17.{i}"
            assert lid in KNOWLEDGE_POINTS, f"{lid} missing from KNOWLEDGE_POINTS"
            assert len(KNOWLEDGE_POINTS[lid]) > 0, f"{lid} has empty knowledge points"

    def test_all_levels_have_xp(self):
        from app.metadata import LEVEL_XP
        for i in range(1, 11):
            lid = f"Q17.{i}"
            assert lid in LEVEL_XP, f"{lid} missing from LEVEL_XP"
            assert LEVEL_XP[lid] == 10, f"{lid} XP should be 10"
