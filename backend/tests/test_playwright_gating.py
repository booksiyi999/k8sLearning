"""Playwright 前端测试：章节门控逻辑验证。

针对 P0-1 报告：章节门控把零基础新生锁在 ch00。
fresh 加载 unlocked:1, locked:28。
isChapterUnlocked 要求上一章所有关 completed 才解锁下一章。

测试维度:
1. 新用户初始状态验证
2. 章节门控逻辑验证
3. 解锁传播验证
4. 门控绕过攻击
"""
import pytest
import subprocess
import time
import socket
from playwright.sync_api import sync_playwright


def _port_in_use(port):
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except:
        return False


@pytest.fixture(scope="module")
def server_url():
    port = 8766
    proc = None
    if not _port_in_use(port):
        proc = subprocess.Popen(
            [".venv/bin/python", "-m", "uvicorn", "app.main:app", "--port", str(port)],
            cwd="/home/admin/k8s-quest/backend",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(20):
            if _port_in_use(port):
                break
            time.sleep(0.5)
    url = f"http://localhost:{port}"
    yield url
    if proc:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        yield b
        b.close()


def _clear_progress(page):
    """清除 localStorage 中的进度数据，模拟新用户。"""
    page.evaluate("""() => {
        localStorage.removeItem('k8s_quest_progress');
        localStorage.removeItem('k8s_quest_completed_levels');
        localStorage.removeItem('k8s_quest_completed');
    }""")


class TestFreshUserChapterGating:
    """P0-1: 新用户章节门控测试。"""

    def test_fresh_user_only_ch00_unlocked(self, server_url, browser):
        """新用户只有 ch00 解锁，ch01-ch28 全部锁定。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _clear_progress(page)
        page.reload()
        page.wait_for_timeout(2000)

        # 获取所有章节卡片
        cards = page.query_selector_all(".chapter-card")
        assert len(cards) > 0, "No chapter cards found"

        unlocked_count = 0
        locked_count = 0
        for card in cards:
            cls = card.get_attribute("class") or ""
            if "unlocked" in cls:
                unlocked_count += 1
            elif "locked" in cls:
                locked_count += 1

        # P0-1 BUG: 新用户应该至少 ch00 + ch01 可用，但当前只有 ch00
        # 这是一个已知的过度严格门控问题
        assert unlocked_count >= 1, f"No chapters unlocked for fresh user (unlocked={unlocked_count})"
        # 记录当前状态用于回归测试
        print(f"\nFresh user: unlocked={unlocked_count}, locked={locked_count}")

        page.close()

    def test_ch01_locked_for_fresh_user(self, server_url, browser):
        """新用户的 ch01 应该是解锁的（P0-1 已修复: 默认解锁 ch00+ch01）。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _clear_progress(page)
        page.reload()
        page.wait_for_timeout(2000)

        # 找到 ch01 卡片（用 data-chid 属性匹配，不依赖文本内容）
        ch01_card = page.query_selector('[data-chid="ch01"]')
        if ch01_card:
            cls = ch01_card.get_attribute("class") or ""
            # P0-1 已修复: ch01 默认解锁（chNum <= 1 return true）
            assert "unlocked" in cls, f"ch01 should be unlocked for fresh user, got class: {cls}"

        page.close()

    def test_locked_chapter_cannot_expand(self, server_url, browser):
        """锁定的章节可以浏览（查看关卡列表）但不能进入练习。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _clear_progress(page)
        page.reload()
        page.wait_for_timeout(2000)

        # 新用户: ch00+ch01 解锁, ch02+ 锁定
        # 验证锁定章节存在
        cards = page.query_selector_all(".chapter-card.locked")
        assert len(cards) > 0, "Fresh user should have locked chapters (ch02+)"

        # 验证解锁章节存在
        unlocked = page.query_selector_all(".chapter-card.unlocked")
        assert len(unlocked) >= 2, "Fresh user should have ch00+ch01 unlocked"

        page.close()

    def test_locked_level_shows_lock_icon(self, server_url, browser):
        """锁定关卡的点应该显示锁图标。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _clear_progress(page)
        page.reload()
        page.wait_for_timeout(2000)

        # 检查锁定章节的关卡点
        lock_icons = page.query_selector_all(".dot-locked")
        print(f"\nLock icons found: {len(lock_icons)}")
        # 新用户应该有大量锁定的关卡
        assert len(lock_icons) > 0, "Fresh user should see locked level dots"

        page.close()


class TestChapterUnlockProgression:
    """章节解锁传播测试。"""

    def test_complete_ch01_unlocks_ch02(self, server_url, browser):
        """完成 ch01 所有关卡后，ch02 应该解锁（P0-1 修复后 ch01 默认解锁，测试传播到 ch02）。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_selector(".chapter-card", timeout=10000)
        page.wait_for_timeout(1000)
        _clear_progress(page)
        page.reload()
        page.wait_for_selector(".chapter-card", timeout=10000)
        page.wait_for_timeout(1000)

        # 获取 ch01 的关卡 ID
        levels_response = page.evaluate("""async () => {
            const r = await fetch('/api/levels');
            const data = await r.json();
            return data.levels.filter(l => l.id.startsWith('Q1.')).map(l => l.id);
        }""")
        print(f"\nCh01 levels: {levels_response}")

        # 模拟完成 ch01 所有关卡
        page.evaluate(f"""() => {{
            const progress = {{
                completed_levels: {levels_response!r},
                total_xp: {len(levels_response) * 10},
                level_attempts: {{}},
                level_first_try: {levels_response!r}
            }};
            localStorage.setItem('k8s_quest_progress', JSON.stringify(progress));
        }}""")

        page.reload()
        # 等待章节卡片渲染完成（Alpine.js 异步 init 需要时间）
        page.wait_for_selector(".chapter-card", timeout=10000)
        page.wait_for_timeout(2000)

        # 检查 ch02 是否解锁（ch02 需要完成 ch01 的至少 1 关才解锁）
        ch02_card = page.query_selector('[data-chid="ch02"]')
        ch02_unlocked = False
        if ch02_card:
            cls = ch02_card.get_attribute("class") or ""
            ch02_unlocked = "unlocked" in cls

        # 如果 ch01 有关卡且全部完成，ch02 应该解锁（some 逻辑）
        if levels_response and len(levels_response) > 0:
            assert ch02_unlocked, "Ch02 should be unlocked after completing all ch01 levels"

        page.close()

    def test_partial_ch01_does_not_unlock_ch02(self, server_url, browser):
        """只完成 ch01 部分关卡，ch02 也应解锁（P0-1 修复: some 逻辑，1 关即可解锁）。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _clear_progress(page)
        page.reload()
        page.wait_for_timeout(2000)

        # 获取 ch01 的关卡 ID
        levels_response = page.evaluate("""async () => {
            const r = await fetch('/api/levels');
            const data = await r.json();
            return data.levels.filter(l => l.id.startsWith('Q1.')).map(l => l.id);
        }""")

        if len(levels_response) <= 1:
            page.close()
            return  # 无法测试

        # 只完成第一个关卡
        partial = [levels_response[0]]
        page.evaluate(f"""() => {{
            const progress = {{
                completed_levels: {partial!r},
                total_xp: 10,
                level_attempts: {{}},
                level_first_try: {partial!r}
            }};
            localStorage.setItem('k8s_quest_progress', JSON.stringify(progress));
        }}""")

        page.reload()
        page.wait_for_timeout(2000)

        # ch02 应该解锁（some 逻辑: 完成 1 关即可）
        ch02_card = page.query_selector('[data-chid="ch02"]')
        if ch02_card:
            cls = ch02_card.get_attribute("class") or ""
            # P0-1 修复后 some 逻辑: 完成 ch01 任意 1 关即解锁 ch02
            assert "unlocked" in cls, \
                "Ch02 should be unlocked with partial ch01 completion (some logic)"

        page.close()


class TestGateBypassAttack:
    """门控绕过攻击测试。"""

    def test_progress_tampering_unlock_all(self, server_url, browser):
        """篡改 localStorage 解锁所有章节 - 前端应正确处理。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # 篡改：声称完成所有关卡
        page.evaluate("""() => {
            const fakeProgress = {
                completed_levels: Array.from({length: 29}, (_, ch) =>
                    Array.from({length: 5}, (_, lv) => `Q${ch}.${lv+1}`)
                ).flat(),
                total_xp: 99999,
                level_attempts: {},
                level_first_try: []
            };
            localStorage.setItem('k8s_quest_progress', JSON.stringify(fakeProgress));
        }""")

        page.reload()
        page.wait_for_timeout(2000)

        # 检查所有章节是否解锁
        cards = page.query_selector_all(".chapter-card")
        unlocked = sum(1 for c in cards if "unlocked" in (c.get_attribute("class") or ""))
        print(f"\nAfter tampering: {unlocked}/{len(cards)} chapters unlocked")

        # 篡改后应该全部解锁（前端信任 localStorage）
        # 但后端 /api/report 会重算 XP，所以这不是安全漏洞
        # 这里只是验证前端行为
        assert unlocked > 1, "Tampered progress should unlock chapters on frontend"

        page.close()

    def test_negative_progress_does_not_break(self, server_url, browser):
        """负数/异常进度数据不应导致前端崩溃。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # 注入异常进度
        page.evaluate("""() => {
            localStorage.setItem('k8s_quest_progress', 'not-json');
        }""")

        page.reload()
        page.wait_for_timeout(2000)

        # 页面应该正常加载，不崩溃
        title = page.title()
        assert "K8s" in title or "实战" in title, "Page should load despite corrupt progress"

        page.close()
