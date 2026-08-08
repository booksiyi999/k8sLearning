// ═══════════════════════════════════════════════
// 🖥️ K8s Quest - 交互式 Kubectl 终端组件
// 可作为 mixin 混入 quest() 或独立使用 (terminalPage)
// 所有方法/状态以 term 前缀避免冲突
// ═══════════════════════════════════════════════

function terminalMixin() {
  return {
    // ── 终端状态 ──
    termInput: '',
    termHistory: [],           // 命令历史（localStorage 持久化）
    termHistoryIndex: -1,      // 浏览历史时的当前索引, -1 = 新输入
    termOutput: [],            // [{type:'cmd'|'out'|'err'|'sys', text:str}]
    termLoading: false,
    termWhitelist: null,       // {allowed:[], dangerous:[], namespace, mode}
    termConfirmCmd: null,      // 待确认的危险命令（非 null 时显示确认按钮）
    termClusterMode: false,
    termNamespace: '',
    termMode: 'simulator',
    termInitialized: false,
    termShowSuggest: true,     // 是否显示自动补全建议

    // ═══════════════════════════════════════════
    // 初始化
    // ═══════════════════════════════════════════
    async termInit() {
      if (this.termInitialized) return;
      this.termInitialized = true;
      await this.termLoadWhitelist();
      await this.termLoadClusterStatus();
      this.termLoadHistory();
      this.termRenderWelcome();
    },

    termRenderWelcome() {
      this.termOutput = [
        { type: 'sys', text: '🍒 K8s Quest 交互式终端' },
        { type: 'sys', text: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━' },
      ];
      if (!this.termClusterMode) {
        this.termOutput.push({
          type: 'sys',
          text: '⚠️ 当前为模拟器模式，如需使用终端请配置 K8S_QUEST_MODE=cluster'
        });
      } else {
        this.termOutput.push({
          type: 'sys',
          text: `✅ 已连接集群 · namespace: ${this.termNamespace} · 模式: ${this.termMode}`
        });
      }
      this.termOutput.push({
        type: 'sys',
        text: '💡 提示: ↑↓ 浏览历史 · Tab 自动补全 · Ctrl+L 清屏'
      });
      this.termOutput.push({
        type: 'sys',
        text: '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'
      });
    },

    async termLoadWhitelist() {
      try {
        const r = await fetch('/api/kubectl/whitelist');
        this.termWhitelist = await r.json();
        this.termMode = this.termWhitelist?.mode || 'simulator';
        this.termNamespace = this.termWhitelist?.namespace || 'default';
        this.termClusterMode = this.termMode === 'cluster';
      } catch(e) {
        console.error('termLoadWhitelist:', e);
      }
    },

    async termLoadClusterStatus() {
      try {
        const r = await fetch('/api/cluster/status');
        const data = await r.json();
        if (data.mode) {
          this.termMode = data.mode;
          this.termClusterMode = this.termMode === 'cluster';
        }
        if (data.namespace) {
          this.termNamespace = data.namespace;
        }
      } catch(e) { /* 静默失败 */ }
    },

    // ═══════════════════════════════════════════
    // 命令历史 (localStorage)
    // ═══════════════════════════════════════════
    termLoadHistory() {
      try {
        const saved = localStorage.getItem('k8s_quest_term_history');
        if (saved) this.termHistory = JSON.parse(saved);
      } catch(e) { this.termHistory = []; }
    },

    termSaveHistory() {
      try {
        const trimmed = this.termHistory.slice(-100);
        localStorage.setItem('k8s_quest_term_history', JSON.stringify(trimmed));
      } catch(e) {}
    },

    // ═══════════════════════════════════════════
    // 键盘事件处理
    // ═══════════════════════════════════════════
    termOnKeydown(e) {
      if (this.termLoading) return;

      if (e.key === 'Enter') {
        e.preventDefault();
        this.termRun();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.termHistoryPrev();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.termHistoryNext();
      } else if (e.key === 'Tab') {
        e.preventDefault();
        this.termDoAutocomplete();
      } else if (e.key === 'Escape') {
        this.termShowSuggest = false;
        if (this.termConfirmCmd) this.termCancelConfirm();
      } else if (e.key === 'l' && e.ctrlKey) {
        e.preventDefault();
        this.termClear();
      }
    },

    // ═══════════════════════════════════════════
    // 历史浏览
    // ═══════════════════════════════════════════
    termHistoryPrev() {
      if (this.termHistory.length === 0) return;
      if (this.termHistoryIndex === -1) {
        this.termHistoryIndex = this.termHistory.length - 1;
      } else if (this.termHistoryIndex > 0) {
        this.termHistoryIndex--;
      } else {
        return; // 已到最旧
      }
      this.termInput = this.termHistory[this.termHistoryIndex] || '';
      this.termShowSuggest = false;
    },

    termHistoryNext() {
      if (this.termHistoryIndex === -1) return;
      this.termHistoryIndex++;
      if (this.termHistoryIndex >= this.termHistory.length) {
        this.termHistoryIndex = -1;
        this.termInput = '';
      } else {
        this.termInput = this.termHistory[this.termHistoryIndex];
      }
    },

    // ═══════════════════════════════════════════
    // 自动补全
    // ═══════════════════════════════════════════
    get termSuggestions() {
      const input = this.termInput.trim();
      if (!input || !this.termWhitelist) return [];
      const parts = input.split(/\s+/);
      // 只在输入 "kubectl xxx" 且 xxx 为部分子命令时给出建议
      if (parts.length === 2 && parts[0] === 'kubectl') {
        const sub = parts[1].toLowerCase();
        if (!sub) return [];
        const all = [
          ...(this.termWhitelist.allowed || []),
          ...(this.termWhitelist.dangerous || []),
        ];
        return all.filter(c => c.toLowerCase().startsWith(sub)).slice(0, 12);
      }
      return [];
    },

    termDoAutocomplete() {
      const suggestions = this.termSuggestions;
      if (suggestions.length === 1) {
        this.termInput = `kubectl ${suggestions[0]} `;
        this.termShowSuggest = false;
      } else if (suggestions.length > 1) {
        // 取所有匹配的公共前缀
        const prefix = suggestions.reduce((acc, s) => {
          while (!s.startsWith(acc)) acc = acc.slice(0, -1);
          return acc;
        });
        if (prefix.length > 0) {
          this.termInput = `kubectl ${prefix}`;
        }
        // 在输出区显示所有候选
        this.termOutput.push({
          type: 'sys',
          text: suggestions.map(s => '  ' + s).join('\n')
        });
        this.termScrollToBottom();
      }
    },

    termPickSuggestion(s) {
      this.termInput = `kubectl ${s} `;
      this.termShowSuggest = false;
      this.termFocusInput();
    },

    // ═══════════════════════════════════════════
    // 危险命令检测
    // ═══════════════════════════════════════════
    termIsDangerous(cmd) {
      if (!this.termWhitelist?.dangerous) return false;
      const lower = cmd.toLowerCase().trim();
      return this.termWhitelist.dangerous.some(d => {
        const dLower = d.toLowerCase();
        return lower === `kubectl ${dLower}` ||
               lower.startsWith(`kubectl ${dLower} `) ||
               lower.startsWith(`${dLower} `) ||
               lower === dLower;
      });
    },

    // ═══════════════════════════════════════════
    // 执行命令
    // ═══════════════════════════════════════════
    async termRun(force = false) {
      const cmd = this.termInput.trim();
      if (!cmd || this.termLoading) return;

      // 写入历史
      if (this.termHistory[this.termHistory.length - 1] !== cmd) {
        this.termHistory.push(cmd);
      }
      this.termSaveHistory();
      this.termHistoryIndex = -1;

      // 显示命令行
      this.termOutput.push({ type: 'cmd', text: cmd });
      this.termInput = '';
      this.termShowSuggest = false;

      // 危险命令需要确认
      if (!force && this.termIsDangerous(cmd)) {
        this.termConfirmCmd = cmd;
        this.termOutput.push({
          type: 'sys',
          text: '⚠️  检测到危险命令，请点击下方「确认执行」按钮以继续（force=true）。'
        });
        this.termScrollToBottom();
        return;
      }

      await this.termExec(cmd, force);
    },

    async termExec(cmd, force) {
      this.termLoading = true;
      this.termConfirmCmd = null;
      try {
        const r = await fetch('/api/kubectl', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: cmd, force: !!force }),
        });
        const data = await r.json();

        if (data.success) {
          if (data.output) {
            this.termOutput.push({ type: 'out', text: data.output });
          } else {
            this.termOutput.push({ type: 'sys', text: '✅ 执行完成（无输出）' });
          }
        } else {
          if (data.error) {
            this.termOutput.push({ type: 'err', text: data.error });
          }
          if (data.output) {
            this.termOutput.push({ type: 'out', text: data.output });
          }
        }

        // 后端标记需要确认但前端未预判
        if (data.dangerous && data.needs_confirm && !force) {
          this.termConfirmCmd = cmd;
          this.termOutput.push({
            type: 'sys',
            text: '⚠️  后端要求确认此命令，请点击「确认执行」。'
          });
        }
      } catch(e) {
        this.termOutput.push({ type: 'err', text: '❌ 网络错误: ' + String(e) });
      } finally {
        this.termLoading = false;
        this.termScrollToBottom();
      }
    },

    // ── 确认执行危险命令 ──
    async termConfirmRun() {
      const cmd = this.termConfirmCmd;
      if (!cmd) return;
      this.termConfirmCmd = null;
      this.termOutput.push({ type: 'sys', text: '→ 确认执行（force=true）' });
      await this.termExec(cmd, true);
    },

    termCancelConfirm() {
      this.termConfirmCmd = null;
      this.termOutput.push({ type: 'sys', text: '✕ 已取消执行' });
      this.termScrollToBottom();
    },

    // ═══════════════════════════════════════════
    // 清屏 & 工具
    // ═══════════════════════════════════════════
    termClear() {
      this.termOutput = [];
      this.termShowSuggest = false;
      this.termConfirmCmd = null;
    },

    termScrollToBottom() {
      this.$nextTick(() => {
        document.querySelectorAll('.term-output-area').forEach(el => {
          el.scrollTop = el.scrollHeight;
        });
      });
    },

    termFocusInput() {
      this.$nextTick(() => {
        document.querySelectorAll('.term-input-field').forEach(el => el.focus());
      });
    },

    // 集群状态文本
    get termStatusText() {
      if (this.termClusterMode) {
        return `🟢 集群模式 · ns: ${this.termNamespace}`;
      }
      return '🟡 模拟器模式';
    },
  };
}

// ═══════════════════════════════════════════════
// 独立终端页面组件
// ═══════════════════════════════════════════════
function terminalPage() {
  return {
    ...terminalMixin(),
    async init() {
      await this.termInit();
    },
  };
}
