// ═══════════════════════════════════════════════
// K8s 实战学堂 - 游戏化逻辑引擎 v2
// 匹配 index.html (sibling version) 的数据结构
// ═══════════════════════════════════════════════

function quest() {
  return {
    ...terminalMixin(),

    // ── 核心数据 ──
    levels: [],
    currentLevel: null,
    userYaml: '',
    result: null,
    running: false,
    renderedDescription: '',
    meta: null,
    chapters: {},

    // ── 进度对象 (匹配 HTML 的 progress.xxx) ──
    progress: {
      total_xp: 0,
      streak: 0,
      max_streak: 0,
      completed_levels: [],
      level_attempts: {},
      level_first_try: [],
      level_time_spent: {},
      badges: [],
    },

    // ── UI 状态 ──
    hints: [],
    hintShown: false,
    expandedChapter: null,
    lineNumbers: '1',
    levelStartTime: null,
    rankUpAnim: false,
    badgePopAnim: null,

    // ── Toast (单条) ──
    toast: { show: false, type: 'info', message: '' },

    // ── XP 浮动动画 ──
    xpFloat: { show: false, x: 0, y: 0, text: '' },

    // ── 弹窗状态 ──
    reportModal: { show: false, loading: false },
    reportData: null,
    resetConfirm: { show: false },

    // ── Tab 状态 ──
    activeTab: 'practice',
    lesson: null,
    lessonLoading: false,
    clusterMode: false,
    clusterStatus: null,

    // ── 集群面板状态 ──
    clusterResources: [],
    clusterLogs: '',
    selectedPod: '',
    connectivityResult: null,
    connectivityService: '',
    connectivityPort: 80,

    // ── Ch28 集群验证状态 ──
    clusterVerifyResult: null,  // /api/check/cluster 的详细结果
    isCh28: false,              // 当前关卡是否属于 Ch28

    // ═══════════════════════════════════════════
    // 初始化
    // ═══════════════════════════════════════════
    async init() {
      await this.loadMeta();
      await this.loadLevels();
      this.loadProgress();
      await this.checkClusterMode();
    },

    async loadMeta() {
      try {
        const r = await fetch('/api/meta');
        this.meta = await r.json();
        const rawChapters = this.meta?.chapters || {};
        // 按 display_order 排序章节（而非 ch_id），使显示顺序可独立于 ch_id
        const sortedEntries = Object.entries(rawChapters).sort(
          (a, b) => (a[1].display_order ?? 999) - (b[1].display_order ?? 999)
        );
        this.chapters = Object.fromEntries(sortedEntries);
      } catch (e) { console.error('loadMeta:', e); }
    },

    async loadLevels() {
      try {
        const r = await fetch('/api/levels');
        const data = await r.json();
        this.levels = data.levels || [];
        if (this.levels.length > 0) {
          const first = this.levels.find(l => !this.isCompleted(l.id)) || this.levels[0];
          await this.loadLevel(first.id);
        }
      } catch (e) { console.error('loadLevels:', e); }
    },

    async loadLevel(id) {
      if (!this.isChapterUnlocked(this.getChapterId(id))) return;
      try {
        const r = await fetch(`/api/level/${id}`);
        const lv = await r.json();
        if (lv.error) { this.showToast(lv.error, 'error'); return; }
        this.currentLevel = lv;
        this.userYaml = lv.starter_yaml || '';
        this.result = null;
        this.clusterVerifyResult = null;
        this.hintShown = false;
        this.hints = lv.hints || [];
        this.lesson = null;
        this.isCh28 = lv.chapter === 'ch28';
        this.renderedDescription = this.renderMarkdown(lv.description || '');
        this.levelStartTime = Date.now();
        this.updateLineNumbers();
      } catch (e) {
        this.showToast('加载失败: ' + e, 'error');
      }
    },

    // ═══════════════════════════════════════════
    // Tab 切换 & 教学文档
    // ═══════════════════════════════════════════
    async switchTab(tab) {
      this.activeTab = tab;
      if (tab === 'lesson' && !this.lesson && this.currentLevel) {
        await this.loadLesson(this.currentLevel.id);
      }
      if (tab === 'terminal') {
        await this.termInit();
        this.termFocusInput();
      }
      if (tab === 'cluster' && this.clusterMode) {
        await this.loadClusterResources();
      }
    },

    async loadLesson(levelId) {
      this.lessonLoading = true;
      try {
        const r = await fetch(`/api/lesson/${levelId}`);
        this.lesson = await r.json();
      } catch(e) { this.lesson = {has_lesson: false}; }
      finally { this.lessonLoading = false; }
    },

    async checkClusterMode() {
      try {
        const r = await fetch('/api/cluster/status');
        this.clusterStatus = await r.json();
        this.clusterMode = this.clusterStatus.mode === 'cluster';
      } catch(e) { this.clusterMode = false; }
    },

    async deployToCluster() {
      if (!this.currentLevel || this.running) return;
      this.running = true;
      try {
        const r = await fetch('/api/deploy', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({level_id: this.currentLevel.id, user_yaml: this.userYaml})
        });
        const data = await r.json();
        if (data.mode === 'cluster') {
          this.clusterResources = data.resources || [];
          this.result = {ok: data.ok, error: data.error || '', hints: []};
        } else {
          // 回退到模拟器结果
          this.result = {ok: data.ok, error: data.error || '', hints: data.hints || [], cluster_state: data.cluster_state};
        }
      } catch(e) { this.showToast('部署失败: ' + e, 'error'); }
      finally { this.running = false; }
    },

    async loadClusterResources() {
      try {
        const r = await fetch('/api/resources');
        const data = await r.json();
        this.clusterResources = data.resources || [];
      } catch(e) {}
    },

    async loadPodLogs(podName) {
      this.selectedPod = podName;
      try {
        const r = await fetch(`/api/logs/${podName}?tail=50`);
        const data = await r.json();
        this.clusterLogs = data.logs || '';
      } catch(e) { this.clusterLogs = '获取日志失败'; }
    },

    async testConnectivity() {
      try {
        const r = await fetch('/api/test-connectivity', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({service_name: this.connectivityService, port: this.connectivityPort})
        });
        this.connectivityResult = await r.json();
      } catch(e) { this.connectivityResult = {reachable: false, error: String(e)}; }
    },

    // ═══════════════════════════════════════════
    // YAML 检查
    // ═══════════════════════════════════════════
    async runCheck() {
      if (!this.currentLevel || this.running) return;
      this.running = true;
      this.result = null;
      this.clusterVerifyResult = null;
      const lid = this.currentLevel.id;
      this.progress.level_attempts[lid] = (this.progress.level_attempts[lid] || 0) + 1;

      try {
        const r = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ level_id: lid, user_yaml: this.userYaml })
        });
        this.result = await r.json();
        // Ch28 集群模式: 获取详细的命令执行结果
        if (this.isCh28 && this.clusterMode) {
          try {
            const r2 = await fetch('/api/check/cluster', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ level_id: lid, user_input: this.userYaml })
            });
            this.clusterVerifyResult = await r2.json();
          } catch(e) { /* 静默失败, /api/check 结果已足够 */ }
        }
        if (this.result.ok) this.onPass(lid);
        else this.onFail(lid);
      } catch (e) {
        this.result = { ok: false, error: String(e), hints: [] };
        this.onFail(lid);
      } finally {
        this.running = false;
        this.saveProgress();
      }
    },

    onPass(lid) {
      const wasDone = this.progress.completed_levels.includes(lid);
      const isFirstTry = this.progress.level_attempts[lid] === 1;
      const xp = this.currentLevel?.xp || 10;

      if (!wasDone) {
        this.progress.completed_levels.push(lid);
        this.progress.total_xp += xp;
        // XP 浮动动画
        this.showXpFloat(xp);
      }

      if (isFirstTry && !this.progress.level_first_try.includes(lid)) {
        this.progress.level_first_try.push(lid);
      }

      this.progress.streak++;
      if (this.progress.streak > this.progress.max_streak) {
        this.progress.max_streak = this.progress.streak;
      }

      if (this.levelStartTime) {
        const spent = Math.floor((Date.now() - this.levelStartTime) / 1000);
        this.progress.level_time_spent[lid] = (this.progress.level_time_spent[lid] || 0) + spent;
      }

      this.checkChapterBonus(lid);
      this.checkBadges();
      this.fireConfetti();
      this.showCherryMsg();

      if (wasDone) {
        this.showToast(`✓ 再次通过！连击 x${this.progress.streak}`, 'success');
      } else {
        this.showToast(`🎉 通过！+${xp} XP · 连击 x${this.progress.streak}`, 'success');
      }
    },

    onFail(lid) {
      if (this.progress.streak > 0) {
        this.showToast(`💔 连击中断（最高 x${this.progress.max_streak}）`, 'error');
      }
      this.progress.streak = 0;
    },

    // ═══════════════════════════════════════════
    // 章节奖励
    // ═══════════════════════════════════════════
    checkChapterBonus(lid) {
      const chNum = lid.match(/Q(\d+)\./)?.[1];
      if (!chNum) return;
      const chId = `ch0${chNum}`;
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      const allDone = chLevels.every(l => this.progress.completed_levels.includes(l.id));
      if (allDone) {
        const key = `bonus_${chId}`;
        if (!localStorage.getItem(key)) {
          this.progress.total_xp += 50;
          localStorage.setItem(key, '1');
          this.showToast(`🏆 章节通关！${this.chapters[chId]?.icon} ${this.chapters[chId]?.title} +50 XP`, 'badge');
        }
      }
    },

    // ═══════════════════════════════════════════
    // 徽章系统
    // ═══════════════════════════════════════════
    badgeDefs: [
      { id: 'pod_newbie', icon: '🌱', name: 'Pod 新手', desc: '完成 Ch1 全部 7 关', check: (s) => s.isChapterComplete('ch01') },
      { id: 'deploy_master', icon: '🚀', name: 'Deployment 大师', desc: '完成 Ch2 全部 4 关', check: (s) => s.isChapterComplete('ch02') },
      { id: 'svc_driver', icon: '🔗', name: 'Service 老司机', desc: '完成 Ch3 全部 4 关', check: (s) => s.isChapterComplete('ch03') },
      { id: 'config_expert', icon: '⚙️', name: '配置专家', desc: '完成 Ch4 全部 4 关', check: (s) => s.isChapterComplete('ch04') },
      { id: 'storage_pro', icon: '💾', name: '存储达人', desc: '完成 Ch5 全部 4 关', check: (s) => s.isChapterComplete('ch05') },
      { id: 'sched_sage', icon: '🎯', name: '调度贤者', desc: '完成 Ch6 全部 4 关', check: (s) => s.isChapterComplete('ch06') },
      { id: 'first_blood', icon: '⭐', name: '一击必杀', desc: '某关一次通过', check: (s) => s.progress.level_first_try.length > 0 },
      { id: 'persistent', icon: '💪', name: '百折不挠', desc: '某关尝试 3 次以上才通过', check: (s) => Object.entries(s.progress.level_attempts).some(([k,v]) => v >= 3 && s.progress.completed_levels.includes(k)) },
      { id: 'combo_master', icon: '⚡', name: '连击大师', desc: '连击达到 5', check: (s) => s.progress.max_streak >= 5 },
      { id: 'legend', icon: '👑', name: 'K8s 传奇', desc: '全部关卡通关', check: (s) => s.progress.completed_levels.length >= s.levels.length },
    ],

    get allBadges() { return this.badgeDefs; },

    isBadgeUnlocked(badgeId) { return this.progress.badges.includes(badgeId); },

    checkBadges() {
      for (const b of this.badgeDefs) {
        if (!this.isBadgeUnlocked(b.id) && b.check(this)) {
          this.progress.badges.push(b.id);
          this.badgePopAnim = b.id;
          setTimeout(() => this.badgePopAnim = null, 1000);
          this.showToast(`🏅 徽章解锁：${b.icon} ${b.name}`, 'badge');
        }
      }
    },

    // ═══════════════════════════════════════════
    // 特效
    // ═══════════════════════════════════════════
    fireConfetti() {
      if (typeof confetti !== 'function') return;
      const colors = ['#ff6b9d', '#ffd700', '#98c379', '#61afef', '#c678dd'];
      // 左边发射
      confetti({ particleCount: 60, spread: 70, origin: { x: 0.2, y: 0.6 }, colors });
      // 右边发射
      setTimeout(() => confetti({ particleCount: 60, spread: 70, origin: { x: 0.8, y: 0.6 }, colors }), 150);
      // 中间补一波
      setTimeout(() => confetti({ particleCount: 40, spread: 100, origin: { x: 0.5, y: 0.5 }, colors }), 300);
    },

    showCherryMsg() {
      const msgs = [
        '🍒 太棒了！你正在成为 K8s 高手！',
        '🍒 漂亮！这就是 Kubernetes 的魅力！',
        '🍒 完美！继续闯关，距离传奇越来越近！',
        '🍒 厉害了！这个知识点你已经掌握了！',
        '🍒 干得漂亮！YAML 写得真不错！',
        '🍒 太强了！连 K8s 老司机都为你点赞！',
        '🍒 答对了！你就是下一个 K8s 传奇！',
        '🍒 稳！这种操作在生产环境也是满分！',
      ];
      this.showToast(msgs[Math.floor(Math.random() * msgs.length)], 'success');
    },

    showXpFloat(xp) {
      this.xpFloat = { show: true, x: window.innerWidth / 2 - 30, y: window.innerHeight / 2, text: `+${xp} XP` };
      setTimeout(() => this.xpFloat.show = false, 1500);
    },

    showToast(message, type = 'info') {
      this.toast = { show: true, type, message };
      setTimeout(() => this.toast.show = false, 3500);
    },

    // ═══════════════════════════════════════════
    // 结业报告
    // ═══════════════════════════════════════════
    async showReport() {
      this.reportModal = { show: true, loading: true };
      this.reportData = null;
      try {
        const r = await fetch('/api/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            completed_levels: this.progress.completed_levels,
            level_attempts: this.progress.level_attempts,
            level_first_try: this.progress.level_first_try,
            level_time_spent: this.progress.level_time_spent,
            total_xp: this.progress.total_xp,
          })
        });
        this.reportData = await r.json();
      } catch (e) {
        this.showToast('报告生成失败: ' + e, 'error');
        this.reportModal.show = false;
      } finally {
        this.reportModal.loading = false;
      }
    },

    exportReport() {
      if (!this.reportData) return;
      const r = this.reportData;
      const domains = Object.entries(r.domain_stats || {}).map(([d, s]) =>
        `<tr><td>${d}</td><td>${s.completed}/${s.total}</td><td>${Math.round(s.rate*100)}%</td></tr>`
      ).join('');
      const weaks = (r.weak_areas || []).map(w =>
        `<li><b>${w.level_id}</b> - ${w.reason} (知识点: ${w.knowledge_points.join(', ')})</li>`
      ).join('');
      const recs = (r.recommendations || []).map(rec => `<li>${rec}</li>`).join('');
      const colors = { S: '#ffd700', A: '#98c379', B: '#61afef', C: '#d19a66', D: '#e06c75' };
      const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>K8s Quest 结业报告</title>
<style>body{font-family:system-ui;max-width:800px;margin:40px auto;padding:20px;background:#1a1f2e;color:#e6e6e6}
h1{color:#ff6b9d}table{width:100%;border-collapse:collapse;margin:16px 0}td,th{padding:8px;border:1px solid #2a3142}
.grade{font-size:48px;font-weight:900;color:${colors[r.grade]||'#fff'}}.summary{display:flex;gap:20px;margin:20px 0}
.summary div{text-align:center;padding:12px;background:#0f1419;border-radius:8px}
</style></head><body>
<h1>🚀 K8s 实战学堂 - 结业报告</h1>
<div class="grade">${r.grade}</div>
<p>${r.grade_comment}</p>
<div class="summary">
<div><div style="font-size:24px;color:#ff6b9d">${r.completed_count}/${r.total_levels}</div>关卡完成</div>
<div><div style="font-size:24px;color:#ffd700">${r.total_xp}</div>总 XP</div>
<div><div style="font-size:24px;color:#98c379">${r.first_try_count}</div>一次通过</div>
<div><div style="font-size:24px;color:#61afef">${r.rank}</div>当前称号</div>
</div>
<h2>📈 知识域掌握度</h2>
<table><tr><th>知识域</th><th>完成</th><th>完成率</th></tr>${domains}</table>
<h2>⚠️ 薄弱项</h2>
<ul>${weaks || '<li>无</li>'}</ul>
<h2>🎯 学习建议</h2>
<ul>${recs || '<li>继续保持！</li>'}</ul>
<p style="color:#8b9bb4;margin-top:40px">由 K8s 实战学堂生成</p>
</body></html>`;
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'k8s-quest-report.html'; a.click();
      URL.revokeObjectURL(url);
      this.showToast('📥 报告已导出', 'success');
    },

    // ═══════════════════════════════════════════════
    // 进度导入导出 (v2.2)
    // ═══════════════════════════════════════════════

    async exportProgress() {
      try {
        const r = await fetch('/api/progress/export', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            completed_levels: this.progress.completed_levels,
            level_attempts: this.progress.level_attempts,
            level_first_try: this.progress.level_first_try,
            level_time_spent: this.progress.level_time_spent,
            total_xp: this.progress.total_xp,
          })
        });
        const data = await r.json();
        // 下载 JSON 文件
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        const today = new Date().toISOString().slice(0, 10);
        a.href = url;
        a.download = `k8s-quest-progress-${today}.json`;
        a.click();
        URL.revokeObjectURL(url);
        // 同步更新本地 XP 为服务端计算值
        if (data.total_xp !== this.progress.total_xp) {
          this.progress.total_xp = data.total_xp;
          this.saveProgress();
        }
        this.showToast(`📤 进度已导出 (${data.level_count} 关 · ${data.total_xp} XP)`, 'success');
      } catch (e) {
        this.showToast('导出失败: ' + e, 'error');
      }
    },

    async importProgress(event) {
      const file = event.target.files[0];
      if (!file) return;
      try {
        const text = await file.text();
        const parsed = JSON.parse(text);
        const r = await fetch('/api/progress/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(parsed)
        });
        const result = await r.json();
        if (result.valid) {
          // 验证通过，更新 localStorage
          this.progress.completed_levels = parsed.completed_levels || [];
          this.progress.level_attempts = parsed.level_attempts || {};
          this.progress.level_first_try = parsed.level_first_try || [];
          this.progress.level_time_spent = parsed.level_time_spent || {};
          this.progress.total_xp = result.total_xp;
          this.saveProgress();
          this.showToast(`📥 导入成功！${result.level_count} 关 · ${result.total_xp} XP`, 'success');
          // 刷新页面显示
          setTimeout(() => location.reload(), 1200);
        } else {
          this.showToast('❌ 导入失败：进度文件校验不通过（可能被篡改）', 'error');
        }
      } catch (e) {
        if (e instanceof SyntaxError) {
          this.showToast('❌ 导入失败：文件不是有效的 JSON', 'error');
        } else {
          this.showToast('❌ 导入失败: ' + e, 'error');
        }
      }
      // 清空 input 以便重复导入同一文件
      event.target.value = '';
    },

    exportMentorReport() {
      if (!this.reportData) return;
      const r = this.reportData;
      const today = new Date().toLocaleDateString('zh-CN');
      const studentName = prompt('请输入学员姓名（可留空）:', '') || '匿名学员';

      // 知识域掌握度表格
      const domains = Object.entries(r.domain_stats || {}).map(([d, s]) => {
        const pct = Math.round(s.rate * 100);
        const bar = '█'.repeat(Math.round(pct / 10)) + '░'.repeat(10 - Math.round(pct / 10));
        return `<tr><td>${d}</td><td>${s.completed}/${s.total}</td><td>${bar}</td><td>${pct}%</td></tr>`;
      }).join('');

      // 章节完成情况
      const chapters = Object.entries(r.chapter_stats || {}).map(([chId, s]) => {
        const pct = Math.round(s.rate * 100);
        return `<tr><td>${s.icon} ${s.title}</td><td>${s.completed}/${s.total}</td><td>${pct}%</td></tr>`;
      }).join('');

      // 薄弱项
      const weaks = (r.weak_areas || []).map(w =>
        `<tr><td>${w.level_id}</td><td>${w.reason}</td><td>${w.knowledge_points.join(', ')}</td></tr>`
      ).join('');

      // 优势项
      const strengths = (r.strengths || []).map(s =>
        `<li>${s.level_id} (${s.knowledge_points.join(', ')})</li>`
      ).join('');

      // 学习建议
      const recs = (r.recommendations || []).map(rec => `<li>${rec}</li>`).join('');

      const colors = { S: '#ffd700', A: '#98c379', B: '#61afef', C: '#d19a66', D: '#e06c75' };

      const html = `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>K8s 实战学堂 - 导师报告 (${studentName})</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,-apple-system,sans-serif;background:#f5f5f5;color:#333;line-height:1.6;padding:20px}
.report-container{max-width:900px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.1)}
.report-header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:30px;text-align:center}
.report-header h1{font-size:28px;margin-bottom:8px}
.report-header .subtitle{font-size:14px;opacity:0.9}
.report-body{padding:30px}
.section{margin-bottom:28px}
.section h2{font-size:18px;color:#333;border-left:4px solid #667eea;padding-left:10px;margin-bottom:12px}
.student-info{display:flex;gap:30px;background:#f8f9fa;padding:16px;border-radius:8px;margin-bottom:20px;flex-wrap:wrap}
.student-info div{font-size:14px}
.student-info strong{color:#667eea}
.grade-display{text-align:center;padding:20px;background:#f8f9fa;border-radius:8px;margin-bottom:20px}
.grade-display .grade{font-size:56px;font-weight:900;color:${colors[r.grade]||'#333'}}
.grade-display .comment{font-size:14px;color:#666;margin-top:4px}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px}
.summary-card{text-align:center;padding:16px;background:#f8f9fa;border-radius:8px}
.summary-card .value{font-size:24px;font-weight:700;color:#333}
.summary-card .label{font-size:12px;color:#888;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{padding:8px 10px;border:1px solid #e0e0e0;text-align:left}
th{background:#f5f5f5;font-weight:600}
.bar{font-family:monospace;color:#667eea}
.weak-list,.strength-list,.rec-list{list-style:none;padding-left:0}
.weak-list li,.rec-list li{padding:6px 10px;background:#fff5f5;border-left:3px solid #e06c75;margin-bottom:4px;border-radius:4px}
.strength-list li{padding:6px 10px;background:#f0fff0;border-left:3px solid #98c379;margin-bottom:4px;border-radius:4px}
.report-footer{text-align:center;padding:16px;background:#f8f9fa;color:#999;font-size:12px;border-top:1px solid #eee}
@media print{body{background:#fff;padding:0}.report-container{box-shadow:none;border-radius:0}}
</style></head><body>
<div class="report-container">
  <div class="report-header">
    <h1>🚀 K8s 实战学堂 - 学员进度报告</h1>
    <div class="subtitle">导师专用报告 · ${today}</div>
  </div>
  <div class="report-body">
    <!-- 学员信息 -->
    <div class="student-info">
      <div>学员姓名：<strong>${studentName}</strong></div>
      <div>当前称号：<strong>${r.rank}</strong></div>
      <div>报告日期：<strong>${today}</strong></div>
    </div>

    <!-- 成绩评定 -->
    <div class="grade-display">
      <div class="grade">${r.grade}</div>
      <div class="comment">${r.grade_comment}</div>
    </div>

    <!-- 综合数据 -->
    <div class="summary-grid">
      <div class="summary-card"><div class="value" style="color:#ff6b9d">${r.completed_count}/${r.total_levels}</div><div class="label">关卡完成</div></div>
      <div class="summary-card"><div class="value" style="color:#ffd700">${r.total_xp}</div><div class="label">总 XP</div></div>
      <div class="summary-card"><div class="value" style="color:#98c379">${Math.round(r.completion_rate*100)}%</div><div class="label">完成率</div></div>
      <div class="summary-card"><div class="value" style="color:#61afef">${r.first_try_count}</div><div class="label">一次通过</div></div>
      <div class="summary-card"><div class="value" style="color:#c678dd">${r.total_attempts}</div><div class="label">总尝试次数</div></div>
      <div class="summary-card"><div class="value" style="color:#e06c75">${this.formatTime(r.total_time_spent)}</div><div class="label">总学习时长</div></div>
    </div>

    <!-- 知识域掌握度 -->
    <div class="section">
      <h2>📈 知识域掌握度</h2>
      <table><thead><tr><th>知识域</th><th>完成</th><th>进度条</th><th>完成率</th></tr></thead><tbody>${domains}</tbody></table>
    </div>

    <!-- 章节完成情况 -->
    <div class="section">
      <h2>📖 章节完成情况</h2>
      <table><thead><tr><th>章节</th><th>完成</th><th>完成率</th></tr></thead><tbody>${chapters}</tbody></table>
    </div>

    <!-- 薄弱项 -->
    <div class="section" ${r.weak_areas.length === 0 ? 'style="display:none"' : ''}>
      <h2>⚠️ 薄弱项分析</h2>
      <table><thead><tr><th>关卡</th><th>原因</th><th>知识点</th></tr></thead><tbody>${weaks}</tbody></table>
    </div>

    <!-- 优势项 -->
    <div class="section" ${r.strengths.length === 0 ? 'style="display:none"' : ''}>
      <h2>⭐ 优势项（一次通过）</h2>
      <ul class="strength-list">${strengths || '<li>暂无</li>'}</ul>
    </div>

    <!-- 学习建议 -->
    <div class="section" ${r.recommendations.length === 0 ? 'style="display:none"' : ''}>
      <h2>💡 学习建议</h2>
      <ul class="rec-list">${recs || '<li>继续保持！</li>'}</ul>
    </div>
  </div>
  <div class="report-footer">
    本报告由 K8s 实战学堂自动生成 · 服务端验证 · 数据可信<br>
    生成时间：${new Date().toLocaleString('zh-CN')}
  </div>
</div>
</body></html>`;

      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `k8s-quest-mentor-report-${studentName}-${today}.html`;
      a.click();
      URL.revokeObjectURL(url);
      this.showToast('📤 导师报告已导出', 'success');
    },

    // ═══════════════════════════════════════════
    // 重置
    // ═══════════════════════════════════════════
    confirmReset() { this.resetConfirm.show = true; },

    doReset() {
      this.resetConfirm.show = false;
      this.progress = {
        total_xp: 0, streak: 0, max_streak: 0,
        completed_levels: [], level_attempts: {},
        level_first_try: [], level_time_spent: {}, badges: [],
      };
      for (let i = 0; i <= 28; i++) localStorage.removeItem(`bonus_ch${i.toString().padStart(2, '0')}`);
      this.saveProgress();
      this.showToast('✓ 进度已重置', 'info');
      if (this.levels.length > 0) this.loadLevel(this.levels[0].id);
    },

    resetAll() { this.confirmReset(); },

    // ═══════════════════════════════════════════
    // 进度持久化
    // ═══════════════════════════════════════════
    saveProgress() {
      localStorage.setItem('k8s_quest_progress', JSON.stringify(this.progress));
    },

    loadProgress() {
      try {
        const saved = localStorage.getItem('k8s_quest_progress');
        if (saved) {
          const p = JSON.parse(saved);
          this.progress = { ...this.progress, ...p };
        }
      } catch (e) { console.error('loadProgress:', e); }
    },

    // ═══════════════════════════════════════════
    // 辅助方法
    // ═══════════════════════════════════════════
    resetYaml() {
      if (this.currentLevel) {
        this.userYaml = this.currentLevel.starter_yaml || '';
        this.result = null;
        this.updateLineNumbers();
      }
    },

    showHint() { this.hintShown = true; },

    getChapterId(lid) {
      const chNum = lid.match(/Q(\d+)\./)?.[1];
      return chNum ? `ch${chNum.padStart(2, '0')}` : 'ch01';
    },

    isChapterUnlocked(chId) {
      const chNum = parseInt(chId.replace('ch', ''));
      if (isNaN(chNum) || chNum <= 0) return true;  // ch00 始终解锁
      const prevNum = chNum - 1;
      const prevLevels = this.levels.filter(l => l.id.startsWith(`Q${prevNum}.`));
      return prevLevels.length > 0 && prevLevels.every(l => this.progress.completed_levels.includes(l.id));
    },

    isChapterComplete(chId) {
      const chNum = parseInt(chId.replace('ch', ''));
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      return chLevels.length > 0 && chLevels.every(l => this.progress.completed_levels.includes(l.id));
    },

    chapterProgress(chId) {
      const chNum = parseInt(chId.replace('ch', ''));
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      const done = chLevels.filter(l => this.progress.completed_levels.includes(l.id)).length;
      return `${done}/${chLevels.length}`;
    },

    chapterProgressPercent(chId) {
      const chNum = parseInt(chId.replace('ch', ''));
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      if (!chLevels.length) return 0;
      const done = chLevels.filter(l => this.progress.completed_levels.includes(l.id)).length;
      return (done / chLevels.length) * 100;
    },

    chapterLevels(chId) {
      const chNum = parseInt(chId.replace('ch', ''));
      return this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
    },

    toggleChapter(chId) {
      this.expandedChapter = this.expandedChapter === chId ? null : chId;
    },

    isCompleted(lid) { return this.progress.completed_levels.includes(lid); },

    // ── 双轨制: 章节赛道标签 ──
    chapterTrack(chId) {
      return this.chapters?.[chId]?.track || '基础级';
    },

    trackIcon(track) {
      const icons = { '基础级': '📗', '认知级': '📘', '实战级': '📙' };
      return icons[track] || '📗';
    },

    trackClass(track) {
      const classes = { '基础级': 'track-basic', '认知级': 'track-cognitive', '实战级': 'track-practical' };
      return classes[track] || 'track-basic';
    },

    // 当前关卡的检查按钮文本
    get checkButtonLabel() {
      if (this.running) return '⏳ 检查中...';
      if (this.isCh28 && this.clusterMode) return '▶ 集群验证';
      return '▶ 模拟器校验';
    },

    // 当前关卡是否为实战级 (支持集群验证)
    get isPracticalTrack() {
      if (!this.currentLevel) return false;
      const chId = this.currentLevel.chapter;
      return this.chapters?.[chId]?.track === '实战级';
    },

    // ── 计算属性 ──
    get currentRank() {
      if (!this.meta?.ranks) return '🎓 K8s 萌新';
      let name = this.meta.ranks[0]?.[1] || '🎓 K8s 萌新';
      for (const [threshold, n] of this.meta.ranks) {
        if (this.progress.total_xp >= threshold) name = n;
      }
      return name;
    },

    get xpPercent() {
      if (!this.meta?.ranks) return 0;
      let prev = 0;
      for (const [threshold, _] of this.meta.ranks) {
        if (this.progress.total_xp < threshold) {
          return Math.round(((this.progress.total_xp - prev) / (threshold - prev)) * 100);
        }
        prev = threshold;
      }
      return 100;
    },

    get xpBarLabel() {
      if (!this.meta?.ranks) return '';
      for (const [threshold, name] of this.meta.ranks) {
        if (this.progress.total_xp < threshold) {
          return `${this.progress.total_xp} / ${threshold}`;
        }
      }
      return `${this.progress.total_xp} XP`;
    },

    get totalAttempts() {
      return Object.values(this.progress.level_attempts).reduce((a, b) => a + b, 0);
    },

    get totalTimeSpent() {
      return Object.values(this.progress.level_time_spent).reduce((a, b) => a + b, 0);
    },

    // ── 时间格式化 ──
    formatTime(seconds) {
      if (!seconds || seconds === 0) return '0s';
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      return m > 0 ? `${m}m ${s}s` : `${s}s`;
    },

    // ── 行号 ──
    updateLineNumbers() {
      const lines = (this.userYaml || '').split('\n').length;
      this.lineNumbers = Array.from({ length: Math.max(lines, 1) }, (_, i) => i + 1).join('<br>');
    },

    insertTab(event) {
      const textarea = event.target;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      this.userYaml = this.userYaml.substring(0, start) + '  ' + this.userYaml.substring(end);
      this.$nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
      });
      this.updateLineNumbers();
    },

    // ── Markdown 渲染 ──
    renderMarkdown(md) {
      if (!md) return '';
      // 优先使用 marked.js
      if (typeof marked !== 'undefined') {
        try { return marked.parse(md); } catch (e) { /* fall through */ }
      }
      // 降级：极简 markdown
      return md.split('\n').map(line => {
        if (line.startsWith('# ')) return `<h1>${this.escapeHtml(line.slice(2))}</h1>`;
        if (line.startsWith('## ')) return `<h2>${this.escapeHtml(line.slice(3))}</h2>`;
        if (line.startsWith('### ')) return `<h3>${this.escapeHtml(line.slice(4))}</h3>`;
        if (line.startsWith('- ') || line.startsWith('* ')) return `<p>• ${this.escapeHtml(line.slice(2))}</p>`;
        if (line.trim() === '') return '<br>';
        return `<p>${this.escapeHtml(line)}</p>`;
      }).join('');
    },

    escapeHtml(text) {
      const div = document.createElement('div');
      div.textContent = text;
      return div.innerHTML;
    },
  };
}
