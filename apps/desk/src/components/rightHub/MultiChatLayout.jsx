import { useState, useCallback } from 'react';
import {
  LayoutTemplate,
  Columns2,
  Grid2X2,
  Maximize2,
  X,
  Merge,
  MessageSquare,
  Plus,
} from 'lucide-react';
import { AgentChatPane } from './AgentChatPane';
import { MergeDialog } from './MergeDialog';

const LAYOUTS = {
  single: { id: 'single', label: 'Full', icon: Maximize2, cols: 1, rows: 1, maxPanes: 1 },
  split: { id: 'split', label: 'Split', icon: Columns2, cols: 2, rows: 1, maxPanes: 2 },
  quad: { id: 'quad', label: 'Quad', icon: Grid2X2, cols: 2, rows: 2, maxPanes: 4 },
};

export function MultiChatLayout({
  sources,
  messages,
  onSendMessage,
  onPatchMessage,
  activeAgentId,
  onSetActiveAgent,
}) {
  const [layoutMode, setLayoutMode] = useState('single');
  const [panes, setPanes] = useState([{ id: 'pane-0', agentId: activeAgentId }]);
  const [showMerge, setShowMerge] = useState(false);
  const [mergeTarget, setMergeTarget] = useState(null);

  const layout = LAYOUTS[layoutMode];

  const setLayout = useCallback((mode) => {
    const config = LAYOUTS[mode];
    setLayoutMode(mode);
    setPanes((prev) => {
      const next = [];
      for (let i = 0; i < config.maxPanes; i++) {
        if (i < prev.length) {
          next.push(prev[i]);
        } else {
          next.push({ id: `pane-${i}`, agentId: activeAgentId });
        }
      }
      return next;
    });
  }, [activeAgentId]);

  const assignAgentToPane = useCallback((paneIndex, agentId) => {
    setPanes((prev) =>
      prev.map((p, i) => (i === paneIndex ? { ...p, agentId } : p))
    );
  }, []);

  const removePane = useCallback((paneIndex) => {
    setPanes((prev) => {
      if (prev.length <= 1) return prev;
      return prev.filter((_, i) => i !== paneIndex);
    });
    setPanes((prev) => {
      if (prev.length <= 1 && layoutMode !== 'single') {
        setLayoutMode('single');
      } else if (prev.length <= 2 && layoutMode === 'quad') {
        setLayoutMode('split');
      }
      return prev;
    });
  }, [layoutMode]);

  const openMerge = useCallback((pane) => {
    setMergeTarget(pane);
    setShowMerge(true);
  }, []);

  const handleMerge = useCallback((options) => {
    console.log('Merge', mergeTarget?.agentId, 'with options:', options);
    setShowMerge(false);
    setMergeTarget(null);
  }, [mergeTarget]);

  const usedAgentIds = new Set(panes.map((p) => p.agentId));

  return (
    <div className="multi-chat-layout">
      <div className="multi-chat-toolbar">
        <div className="layout-selector">
          <LayoutTemplate size={14} />
          {Object.values(LAYOUTS).map((l) => {
            const Icon = l.icon;
            return (
              <button
                key={l.id}
                className={layoutMode === l.id ? 'active' : ''}
                onClick={() => setLayout(l.id)}
                title={`${l.label} (${l.maxPanes} max)`}
              >
                <Icon size={14} />
                <span>{l.label}</span>
              </button>
            );
          })}
        </div>

        <div className="pane-actions">
          {panes.length < layout.maxPanes && layoutMode !== 'single' && (
            <button
              className="add-pane-btn"
              onClick={() => {
                const unused = sources.find((s) => !usedAgentIds.has(s.id));
                if (unused) {
                  setPanes((prev) => [
                    ...prev,
                    { id: `pane-${prev.length}`, agentId: unused.id },
                  ]);
                }
              }}
              title="Add pane"
            >
              <Plus size={14} /> Add AI
            </button>
          )}
          <span className="pane-count">
            {panes.length} / {layout.maxPanes}
          </span>
        </div>
      </div>

      <div
        className="multi-chat-grid"
        style={{
          gridTemplateColumns: `repeat(${layout.cols}, 1fr)`,
          gridTemplateRows: `repeat(${layout.rows}, 1fr)`,
        }}
      >
        {panes.map((pane, idx) => {
          const source = sources.find((s) => s.id === pane.agentId) || sources[0];
          const paneMessages = messages.filter((m) => {
            const msgSource = (m.source || m.source_id || m.source_label || '').toLowerCase();
            return msgSource.includes((source?.id || '').toLowerCase());
          });

          return (
            <AgentChatPane
              key={pane.id}
              paneIndex={idx}
              source={source}
              sources={sources}
              messages={paneMessages}
              allMessages={messages}
              onSend={onSendMessage}
              onPatch={onPatchMessage}
              onAssignAgent={(agentId) => assignAgentToPane(idx, agentId)}
              onRemove={() => removePane(idx)}
              onMerge={() => openMerge(pane)}
              canRemove={panes.length > 1}
              isSingle={layoutMode === 'single'}
            />
          );
        })}
      </div>

      {showMerge && mergeTarget && (
        <MergeDialog
          target={mergeTarget}
          sources={sources}
          onMerge={handleMerge}
          onClose={() => { setShowMerge(false); setMergeTarget(null); }}
        />
      )}
    </div>
  );
}
