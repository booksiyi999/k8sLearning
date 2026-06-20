function quest() {
  return {
    levels: [],
    currentLevel: null,
    userYaml: '',
    result: null,
    running: false,
    renderedDescription: '',

    async loadLevels() {
      const r = await fetch('/api/levels');
      const data = await r.json();
      this.levels = data.levels;
      if (this.levels.length > 0) {
        await this.loadLevel(this.levels[0].id);
      }
    },

    async loadLevel(id) {
      // MVP: 从内置数据拿（避免开第二个端点）
      const r = await fetch(`/api/level/${id}`);
      const lv = await r.json();
      this.currentLevel = lv;
      this.userYaml = lv.starter_yaml;
      this.result = null;
      this.renderedDescription = this.renderMarkdown(lv.description);
    },

    async runCheck() {
      this.running = true;
      this.result = null;
      try {
        const r = await fetch('/api/check', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({level_id: this.currentLevel.id, user_yaml: this.userYaml})
        });
        this.result = await r.json();
      } catch (e) {
        this.result = {ok: false, error: String(e), hints: []};
      } finally {
        this.running = false;
      }
    },

    resetYaml() {
      this.userYaml = this.currentLevel.starter_yaml;
      this.result = null;
    },

    renderMarkdown(md) {
      // 极简 markdown：# 标题 + 段落
      return md
        .split('\n')
        .map(line => {
          if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
          if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
          if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`;
          if (line.trim() === '') return '<br>';
          return `<p>${line}</p>`;
        })
        .join('');
    }
  };
}
