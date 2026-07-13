import { useState } from 'react';
import {
  MessageSquare,
  Bell,
  Zap,
  PanelRightOpen,
  PanelRightClose,
} from 'lucide-react';
import { MultiChatLayout } from './MultiChatLayout';
import { MessageBoard } from './MessageBoard';
import { AutomationPanel } from './AutomationPanel';

const TABS = [
  { id: 'chat', label: 'AI Chat', icon: MessageSquare },
  { id: 'board', label: 'Board', icon: Bell },
  { id: 'automation', label: 'Auto', icon: Zap },
];

export function RightHub({
  sources,
  messages,
  onSendMessage,
  onPatchMessage,
  activeAgentId,
  onSetActiveAgent,
}) {
  const [collapsed, setCollapsed] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const boardUnread = 2;

  return (
    <>
      {/* Collapsed bar */}
      {collapsed && (
        <aside className="right-hub-collapsed">
          <button
            className="rh-collapse-btn"
            onClick={() => setCollapsed(false)}
            title="Open AI Hub"
          >
            <PanelRightOpen size={16} />
          </button>

          {TABS.map((tab) => {
            const Icon = tab.icon;
            const badge = tab.id === 'board' ? boardUnread : 0;
            return (
              <button
                key={tab.id}
                className={`rh-tab-btn ${activeTab === tab.id ? 'active' : ''}`}
                onClick={() => { setActiveTab(tab.id); setCollapsed(false); }}
                title={tab.label}
              >
                <Icon size={15} />
                {badge > 0 && <span className="rh-tab-badge">{badge}</span>}
              </button>
            );
          })}
        </aside>
      )}

      {/* Expanded panel */}
      {!collapsed && (
        <aside className="right-hub">
          {/* Hub header */}
          <div className="rh-header">
            <div className="rh-tabs">
              {TABS.map((tab) => {
                const Icon = tab.icon;
                const badge = tab.id === 'board' ? boardUnread : 0;
                return (
                  <button
                    key={tab.id}
                    className={activeTab === tab.id ? 'active' : ''}
                    onClick={() => setActiveTab(tab.id)}
                  >
                    <Icon size={13} />
                    <span>{tab.label}</span>
                    {badge > 0 && <span className="rh-badge">{badge}</span>}
                  </button>
                );
              })}
            </div>
            <button
              className="rh-close"
              onClick={() => setCollapsed(true)}
              title="Collapse"
            >
              <PanelRightClose size={15} />
            </button>
          </div>

          {/* Hub content */}
          <div className="rh-content">
            {activeTab === 'chat' && (
              <MultiChatLayout
                sources={sources}
                messages={messages}
                onSendMessage={onSendMessage}
                onPatchMessage={onPatchMessage}
                activeAgentId={activeAgentId}
                onSetActiveAgent={onSetActiveAgent}
              />
            )}
            {activeTab === 'board' && <MessageBoard />}
            {activeTab === 'automation' && <AutomationPanel sources={sources} />}
          </div>
        </aside>
      )}
    </>
  );
}
