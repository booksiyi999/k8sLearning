#!/bin/bash
# k8s-quest 一键部署脚本（openEuler + K8s/K3s）
# 基于实战踩坑总结，自动适配 k8s / k3s，自动选择镜像导入方式。
#
# 用法:
#   bash deploy/deploy.sh          # 首次部署
#   bash deploy/deploy.sh --rebuild # 代码更新后重新构建+部署
#
# 访问（部署成功后）:
#   kubectl -n k8s-quest port-forward svc/k8s-quest 18000:8000 --address=127.0.0.1
#   浏览器: http://localhost:18000

set -e

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"

echo "=========================================="
echo "  k8s-quest 一键部署"
echo "=========================================="

# ── 步骤 1: 检查环境 ──
echo ""
echo "[1/7] 检查环境..."

for cmd in podman kubectl; do
    if ! command -v $cmd &>/dev/null; then
        echo "  ✗ 未安装 $cmd，请先安装:"
        echo "    sudo dnf install -y podman" 
        echo "    （kubectl 由 K8s/K3s 自带）"
        exit 1
    fi
done
echo "  ✓ podman、kubectl 就绪"

# ── 步骤 2: 自动识别 k8s 还是 k3s ──
echo ""
echo "[2/7] 识别集群类型..."

CTR_CMD=""
CRICTL_CMD=""
CLUSTER_TYPE=""

if command -v k3s &>/dev/null; then
    CLUSTER_TYPE="k3s"
    CTR_CMD="sudo k3s ctr"
    CRICTL_CMD="sudo k3s crictl"
    echo "  ✓ 检测到 k3s（用 k3s ctr / k3s crictl）"
else
    CLUSTER_TYPE="k8s"
    CTR_CMD="sudo ctr -n k8s.io"
    CRICTL_CMD="sudo crictl"
    echo "  ✓ 检测到标准 k8s（用 ctr -n k8s.io / crictl）"
fi

# ── 步骤 3: 获取节点名 ──
echo ""
echo "[3/7] 获取集群节点信息..."

NODES=$(kubectl get nodes -o name | sed 's|node/||' | head -20)
NODE_COUNT=$(echo "$NODES" | wc -l)
FIRST_NODE=$(echo "$NODES" | head -1)

echo "  集群节点: "
echo "$NODES" | sed 's/^/    - /'
echo "  节点数: $NODE_COUNT"
echo "  首选节点: $FIRST_NODE"

if [ -z "$FIRST_NODE" ]; then
    echo "  ✗ 未找到任何节点，请检查 K8s 集群状态"
    exit 1
fi

# ── 步骤 4: 构建镜像 ──
echo ""
echo "[4/7] 构建镜像..."

if [ "$1" = "--rebuild" ] || ! podman images --format '{{.Names}}' | grep -q 'k8s-quest:v2'; then
    echo "  构建中（--no-cache 确保用最新代码）..."
    podman build --no-cache -t k8s-quest:v2 -f Dockerfile .
    echo "  ✓ 镜像构建完成"
else
    echo "  ✓ 镜像已存在（用 --rebuild 强制重建）"
fi

# ── 步骤 5: 导入镜像到 containerd ──
echo ""
echo "[5/7] 导入镜像到容器运行时..."

echo "  导出镜像 tar..."
podman save k8s-quest:v2 -o /tmp/k8s-quest.tar

echo "  导入到 containerd（${CLUSTER_TYPE}）..."
$CTR_CMD images import /tmp/k8s-quest.tar
rm -f /tmp/k8s-quest.tar

echo "  打标签 k8s-quest:v2（避免 CRI 归一化不匹配）..."
$CTR_CMD images tag --force localhost/k8s-quest:v2 k8s-quest:v2 2>/dev/null || true

echo "  确认 CRI 能看到镜像..."
$CRICTL_CMD images | grep 'k8s-quest' && echo "  ✓ CRI 已识别镜像" || echo "  ✗ 镜像导入失败"

# ── 步骤 6: 部署 ──
echo ""
echo "[6/7] 部署到 K8s..."

kubectl apply -f deploy/k8s-quest.yaml

# 注入 nodeName（单节点直接填，多节点填首个）
echo "  注入 nodeName: $FIRST_NODE ..."
kubectl -n k8s-quest patch deploy k8s-quest --type=json \
    -p="[{\"op\":\"add\",\"path\":\"/spec/template/spec/nodeName\",\"value\":\"${FIRST_NODE}\"}]" 2>/dev/null || true

# 确保镜像名是 k8s-quest:v2（去掉 localhost/ 前缀，避免 CRI 归一化问题）
kubectl -n k8s-quest patch deploy k8s-quest --type=json \
    -p='[{"op":"replace","path":"/spec/template/spec/containers/0/image","value":"k8s-quest:v2"}]' 2>/dev/null || true

# ── 步骤 7: 等待 Running ──
echo ""
echo "[7/7] 等待 Pod 启动..."
echo "  （实时状态如下，Running 后 Ctrl+C 即可）"

kubectl -n k8s-quest get pod -w
