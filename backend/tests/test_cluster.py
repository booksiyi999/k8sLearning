"""ClusterManager 单元测试。

测试策略：
- 无 kubectl 环境下 enabled=False、回退模拟器
- get_status 返回正确结构
- apply / get_resources / get_logs / delete_resource / test_connectivity / cleanup_namespace
  的错误处理和正常路径（Mock subprocess.run）
- subprocess 异常：TimeoutExpired / FileNotFoundError / 通用异常
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app.cluster import ClusterManager, KUBECTL_TIMEOUT


# ---------------------------------------------------------------------------
# 辅助：同步调用 async 方法（无需 pytest-asyncio）
# ---------------------------------------------------------------------------

def run(coro):
    """同步运行协程。"""
    return asyncio.get_event_loop().run_until_complete(coro)


def make_completed_process(
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess:
    """构造 subprocess.run 的返回值。"""
    return subprocess.CompletedProcess(
        args=["kubectl"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


@contextmanager
def enabled_cluster_mgr(kubeconfig_path: str = "/tmp/fake_kubeconfig"):
    """上下文管理器：创建一个 enabled=True 的 ClusterManager。

    所有 patch 在 with 块内保持激活，退出后自动还原。
    """
    with patch.dict(os.environ, {"K8S_QUEST_MODE": "cluster"}):
        with patch("app.cluster.shutil.which", return_value="/usr/bin/kubectl"):
            with patch("app.cluster.os.path.isfile", return_value=True):
                mgr = ClusterManager(kubeconfig_path=kubeconfig_path)
                yield mgr


# ---------------------------------------------------------------------------
# 1. 无 kubectl 环境（真实环境：kubectl 不在 PATH 中）
# ---------------------------------------------------------------------------

class TestNoKubectlEnvironment:
    """当前测试环境没有 kubectl 时的行为。"""

    def test_enabled_false_without_kubectl(self):
        """K8S_QUEST_MODE 未设为 cluster → enabled=False。"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("K8S_QUEST_MODE", None)
            os.environ.pop("KUBECONFIG", None)
            mgr = ClusterManager()
            assert mgr.enabled is False

    def test_enabled_false_when_mode_not_cluster(self):
        """K8S_QUEST_MODE=simulator → enabled=False。"""
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            assert mgr.enabled is False

    def test_enabled_false_when_mode_cluster_but_no_kubectl(self):
        """K8S_QUEST_MODE=cluster 但 kubectl 不存在 → enabled=False。"""
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "cluster"}):
            with patch("app.cluster.shutil.which", return_value=None):
                mgr = ClusterManager()
                assert mgr.enabled is False

    def test_enabled_false_when_kubectl_exists_but_no_kubeconfig(self):
        """kubectl 存在但 kubeconfig 文件不存在 → enabled=False。"""
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "cluster"}):
            with patch("app.cluster.shutil.which", return_value="/usr/bin/kubectl"):
                with patch("app.cluster.os.path.isfile", return_value=False):
                    mgr = ClusterManager(kubeconfig_path="/nonexistent/kubeconfig")
                    assert mgr.enabled is False

    def test_enabled_true_when_all_conditions_met(self):
        """所有条件满足 → enabled=True。"""
        with enabled_cluster_mgr() as mgr:
            assert mgr.enabled is True

    def test_enabled_uses_default_kubeconfig(self):
        """无显式 kubeconfig 时检查 ~/.kube/config。"""
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "cluster", "KUBECONFIG": ""}):
            with patch("app.cluster.shutil.which", return_value="/usr/bin/kubectl"):
                with patch("app.cluster.os.path.isfile", return_value=True):
                    mgr = ClusterManager()
                    assert mgr.enabled is True


# ---------------------------------------------------------------------------
# 2. get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_returns_correct_structure(self):
        """get_status 返回包含 mode/kubectl/namespace 的 dict。"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("K8S_QUEST_MODE", None)
            mgr = ClusterManager()
            status = mgr.get_status()
            assert isinstance(status, dict)
            assert "mode" in status
            assert "kubectl" in status
            assert "namespace" in status

    def test_mode_simulator_when_disabled(self):
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            assert mgr.get_status()["mode"] == "simulator"

    def test_mode_cluster_when_enabled(self):
        with enabled_cluster_mgr() as mgr:
            assert mgr.get_status()["mode"] == "cluster"

    def test_namespace_from_env(self):
        with patch.dict(os.environ, {"K8S_QUEST_NAMESPACE": "myns"}):
            mgr = ClusterManager()
            assert mgr.get_status()["namespace"] == "myns"

    def test_namespace_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("K8S_QUEST_NAMESPACE", None)
            mgr = ClusterManager()
            assert mgr.get_status()["namespace"] == "default"

    def test_kubectl_field_reflects_availability(self):
        with patch("app.cluster.shutil.which", return_value="/usr/bin/kubectl"):
            mgr = ClusterManager()
            assert mgr.get_status()["kubectl"] is True

    def test_kubectl_field_false_when_missing(self):
        with patch("app.cluster.shutil.which", return_value=None):
            mgr = ClusterManager()
            assert mgr.get_status()["kubectl"] is False


# ---------------------------------------------------------------------------
# 3. apply — Mock subprocess.run
# ---------------------------------------------------------------------------

class TestApply:
    def test_apply_success(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(
                returncode=0,
                stdout="pod/nginx created\n",
                stderr="",
            )
            with patch("app.cluster.subprocess.run", return_value=mock_proc) as mock_run:
                result = run(mgr.apply("apiVersion: v1\nkind: Pod\n"))
                assert result["success"] is True
                assert "nginx created" in result["output"]
                assert result["error"] == ""
                mock_run.assert_called_once()
                # 验证传入了 stdin
                assert mock_run.call_args.kwargs.get("input") is not None

    def test_apply_failure(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(
                returncode=1,
                stdout="",
                stderr="Error: pod already exists\n",
            )
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                result = run(mgr.apply("kind: Pod\n"))
                assert result["success"] is False
                assert "already exists" in result["error"]

    def test_apply_disabled_returns_error(self):
        """集群未启用时 apply 返回错误。"""
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            result = run(mgr.apply("kind: Pod\n"))
            assert result["success"] is False
            assert "未启用" in result["error"]

    def test_apply_timeout(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="kubectl", timeout=30),
            ):
                result = run(mgr.apply("kind: Pod\n"))
                assert result["success"] is False
                assert "超时" in result["error"]

    def test_apply_kubectl_not_found(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                side_effect=FileNotFoundError("kubectl not found"),
            ):
                result = run(mgr.apply("kind: Pod\n"))
                assert result["success"] is False
                assert "kubectl" in result["error"].lower() or "未安装" in result["error"]

    def test_apply_generic_exception(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                side_effect=RuntimeError("unexpected"),
            ):
                result = run(mgr.apply("kind: Pod\n"))
                assert result["success"] is False
                assert "失败" in result["error"] or "unexpected" in result["error"]


# ---------------------------------------------------------------------------
# 4. get_resources — Mock subprocess.run + table 解析
# ---------------------------------------------------------------------------

class TestGetResources:
    def test_get_resources_parses_pods(self):
        with enabled_cluster_mgr() as mgr:
            table = (
                "NAME       READY   STATUS    RESTARTS   AGE\n"
                "nginx      1/1     Running   0          5m\n"
                "redis      0/1     Pending   0          1m\n"
            )
            mock_proc = make_completed_process(returncode=0, stdout=table)
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                resources = run(mgr.get_resources("pods"))
                assert len(resources) == 2
                assert resources[0]["name"] == "nginx"
                assert resources[0]["ready"] == "1/1"
                assert resources[0]["status"] == "Running"
                assert resources[0]["age"] == "5m"
                assert resources[1]["name"] == "redis"
                assert resources[1]["status"] == "Pending"

    def test_get_resources_parses_multi_section(self):
        """kubectl get all 输出多段表格。"""
        with enabled_cluster_mgr() as mgr:
            table = (
                "NAME                 READY   STATUS    RESTARTS   AGE\n"
                "pod/web-abc          1/1     Running   0          3m\n\n"
                "NAME                 TYPE        CLUSTER-IP   EXTERNAL-IP   PORT(S)   AGE\n"
                "service/web          ClusterIP   10.96.0.5    <none>        80/TCP    3m\n"
            )
            mock_proc = make_completed_process(returncode=0, stdout=table)
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                resources = run(mgr.get_resources("all"))
                assert len(resources) == 2
                # 第一段是 pod (kubectl get all 输出 name 含类型前缀)
                assert resources[0]["name"] == "pod/web-abc"
                assert resources[0]["ready"] == "1/1"
                # 第二段是 service（没有 READY 列 → ready=""）
                assert resources[1]["name"] == "service/web"
                assert resources[1]["age"] == "3m"

    def test_get_resources_empty(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(returncode=0, stdout="")
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                resources = run(mgr.get_resources("pods"))
                assert resources == []

    def test_get_resources_failure(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(
                returncode=1, stdout="", stderr="No resources found"
            )
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                resources = run(mgr.get_resources("pods"))
                assert resources == []

    def test_get_resources_disabled(self):
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            resources = run(mgr.get_resources())
            assert resources == []

    def test_get_resources_timeout(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="kubectl", timeout=30),
            ):
                resources = run(mgr.get_resources("pods"))
                assert resources == []


# ---------------------------------------------------------------------------
# 5. get_logs — Mock subprocess.run
# ---------------------------------------------------------------------------

class TestGetLogs:
    def test_get_logs_success(self):
        with enabled_cluster_mgr() as mgr:
            logs = "line1\nline2\nline3\n"
            mock_proc = make_completed_process(returncode=0, stdout=logs)
            with patch("app.cluster.subprocess.run", return_value=mock_proc) as mock_run:
                result = run(mgr.get_logs("nginx", tail=10))
                assert result == logs
                # 验证 --tail 参数传入
                call_args = mock_run.call_args
                cmd = call_args.args[0]
                assert "--tail" in cmd
                assert "10" in cmd

    def test_get_logs_failure_returns_stderr(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(
                returncode=1, stdout="", stderr="Error: pod not found"
            )
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                result = run(mgr.get_logs("nonexistent"))
                assert "not found" in result

    def test_get_logs_disabled(self):
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            result = run(mgr.get_logs("nginx"))
            assert result == ""

    def test_get_logs_timeout(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="kubectl", timeout=30),
            ):
                result = run(mgr.get_logs("nginx"))
                assert "超时" in result

    def test_get_logs_kubectl_not_found(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                side_effect=FileNotFoundError("kubectl not found"),
            ):
                result = run(mgr.get_logs("nginx"))
                assert "kubectl" in result.lower() or "未安装" in result


# ---------------------------------------------------------------------------
# 6. delete_resource
# ---------------------------------------------------------------------------

class TestDeleteResource:
    def test_delete_success(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(
                returncode=0, stdout='pod "nginx" deleted\n', stderr=""
            )
            with patch("app.cluster.subprocess.run", return_value=mock_proc) as mock_run:
                result = run(mgr.delete_resource("pod", "nginx"))
                assert result is True
                cmd = mock_run.call_args.args[0]
                assert "delete" in cmd
                assert "pod" in cmd
                assert "nginx" in cmd

    def test_delete_failure(self):
        with enabled_cluster_mgr() as mgr:
            mock_proc = make_completed_process(
                returncode=1, stdout="", stderr="Error: pod not found"
            )
            with patch("app.cluster.subprocess.run", return_value=mock_proc):
                result = run(mgr.delete_resource("pod", "nonexistent"))
                assert result is False

    def test_delete_disabled(self):
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            result = run(mgr.delete_resource("pod", "nginx"))
            assert result is False


# ---------------------------------------------------------------------------
# 7. test_connectivity
# ---------------------------------------------------------------------------

class TestTestConnectivity:
    def test_connectivity_success_via_exec(self):
        """策略 1: exec 到已有 Pod 内 curl 成功。"""
        with enabled_cluster_mgr() as mgr:
            pods_table = (
                "NAME       READY   STATUS    RESTARTS   AGE\n"
                "nginx      1/1     Running   0          5m\n"
            )
            curl_output = "Hello World\n200"

            call_count = [0]

            def mock_run_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # 第一次调用: get_resources("pods")
                    return make_completed_process(returncode=0, stdout=pods_table)
                else:
                    # 第二次调用: exec curl
                    return make_completed_process(returncode=0, stdout=curl_output)

            with patch("app.cluster.subprocess.run", side_effect=mock_run_side_effect):
                result = run(mgr.test_connectivity("web", 80))
                assert result["reachable"] is True
                assert result["status_code"] == 200
                assert "Hello World" in result["response"]

    def test_connectivity_success_404(self):
        """curl 返回 404 → reachable=False。"""
        with enabled_cluster_mgr() as mgr:
            pods_table = (
                "NAME       READY   STATUS    RESTARTS   AGE\n"
                "nginx      1/1     Running   0          5m\n"
            )
            curl_output = "Not Found\n404"

            call_count = [0]

            def mock_run_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return make_completed_process(returncode=0, stdout=pods_table)
                return make_completed_process(returncode=0, stdout=curl_output)

            with patch("app.cluster.subprocess.run", side_effect=mock_run_side_effect):
                result = run(mgr.test_connectivity("web", 80))
                assert result["reachable"] is False
                assert result["status_code"] == 404

    def test_connectivity_disabled(self):
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            result = run(mgr.test_connectivity("web", 80))
            assert result["reachable"] is False
            assert result["status_code"] == 0

    def test_connectivity_all_fail(self):
        """没有可用 Pod 且 kubectl run 也失败。"""
        with enabled_cluster_mgr() as mgr:
            pods_output = ""
            call_count = [0]

            def mock_run_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return make_completed_process(returncode=0, stdout=pods_output)
                return make_completed_process(
                    returncode=1, stdout="", stderr="ImagePullBackOff"
                )

            with patch("app.cluster.subprocess.run", side_effect=mock_run_side_effect):
                result = run(mgr.test_connectivity("web", 80))
                assert result["reachable"] is False


# ---------------------------------------------------------------------------
# 8. cleanup_namespace
# ---------------------------------------------------------------------------

class TestCleanupNamespace:
    def test_cleanup_deletes_resources(self):
        with enabled_cluster_mgr() as mgr:
            resource_list = (
                "pod/web-abc\n"
                "deployment.apps/web\n"
                "service/kubernetes\n"
                "service/web\n"
            )
            call_count = [0]

            def mock_run_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    # get all -o name
                    return make_completed_process(returncode=0, stdout=resource_list)
                # 后续都是 delete 调用，全部成功
                return make_completed_process(returncode=0, stdout="deleted")

            with patch("app.cluster.subprocess.run", side_effect=mock_run_side_effect):
                count = run(mgr.cleanup_namespace("default"))
                # pod/web-abc + deployment.apps/web + service/web = 3（跳过 service/kubernetes）
                assert count == 3

    def test_cleanup_disabled(self):
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "simulator"}):
            mgr = ClusterManager()
            count = run(mgr.cleanup_namespace("default"))
            assert count == 0

    def test_cleanup_get_fails(self):
        with enabled_cluster_mgr() as mgr:
            with patch(
                "app.cluster.subprocess.run",
                return_value=make_completed_process(
                    returncode=1, stdout="", stderr="error"
                ),
            ):
                count = run(mgr.cleanup_namespace("default"))
                assert count == 0

    def test_cleanup_partial_failure(self):
        with enabled_cluster_mgr() as mgr:
            resource_list = "pod/a\npod/b\npod/c\n"
            results = [
                make_completed_process(returncode=0, stdout=resource_list),  # get
                make_completed_process(returncode=0, stdout=""),  # delete a: success
                make_completed_process(returncode=1, stderr="error"),  # delete b: fail
                make_completed_process(returncode=0, stdout=""),  # delete c: success
            ]
            with patch("app.cluster.subprocess.run", side_effect=results):
                count = run(mgr.cleanup_namespace("default"))
                assert count == 2


# ---------------------------------------------------------------------------
# 9. 命令构建
# ---------------------------------------------------------------------------

class TestCommandBuilding:
    def test_kubeconfig_added_to_command(self):
        """kubectl 命令包含 --kubeconfig 参数。"""
        with enabled_cluster_mgr(kubeconfig_path="/custom/kubeconfig") as mgr:
            cmd = mgr._build_cmd("get", "pods")
            assert "--kubeconfig" in cmd
            assert "/custom/kubeconfig" in cmd
            assert "-n" in cmd
            assert "default" in cmd
            assert "get" in cmd
            assert "pods" in cmd

    def test_no_kubeconfig_when_not_set(self):
        """无 kubeconfig 时不添加 --kubeconfig。"""
        with patch.dict(os.environ, {"K8S_QUEST_MODE": "cluster", "KUBECONFIG": ""}):
            with patch("app.cluster.shutil.which", return_value="/usr/bin/kubectl"):
                mgr = ClusterManager()
                cmd = mgr._build_cmd("get", "pods")
                assert "--kubeconfig" not in cmd
