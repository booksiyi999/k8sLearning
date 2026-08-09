"""Playwright 前端浏览器测试（精简版）。

捕获后端 API 测试无法发现的问题：
- JavaScript 运行时错误
- 页面加载完整性
- 终端输出对齐
- 关键 UI 元素存在性
"""
import pytest
import subprocess
import time
import socket
import os
from playwright.sync_api import sync_playwright


def _port_in_use(port):
    try:
        with socket.create_connection(("localhost", port), timeout=1):
            return True
    except:
        return False


@pytest.fixture(scope="module")
def server_url():
    port = 8765
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


class TestPageLoad:
    def test_page_loads_no_js_errors(self, server_url, browser):
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        assert "K8s 实战学堂" in page.title()
        assert len(errors) == 0, f"JS errors: {errors}"
        page.close()

    def test_no_external_cdn(self, server_url, browser):
        page = browser.new_page()
        cdn_urls = []
        page.on("request", lambda req: cdn_urls.append(req.url) if req.url.startswith("https://unpkg") or req.url.startswith("https://cdn") else None)
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        assert len(cdn_urls) == 0, f"External CDN: {cdn_urls}"
        page.close()


class TestChapterNav:
    def test_ch00_first(self, server_url, browser):
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        titles = page.eval_on_selector_all(".chapter-title", "els => els.map(e => e.textContent)")
        assert len(titles) > 0
        assert "架构" in titles[0] or "总览" in titles[0], f"First: {titles[0]}"
        page.close()

    def test_ch00_unlocked(self, server_url, browser):
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        card = page.query_selector(".chapter-card")
        assert card is not None
        cls = card.get_attribute("class") or ""
        assert "unlocked" in cls, f"Ch00 not unlocked: {cls}"
        page.close()


class TestTerminal:
    def test_simulator_mode_warning(self, server_url, browser):
        """模拟器模式下终端 Tab 应显示提示信息。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        # 展开第一章
        header = page.query_selector(".chapter-header")
        if header:
            header.click()
            page.wait_for_timeout(500)
        dot = page.query_selector(".level-dot-row")
        if dot:
            dot.click()
            page.wait_for_timeout(1000)
        # 切换到终端 Tab
        tab = page.query_selector("button:has-text('终端')")
        if tab:
            tab.click()
            page.wait_for_timeout(500)
            # 模拟器模式下应显示提示
            panel_text = page.eval_on_selector(".terminal-panel", "el => el.textContent")
            assert "模拟器" in panel_text or "cluster" in panel_text.lower(), \
                f"Expected simulator warning, got: {panel_text[:100]}"
        page.close()

    def test_term_lines_aligned(self, server_url, browser):
        """终端行左对齐一致性检查。"""
        page = browser.new_page()
        page.goto(server_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        # 展开第一章
        header = page.query_selector(".chapter-header")
        if header:
            header.click()
            page.wait_for_timeout(500)
        dot = page.query_selector(".level-dot-row")
        if dot:
            dot.click()
            page.wait_for_timeout(1000)
        tab = page.query_selector("button:has-text('终端')")
        if tab:
            tab.click()
            page.wait_for_timeout(500)
            paddings = page.eval_on_selector_all(
                ".term-line",
                """els => els.map(e => window.getComputedStyle(e).paddingLeft)"""
            )
            if len(paddings) > 1:
                first = paddings[0]
                for i, p in enumerate(paddings[1:], 1):
                    assert p == first, f"Line {i} padding {p} != {first}"
        page.close()


class TestPlaygroundAPI:
    def test_playground_levels(self, server_url, browser):
        page = browser.new_page()
        page.goto(f"{server_url}/api/playground/levels", wait_until="domcontentloaded")
        text = page.evaluate("() => document.body.innerText")
        assert "Q1.1" in text
        assert "Q0.1" in text
        page.close()
