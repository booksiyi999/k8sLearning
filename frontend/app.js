/* ============================================
 * 🍒 樱桃的 K8s Quest - 前端核心逻辑
 * 游戏化学习平台: XP/等级/连击/徽章/结业报告
 * 使用 Alpine.js 响应式框架 + localStorage 持久化
 * ============================================ */

function quest() {
  return {
    // ==================== 状态数据 ====================
    levels: [],           // 所有关卡列表 (从 /api/levels 获取)
    chapters: {},         // 章节元数据 (从 /api/meta 获取)
    meta: null,           // 完整元数据 (ranks, knowledge_domains 等)
    currentLevel: null,   // 当前选中的关卡详情
    userYaml: '',         // 用户输入的 YAML
    result: null,         // 检查结果
    running: false,       // 是否正在检查
    renderedDescription: '', // 渲染后的 Markdown HTML
    lineNumbers: '1',     // YAML 编辑器行号
    hints: [],            // 当前关卡提示
    hintShown: false,     // 是否显示提示
    expandedChapter: 'ch01', // 当前展开的章节

    // 进度数据 (localStorage 持久化)
    progress: {
      completed_levels: [],
      level_attempts: {},
      level_first_try: [],
      level_time_spent: {},
      total_xp: 0,
      streak: 0,
      max_streak: 0,
      badges: [],
      level_start_time: {},
      last_visited_level: null,
      start_time: Date.now(),
    },

    // UI 状态
    toast: { show: false, message: '', type: 'info' },
    xpFloat: { show: false, text: '', x: 0, y: 0 },
    rankUpAnim: false,
    badgePopAnim: null,
    reportModal: { show: false, loading: false },
    reportData: null,
    resetConfirm: { show: false },

    // 徽章定义
    allBadges: [
      { id: 'ch01', name: 'Pod 新手', icon: '🌱', desc: '完成第一章 Pod 基础' },
      { id: 'ch02', name: 'Deployment 大师', icon: '🚀', desc: '完成第二章 Deployment' },
      { id: 'ch03', name: 'Service 老司机', icon: '🔗', desc: '完成第三章 Service 网络' },
      { id: 'ch04', name: '配置专家', icon: '⚙️', desc: '完成第四章配置管理' },
      { id: 'ch05', name: '存储达人', icon: '💾', desc: '完成第五章存储' },
      { id: 'ch06', name: '调度贤者', icon: '🎯', desc: '完成第六章调度' },
      { id: 'first_try', name: '一击必杀', icon: '⭐', desc: '一次通过关卡 (无失败尝试)' },
      { id: 'persistent', name: '百折不挠', icon: '💪', desc: '尝试3次以上才通过' },
      { id: 'speedrun', name: '速通达人', icon: '⚡', desc: '60秒内完成关卡' },
      { id: 'legend', name: 'K8s 传奇', icon: '👑', desc: '全部24关通关' },
    ],

    // 樱桃鼓励语 (成功时随机)
    successMessages: [
      '干得漂亮！🐱✨',
      '喵～完美通过！',
      '太强了！继续加油喵～🍒',
      '哇！这波操作很稳喵！',
      '樱桃为你骄傲！🌸',
      'YAML 写得真好看喵～',
    ],
    // 樱桃鼓励语 (失败时随机)
    failMessages: [
      '差一点点喵！再试试～',
      '别灰心，YAML 少个空格都很常见喵',
      '樱桃相信你可以的！再试一次～',
      '嗯...检查下缩进？K8s 的 YAML 很严格喵',
      '没关系，错误也是学习的一部分喵！',
    ],

    // ==================== 初始化 ====================
    async init() {
      this.loadProgress();   // 从 localStorage 恢复进度
      await this.loadMeta(); // 加载元数据
      await this.loadLevels(); // 加载关卡列表
      // 恢复上次访问的关卡
      const lastLevel = this.progress.last_visited_level;
      if (lastLevel) {
        await this.loadLevel(lastLevel);
      } else if (this.levels.length > 0) {
        await this.loadLevel(this.levels[0].id);
      }
    },

    // ==================== API 调用 ====================
    async loadMeta() {
      try {
        const r = await fetch('/api/meta');
        this.meta = await r.json();
        this.chapters = this.meta.chapters;
      } catch (e) {
        console.error('加载元数据失败:', e);
      }
    },

    async loadLevels() {
      try {
        const r = await fetch('/api/levels');
        const data = await r.json();
        this.levels = data.levels;
      } catch (e) {
        console.error('加载关卡列表失败:', e);
      }
    },

    async loadLevel(id) {
      try {
        const r = await fetch(`/api/level/${id}`);
        const lv = await r.json();
        if (lv.error) {
          this.showToast(lv.error, 'error');
          return;
        }
        this.currentLevel = lv;
        this.userYaml = lv.starter_yaml || '';
        this.result = null;
        this.hintShown = false;
        this.hints = lv.hints || [];
        this.renderedDescription = this.renderMarkdown(lv.description || '');
        this.updateLineNumbers();

        // 记录关卡开始时间 (如果还没记录)
        if (!this.progress.level_start_time[id]) {
          this.progress.level_start_time[id] = Date.now();
        }
        this.progress.last_visited_level = id;
        this.saveProgress();
      } catch (e) {
        console.error('加载关卡失败:', e);
        this.showToast('加载关卡失败: ' + String(e), 'error');
      }
    },

    async runCheck() {
      if (this.running || !this.currentLevel) return;
      this.running = true;
      this.result = null;
      try {
        const r = await fetch('/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            level_id: this.currentLevel.id,
            user_yaml: this.userYaml,
          }),
        });
        this.result = await r.json();
        this.handleCheckResult();
      } catch (e) {
        this.result = { ok: false, error: String(e), hints: [] };
        this.showToast('网络错误: ' + String(e), 'error');
      } finally {
        this.running = false;
      }
    },

    // ==================== 检查结果处理 (核心游戏逻辑) ====================
    handleCheckResult() {
      const levelId = this.currentLevel.id;
      const wasCompleted = this.progress.completed_levels.includes(levelId);

      // 记录尝试次数
      this.progress.level_attempts[levelId] = (this.progress.level_attempts[levelId] || 0) + 1;

      if (this.result.ok) {
        // ==================== 成功 ====================
        this.onLevelSuccess(levelId, wasCompleted);
      } else {
        // ==================== 失败 ====================
        this.onLevelFail(levelId);
      }
      this.saveProgress();
    },

    // 成功处理
    onLevelSuccess(levelId, wasCompleted) {
      const attempts = this.progress.level_attempts[levelId];
      const isFirstTry = attempts === 1;
      const startTime = this.progress.level_start_time[levelId];
      const timeSpent = startTime ? Math.round((Date.now() - startTime) / 1000) : 0;

      // 记录用时
      this.progress.level_time_spent[levelId] = timeSpent;

      // 如果是首次通过
      if (!wasCompleted) {
        // 添加到已完成列表
        this.progress.completed_levels.push(levelId);

        // 一次通过标记
        if (isFirstTry) {
          this.progress.level_first_try.push(levelId);
        }

        // 增加 XP
        const levelXp = this.currentLevel.xp || 10;
        const oldRank = this.currentRank;
        this.progress.total_xp += levelXp;

        // 连击+1
        this.progress.streak += 1;
        this.progress.max_streak = Math.max(this.progress.max_streak, this.progress.streak);

        // 检查称号是否升级
        const newRank = this.computeRank(this.progress.total_xp);
        if (newRank !== oldRank) {
          this.rankUpAnim = true;
          setTimeout(() => { this.rankUpAnim = false; }, 1000);
          this.showToast('🎉 称号升级！' + newRank, 'celebrate');
        }

        // +XP 浮动动画
        this.showXpFloat('+' + levelXp + ' XP');

        // 纸屑特效
        this.fireConfetti();

        // 绿色闪光
        const detailEl = document.querySelector('.level-detail');
        if (detailEl) {
          detailEl.classList.add('green-flash');
          setTimeout(() => detailEl.classList.remove('green-flash'), 500);
        }

        // 樱桃鼓励语
        const msg = this.successMessages[Math.floor(Math.random() * this.successMessages.length)];
        this.showToast(msg, 'success');

        // 连击>=3 特殊提示
        if (this.progress.streak >= 3) {
          setTimeout(() => {
            this.showToast('🔥 连击 x' + this.progress.streak + '！势不可挡喵！', 'celebrate');
          }, 800);
        }

        // 检查徽章
        this.checkBadges(levelId, isFirstTry, timeSpent);

        // 检查章节通关
        this.checkChapterComplete(levelId);
      } else {
        // 重复通关，只给鼓励
        this.showToast('🎉 又通过了！继续探索其他关卡吧～', 'success');
      }
    },

    // 失败处理
    onLevelFail(levelId) {
      // 连击归零
      this.progress.streak = 0;
      // 红色震动效果 (CSS 类已加在 result-fail 上)
      const msg = this.failMessages[Math.floor(Math.random() * this.failMessages.length)];
      this.showToast(msg, 'error');
    },

    // ==================== 徽章检查 ====================
    checkBadges(levelId, isFirstTry, timeSpent) {
      const newBadges = [];

      // 章节通关徽章
      const chapterId = this.currentLevel.chapter;
      if (this.isChapterComplete(chapterId)) {
        if (!this.progress.badges.includes(chapterId)) {
          newBadges.push(chapterId);
        }
      }

      // 一击必杀徽章
      if (isFirstTry && !this.progress.badges.includes('first_try')) {
        newBadges.push('first_try');
      }

      // 百折不挠徽章
      const attempts = this.progress.level_attempts[levelId];
      if (attempts >= 3 && !this.progress.badges.includes('persistent')) {
        newBadges.push('persistent');
      }

      // 速通达人徽章
      if (timeSpent > 0 && timeSpent <= 60 && !this.progress.badges.includes('speedrun')) {
        newBadges.push('speedrun');
      }

      // K8s 传奇徽章
      if (this.progress.completed_levels.length >= 24 && !this.progress.badges.includes('legend')) {
        newBadges.push('legend');
      }

      // 解锁新徽章
      for (const badgeId of newBadges) {
        this.progress.badges.push(badgeId);
        const badge = this.allBadges.find(b => b.id === badgeId);
        if (badge) {
          this.badgePopAnim = badgeId;
          setTimeout(() => { this.badgePopAnim = null; }, 1000);
          setTimeout(() => {
            this.showToast('🏅 徽章解锁: ' + badge.icon + ' ' + badge.name + '！', 'celebrate');
          }, 600);
        }
      }
    },

    // ==================== 章节通关检查 ====================
    checkChapterComplete(levelId) {
      const chapterId = this.currentLevel.chapter;
      if (this.isChapterComplete(chapterId)) {
        const ch = this.chapters[chapterId];
        if (ch) {
          // 章节通关奖励 XP
          const bonusXp = (this.meta && this.meta.chapter_bonus_xp && this.meta.chapter_bonus_xp[chapterId]) || 50;
          // 只在首次通关时给奖励 (检查是否已有该章节徽章)
          if (!this.progress.badges.includes(chapterId)) {
            this.progress.total_xp += bonusXp;
            this.showXpFloat('+' + bonusXp + ' XP 章节奖励!');

            // 大型庆祝特效
            this.fireConfetti(true);

            setTimeout(() => {
              this.showToast('🎉 恭喜通关【' + ch.title + '】！获得' + this.getChapterBadgeName(chapterId) + '徽章！', 'celebrate');
            }, 1200);

            // 检查是否解锁了新章节
            const nextChapter = this.getNextChapter(chapterId);
            if (nextChapter) {
              setTimeout(() => {
                this.showToast('🎉 新章节已解锁: ' + this.chapters[nextChapter].icon + ' ' + this.chapters[nextChapter].title + '！', 'celebrate');
              }, 2400);
            }
          }
        }
      }
    },

    getChapterBadgeName(chapterId) {
      const badge = this.allBadges.find(b => b.id === chapterId);
      return badge ? (badge.icon + ' ' + badge.name) : '';
    },

    // ==================== 计算属性 ====================
    get currentRank() {
      return this.computeRank(this.progress.total_xp);
    },

    computeRank(xp) {
      if (!this.meta || !this.meta.ranks) return '🎓 K8s 萌新';
      let rank = this.meta.ranks[0][1];
      for (const item of this.meta.ranks) {
        const threshold = item[0];
        const name = item[1];
        if (xp >= threshold) rank = name;
      }
      return rank;
    },

    get nextRank() {
      if (!this.meta || !this.meta.ranks) return null;
      for (const item of this.meta.ranks) {
        const threshold = item[0];
        const name = item[1];
        if (this.progress.total_xp < threshold) return name;
      }
      return null;
    },

    get xpToNextRank() {
      if (!this.meta || !this.meta.ranks) return 0;
      for (const item of this.meta.ranks) {
        const threshold = item[0];
        if (this.progress.total_xp < threshold) return threshold - this.progress.total_xp;
      }
      return 0;
    },

    get xpPercent() {
      if (!this.meta || !this.meta.ranks || this.meta.ranks.length < 2) return 0;
      // 找到当前段位和下一段位
      let currentThreshold = 0;
      let nextThreshold = this.meta.ranks[this.meta.ranks.length - 1][0];
      for (let i = 0; i < this.meta.ranks.length; i++) {
        if (this.progress.total_xp >= this.meta.ranks[i][0]) {
          currentThreshold = this.meta.ranks[i][0];
          if (i + 1 < this.meta.ranks.length) {
            nextThreshold = this.meta.ranks[i + 1][0];
          } else {
            // 已满级
            return 100;
          }
        }
      }
      const range = nextThreshold - currentThreshold;
      const current = this.progress.total_xp - currentThreshold;
      return range > 0 ? Math.min(100, (current / range) * 100) : 100;
    },

    get xpBarLabel() {
      if (this.nextRank) {
        return this.progress.total_xp + ' / 距 ' + this.nextRank + ' 还需 ' + this.xpToNextRank + ' XP';
      }
      return this.progress.total_xp + ' XP · 已满级 👑';
    },

    get totalAttempts() {
      return Object.values(this.progress.level_attempts).reduce((a, b) => a + b, 0);
    },

    get totalTimeSpent() {
      return Object.values(this.progress.level_time_spent).reduce((a, b) => a + b, 0);
    },

    // ==================== 章节相关方法 ====================
    chapterLevels(chId) {
      // chId 格式如 "ch01", 提取数字部分匹配关卡 ID 前缀
      const num = chId.replace('ch', '');
      return this.levels.filter(lv => lv.id.startsWith('Q' + num + '.'));
    },

    chapterProgress(chId) {
      const levels = this.chapterLevels(chId);
      const completed = levels.filter(lv => this.isCompleted(lv.id)).length;
      return completed + '/' + levels.length;
    },

    chapterProgressPercent(chId) {
      const levels = this.chapterLevels(chId);
      if (levels.length === 0) return 0;
      const completed = levels.filter(lv => this.isCompleted(lv.id)).length;
      return (completed / levels.length) * 100;
    },

    isChapterComplete(chId) {
      const levels = this.chapterLevels(chId);
      return levels.length > 0 && levels.every(lv => this.isCompleted(lv.id));
    },

    isChapterUnlocked(chId) {
      // 第一章始终解锁
      if (chId === 'ch01') return true;
      // 前一章全部通关才解锁
      const chapterNum = parseInt(chId.replace('ch', ''));
      const prevChId = 'ch' + String(chapterNum - 1).padStart(2, '0');
      return this.isChapterComplete(prevChId);
    },

    getNextChapter(chId) {
      const num = parseInt(chId.replace('ch', ''));
      const nextNum = num + 1;
      if (nextNum > 6) return null;
      return 'ch' + String(nextNum).padStart(2, '0');
    },

    toggleChapter(chId) {
      if (this.expandedChapter === chId) {
        this.expandedChapter = null;
      } else {
        this.expandedChapter = chId;
      }
    },

    // ==================== 状态检查方法 ====================
    isCompleted(levelId) {
      return this.progress.completed_levels.includes(levelId);
    },

    isBadgeUnlocked(badgeId) {
      // 特殊徽章逻辑
      if (badgeId === 'first_try') {
        return this.progress.badges.includes('first_try') ||
               this.progress.level_first_try.length > 0;
      }
      if (badgeId === 'persistent') {
        return this.progress.badges.includes('persistent');
      }
      if (badgeId === 'speedrun') {
        return this.progress.badges.includes('speedrun');
      }
      if (badgeId === 'legend') {
        return this.progress.completed_levels.length >= 24;
      }
      // 章节徽章
      return this.progress.badges.includes(badgeId) ||
             (this.chapters[badgeId] && this.isChapterComplete(badgeId));
    },

    // ==================== UI 方法 ====================
    resetYaml() {
      if (this.currentLevel) {
        this.userYaml = this.currentLevel.starter_yaml || '';
        this.result = null;
        this.updateLineNumbers();
      }
    },

    showHint() {
      // 尝试获取提示: 如果有关卡自带 hints 就用，否则给通用提示
      if (this.hints && this.hints.length > 0) {
        this.hintShown = true;
      } else {
        // 通用提示
        this.hints = ['检查 YAML 缩进是否正确 (K8s 使用空格而非 Tab)', '确认 apiVersion、kind、metadata、spec 字段是否齐全'];
        this.hintShown = true;
      }
    },

    updateLineNumbers() {
      const lines = this.userYaml.split('\n').length;
      this.lineNumbers = Array.from({ length: Math.max(lines, 1) }, (_, i) => i + 1).join('\n');
    },

    insertTab(event) {
      // Tab 键插入两个空格 (YAML 规范)
      const textarea = event.target;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      this.userYaml = this.userYaml.substring(0, start) + '  ' + this.userYaml.substring(end);
      this.$nextTick(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
        this.updateLineNumbers();
      });
    },

    // Markdown 渲染 (使用 marked.js)
    renderMarkdown(md) {
      if (typeof marked !== 'undefined' && marked.parse) {
        return marked.parse(md);
      }
      // 降级: 极简渲染
      return md
        .split('\n')
        .map(line => {
          if (line.startsWith('# ')) return '<h1>' + line.slice(2) + '</h1>';
          if (line.startsWith('## ')) return '<h2>' + line.slice(3) + '</h2>';
          if (line.startsWith('### ')) return '<h3>' + line.slice(4) + '</h3>';
          if (line.trim() === '') return '<br>';
          return '<p>' + line + '</p>';
        })
        .join('');
    },

    // ==================== 特效方法 ====================
    fireConfetti(big) {
      if (typeof confetti !== 'function') return;
      if (big) {
        // 大型庆祝: 多波纸屑
        const duration = 3000;
        const animationEnd = Date.now() + duration;
        const colors = ['#ff6b9d', '#ffd700', '#4caf50', '#2196f3', '#ff9800'];
        const frame = () => {
          confetti({
            particleCount: 5,
            angle: 60,
            spread: 70,
            origin: { x: 0, y: 0.7 },
            colors: colors,
          });
          confetti({
            particleCount: 5,
            angle: 120,
            spread: 70,
            origin: { x: 1, y: 0.7 },
            colors: colors,
          });
          if (Date.now() < animationEnd) requestAnimationFrame(frame);
        };
        frame();
        // 中央爆发
        confetti({
          particleCount: 100,
          spread: 100,
          origin: { y: 0.5 },
          colors: colors,
        });
      } else {
        // 普通庆祝
        confetti({
          particleCount: 60,
          spread: 70,
          origin: { y: 0.6 },
          colors: ['#ff6b9d', '#ffd700', '#4caf50'],
        });
      }
    },

    showXpFloat(text) {
      this.xpFloat = {
        show: true,
        text: text,
        x: window.innerWidth / 2 - 50,
        y: window.innerHeight / 2,
      };
      setTimeout(() => { this.xpFloat.show = false; }, 1500);
    },

    showToast(message, type) {
      type = type || 'info';
      this.toast = { show: true, message: message, type: type };
      setTimeout(() => { this.toast.show = false; }, 3000);
    },

    // ==================== 时间格式化 ====================
    formatTime(seconds) {
      if (seconds < 60) return seconds + '秒';
      if (seconds < 3600) return Math.floor(seconds / 60) + '分' + (seconds % 60) + '秒';
      return Math.floor(seconds / 3600) + '时' + Math.floor((seconds % 3600) / 60) + '分';
    },

    // ==================== localStorage 持久化 ====================
    loadProgress() {
      try {
        const saved = localStorage.getItem('k8s_quest_progress');
        if (saved) {
          const data = JSON.parse(saved);
          // 合并保存的数据和默认值 (防止字段缺失)
          this.progress = Object.assign({}, this.progress, data);
        }
      } catch (e) {
        console.error('加载进度失败:', e);
      }
    },

    saveProgress() {
      try {
        localStorage.setItem('k8s_quest_progress', JSON.stringify(this.progress));
      } catch (e) {
        console.error('保存进度失败:', e);
      }
    },

    // ==================== 结业报告 ====================
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
          }),
        });
        this.reportData = await r.json();
      } catch (e) {
        this.showToast('生成报告失败: ' + String(e), 'error');
      } finally {
        this.reportModal.loading = false;
      }
    },

    // 导出报告为 HTML 文件
    exportReport() {
      if (!this.reportData) return;
      const html = this.generateReportHtml();
      const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'k8s-quest-report.html';
      a.click();
      URL.revokeObjectURL(url);
    },

    generateReportHtml() {
      const d = this.reportData;
      const domains = Object.entries(d.domain_stats || {}).map(function(entry) {
        var name = entry[0], s = entry[1];
        return '<div style="margin:8px 0"><div style="display:flex;justify-content:space-between;font-size:13px"><span>' + name + '</span><span>' + s.completed + '/' + s.total + '</span></div><div style="height:8px;background:#1a1f2e;border-radius:4px;margin-top:4px"><div style="height:100%;width:' + (s.rate * 100) + '%;background:linear-gradient(90deg,#ff6b9d,#ffd700);border-radius:4px"></div></div></div>';
      }).join('');

      const weakAreas = (d.weak_areas || []).map(function(w) {
        return '<div style="padding:8px 12px;background:rgba(244,67,54,0.1);border-radius:8px;margin:4px 0;font-size:13px"><strong>' + w.level_id + '</strong> - ' + w.reason + ' (' + w.knowledge_points.join(', ') + ')</div>';
      }).join('');

      const strengths = (d.strengths || []).map(function(s) {
        return '<span style="background:rgba(76,175,80,0.1);color:#4caf50;padding:3px 10px;border-radius:12px;font-size:12px">' + s.level_id + '</span>';
      }).join(' ');

      const recs = (d.recommendations || []).map(function(r) {
        return '<li style="padding:8px 12px;background:#1a1f2e;border-radius:8px;margin:4px 0;font-size:13px;color:#8b95a7;border-left:3px solid #ff6b9d">' + r + '</li>';
      }).join('');

      return '<!DOCTYPE html><html><head><meta charset="UTF-8"><title>K8s Quest 结业报告</title>' +
        '<style>body{font-family:system-ui;background:#0f1419;color:#e6e6e6;padding:40px;max-width:700px;margin:0 auto}' +
        'h1{color:#ff6b9d;text-align:center}h2{color:#ff6b9d;font-size:18px;margin:24px 0 12px}' +
        '.grade{font-size:72px;font-weight:900;text-align:center}' +
        '.grade-S{color:#ffd700}.grade-A{color:#4caf50}.grade-B{color:#2196f3}.grade-C{color:#ff9800}.grade-D{color:#f44336}' +
        '.comment{text-align:center;color:#8b95a7;margin:8px 0 24px}</style></head><body>' +
        '<h1>🍒 K8s Quest 结业报告</h1>' +
        '<div class="grade grade-' + d.grade + '">' + d.grade + '</div>' +
        '<p class="comment">' + d.grade_comment + '</p>' +
        '<p style="text-align:center;font-size:24px;font-weight:800;color:#ff6b9d">' + d.completed_count + '/' + d.total_levels + ' 关卡完成 (' + (d.completion_rate * 100).toFixed(0) + '%)</p>' +
        '<p style="text-align:center;color:#ffd700;font-weight:700">' + d.rank + '</p>' +
        '<h2>📚 知识域掌握度</h2>' + domains +
        '<h2>⚠️ 薄弱项</h2>' + (weakAreas || '<p style="color:#8b95a7">无</p>') +
        '<h2>⭐ 优势项 (一次通过)</h2><div style="display:flex;flex-wrap:wrap;gap:6px">' + (strengths || '<p style="color:#8b95a7">无</p>') + '</div>' +
        '<h2>💡 学习建议</h2><ul style="list-style:none;padding:0">' + (recs || '<li style="color:#8b95a7">暂无建议</li>') + '</ul>' +
        '<p style="text-align:center;color:#5a6378;margin-top:40px">Generated by 🍒 樱桃 (Hermes Agent) · ' + new Date().toLocaleString('zh-CN') + '</p>' +
        '</body></html>';
    },

    // ==================== 重置进度 ====================
    confirmReset() {
      this.resetConfirm.show = true;
    },

    doReset() {
      this.progress = {
        completed_levels: [],
        level_attempts: {},
        level_first_try: [],
        level_time_spent: {},
        total_xp: 0,
        streak: 0,
        max_streak: 0,
        badges: [],
        level_start_time: {},
        last_visited_level: null,
        start_time: Date.now(),
      };
      this.saveProgress();
      this.resetConfirm.show = false;
      this.reportModal.show = false;
      this.showToast('进度已重置，重新开始冒险吧！🍒', 'info');
      // 重新加载第一关
      if (this.levels.length > 0) {
        this.loadLevel(this.levels[0].id);
      }
    },

    // 顶栏 logo 点击 (滚动到顶部)
    resetAll() {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
  };
}
