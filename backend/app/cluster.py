"""真实 K8s 集群连接模块。

通过 subprocess 调用 kubectl 实现，不引入 python-kubernetes。
启用条件：环境变量 K8S_QUEST_MODE=cluster 且 KUBECONFIG 指向有效文件。
无 kubeconfig 或 kubectl 不可用时自动回退到模拟器模式。
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess

logger = logging.getLogger(__name__)

#: 所有 kubectl 调用的超时秒数
KUBECTL_TIMEOUT = 30

#: 默认 namespace
DEFAULT_NAMESPACE = "default"

#: kubectl 二进制名称
KUBECTL_BIN = "kubectl"


class ClusterManager:
    """管理与真实 K8s 集群的交互。

    通过 subprocess 调用 kubectl 命令行工具完成所有操作。
    当 kubectl 不可用或未配置 kubeconfig 时，自动回退到模拟器模式
    （所有方法返回安全的空值 / 错误信息，不抛异常）。
    """

    def __init__(self, kubeconfig_path: str | None = None):
        """初始化 ClusterManager。

        Args:
            kubeconfig_path: kubeconfig 文件路径。为 None 时读取 KUBECONFIG 环境变量。
        """
        # 确定 kubeconfig 路径：显式传入 > 环境变量 > 默认位置
        if kubeconfig_path is not None:
            self.kubeconfig_path: str | None = kubeconfig_path
        else:
            self.kubeconfig_path = os.environ.get("KUBECONFIG")

        # 检查 kubectl 是否在 PATH 中
        self._kubectl_available: bool = shutil.which(KUBECTL_BIN) is not None

        # 读取运行模式
        self._mode_env: str = os.environ.get("K8S_QUEST_MODE", "simulator")

        # namespace
        self.namespace: str = os.environ.get(
            "K8S_QUEST_NAMESPACE", DEFAULT_NAMESPACE
        )

    # ------------------------------------------------------------------
    # 状态属性
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        """是否启用真实集群模式。

        需要同时满足：
        1. K8S_QUEST_MODE=cluster
        2. kubectl 在 PATH 中
        3. kubeconfig 文件存在（显式路径或 ~/.kube/config）
        """
        if self._mode_env != "cluster":
            return False
        if not self._kubectl_available:
            return False

        # 检查 kubeconfig 文件是否存在
        if self.kubeconfig_path:
            return os.path.isfile(self.kubeconfig_path)
        # 没有显式 kubeconfig，检查默认位置
        default_config = os.path.expanduser("~/.kube/config")
        return os.path.isfile(default_config)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _build_cmd(self, *args: str) -> list[str]:
        """构建 kubectl 命令，附加 --kubeconfig 和 -n 参数。"""
        cmd: list[str] = [KUBECTL_BIN]
        if self.kubeconfig_path:
            cmd.extend(["--kubeconfig", self.kubeconfig_path])
        cmd.extend(["-n", self.namespace])
        cmd.extend(args)
        return cmd

    def _run_sync(
        self, cmd: list[str], stdin_input: str | None = None
    ) -> tuple[int, str, str]:
        """同步执行命令，返回 (returncode, stdout, stderr)。

        所有异常都被捕获并转为返回值，不抛出。
        """
        try:
            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=KUBECTL_TIMEOUT,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", f"命令超时（{KUBECTL_TIMEOUT}s）: {' '.join(cmd)}"
        except FileNotFoundError:
            return -1, "", "kubectl 未安装或不在 PATH 中"
        except PermissionError:
            return -1, "", "kubectl 无执行权限"
        except Exception as e:
            return -1, "", f"执行命令失败: {e}"

    async def _run(
        self, cmd: list[str], stdin_input: str | None = None
    ) -> tuple[int, str, str]:
        """异步执行命令（在线程池中运行同步 subprocess.run）。"""
        return await asyncio.to_thread(self._run_sync, cmd, stdin_input)

    @staticmethod
    def _find_column(headers: list[str], name: str) -> int | None:
        """在表头中查找列名，返回索引；不存在返回 None。"""
        for i, col in enumerate(headers):
            if col.upper() == name.upper():
                return i
        return None

    @staticmethod
    def _parse_table(output: str) -> list[dict]:
        """解析 kubectl get 的 table 输出为结构化数据。

        kubectl get all 会输出多段表格（pods / deployments / services 等），
        每段以 "NAME" 开头，段间空行分隔。本函数统一提取每行的
        NAME / READY / STATUS / AGE 列。
        """
        results: list[dict] = []
        # 按空行分割为多个段落
        sections = output.strip().split("\n\n")
        for section in sections:
            lines = [l for l in section.strip().splitlines() if l.strip()]
            if not lines:
                continue
            # 第一行是表头
            headers = lines[0].split()
            if not headers or headers[0].upper() != "NAME":
                continue

            name_idx = ClusterManager._find_column(headers, "NAME")
            ready_idx = ClusterManager._find_column(headers, "READY")
            status_idx = ClusterManager._find_column(headers, "STATUS")
            age_idx = ClusterManager._find_column(headers, "AGE")

            for line in lines[1:]:
                parts = line.split()
                if not parts:
                    continue

                def _safe_get(idx: int | None) -> str:
                    if idx is None or idx >= len(parts):
                        return ""
                    return parts[idx]

                results.append(
                    {
                        "name": _safe_get(name_idx),
                        "ready": _safe_get(ready_idx),
                        "status": _safe_get(status_idx),
                        "age": _safe_get(age_idx),
                    }
                )
        return results

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    async def apply(self, yaml_text: str) -> dict:
        """kubectl apply -f -，应用 YAML 到集群。

        Returns:
            {"success": bool, "output": str, "error": str}
        """
        if not self.enabled:
            return {
                "success": False,
                "output": "",
                "error": "集群模式未启用，无法 apply",
            }
        cmd = self._build_cmd("apply", "-f", "-")
        rc, stdout, stderr = await self._run(cmd, stdin_input=yaml_text)
        return {
            "success": rc == 0,
            "output": stdout,
            "error": stderr if rc != 0 else "",
        }

    async def get_resources(self, resource_type: str = "all") -> list[dict]:
        """kubectl get <resource_type>，返回资源列表。

        Args:
            resource_type: 资源类型，如 "all"、"pods"、"services"、"deployments"

        Returns:
            每个资源: {"name": str, "ready": str, "status": str, "age": str}
        """
        if not self.enabled:
            return []
        cmd = self._build_cmd("get", resource_type)
        rc, stdout, stderr = await self._run(cmd)
        if rc != 0:
            logger.warning("kubectl get %s 失败: %s", resource_type, stderr)
            return []
        return self._parse_table(stdout)

    async def get_logs(self, pod_name: str, tail: int = 50) -> str:
        """kubectl logs <pod_name> --tail=N，获取 Pod 日志。

        Args:
            pod_name: Pod 名称
            tail: 获取最后 N 行

        Returns:
            日志文本；失败时返回错误信息
        """
        if not self.enabled:
            return ""
        cmd = self._build_cmd("logs", pod_name, "--tail", str(tail))
        rc, stdout, stderr = await self._run(cmd)
        if rc != 0:
            return stderr if stderr else f"获取日志失败 (rc={rc})"
        return stdout

    async def test_connectivity(
        self, service_name: str, port: int = 80
    ) -> dict:
        """测试 Service 连通性。

        策略：先尝试在已有 Pod 内 exec curl；若无可用 Pod 则用
        kubectl run 创建临时 curl Pod。

        Returns:
            {"reachable": bool, "status_code": int, "response": str}
        """
        if not self.enabled:
            return {
                "reachable": False,
                "status_code": 0,
                "response": "集群模式未启用",
            }

        target = f"http://{service_name}:{port}"

        # 策略 1: 尝试在已有 Pod 内 exec curl
        pods = await self.get_resources("pods")
        running_pod = next(
            (p for p in pods if p["status"] == "Running" and p["name"]),
            None,
        )
        if running_pod:
            cmd = self._build_cmd(
                "exec", running_pod["name"],
                "--", "curl", "-s", "-w", "\\n%{http_code}", target,
            )
            rc, stdout, stderr = await self._run(cmd)
            if rc == 0 and stdout:
                return self._parse_curl_output(stdout)

        # 策略 2: kubectl run 临时 Pod
        pod_name = "k8s-quest-conn-test"
        cmd = self._build_cmd(
            "run", pod_name,
            "--image=curlimages/curl:8.5.0",
            "--restart=Never",
            "--rm", "-i",
            "--command", "--",
            "curl", "-s", "-w", "\\n%{http_code}", target,
        )
        rc, stdout, stderr = await self._run(cmd)
        if rc == 0 and stdout:
            return self._parse_curl_output(stdout)

        return {
            "reachable": False,
            "status_code": 0,
            "response": stderr or stdout or "连接失败",
        }

    @staticmethod
    def _parse_curl_output(stdout: str) -> dict:
        """解析 curl -w '\\n%{http_code}' 的输出。

        最后一行是 HTTP 状态码，其余是响应体。
        """
        lines = stdout.strip().splitlines()
        status_code = 0
        response_body = stdout
        if lines:
            try:
                status_code = int(lines[-1])
                response_body = "\n".join(lines[:-1])
            except ValueError:
                # 最后一行不是数字，可能是纯文本响应
                response_body = stdout
        return {
            "reachable": 200 <= status_code < 400,
            "status_code": status_code,
            "response": response_body,
        }

    async def delete_resource(self, resource_type: str, name: str) -> bool:
        """kubectl delete <type> <name>，删除指定资源。

        Returns:
            True 表示删除成功
        """
        if not self.enabled:
            return False
        cmd = self._build_cmd("delete", resource_type, name)
        rc, stdout, stderr = await self._run(cmd)
        if rc != 0:
            logger.warning("删除 %s/%s 失败: %s", resource_type, name, stderr)
        return rc == 0

    async def cleanup_namespace(self, namespace: str = "default") -> int:
        """清理 namespace 中学员创建的资源。

        获取所有资源并逐个删除，返回成功删除的资源数。
        排除系统资源 (kubernetes service)。

        Returns:
            删除的资源数量
        """
        if not self.enabled:
            return 0

        # 临时切换 namespace
        original_ns = self.namespace
        self.namespace = namespace
        try:
            cmd = self._build_cmd("get", "all", "-o", "name")
            rc, stdout, stderr = await self._run(cmd)
            if rc != 0:
                logger.warning("获取资源列表失败: %s", stderr)
                return 0

            count = 0
            for line in stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                # 格式: pod/name, deployment.apps/name, service/name
                if "/" not in line:
                    continue
                rtype, rname = line.split("/", 1)
                # 跳过系统 service
                if rtype == "service" and rname == "kubernetes":
                    continue
                if await self.delete_resource(rtype, rname):
                    count += 1
            return count
        finally:
            self.namespace = original_ns

    # 子命令白名单（允许执行的 kubectl 子命令）
    ALLOWED_SUBCOMMANDS = frozenset({
        "get", "describe", "logs", "apply", "delete", "create",
        "rollout", "scale", "top", "explain", "exec", "wait",
        "annotate", "label", "patch", "set", "edit",
        "port-forward", "cp", "auth", "api-resources", "api-versions",
        "cluster-info", "config", "version", "drain", "cordon", "uncordon",
        "taint", "rollout",
    })

    # 危险子命令（需要前端确认）
    DANGEROUS_SUBCOMMANDS = frozenset({
        "delete", "drain", "cordon", "uncordon", "taint",
        "scale", "rollout", "edit", "exec",
    })

    # 禁止的子命令（集群级破坏性操作）
    FORBIDDEN_SUBCOMMANDS = frozenset({
        "destroy", "reset", "init",  # kubeadm 级别操作
    })

    @staticmethod
    def _validate_kubectl_command(command: str) -> tuple[bool, str, list[str]]:
        """验证 kubectl 命令安全性。

        Returns:
            (is_valid, error_message, parsed_args)
            is_valid=True 时 parsed_args 是要传给 kubectl 的参数列表
        """
        command = command.strip()
        if not command:
            return False, "命令不能为空", []

        # 去除可能的 "kubectl " 前缀
        if command.startswith("kubectl "):
            command = command[8:]
        elif command == "kubectl":
            return False, "请输入 kubectl 子命令", []

        # 禁止 shell 元字符（防止注入）
        dangerous_chars = [";", "|", "&", "`", "$", "(", ")", "<", ">", "\n", "\r"]
        for ch in dangerous_chars:
            if ch in command:
                return False, f"命令包含禁止字符 '{ch}'", []

        # 解析参数
        import shlex
        try:
            args = shlex.split(command)
        except ValueError as e:
            return False, f"命令解析失败: {e}", []

        if not args:
            return False, "命令不能为空", []

        subcommand = args[0].lower()

        # 检查禁止的子命令
        if subcommand in ClusterManager.FORBIDDEN_SUBCOMMANDS:
            return False, f"子命令 '{subcommand}' 被禁止（破坏性集群操作）", []

        # 检查白名单
        if subcommand not in ClusterManager.ALLOWED_SUBCOMMANDS:
            return False, f"子命令 '{subcommand}' 不在白名单中。允许: {', '.join(sorted(ClusterManager.ALLOWED_SUBCOMMANDS))}", []

        return True, "", args

    async def kubectl_exec(self, command: str, force: bool = False) -> dict:
        """执行任意 kubectl 命令（经过安全验证）。

        Args:
            command: kubectl 命令字符串（不含 kubectl 前缀）
            force: 跳过危险命令确认

        Returns:
            {
                "success": bool,
                "output": str,       # stdout
                "error": str,        # stderr (if any)
                "command": str,      # 实际执行的命令
                "dangerous": bool,   # 是否危险命令
                "needs_confirm": bool,  # 是否需要确认
            }
        """
        # 先验证命令（无论是否集群模式，都给用户语法反馈）
        is_valid, error_msg, args = self._validate_kubectl_command(command)
        if not is_valid:
            return {
                "success": False,
                "output": "",
                "error": error_msg,
                "command": command,
                "dangerous": False,
                "needs_confirm": False,
            }

        if not self.enabled:
            return {
                "success": False,
                "output": "",
                "error": "集群模式未启用。请设置 K8S_QUEST_MODE=cluster 并配置 KUBECONFIG。",
                "command": command,
                "dangerous": False,
                "needs_confirm": False,
            }

        subcommand = args[0].lower()
        is_dangerous = subcommand in self.DANGEROUS_SUBCOMMANDS

        if is_dangerous and not force:
            return {
                "success": False,
                "output": "",
                "error": f"⚠️ 危险命令 '{subcommand}' 需要确认。请使用确认按钮再次执行。",
                "command": command,
                "dangerous": True,
                "needs_confirm": True,
            }

        # 构建完整命令
        cmd = self._build_cmd(*args)
        rc, stdout, stderr = await self._run(cmd)

        return {
            "success": rc == 0,
            "output": stdout if stdout else "",
            "error": stderr if rc != 0 else "",
            "command": f"kubectl -n {self.namespace} {' '.join(args)}",
            "dangerous": is_dangerous,
            "needs_confirm": False,
        }

    def get_status(self) -> dict:
        """返回集群状态信息。

        Returns:
            {"mode": "cluster"|"simulator", "kubectl": bool, "namespace": str}
        """
        return {
            "mode": "cluster" if self.enabled else "simulator",
            "kubectl": self._kubectl_available,
            "namespace": self.namespace,
        }
