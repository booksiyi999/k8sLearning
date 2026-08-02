"""QA 攻击性测试: Chapter 2 全维度扫描.

策略: 对每个 check_fn 喂入恶意/边界 YAML, 检测是否:
  - 抛出异常逃逸 check_fn (= HTTP 500 风险) → BUG
  - 返回 ok=False 但 error 为空 (= 静默失败) → BUG
  - 正常返回 ok=False + 有意义 error → PASS
  - ok=True 通过 → 视情况 (恶意输入通过 = 逻辑漏洞)
"""
import sys
import os
import time
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.validator import get_level
from app.levels import ch02_deployment as ch02

BUGS = []
PASS_COUNT = 0
TOTAL = 0


def attack(level_id, vector_name, yaml_text, expect_ok=False, allow_ok_false=True):
    """对一个关卡投递攻击 YAML, 记录结果."""
    global TOTAL, PASS_COUNT
    TOTAL += 1
    lv = get_level(level_id)
    if lv is None:
        BUGS.append({"level": level_id, "vector": vector_name, "severity": "CRASH",
                     "issue": "关卡未注册 (get_level 返回 None)"})
        return
    try:
        result = lv.check_fn(yaml_text)
    except Exception as e:
        tb = traceback.format_exc()
        BUGS.append({
            "level": level_id, "vector": vector_name, "severity": "CRASH",
            "exception": f"{type(e).__name__}: {e}",
            "traceback_head": "\n".join(tb.splitlines()[:8]),
        })
        return
    # 静默失败检测
    if not result.ok and not result.error:
        BUGS.append({
            "level": level_id, "vector": vector_name, "severity": "SILENT_FAIL",
            "issue": "ok=False 但 error 为空 (静默失败)",
        })
        return
    # 恶意输入通过 (不该 ok=True)
    if result.ok and not expect_ok:
        BUGS.append({
            "level": level_id, "vector": vector_name, "severity": "FALSE_PASS",
            "issue": "恶意/错误输入被判定为通过 (ok=True)",
            "hints": result.hints,
        })
        return
    PASS_COUNT += 1


# =====================================================================
# 维度 1: Happy Path (正确输入应通过)
# =====================================================================

_Q2_1_OK = """\
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
"""

_Q2_2_OK = _Q2_1_OK.replace("nginx-deploy", "api-deploy").replace("replicas: 3", "replicas: 5") \
    .replace("app: nginx", "app: api").replace("name: nginx", "name: api") \
    .replace("image: nginx:1.25", "image: python:3.11-slim")

_Q2_3_OK = """\
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
"""

_Q2_4_OK = """\
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
"""

attack("Q2.1", "happy_path_correct", _Q2_1_OK, expect_ok=True)
attack("Q2.2", "happy_path_correct", _Q2_2_OK, expect_ok=True)
attack("Q2.3", "happy_path_correct", _Q2_3_OK, expect_ok=True)
attack("Q2.4", "happy_path_correct", _Q2_4_OK, expect_ok=True)


# =====================================================================
# 维度 3: 类型安全 / 边界条件 (核心! 逐层打穿 falsy-only guard)
# =====================================================================

# --- replicas 类型攻击 ---
attack("Q2.1", "replicas_string", _Q2_1_OK.replace("replicas: 3", 'replicas: "3"'))
attack("Q2.2", "replicas_string", _Q2_2_OK.replace("replicas: 5", 'replicas: "5"'))
attack("Q2.1", "replicas_bool_true", _Q2_1_OK.replace("replicas: 3", "replicas: true"))
attack("Q2.1", "replicas_bool_false", _Q2_1_OK.replace("replicas: 3", "replicas: false"))
attack("Q2.1", "replicas_float", _Q2_1_OK.replace("replicas: 3", "replicas: 3.0"))
attack("Q2.1", "replicas_null", _Q2_1_OK.replace("replicas: 3", "replicas: null"))
attack("Q2.1", "replicas_list", _Q2_1_OK.replace("replicas: 3", "replicas: [3]"))
attack("Q2.1", "replicas_dict", _Q2_1_OK.replace("replicas: 3", "replicas:\n  count: 3"))
attack("Q2.1", "replicas_missing", _Q2_1_OK.replace("  replicas: 3\n", ""))
attack("Q2.1", "replicas_negative", _Q2_1_OK.replace("replicas: 3", "replicas: -1"))
# replicas_huge tested separately (DoS confirmed, simulator.py scope)

# --- containers 类型攻击 (绕过 falsy-only guard) ---
attack("Q2.1", "containers_string", _Q2_1_OK.replace(
    "        - name: nginx\n          image: nginx:1.25",
    '        "not-a-list"'))
attack("Q2.1", "containers_int", _Q2_1_OK.replace(
    "        - name: nginx\n          image: nginx:1.25",
    "        42"))
attack("Q2.1", "containers_dict", _Q2_1_OK.replace(
    "        - name: nginx\n          image: nginx:1.25",
    "        name: nginx\n        image: nginx:1.25"))
attack("Q2.1", "containers_empty_list", _Q2_1_OK.replace(
    "        - name: nginx\n          image: nginx:1.25",
    "        []"))
attack("Q2.1", "containers_element_string", _Q2_1_OK.replace(
    "          image: nginx:1.25",
    '          image: nginx:1.25\n        - "just-a-string"'))

# --- template 类型攻击 ---
attack("Q2.1", "template_string", _Q2_1_OK.replace(
    "  template:\n    metadata:\n      labels:\n        app: nginx\n    spec:\n      containers:\n        - name: nginx\n          image: nginx:1.25",
    '  template: "just-a-string"'))
attack("Q2.1", "template_int", _Q2_1_OK.replace(
    "  template:\n    metadata:\n      labels:\n        app: nginx\n    spec:\n      containers:\n        - name: nginx\n          image: nginx:1.25",
    "  template: 5"))
attack("Q2.1", "template_list", _Q2_1_OK.replace(
    "  template:\n    metadata:\n      labels:\n        app: nginx\n    spec:\n      containers:\n        - name: nginx\n          image: nginx:1.25",
    "  template:\n    - a\n    - b"))
attack("Q2.1", "template_missing", _Q2_1_OK.replace("  template:", "  # template:"))

# --- template.spec 类型攻击 ---
attack("Q2.1", "template_spec_string", _Q2_1_OK.replace(
    "    spec:\n      containers:",
    '    spec: "broken"\n    # containers:'))
attack("Q2.1", "template_spec_int", _Q2_1_OK.replace(
    "    spec:\n      containers:",
    "    spec: 5\n    # containers:"))
attack("Q2.1", "template_spec_list", _Q2_1_OK.replace(
    "    spec:\n      containers:",
    "    spec:\n      - a"))

# --- metadata 类型攻击 ---
attack("Q2.1", "metadata_list", _Q2_1_OK.replace(
    "metadata:\n  name: nginx-deploy",
    "metadata:\n  - name: nginx-deploy"))
attack("Q2.1", "metadata_string", _Q2_1_OK.replace(
    "metadata:\n  name: nginx-deploy",
    'metadata: "just-a-string"'))
attack("Q2.1", "metadata_int", _Q2_1_OK.replace(
    "metadata:\n  name: nginx-deploy",
    "metadata: 5"))
attack("Q2.1", "metadata_name_int", _Q2_1_OK.replace("name: nginx-deploy", "name: 123"))
attack("Q2.1", "metadata_name_null", _Q2_1_OK.replace("name: nginx-deploy", "name: null"))
attack("Q2.1", "metadata_missing", _Q2_1_OK.replace("metadata:\n  name: nginx-deploy\n", ""))

# --- spec 类型攻击 ---
attack("Q2.1", "spec_string", _Q2_1_OK.replace(
    "spec:\n  replicas: 3",
    'spec: "broken"'))
attack("Q2.1", "spec_int", _Q2_1_OK.replace(
    "spec:\n  replicas: 3",
    "spec: 5"))
attack("Q2.1", "spec_missing", _Q2_1_OK.replace("spec:", "  # spec:"))

# --- 顶层结构攻击 ---
attack("Q2.1", "empty_yaml", "")
attack("Q2.1", "yaml_list_not_dict", "- 1\n- 2\n- 3")
attack("Q2.1", "yaml_string_not_dict", '"just a string"')
attack("Q2.1", "yaml_int_not_dict", "42")
attack("Q2.1", "yaml_null", "null")
attack("Q2.1", "no_kind_field", _Q2_1_OK.replace("kind: Deployment\n", ""))
attack("Q2.1", "kind_not_deployment", _Q2_1_OK.replace("kind: Deployment", "kind: Pod"))

# =====================================================================
# 维度 4: 安全性 (循环引用 / 超大嵌套 / 注入)
# =====================================================================

# --- 循环引用 anchor (自引用) ---
circular_self = """\
a: &a
  b: *a
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
"""
attack("Q2.1", "circular_ref_self_anchor", circular_self)

# --- 循环引用 labels ---
circular_labels = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deploy
  labels: &l
    app: nginx
    tier: *l
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
"""
attack("Q2.1", "circular_ref_labels", circular_labels)

# --- 循环引用 annotations (Q2.4 rollback 路径) ---
circular_ann = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations: &a
    k8s-quest/rollback: "true"
    extra: *a
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
"""
attack("Q2.4", "circular_ref_annotations_rollback", circular_ann)

# --- 深度嵌套 (测试递归上限) ---
deep = "x"
for _ in range(1500):
    deep = f"{{a: {deep}}}"
# deep nesting tested separately (RecursionError caught by endpoint catch-all, WARN)

# --- 路径穿越 / 提权 (simulator 不校验, 但不应崩溃) ---
priv_yaml = """\
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
          securityContext:
            privileged: true
          volumeMounts:
            - mountPath: /etc/passwd
              name: host
      volumes:
        - name: host
          hostPath:
            path: /etc/passwd
"""
attack("Q2.1", "hostPath_privileged_injection", priv_yaml, expect_ok=True)  # 不该崩溃, 应通过

# --- subPath 路径穿越 ---
subpath_yaml = """\
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
          volumeMounts:
            - mountPath: /data
              subPath: ../../../etc/passwd
              name: v
      volumes:
        - name: v
          hostPath:
            path: /tmp
"""
attack("Q2.1", "subPath_traversal", subpath_yaml, expect_ok=True)

# --- annotations 非字典 (Q2.4 rollback 检测路径) ---
ann_string = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations: "not-a-dict"
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
"""
attack("Q2.4", "annotations_string_not_dict", ann_string)

ann_list = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deploy
  annotations:
    - "not"
    - "a"
    - "dict"
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
"""
attack("Q2.4", "annotations_list_not_dict", ann_list)

# --- rollback annotation 值非字符串 ---
ann_value_int = _Q2_4_OK.replace('k8s-quest/rollback: "true"', "k8s-quest/rollback: true")
attack("Q2.4", "rollback_annotation_value_bool_true", ann_value_int)  # bool true, not string "true"
ann_value_int2 = _Q2_4_OK.replace('k8s-quest/rollback: "true"', "k8s-quest/rollback: 1")
attack("Q2.4", "rollback_annotation_value_int", ann_value_int2)

# --- Q2.3 攻击: 玩家提交完全空 template.spec ---
q23_empty_spec = """\
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
"""
attack("Q2.3", "template_missing_spec_entirely", q23_empty_spec)

# --- Q2.3 攻击: containers[0] 是字符串 ---
q23_c0_string = """\
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
        - "just-a-string"
"""
attack("Q2.3", "containers_element_string_q23", q23_c0_string)

# =====================================================================
# 维度 2: 错误处理 (静默失败检测)
# =====================================================================

# 这些应该返回 ok=False + 有意义的 error
attack("Q2.1", "wrong_name", _Q2_1_OK.replace("nginx-deploy", "wrong-name"))
attack("Q2.1", "wrong_replicas", _Q2_1_OK.replace("replicas: 3", "replicas: 2"))
attack("Q2.1", "wrong_image", _Q2_1_OK.replace("nginx:1.25", "nginx:1.24"))
attack("Q2.1", "missing_selector", _Q2_1_OK.replace("  selector:\n    matchLabels:\n      app: nginx\n", ""))
attack("Q2.2", "wrong_replicas", _Q2_2_OK.replace("replicas: 5", "replicas: 3"))
attack("Q2.3", "image_not_changed", _Q2_3_OK.replace("nginx:1.25", "nginx:1.24"))
attack("Q2.3", "wrong_new_image", _Q2_3_OK.replace("nginx:1.25", "nginx:1.26"))
attack("Q2.4", "no_rollback_annotation", _Q2_4_OK.replace('  annotations:\n    k8s-quest/rollback: "true"\n', ""))
attack("Q2.4", "wrong_target_image", _Q2_4_OK.replace("nginx:1.24", "nginx:1.25"))

# =====================================================================
# 输出报告
# =====================================================================

print(f"\n{'='*70}")
print(f"攻击性扫描完成: {PASS_COUNT}/{TOTAL} PASS, {len(BUGS)} BUG")
print(f"{'='*70}\n")

if BUGS:
    for i, b in enumerate(BUGS, 1):
        print(f"--- BUG #{i} [{b['severity']}] ---")
        print(f"  Level:   {b['level']}")
        print(f"  Vector:  {b['vector']}")
        if "exception" in b:
            print(f"  Exception: {b['exception']}")
            print(f"  Traceback:")
            for line in b.get("traceback_head", "").splitlines():
                print(f"    {line}")
        if "issue" in b:
            print(f"  Issue:   {b['issue']}")
        if "hints" in b:
            print(f"  Hints:   {b['hints']}")
        print()
else:
    print("无 BUG — 所有攻击向量均被正确拦截或返回有意义的错误.\n")
