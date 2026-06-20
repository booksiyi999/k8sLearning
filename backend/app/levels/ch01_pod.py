"""Chapter 1: Pod 基础"""
from app.validator import Level, CheckResult
from app.simulator import apply_manifest, ClusterState, K8sError


def _check_01_create_pod(user_yaml: str) -> CheckResult:
    """Q1.1 创建第一个 Pod"""
    hints = []
    try:
        state = ClusterState()
        state = apply_manifest(state, user_yaml)
    except K8sError as e:
        return CheckResult(ok=False, error=str(e), hints=[])

    # 至少一个 Pod
    if not state.pods:
        return CheckResult(ok=False, error="没有创建任何 Pod", hints=["你需要 apply 一个 kind: Pod 的 YAML"])

    # 检查 Pod 必须字段
    for name, pod in state.pods.items():
        containers = pod.get("spec", {}).get("containers", [])
        if not containers:
            return CheckResult(ok=False, error=f"Pod {name} 没有 containers", hints=[])
        if not containers[0].get("image"):
            return CheckResult(ok=False, error=f"Pod {name} 的 container 缺少 image", hints=[])

    return CheckResult(ok=True, state=state, hints=["干得漂亮！第一个 Pod 已经起飞了 🚀"])


LEVEL_Q1_1 = Level(
    id="Q1.1",
    chapter="ch01",
    title="创建第一个 Pod",
    description="""
# 创建第一个 Pod

欢迎来到 k8s-quest！你的第一个任务：在 K8s 集群里创建一个运行 nginx 的 Pod。

## 要求

写一个 YAML，apply 后能产生一个：
- `kind: Pod`
- 名字叫 `nginx-pod`
- container 镜像是 `nginx:1.25`
""",
    starter_yaml="""\
apiVersion: v1
kind: Pod
metadata:
  name: nginx-pod
spec:
  containers:
    # 在这里补全 container 定义
""",
    check_fn=_check_01_create_pod,
)

CHAPTER_1_LEVELS = [LEVEL_Q1_1]
