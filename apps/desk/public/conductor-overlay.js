(function () {
  const STORE_KEY = 'topOfMind.conductor.v1';
  const UI_KEY = 'topOfMind.conductor.ui.v1';

  const defaults = {
    patterns: [
      { id: 'programming', name: 'Programming', cadence: 'manual', prompt: 'Work as the coding/build agent. Track files changed, tests run, blockers, and next action.' },
      { id: 'cleanup', name: 'Cleanup / City', cadence: 'daily', prompt: 'Find small cleanup work: folders, stale notes, loose files, broken links, and drift. Report safe actions first.' },
      { id: 'canon', name: 'Canon Drift Audit', cadence: 'hourly', prompt: 'Check current work against canon decisions, law table, and source pointers. Flag drift without rewriting.' }
    ],
    agents: [
      { id: 'codex', name: 'Codex', folder: 'AI/Codex/continuous.md', welcome: true, idleHours: 2, dailyAfter: '12:00', model: 'coding lane' },
      { id: 'kimi', name: 'Kimi', folder: 'AI/Kimi/continuous.md', welcome: true, idleHours: 2, dailyAfter: '12:00', model: 'research lane' },
      { id: 'claude', name: 'Claude', folder: 'AI/Claude/continuous.md', welcome: true, idleHours: 2, dailyAfter: '12:00', model: 'writing lane' },
      { id: 'gemini', name: 'Gemini', folder: 'AI/Gemini/continuous.md', welcome: true, idleHours: 2, dailyAfter: '12:00', model: 'audit lane' }
    ],
    rules: {
      coldAfterHours: 2,
      dailyMaintenanceAfter: '12:00',
      contextDefault: 'ask',
      routingDefault: 'selected',
      saveMode: 'shared_and_agent',
      projectRoot: 'D:/00_CANON_REFERENCE',
      codexDefaultFolder: 'AI/Codex/continuous.md',
      apiBaseUrl: 'http://127.0.0.1:10000',
      memorySource: 'conductor',
      memoryFolder: 'Conductor'
    },
    boardTiles: [
      { id: 'codex-task', name: 'Codex Task', folder: 'AI/Codex', tags: ['needs_codex', 'task'], body: 'Task:\n\nContext:\n\nDefinition of done:\n\nFiles or folders:\n' },
      { id: 'canon-note', name: 'Canon Note', folder: 'Canon', tags: ['canon', 'no_drift'], body: 'Canon decision:\n\nReason:\n\nSource or session:\n\nOpen risk:\n' },
      { id: 'drift-flag', name: 'Drift Flag', folder: 'Audit', tags: ['drift', 'review'], body: 'Possible drift:\n\nCanonical reference:\n\nWhy it may conflict:\n\nSuggested next check:\n' },
      { id: 'source-capture', name: 'Source Capture', folder: 'Sources', tags: ['source', 'capture'], body: 'Source:\n\nWhat it supports:\n\nWhere it should live:\n\nConfidence:\n' },
      { id: 'follow-up', name: 'Follow-Up', folder: 'Follow Up', tags: ['follow_up'], body: 'Follow-up item:\n\nWhy it matters:\n\nBest next action:\n' }
    ]
  };

  function mergeState(saved) {
    const state = { ...defaults, ...(saved || {}) };
    state.patterns = Array.isArray(saved?.patterns) ? saved.patterns : defaults.patterns;
    state.agents = Array.isArray(saved?.agents) ? saved.agents : defaults.agents;
    state.boardTiles = Array.isArray(saved?.boardTiles) ? saved.boardTiles : defaults.boardTiles;
    state.rules = { ...defaults.rules, ...(saved?.rules || {}) };
    return state;
  }

  function load() {
    try {
      return mergeState(JSON.parse(localStorage.getItem(STORE_KEY) || '{}'));
    } catch {
      return mergeState({});
    }
  }

  function loadUi() {
    try {
      return { activeTab: 'patterns', selectedAgent: 'codex', ...JSON.parse(localStorage.getItem(UI_KEY) || '{}') };
    } catch {
      return { activeTab: 'patterns', selectedAgent: 'codex' };
    }
  }

  function save(state) {
    localStorage.setItem(STORE_KEY, JSON.stringify(state, null, 2));
  }

  function saveUi(ui) {
    localStorage.setItem(UI_KEY, JSON.stringify(ui, null, 2));
  }

  function copy(text) {
    navigator.clipboard?.writeText(text);
  }

  async function postJson(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  async function getJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }

  function option(value, label, selected) {
    return `<option value="${value}"${selected === value ? ' selected' : ''}>${label}</option>`;
  }

  function currentPattern(state, drawer) {
    const selected = drawer.querySelector('#cond-pattern')?.value;
    return state.patterns.find((p) => p.id === selected) || state.patterns[0];
  }

  function routinePacket(state, drawer) {
    const pattern = currentPattern(state, drawer);
    return JSON.stringify({
      type: 'top_of_mind_conductor_routine',
      pattern,
      rules: state.rules,
      agent_folders: state.agents.map((a) => ({ id: a.id, name: a.name, folder: a.folder }))
    }, null, 2);
  }

  function setActiveTab(drawer, activeTab) {
    drawer.querySelectorAll('.tom-cond-nav button').forEach((button) => {
      button.classList.toggle('active', button.dataset.tab === activeTab);
    });
    drawer.querySelectorAll('.tom-cond-panel').forEach((panel) => {
      panel.classList.toggle('active', panel.dataset.panel === activeTab);
    });
  }

  function render() {
    const state = load();
    const ui = loadUi();
    const selectedAgent = state.agents.find((agent) => agent.id === ui.selectedAgent) || state.agents[0];

    document.querySelector('.tom-conductor')?.remove();
    document.querySelector('.tom-conductor-tab')?.remove();

    const tab = document.createElement('button');
    tab.className = 'tom-conductor-tab';
    tab.textContent = 'Conductor';
    document.body.appendChild(tab);

    const drawer = document.createElement('aside');
    drawer.className = 'tom-conductor';
    drawer.innerHTML = `
      <div class="tom-cond-head">
        <div class="tom-cond-title">
          <b>Conductor</b>
          <span>Patterns, agents, routing, folders</span>
        </div>
        <button class="tom-cond-close" title="Close">x</button>
      </div>

      <nav class="tom-cond-nav" aria-label="Conductor sections">
        <button data-tab="board">Board</button>
        <button data-tab="patterns">Patterns</button>
        <button data-tab="agents">Agents</button>
        <button data-tab="rules">Rules</button>
        <button data-tab="memory">Memory</button>
        <button data-tab="folders">Folders</button>
      </nav>

      <div class="tom-cond-body">
        <section class="tom-cond-panel" data-panel="board">
          <div class="tom-cond-card featured">
            <h3>Tap Board</h3>
            <div class="tom-cond-command">
              <span>flow</span>
              <code>tap -> draft memory -> review -> save</code>
            </div>
            <p class="tom-cond-note">Quick structural captures. These do not auto-send yet; they fill the Memory tab with a clean packet.</p>
          </div>

          <div class="tom-cond-board">
            ${state.boardTiles.map((tile) => `
              <button class="tom-cond-tile" data-action="tap-board" data-tile="${tile.id}">
                <b>${tile.name}</b>
                <span>${tile.folder}</span>
                <em>${tile.tags.join(', ')}</em>
              </button>
            `).join('')}
          </div>

          <div class="tom-cond-card">
            <h3>Add Tile</h3>
            <div class="tom-cond-grid2">
              <div class="tom-cond-row"><label>Name</label><input id="cond-tile-name" placeholder="Research Pull"></div>
              <div class="tom-cond-row"><label>Folder</label><input id="cond-tile-folder" placeholder="Research"></div>
            </div>
            <div class="tom-cond-row"><label>Tags</label><input id="cond-tile-tags" placeholder="research, source"></div>
            <div class="tom-cond-row"><label>Template</label><textarea id="cond-tile-body" placeholder="Question:\nSource:\nNext action:"></textarea></div>
            <button class="tom-cond-btn primary" data-action="add-board-tile">Add tile</button>
          </div>
        </section>

        <section class="tom-cond-panel" data-panel="patterns">
          <div class="tom-cond-card featured">
            <h3>Quick Pattern</h3>
            <div class="tom-cond-row">
              <label>Pattern</label>
              <select id="cond-pattern">
                ${state.patterns.map((p) => `<option value="${p.id}">${p.name} - ${p.cadence}</option>`).join('')}
              </select>
            </div>
            <div class="tom-cond-command">
              <span>packet</span>
              <code>pattern -> context -> folders -> send</code>
            </div>
            <div class="tom-cond-buttons">
              <button class="tom-cond-btn primary" data-action="copy-pattern">Copy prompt</button>
              <button class="tom-cond-btn gold" data-action="copy-routine">Copy routine packet</button>
            </div>
          </div>

          <div class="tom-cond-card">
            <h3>Saved Patterns</h3>
            <div class="tom-cond-list">
              ${state.patterns.map((p) => `
                <button class="tom-cond-rowbutton" data-action="select-pattern" data-pattern="${p.id}">
                  <span><b>${p.name}</b><small>${p.prompt}</small></span>
                  <em>${p.cadence}</em>
                </button>
              `).join('')}
            </div>
          </div>

          <div class="tom-cond-card">
            <h3>Add Pattern</h3>
            <div class="tom-cond-row"><label>Name</label><input id="cond-new-name" placeholder="Obsidian cleanup"></div>
            <div class="tom-cond-row"><label>Cadence</label><select id="cond-new-cadence">
              <option>manual</option><option>hourly</option><option>daily</option><option>weekly</option><option>monthly</option>
            </select></div>
            <div class="tom-cond-row"><label>Prompt</label><textarea id="cond-new-prompt" placeholder="Tell the AI what this routine does..."></textarea></div>
            <button class="tom-cond-btn primary" data-action="add-pattern">Add pattern</button>
          </div>
        </section>

        <section class="tom-cond-panel" data-panel="agents">
          <div class="tom-cond-split">
            <div class="tom-cond-card">
              <h3>Agent Lanes</h3>
              <div class="tom-cond-list">
                ${state.agents.map((a) => `
                  <button class="tom-cond-agent ${a.id === selectedAgent.id ? 'active' : ''}" data-action="select-agent" data-agent="${a.id}">
                    <span class="tom-cond-avatar">${a.name.slice(0, 1)}</span>
                    <span><b>${a.name}</b><small>${a.model}</small></span>
                    <em>${a.welcome ? 'on' : 'off'}</em>
                  </button>
                `).join('')}
              </div>
            </div>

            <div class="tom-cond-card detail">
              <h3>Selected Agent</h3>
              <div class="tom-cond-detail-title">
                <span class="tom-cond-avatar large">${selectedAgent.name.slice(0, 1)}</span>
                <div><b>${selectedAgent.name}</b><small>${selectedAgent.id}</small></div>
              </div>
              <div class="tom-cond-row"><label>Default folder</label><input id="cond-agent-folder" value="${selectedAgent.folder}"></div>
              <div class="tom-cond-row"><label>Cold after hours</label><input id="cond-agent-idle" type="number" min="0" step="0.5" value="${selectedAgent.idleHours}"></div>
              <div class="tom-cond-row"><label>Daily maintenance after</label><input id="cond-agent-daily" type="time" value="${selectedAgent.dailyAfter}"></div>
              <label class="tom-cond-toggle"><input id="cond-agent-welcome" type="checkbox"${selectedAgent.welcome ? ' checked' : ''}> Send welcome prompt on cold start</label>
              <button class="tom-cond-btn primary" data-action="save-agent">Save agent</button>
            </div>
          </div>
        </section>

        <section class="tom-cond-panel" data-panel="rules">
          <div class="tom-cond-card featured">
            <h3>Entry Rules</h3>
            <div class="tom-cond-grid2">
              <div class="tom-cond-row"><label>Cold after hours</label><input id="cond-cold" type="number" min="0" step="0.5" value="${state.rules.coldAfterHours}"></div>
              <div class="tom-cond-row"><label>Daily maintenance after</label><input id="cond-daily" type="time" value="${state.rules.dailyMaintenanceAfter}"></div>
            </div>
            <div class="tom-cond-row"><label>When adding AI to thread</label><select id="cond-context">
              ${option('ask', 'Ask me every time', state.rules.contextDefault)}
              ${option('whole_thread', 'Whole thread by default', state.rules.contextDefault)}
              ${option('from_here', 'From here by default', state.rules.contextDefault)}
              ${option('summary', 'Summary packet by default', state.rules.contextDefault)}
            </select></div>
            <div class="tom-cond-row"><label>Save mode</label><select id="cond-save">
              ${option('shared_and_agent', 'Shared stream + AI folder', state.rules.saveMode)}
              ${option('agent_only', 'AI folder only', state.rules.saveMode)}
              ${option('shared_only', 'Shared stream only', state.rules.saveMode)}
            </select></div>
            <button class="tom-cond-btn primary" data-action="save-rules">Save rules</button>
          </div>
        </section>

        <section class="tom-cond-panel" data-panel="memory">
          <div class="tom-cond-card featured">
            <h3>API Memory</h3>
            <div class="tom-cond-row"><label>API base URL</label><input id="cond-api-base" value="${state.rules.apiBaseUrl}"></div>
            <div class="tom-cond-grid2">
              <div class="tom-cond-row"><label>Source</label><input id="cond-memory-source" value="${state.rules.memorySource}"></div>
              <div class="tom-cond-row"><label>Folder</label><input id="cond-memory-folder" value="${state.rules.memoryFolder}"></div>
            </div>
            <div class="tom-cond-buttons">
              <button class="tom-cond-btn primary" data-action="save-memory-settings">Save settings</button>
              <button class="tom-cond-btn gold" data-action="test-memory-api">Test API</button>
            </div>
            <p class="tom-cond-note" id="cond-memory-status">Ready. This writes to the local Top of Mind memory API when it is online.</p>
          </div>

          <div class="tom-cond-card">
            <h3>Save Memory</h3>
            <div class="tom-cond-row"><label>Title</label><input id="cond-memory-title" placeholder="Canon change, project note, API idea..."></div>
            <div class="tom-cond-row"><label>Body</label><textarea id="cond-memory-body" placeholder="Write the memory you want saved into the hub..."></textarea></div>
            <div class="tom-cond-row"><label>Tags</label><input id="cond-memory-tags" placeholder="codex, conductor, canon"></div>
            <div class="tom-cond-buttons">
              <button class="tom-cond-btn primary" data-action="save-memory-item">Save to API</button>
              <button class="tom-cond-btn" data-action="copy-memory-json">Copy JSON</button>
            </div>
          </div>
        </section>

        <section class="tom-cond-panel" data-panel="folders">
          <div class="tom-cond-card featured">
            <h3>Project Memory</h3>
            <div class="tom-cond-row"><label>Project root</label><input id="cond-project-root" value="${state.rules.projectRoot}"></div>
            <div class="tom-cond-row"><label>Codex default folder</label><input id="cond-codex-folder" value="${state.rules.codexDefaultFolder}"></div>
            <button class="tom-cond-btn primary" data-action="save-folders">Save folders</button>
          </div>

          <div class="tom-cond-card">
            <h3>Default Agent Folders</h3>
            <div class="tom-cond-list">
              ${state.agents.map((a) => `<div class="tom-cond-chip"><div><b>${a.name}</b><span>${a.folder}</span></div><div class="tom-cond-pill">${a.id}</div></div>`).join('')}
            </div>
          </div>
        </section>
      </div>
    `;
    document.body.appendChild(drawer);

    setActiveTab(drawer, ui.activeTab);

    tab.addEventListener('click', () => drawer.classList.add('open'));
    drawer.querySelector('.tom-cond-close').addEventListener('click', () => drawer.classList.remove('open'));

    drawer.querySelector('.tom-cond-nav').addEventListener('click', (event) => {
      const activeTab = event.target?.dataset?.tab;
      if (!activeTab) return;
      const nextUi = { ...loadUi(), activeTab };
      saveUi(nextUi);
      setActiveTab(drawer, activeTab);
    });

    drawer.addEventListener('click', (event) => {
      const action = event.target?.closest('[data-action]')?.dataset?.action;
      if (!action) return;
      const target = event.target.closest('[data-action]');
      const current = load();

      if (action === 'select-pattern') {
        drawer.querySelector('#cond-pattern').value = target.dataset.pattern;
      }

      if (action === 'select-agent') {
        saveUi({ ...loadUi(), activeTab: 'agents', selectedAgent: target.dataset.agent });
        render();
        document.querySelector('.tom-conductor')?.classList.add('open');
      }

      if (action === 'tap-board') {
        const tile = current.boardTiles.find((item) => item.id === target.dataset.tile);
        if (!tile) return;
        drawer.querySelector('#cond-memory-title').value = tile.name;
        drawer.querySelector('#cond-memory-body').value = tile.body;
        drawer.querySelector('#cond-memory-tags').value = tile.tags.join(', ');
        drawer.querySelector('#cond-memory-folder').value = tile.folder;
        saveUi({ ...loadUi(), activeTab: 'memory' });
        setActiveTab(drawer, 'memory');
        const status = drawer.querySelector('#cond-memory-status');
        if (status) status.textContent = `Drafted from ${tile.name}. Review, then Save to API.`;
      }

      if (action === 'add-board-tile') {
        const name = drawer.querySelector('#cond-tile-name').value.trim();
        const folder = drawer.querySelector('#cond-tile-folder').value.trim() || 'Conductor';
        const tags = drawer.querySelector('#cond-tile-tags').value.split(',').map((tag) => tag.trim()).filter(Boolean);
        const body = drawer.querySelector('#cond-tile-body').value.trim();
        if (!name || !body) return;
        current.boardTiles.push({ id: `tile-${Date.now()}`, name, folder, tags, body });
        save(current);
        saveUi({ ...loadUi(), activeTab: 'board' });
        render();
        document.querySelector('.tom-conductor')?.classList.add('open');
      }

      if (action === 'save-agent') {
        const uiNow = loadUi();
        const agent = current.agents.find((a) => a.id === uiNow.selectedAgent);
        if (agent) {
          agent.folder = drawer.querySelector('#cond-agent-folder').value.trim() || agent.folder;
          agent.idleHours = Number(drawer.querySelector('#cond-agent-idle').value || agent.idleHours);
          agent.dailyAfter = drawer.querySelector('#cond-agent-daily').value || agent.dailyAfter;
          agent.welcome = drawer.querySelector('#cond-agent-welcome').checked;
          if (agent.id === 'codex') current.rules.codexDefaultFolder = agent.folder;
          save(current);
        }
        target.textContent = 'Saved';
        setTimeout(() => (target.textContent = 'Save agent'), 900);
      }

      if (action === 'save-rules') {
        current.rules = {
          ...current.rules,
          coldAfterHours: Number(drawer.querySelector('#cond-cold').value || 2),
          dailyMaintenanceAfter: drawer.querySelector('#cond-daily').value || '12:00',
          contextDefault: drawer.querySelector('#cond-context').value,
          saveMode: drawer.querySelector('#cond-save').value
        };
        save(current);
        target.textContent = 'Saved';
        setTimeout(() => (target.textContent = 'Save rules'), 900);
      }

      if (action === 'save-folders') {
        current.rules.projectRoot = drawer.querySelector('#cond-project-root').value.trim() || current.rules.projectRoot;
        current.rules.codexDefaultFolder = drawer.querySelector('#cond-codex-folder').value.trim() || current.rules.codexDefaultFolder;
        const codex = current.agents.find((a) => a.id === 'codex');
        if (codex) codex.folder = current.rules.codexDefaultFolder;
        save(current);
        target.textContent = 'Saved';
        setTimeout(() => (target.textContent = 'Save folders'), 900);
      }

      if (action === 'save-memory-settings') {
        current.rules.apiBaseUrl = drawer.querySelector('#cond-api-base').value.trim() || current.rules.apiBaseUrl;
        current.rules.memorySource = drawer.querySelector('#cond-memory-source').value.trim() || current.rules.memorySource;
        current.rules.memoryFolder = drawer.querySelector('#cond-memory-folder').value.trim() || current.rules.memoryFolder;
        save(current);
        target.textContent = 'Saved';
        setTimeout(() => (target.textContent = 'Save settings'), 900);
      }

      if (action === 'test-memory-api') {
        const status = drawer.querySelector('#cond-memory-status');
        const apiBaseUrl = drawer.querySelector('#cond-api-base').value.trim() || current.rules.apiBaseUrl;
        status.textContent = 'Testing API...';
        getJson(`${apiBaseUrl.replace(/\/$/, '')}/memory/items`)
          .then((result) => {
            const count = Array.isArray(result.memory_items) ? result.memory_items.length : 0;
            status.textContent = `API connected. ${count} memory item(s) visible.`;
          })
          .catch((error) => {
            status.textContent = `API test failed: ${error.message}`;
          });
      }

      if (action === 'save-memory-item' || action === 'copy-memory-json') {
        const apiBaseUrl = drawer.querySelector('#cond-api-base').value.trim() || current.rules.apiBaseUrl;
        const payload = {
          title: drawer.querySelector('#cond-memory-title').value.trim() || 'Conductor memory',
          body: drawer.querySelector('#cond-memory-body').value.trim(),
          source: drawer.querySelector('#cond-memory-source').value.trim() || current.rules.memorySource,
          folder: drawer.querySelector('#cond-memory-folder').value.trim() || current.rules.memoryFolder,
          tags: drawer.querySelector('#cond-memory-tags').value.split(',').map((tag) => tag.trim()).filter(Boolean),
          metadata: {
            saved_from: 'top_of_mind_conductor',
            project_root: current.rules.projectRoot,
            created_at: new Date().toISOString()
          }
        };
        if (!payload.body) return;
        if (action === 'copy-memory-json') {
          copy(JSON.stringify(payload, null, 2));
          const original = target.textContent;
          target.textContent = 'Copied';
          setTimeout(() => (target.textContent = original), 900);
          return;
        }
        const status = drawer.querySelector('#cond-memory-status');
        status.textContent = 'Saving memory...';
        postJson(`${apiBaseUrl.replace(/\/$/, '')}/memory/items`, payload)
          .then(() => {
            status.textContent = 'Memory saved to API.';
            drawer.querySelector('#cond-memory-title').value = '';
            drawer.querySelector('#cond-memory-body').value = '';
            drawer.querySelector('#cond-memory-tags').value = '';
          })
          .catch((error) => {
            status.textContent = `Save failed: ${error.message}`;
          });
      }

      if (action === 'add-pattern') {
        const name = drawer.querySelector('#cond-new-name').value.trim();
        const cadence = drawer.querySelector('#cond-new-cadence').value;
        const prompt = drawer.querySelector('#cond-new-prompt').value.trim();
        if (!name || !prompt) return;
        current.patterns.push({ id: `pattern-${Date.now()}`, name, cadence, prompt });
        save(current);
        saveUi({ ...loadUi(), activeTab: 'patterns' });
        render();
        document.querySelector('.tom-conductor')?.classList.add('open');
      }

      if (action === 'copy-pattern' || action === 'copy-routine') {
        const packet = action === 'copy-pattern' ? currentPattern(current, drawer).prompt : routinePacket(current, drawer);
        copy(packet);
        const original = target.textContent;
        target.textContent = 'Copied';
        setTimeout(() => (target.textContent = original), 900);
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', render);
  } else {
    render();
  }
})();
