"""测试进度导入导出 API (/api/progress/export, /api/progress/import)。

覆盖场景:
- 导出返回完整 JSON（所有字段齐全）
- 导出的 total_xp 是服务端计算值（不信任客户端提交的值）
- 导出包含 checksum 防篡改签名
- 导入有效 checksum 时返回 valid=True
- 导入篡改后的 checksum 时返回 valid=False
- 导入无效 JSON 时返回错误
"""
from fastapi.testclient import TestClient
from app.main import app, _calculate_server_xp, _calculate_checksum, PROGRESS_SECRET

client = TestClient(app)

# ── 测试数据 ──
SAMPLE_PROGRESS = {
    "completed_levels": ["Q0.1", "Q0.2", "Q1.1", "Q1.2"],
    "level_attempts": {"Q0.1": 1, "Q0.2": 2, "Q1.1": 1, "Q1.2": 3},
    "level_first_try": ["Q0.1", "Q1.1"],
    "level_time_spent": {"Q0.1": 60, "Q0.2": 120, "Q1.1": 45, "Q1.2": 200},
    "total_xp": 999,  # 故意填错，验证服务端重算
}


# ═══════════════════════════════════════════════
# 导出测试
# ═══════════════════════════════════════════════

def test_export_returns_complete_json():
    """导出返回包含所有必需字段的完整 JSON。"""
    r = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    assert r.status_code == 200
    data = r.json()

    required_fields = [
        "completed_levels",
        "level_attempts",
        "level_first_try",
        "level_time_spent",
        "total_xp",
        "exported_at",
        "level_count",
        "completion_rate",
        "checksum",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    # 验证数据内容
    assert data["completed_levels"] == SAMPLE_PROGRESS["completed_levels"]
    assert data["level_attempts"] == SAMPLE_PROGRESS["level_attempts"]
    assert data["level_first_try"] == SAMPLE_PROGRESS["level_first_try"]
    assert data["level_time_spent"] == SAMPLE_PROGRESS["level_time_spent"]
    assert data["level_count"] == 4
    assert isinstance(data["completion_rate"], float)
    assert 0 <= data["completion_rate"] <= 1
    assert data["exported_at"]  # 非空时间字符串


def test_export_server_recalculates_xp():
    """导出的 total_xp 是服务端计算值，不信任客户端提交的值。"""
    r = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    assert r.status_code == 200
    data = r.json()

    expected_xp = _calculate_server_xp(SAMPLE_PROGRESS["completed_levels"])
    assert data["total_xp"] == expected_xp
    # 确保不是客户端提交的错误值
    assert data["total_xp"] != 999


def test_export_includes_checksum():
    """导出返回包含 checksum 防篡改签名。"""
    r = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    assert r.status_code == 200
    data = r.json()

    assert "checksum" in data
    assert isinstance(data["checksum"], str)
    assert len(data["checksum"]) == 64  # SHA-256 hex digest

    # 验证 checksum 是基于 completed_levels + secret 计算的
    expected = _calculate_checksum(SAMPLE_PROGRESS["completed_levels"])
    assert data["checksum"] == expected


def test_export_completion_rate_correct():
    """导出的 completion_rate 与完成关卡数一致。"""
    r = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    assert r.status_code == 200
    data = r.json()

    from app.metadata import KNOWLEDGE_POINTS
    total = len(KNOWLEDGE_POINTS)
    expected_rate = 4 / total
    assert abs(data["completion_rate"] - expected_rate) < 0.001


def test_export_empty_progress():
    """空进度也能正常导出。"""
    r = client.post("/api/progress/export", json={
        "completed_levels": [],
        "level_attempts": {},
        "level_first_try": [],
        "level_time_spent": {},
        "total_xp": 0,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["total_xp"] == 0
    assert data["level_count"] == 0
    assert data["completion_rate"] == 0.0
    assert data["checksum"]  # 仍然有 checksum


# ═══════════════════════════════════════════════
# 导入测试
# ═══════════════════════════════════════════════

def test_import_valid_checksum():
    """有效 checksum 的导入返回 valid=True。"""
    # 先导出
    export_resp = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    assert export_resp.status_code == 200
    exported = export_resp.json()

    # 再导入
    import_resp = client.post("/api/progress/import", json=exported)
    assert import_resp.status_code == 200
    result = import_resp.json()

    assert result["valid"] is True
    assert result["total_xp"] == exported["total_xp"]
    assert result["level_count"] == 4
    assert isinstance(result["completion_rate"], float)


def test_import_tampered_checksum():
    """篡改后的 checksum 返回 valid=False。"""
    # 先导出
    export_resp = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    exported = export_resp.json()

    # 篡改 checksum
    exported["checksum"] = "a" * 64  # 伪造的 checksum

    import_resp = client.post("/api/progress/import", json=exported)
    assert import_resp.status_code == 200
    result = import_resp.json()

    assert result["valid"] is False
    assert result["total_xp"] == 0  # 验证失败不返回 XP


def test_import_tampered_completed_levels():
    """篡改 completed_levels 但保留原 checksum 时返回 valid=False。"""
    # 先导出
    export_resp = client.post("/api/progress/export", json=SAMPLE_PROGRESS)
    exported = export_resp.json()

    # 篡改 completed_levels（添加一个不存在的关卡）
    exported["completed_levels"] = exported["completed_levels"] + ["Q99.99"]

    import_resp = client.post("/api/progress/import", json=exported)
    assert import_resp.status_code == 200
    result = import_resp.json()

    assert result["valid"] is False


def test_import_invalid_json():
    """无效 JSON 字段类型返回错误。"""
    # Pydantic 会拒绝类型不匹配的请求，FastAPI 默认返回 422
    r = client.post("/api/progress/import", json={
        "completed_levels": "not_a_list",  # 应为 list
        "checksum": "some_checksum",
    })
    assert r.status_code == 422


def test_import_missing_checksum():
    """缺失 checksum 字段时 valid=False（默认空字符串）。"""
    r = client.post("/api/progress/import", json={
        "completed_levels": ["Q0.1", "Q1.1"],
        "level_attempts": {},
        "level_first_try": [],
        "level_time_spent": {},
        "total_xp": 20,
    })
    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is False


def test_import_empty_progress_valid():
    """空进度 + 正确 checksum 的导入返回 valid=True。"""
    # 计算空列表的 checksum
    empty_checksum = _calculate_checksum([])

    r = client.post("/api/progress/import", json={
        "completed_levels": [],
        "level_attempts": {},
        "level_first_try": [],
        "level_time_spent": {},
        "total_xp": 0,
        "checksum": empty_checksum,
    })
    assert r.status_code == 200
    result = r.json()
    assert result["valid"] is True
    assert result["total_xp"] == 0
    assert result["level_count"] == 0
