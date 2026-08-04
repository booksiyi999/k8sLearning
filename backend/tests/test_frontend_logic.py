"""前端游戏化逻辑的 API 测试。

测试前端依赖的后端 API 逻辑，重点覆盖：
- /api/report 端点的各种边界情况（空数据/部分数据/完整数据）
- /api/meta 端点的数据结构完整性
- /api/level/{id} 端点对所有 120 关的正确返回
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# 所有 120 个关卡 ID
ALL_LEVEL_IDS = [f"Q{ch}.{lv}" for ch in range(1, 29) for lv in range(1, 6)]

# 各章节的关卡 ID
CH_LEVELS = {
    1: ["Q1.1", "Q1.2", "Q1.3", "Q1.4", "Q1.5"],
    2: ["Q2.1", "Q2.2", "Q2.3", "Q2.4", "Q2.5"],
    3: ["Q3.1", "Q3.2", "Q3.3", "Q3.4", "Q3.5"],
    4: ["Q4.1", "Q4.2", "Q4.3", "Q4.4", "Q4.5"],
    5: ["Q5.1", "Q5.2", "Q5.3", "Q5.4", "Q5.5"],
    6: ["Q6.1", "Q6.2", "Q6.3", "Q6.4", "Q6.5"],
    7: ["Q7.1", "Q7.2", "Q7.3", "Q7.4", "Q7.5"],
    8: ["Q8.1", "Q8.2", "Q8.3", "Q8.4", "Q8.5"],
    9: ["Q9.1", "Q9.2", "Q9.3", "Q9.4", "Q9.5"],
    10: ["Q10.1", "Q10.2", "Q10.3", "Q10.4", "Q10.5"],
    11: ["Q11.1", "Q11.2", "Q11.3", "Q11.4", "Q11.5"],
    12: ["Q12.1", "Q12.2", "Q12.3", "Q12.4", "Q12.5"],
}


# ==========================================================================
#  /api/report 端点测试
# ==========================================================================

class TestReportEmptyData:
    """空数据（completed_levels=[]）"""

    def test_empty_completed_levels(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "level_attempts": {},
            "level_first_try": [],
            "level_time_spent": {},
            "total_xp": 0,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["completion_rate"] == 0.0
        assert data["completed_count"] == 0
        assert data["total_levels"] == 140
        assert data["total_xp"] == 0
        assert data["grade"] == "D"
        assert data["first_try_count"] == 0
        assert data["total_attempts"] == 0

    def test_empty_weak_areas_all_unfinished(self):
        """空数据时所有 120 关都是薄弱项"""
        r = client.post("/api/report", json={
            "completed_levels": [],
            "level_attempts": {},
            "level_first_try": [],
            "level_time_spent": {},
            "total_xp": 0,
        })
        data = r.json()
        assert len(data["weak_areas"]) == 140
        for wa in data["weak_areas"]:
            assert wa["reason"] == "未完成"

    def test_empty_rank_is_newbie(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 0,
        })
        data = r.json()
        assert "萌新" in data["rank"]

    def test_empty_recommendations_all_domains(self):
        """空数据时 11 个知识域都应建议开始学习"""
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 0,
        })
        data = r.json()
        assert len(data["recommendations"]) == 27
        for rec in data["recommendations"]:
            assert "尚未开始" in rec


class TestReportPartialData:
    """部分数据（只完成 Ch1）"""

    def test_ch1_only_completion_rate(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "level_attempts": {lid: 1 for lid in CH_LEVELS[1]},
            "level_first_try": CH_LEVELS[1],
            "level_time_spent": {},
            "total_xp": 100,  # 5*10 + 1*50
        })
        data = r.json()
        assert data["completion_rate"] == pytest.approx(5 / 140)
        assert data["completed_count"] == 5

    def test_ch1_only_grade_is_c(self):
        """5/120 ≈ 4.2% -> D 级"""
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "total_xp": 100,
        })
        data = r.json()
        assert data["grade"] == "D"

    def test_ch1_only_weak_areas_count(self):
        """只完成 5 关，115 关未完成 -> 115 个薄弱项"""
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "total_xp": 100,
        })
        data = r.json()
        unfinished = [wa for wa in data["weak_areas"] if wa["reason"] == "未完成"]
        assert len(unfinished) == 135

    def test_ch1_only_domain_stats(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "total_xp": 100,
        })
        data = r.json()
        # 工作负载管理域包含 Q1.x + Q2.x 共 10 关，完成了 5 关
        wl = data["domain_stats"]["工作负载管理"]
        assert wl["total"] == 10
        assert wl["completed"] == 5
        assert wl["rate"] == pytest.approx(0.5)
        # 其他域都为 0
        for domain in ["网络与服务", "配置与密钥", "存储管理", "调度与资源",
                        "批量任务", "有状态应用", "权限管理", "自动伸缩",
                        "入口路由", "网络安全"]:
            assert data["domain_stats"][domain]["completed"] == 0
            assert data["domain_stats"][domain]["rate"] == 0.0

    def test_ch1_only_chapter_stats(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "total_xp": 100,
        })
        data = r.json()
        ch1 = data["chapter_stats"]["ch01"]
        assert ch1["total"] == 5
        assert ch1["completed"] == 5
        assert ch1["rate"] == 1.0
        for ch_id in [f"ch{i:02d}" for i in range(2, 29)]:
            assert data["chapter_stats"][ch_id]["completed"] == 0


class TestReportFullData:
    """全部完成（120关全通）"""

    def _full_report_payload(self, first_try_count=140, extra_attempts=None):
        first_try = ALL_LEVEL_IDS[:first_try_count]
        attempts = {lid: 1 for lid in ALL_LEVEL_IDS}
        if extra_attempts:
            for lid, cnt in extra_attempts.items():
                attempts[lid] = cnt
        return {
            "completed_levels": ALL_LEVEL_IDS,
            "level_attempts": attempts,
            "level_first_try": first_try,
            "level_time_spent": {lid: 60 for lid in ALL_LEVEL_IDS},
            "total_xp": 2800,
        }

    def test_full_completion_rate(self):
        r = client.post("/api/report", json=self._full_report_payload())
        data = r.json()
        assert data["completion_rate"] == 1.0
        assert data["completed_count"] == 140

    def test_full_grade_s_with_20_plus_first_try(self):
        """120 关全通 + 首通 >= 20 -> S 级"""
        r = client.post("/api/report", json=self._full_report_payload(first_try_count=140))
        data = r.json()
        assert data["grade"] == "S"
        assert "完美通关" in data["grade_comment"]

    def test_full_grade_a_when_first_try_below_20(self):
        """120 关全通但首通 < 20 -> A 级（因为 completion_rate=1.0 但 first_try < 20）"""
        r = client.post("/api/report", json=self._full_report_payload(first_try_count=19))
        data = r.json()
        assert data["grade"] == "A"

    def test_full_grade_s_boundary_first_try_exactly_20(self):
        """首通恰好 20 -> S 级（边界值）"""
        r = client.post("/api/report", json=self._full_report_payload(first_try_count=20))
        data = r.json()
        assert data["grade"] == "S"

    def test_full_grade_a_boundary_first_try_19(self):
        """首通恰好 19 -> A 级（边界值）"""
        r = client.post("/api/report", json=self._full_report_payload(first_try_count=19))
        data = r.json()
        assert data["grade"] == "A"

    def test_full_no_weak_areas(self):
        """全通且尝试次数都 <= 2 -> 无薄弱项"""
        r = client.post("/api/report", json=self._full_report_payload())
        data = r.json()
        assert len(data["weak_areas"]) == 0

    def test_full_domain_stats_all_100(self):
        r = client.post("/api/report", json=self._full_report_payload())
        data = r.json()
        for domain, stats in data["domain_stats"].items():
            assert stats["rate"] == 1.0, f"Domain {domain} should be 100%"
            assert stats["completed"] == stats["total"]

    def test_full_recommendations_empty(self):
        """全部 100% -> 无学习建议"""
        r = client.post("/api/report", json=self._full_report_payload())
        data = r.json()
        assert len(data["recommendations"]) == 0

    def test_full_rank_is_legend(self):
        r = client.post("/api/report", json=self._full_report_payload())
        data = r.json()
        assert "K8s 传奇" in data["rank"]
        assert data["next_rank"] is None
        assert data["xp_to_next_rank"] == 0

    def test_full_strengths_count(self):
        r = client.post("/api/report", json=self._full_report_payload(first_try_count=140))
        data = r.json()
        assert len(data["strengths"]) == 140


class TestReportFirstTry:
    """首通标记验证（level_first_try）"""

    def test_first_try_count_reflected(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "level_first_try": CH_LEVELS[1][:2],
            "total_xp": 40,
        })
        data = r.json()
        assert data["first_try_count"] == 2

    def test_first_try_appears_in_domain_levels(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "level_first_try": ["Q1.1"],
            "total_xp": 40,
        })
        data = r.json()
        levels = data["domain_stats"]["工作负载管理"]["levels"]
        q11 = next(l for l in levels if l["id"] == "Q1.1")
        q12 = next(l for l in levels if l["id"] == "Q1.2")
        assert q11["first_try"] is True
        assert q12["first_try"] is False

    def test_strengths_only_include_completed_first_try(self):
        """strengths 只包含已完成的 first_try 关卡"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_first_try": ["Q1.1", "Q13.9"],  # Q13.9 不在 completed 中
            "total_xp": 10,
        })
        data = r.json()
        assert len(data["strengths"]) == 1
        assert data["strengths"][0]["level_id"] == "Q1.1"


class TestReportAttempts:
    """尝试次数验证（level_attempts）"""

    def test_attempts_reflected_in_domain_levels(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "level_attempts": {"Q1.1": 3, "Q1.2": 1, "Q1.3": 5, "Q1.4": 2, "Q1.5": 1},
            "total_xp": 40,
        })
        data = r.json()
        levels = data["domain_stats"]["工作负载管理"]["levels"]
        q11 = next(l for l in levels if l["id"] == "Q1.1")
        q13 = next(l for l in levels if l["id"] == "Q1.3")
        assert q11["attempts"] == 3
        assert q13["attempts"] == 5

    def test_total_attempts_summed(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[1],
            "level_attempts": {"Q1.1": 3, "Q1.2": 1, "Q1.3": 5, "Q1.4": 2, "Q1.5": 1},
            "total_xp": 40,
        })
        data = r.json()
        assert data["total_attempts"] == 12

    def test_attempts_default_zero_when_missing(self):
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_attempts": {},
            "total_xp": 10,
        })
        data = r.json()
        levels = data["domain_stats"]["工作负载管理"]["levels"]
        q11 = next(l for l in levels if l["id"] == "Q1.1")
        assert q11["attempts"] == 0


class TestReportXP:
    """XP 计算验证"""

    def test_total_xp_echoed(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 2800,
        })
        data = r.json()
        assert data["total_xp"] == 2800

    def test_rank_pod_apprentice_at_40_xp(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 40,
        })
        data = r.json()
        assert "Pod 学徒" in data["rank"]

    def test_rank_deployment_walker_at_100(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 100,
        })
        data = r.json()
        assert "Deployment 行者" in data["rank"]

    def test_rank_legend_at_500(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 500,
        })
        data = r.json()
        assert "K8s 传奇" in data["rank"]
        assert data["next_rank"] is None

    def test_next_rank_xp_needed(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 30,
        })
        data = r.json()
        # 30 XP, next rank at 40 -> need 10 more
        assert data["xp_to_next_rank"] == 10

    def test_time_spent_summed(self):
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1", "Q1.2"],
            "level_time_spent": {"Q1.1": 120, "Q1.2": 60},
            "total_xp": 20,
        })
        data = r.json()
        assert data["total_time_spent"] == 180


class TestReportDomainMastery:
    """知识域掌握度计算验证"""

    def test_partial_domain_completion(self):
        """工作负载管理域完成 7/10"""
        completed = CH_LEVELS[1] + CH_LEVELS[2][:2]  # Q1.1-Q1.5 + Q2.1-Q2.2
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 60,
        })
        data = r.json()
        wl = data["domain_stats"]["工作负载管理"]
        assert wl["total"] == 10
        assert wl["completed"] == 7
        assert wl["rate"] == pytest.approx(7 / 10)

    def test_network_domain(self):
        r = client.post("/api/report", json={
            "completed_levels": CH_LEVELS[3],
            "total_xp": 100,
        })
        data = r.json()
        net = data["domain_stats"]["网络与服务"]
        assert net["total"] == 5
        assert net["completed"] == 5
        assert net["rate"] == 1.0

    def test_domain_levels_include_knowledge_points(self):
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "total_xp": 10,
        })
        data = r.json()
        levels = data["domain_stats"]["工作负载管理"]["levels"]
        q11 = next(l for l in levels if l["id"] == "Q1.1")
        assert len(q11["knowledge_points"]) > 0
        assert "Pod 概念" in q11["knowledge_points"]


class TestReportWeakAreas:
    """薄弱项识别验证"""

    def test_weak_area_unfinished(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 0,
        })
        data = r.json()
        assert len(data["weak_areas"]) == 140
        assert data["weak_areas"][0]["reason"] == "未完成"

    def test_weak_area_too_many_attempts(self):
        """尝试 > 2 次的已完成关卡也是薄弱项"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_attempts": {"Q1.1": 3},
            "total_xp": 10,
        })
        data = r.json()
        weak_q11 = [wa for wa in data["weak_areas"] if wa["level_id"] == "Q1.1"]
        assert len(weak_q11) == 1
        assert "尝试 3 次" in weak_q11[0]["reason"]

    def test_weak_area_boundary_attempts_2_not_weak(self):
        """尝试恰好 2 次不算薄弱项"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_attempts": {"Q1.1": 2},
            "total_xp": 10,
        })
        data = r.json()
        weak_q11 = [wa for wa in data["weak_areas"] if wa["level_id"] == "Q1.1"]
        assert len(weak_q11) == 0

    def test_weak_area_boundary_attempts_3_is_weak(self):
        """尝试恰好 3 次算薄弱项（边界值）"""
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1"],
            "level_attempts": {"Q1.1": 3},
            "total_xp": 10,
        })
        data = r.json()
        weak_q11 = [wa for wa in data["weak_areas"] if wa["level_id"] == "Q1.1"]
        assert len(weak_q11) == 1

    def test_weak_area_includes_knowledge_points(self):
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 0,
        })
        data = r.json()
        wa = data["weak_areas"][0]
        assert len(wa["knowledge_points"]) > 0


class TestReportGradeBoundaries:
    """成绩评定边界（S/A/B/C/D 各级别）"""

    def test_grade_d_below_50_percent(self):
        """完成率 < 50% -> D"""
        completed = ALL_LEVEL_IDS[:69]  # 69/140 ≈ 49.3%
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 690,
        })
        assert r.json()["grade"] == "D"

    def test_grade_c_at_50_percent(self):
        """完成率 = 50% (70/140) -> C"""
        completed = ALL_LEVEL_IDS[:70]  # 70/140 = 50%
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 700,
        })
        assert r.json()["grade"] == "C"

    def test_grade_c_boundary_just_below_70(self):
        """完成率 97/140 ≈ 69.3% -> C"""
        completed = ALL_LEVEL_IDS[:97]
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 970,
        })
        assert r.json()["grade"] == "C"

    def test_grade_b_at_70_percent(self):
        """完成率 98/140 = 70% -> B"""
        completed = ALL_LEVEL_IDS[:98]  # 98/140 = 70%
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 980,
        })
        assert r.json()["grade"] == "B"

    def test_grade_b_boundary_just_below_90(self):
        """完成率 125/140 ≈ 89.3% -> B"""
        completed = ALL_LEVEL_IDS[:125]
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 1250,
        })
        assert r.json()["grade"] == "B"

    def test_grade_a_at_90_percent(self):
        """完成率 126/140 = 90% -> A"""
        completed = ALL_LEVEL_IDS[:126]
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 1260,
        })
        assert r.json()["grade"] == "A"

    def test_grade_a_when_full_but_few_first_try(self):
        """100% 完成但 first_try < 20 -> A"""
        r = client.post("/api/report", json={
            "completed_levels": ALL_LEVEL_IDS,
            "level_first_try": ALL_LEVEL_IDS[:10],
            "total_xp": 2800,
        })
        assert r.json()["grade"] == "A"

    def test_grade_s_full_and_20_first_try(self):
        """100% 完成 + 20 首通 -> S"""
        r = client.post("/api/report", json={
            "completed_levels": ALL_LEVEL_IDS,
            "level_first_try": ALL_LEVEL_IDS[:20],
            "total_xp": 2800,
        })
        assert r.json()["grade"] == "S"

    def test_grade_s_full_and_60_first_try(self):
        """100% 完成 + 60 首通 -> S"""
        r = client.post("/api/report", json={
            "completed_levels": ALL_LEVEL_IDS,
            "level_first_try": ALL_LEVEL_IDS,
            "total_xp": 2800,
        })
        assert r.json()["grade"] == "S"


class TestReportRecommendations:
    """学习建议生成验证"""

    def test_recommendation_not_started(self):
        """域完成率 0 -> 建议开始学习"""
        r = client.post("/api/report", json={
            "completed_levels": [],
            "total_xp": 0,
        })
        data = r.json()
        assert any("尚未开始" in rec for rec in data["recommendations"])

    def test_recommendation_low_mastery(self):
        """域完成率 < 50% -> 建议重点复习"""
        # 工作负载管理 10 关，完成 2 关 -> 20%
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1", "Q1.2"],
            "total_xp": 20,
        })
        data = r.json()
        wl_recs = [rec for rec in data["recommendations"] if "工作负载管理" in rec]
        assert len(wl_recs) == 1
        assert "掌握度偏低" in wl_recs[0]

    def test_recommendation_almost_done(self):
        """域完成率 >= 50% 但 < 100% -> 建议再完成 N 关"""
        # 工作负载管理 10 关，完成 5 关 -> 50%
        r = client.post("/api/report", json={
            "completed_levels": ["Q1.1", "Q1.2", "Q1.3", "Q1.4", "Q2.1"],
            "total_xp": 50,
        })
        data = r.json()
        wl_recs = [rec for rec in data["recommendations"] if "工作负载管理" in rec]
        assert len(wl_recs) == 1
        assert "即将通关" in wl_recs[0]
        assert "5 关" in wl_recs[0]  # 10-5=5

    def test_recommendation_none_when_full(self):
        r = client.post("/api/report", json={
            "completed_levels": ALL_LEVEL_IDS,
            "level_first_try": ALL_LEVEL_IDS,
            "total_xp": 2800,
        })
        data = r.json()
        assert len(data["recommendations"]) == 0

    def test_mixed_recommendations(self):
        """部分域未开始、部分低掌握度、部分即将通关"""
        # 工作负载管理: 3/10 = 30% -> 低掌握度
        # 网络与服务: 3/5 = 60% -> 即将通关
        # 其他 9 个域: 0% -> 未开始
        completed = ["Q1.1", "Q1.2", "Q1.3", "Q3.1", "Q3.2", "Q3.3"]
        r = client.post("/api/report", json={
            "completed_levels": completed,
            "total_xp": 60,
        })
        data = r.json()
        recs = data["recommendations"]
        assert len(recs) == 27
        assert any("掌握度偏低" in r and "工作负载管理" in r for r in recs)
        assert any("即将通关" in r and "网络与服务" in r for r in recs)
        assert any("尚未开始" in r and "配置与密钥" in r for r in recs)


# ==========================================================================
#  /api/meta 端点测试
# ==========================================================================

class TestMetaEndpoint:
    """/api/meta 端点返回结构完整性"""

    def test_meta_returns_200(self):
        r = client.get("/api/meta")
        assert r.status_code == 200

    def test_meta_has_all_keys(self):
        r = client.get("/api/meta")
        data = r.json()
        expected_keys = {"chapters", "knowledge_points", "level_xp", "ranks", "knowledge_domains"}
        assert expected_keys.issubset(set(data.keys()))

    def test_meta_has_chapter_bonus_xp(self):
        r = client.get("/api/meta")
        data = r.json()
        assert "chapter_bonus_xp" in data


class TestMetaChapters:
    """章节数量 = 24"""

    def test_chapter_count(self):
        r = client.get("/api/meta")
        chapters = r.json()["chapters"]
        assert len(chapters) == 28

    def test_chapter_ids(self):
        r = client.get("/api/meta")
        chapters = r.json()["chapters"]
        for i in range(1, 29):
            assert f"ch{i:02d}" in chapters

    def test_chapter_fields(self):
        r = client.get("/api/meta")
        chapters = r.json()["chapters"]
        for ch_id, ch_meta in chapters.items():
            assert "title" in ch_meta
            assert "icon" in ch_meta
            assert "color" in ch_meta
            assert "description" in ch_meta
            assert "difficulty" in ch_meta


class TestMetaKnowledgePoints:
    """知识点覆盖所有 120 关"""

    def test_kp_covers_all_60(self):
        r = client.get("/api/meta")
        kp = r.json()["knowledge_points"]
        assert len(kp) == 140
        for lid in ALL_LEVEL_IDS:
            assert lid in kp
            assert isinstance(kp[lid], list)
            assert len(kp[lid]) > 0

    def test_kp_q11_content(self):
        r = client.get("/api/meta")
        kp = r.json()["knowledge_points"]
        assert "Pod 概念" in kp["Q1.1"]

    def test_kp_q64_content(self):
        r = client.get("/api/meta")
        kp = r.json()["knowledge_points"]
        assert "资源限制调度" in kp["Q6.4"]


class TestMetaLevelXP:
    """XP 配置正确（每关 10 分）"""

    def test_all_levels_have_xp(self):
        r = client.get("/api/meta")
        level_xp = r.json()["level_xp"]
        assert len(level_xp) == 140

    def test_each_level_xp_is_10(self):
        r = client.get("/api/meta")
        level_xp = r.json()["level_xp"]
        for lid in ALL_LEVEL_IDS:
            assert level_xp[lid] == 10

    def test_chapter_bonus_xp(self):
        r = client.get("/api/meta")
        bonus = r.json()["chapter_bonus_xp"]
        for i in range(1, 29):
            assert bonus[f"ch{i:02d}"] == 50


class TestMetaRanks:
    """称号列表完整（8 级）"""

    def test_rank_count(self):
        r = client.get("/api/meta")
        ranks = r.json()["ranks"]
        assert len(ranks) == 8

    def test_rank_thresholds(self):
        r = client.get("/api/meta")
        ranks = r.json()["ranks"]
        thresholds = [r[0] for r in ranks]
        assert thresholds == [0, 40, 100, 180, 260, 340, 420, 500]

    def test_rank_names(self):
        r = client.get("/api/meta")
        ranks = r.json()["ranks"]
        names = [r[1] for r in ranks]
        assert "萌新" in names[0]
        assert "K8s 传奇" in names[-1]

    def test_rank_ordering(self):
        r = client.get("/api/meta")
        ranks = r.json()["ranks"]
        for i in range(len(ranks) - 1):
            assert ranks[i][0] < ranks[i + 1][0]


class TestMetaKnowledgeDomains:
    """知识域分组正确（23 域）"""

    def test_domain_count(self):
        r = client.get("/api/meta")
        domains = r.json()["knowledge_domains"]
        assert len(domains) == 27

    def test_domain_names(self):
        r = client.get("/api/meta")
        domains = r.json()["knowledge_domains"]
        expected = {
            "工作负载管理", "网络与服务", "配置与密钥", "存储管理", "调度与资源",
            "批量任务", "有状态应用", "权限管理", "自动伸缩", "入口路由", "网络安全",
            "守护进程", "资源管理", "中断保护", "优先级调度", "自定义资源", "安全与身份",
            "包管理", "存储进阶", "集群维护", "故障排查", "监控与日志", "安全策略进阶",
            "多容器模式", "高级调度", "Service Mesh", "CKA 综合考核",
        }
        assert set(domains.keys()) == expected

    def test_domain_covers_all_60(self):
        r = client.get("/api/meta")
        domains = r.json()["knowledge_domains"]
        all_covered = []
        for level_ids in domains.values():
            all_covered.extend(level_ids)
        assert len(all_covered) == 140
        assert set(all_covered) == set(ALL_LEVEL_IDS)

    def test_workload_domain_has_10(self):
        r = client.get("/api/meta")
        domains = r.json()["knowledge_domains"]
        assert len(domains["工作负载管理"]) == 10

    def test_other_domains_have_5(self):
        r = client.get("/api/meta")
        domains = r.json()["knowledge_domains"]
        for d in ["网络与服务", "配置与密钥", "存储管理", "调度与资源",
                   "批量任务", "有状态应用", "权限管理", "自动伸缩",
                   "入口路由", "网络安全"]:
            assert len(domains[d]) == 5


# ==========================================================================
#  /api/level/{id} 端点测试
# ==========================================================================

class TestLevelEndpoint:
    """所有 120 个关卡（Q1.1-Q24.5）都能正确返回"""

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_level_returns_200(self, level_id):
        r = client.get(f"/api/level/{level_id}")
        assert r.status_code == 200

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_level_has_all_fields(self, level_id):
        r = client.get(f"/api/level/{level_id}")
        data = r.json()
        assert "id" in data
        assert "chapter" in data
        assert "title" in data
        assert "description" in data
        assert "starter_yaml" in data
        assert "knowledge_points" in data
        assert "xp" in data
        assert data["id"] == level_id

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_level_xp_is_10(self, level_id):
        r = client.get(f"/api/level/{level_id}")
        assert r.json()["xp"] == 10

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_level_has_knowledge_points(self, level_id):
        r = client.get(f"/api/level/{level_id}")
        kp = r.json()["knowledge_points"]
        assert isinstance(kp, list)
        assert len(kp) > 0

    @pytest.mark.parametrize("level_id", ALL_LEVEL_IDS)
    def test_level_has_starter_yaml(self, level_id):
        r = client.get(f"/api/level/{level_id}")
        yaml_text = r.json()["starter_yaml"]
        assert isinstance(yaml_text, str)
        assert len(yaml_text) > 0

    def test_level_chapter_mapping(self):
        for ch_num in range(1, 29):
            for lv_num in range(1, 6):
                lid = f"Q{ch_num}.{lv_num}"
                r = client.get(f"/api/level/{lid}")
                assert r.json()["chapter"] == f"ch{ch_num:02d}"

    def test_nonexistent_level_returns_error(self):
        r = client.get("/api/level/Q99.1")
        data = r.json()
        assert "error" in data
        assert "Q99.1" in data["error"]

    def test_nonexistent_level_q0(self):
        r = client.get("/api/level/Q0.0")
        assert "error" in r.json()

    def test_nonexistent_level_invalid_format(self):
        r = client.get("/api/level/invalid")
        assert "error" in r.json()
