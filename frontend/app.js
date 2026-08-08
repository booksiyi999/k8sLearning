// ═══════════════════════════════════════════════
// 🍒 K8s Quest - 游戏化逻辑引擎 v2
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
        this.chapters = this.meta?.chapters || {};
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
        this.hintShown = false;
        this.hints = lv.hints || [];
        this.lesson = null;
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
      const lid = this.currentLevel.id;
      this.progress.level_attempts[lid] = (this.progress.level_attempts[lid] || 0) + 1;

      try {
        const r = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ level_id: lid, user_yaml: this.userYaml })
        });
        this.result = await r.json();
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
      { id: 'pod_newbie', icon: '🌱', name: 'Pod 新手', desc: '完成 Ch1 全部 4 关', check: (s) => s.isChapterComplete('ch01') },
      { id: 'deploy_master', icon: '🚀', name: 'Deployment 大师', desc: '完成 Ch2 全部 4 关', check: (s) => s.isChapterComplete('ch02') },
      { id: 'svc_driver', icon: '🔗', name: 'Service 老司机', desc: '完成 Ch3 全部 4 关', check: (s) => s.isChapterComplete('ch03') },
      { id: 'config_expert', icon: '⚙️', name: '配置专家', desc: '完成 Ch4 全部 4 关', check: (s) => s.isChapterComplete('ch04') },
      { id: 'storage_pro', icon: '💾', name: '存储达人', desc: '完成 Ch5 全部 4 关', check: (s) => s.isChapterComplete('ch05') },
      { id: 'sched_sage', icon: '🎯', name: '调度贤者', desc: '完成 Ch6 全部 4 关', check: (s) => s.isChapterComplete('ch06') },
      { id: 'first_blood', icon: '⭐', name: '一击必杀', desc: '某关一次通过', check: (s) => s.progress.level_first_try.length > 0 },
      { id: 'persistent', icon: '💪', name: '百折不挠', desc: '某关尝试 3 次以上才通过', check: (s) => Object.entries(s.progress.level_attempts).some(([k,v]) => v >= 3 && s.progress.completed_levels.includes(k)) },
      { id: 'combo_master', icon: '⚡', name: '连击大师', desc: '连击达到 5', check: (s) => s.progress.max_streak >= 5 },
      { id: 'legend', icon: '👑', name: 'K8s 传奇', desc: '全部 24 关通关', check: (s) => s.progress.completed_levels.length >= 24 },
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
<h1>🍒 K8s Quest 结业报告</h1>
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
<p style="color:#8b9bb4;margin-top:40px">由 🍒 樱桃 K8s Quest 生成</p>
</body></html>`;
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'k8s-quest-report.html'; a.click();
      URL.revokeObjectURL(url);
      this.showToast('📥 报告已导出', 'success');
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
      for (let i = 1; i <= 6; i++) localStorage.removeItem(`bonus_ch0${i}`);
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
      return chNum ? `ch0${chNum}` : 'ch01';
    },

    isChapterUnlocked(chId) {
      const chNum = chId.replace('ch0', '');
      if (chNum === '1') return true;
      const prevNum = parseInt(chNum) - 1;
      const prevLevels = this.levels.filter(l => l.id.startsWith(`Q${prevNum}.`));
      return prevLevels.length > 0 && prevLevels.every(l => this.progress.completed_levels.includes(l.id));
    },

    isChapterComplete(chId) {
      const chNum = chId.replace('ch0', '');
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      return chLevels.length > 0 && chLevels.every(l => this.progress.completed_levels.includes(l.id));
    },

    chapterProgress(chId) {
      const chNum = chId.replace('ch0', '');
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      const done = chLevels.filter(l => this.progress.completed_levels.includes(l.id)).length;
      return `${done}/${chLevels.length}`;
    },

    chapterProgressPercent(chId) {
      const chNum = chId.replace('ch0', '');
      const chLevels = this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
      if (!chLevels.length) return 0;
      const done = chLevels.filter(l => this.progress.completed_levels.includes(l.id)).length;
      return (done / chLevels.length) * 100;
    },

    chapterLevels(chId) {
      const chNum = chId.replace('ch0', '');
      return this.levels.filter(l => l.id.startsWith(`Q${chNum}.`));
    },

    toggleChapter(chId) {
      this.expandedChapter = this.expandedChapter === chId ? null : chId;
    },

    isCompleted(lid) { return this.progress.completed_levels.includes(lid); },

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
