import { navIcons, SourceAvatar } from '../icons/AppIcons';

const nav = [['chats', 'Chats'], ['agents', 'Agents'], ['prompts', 'Prompts'], ['models', 'Models'], ['tools', 'Tools/Plugins'], ['settings', 'Settings']];

export function IconRail({ activePanel, setActivePanel, sources }) {
  const KnowledgeIcon = navIcons.knowledge;
  return <aside className="icon-rail"><div className="brand">ToM</div>{nav.map(([key, label]) => { const Icon = navIcons[key]; return <button key={key} title={label} className={activePanel === key ? 'active' : ''} onClick={() => setActivePanel(key)}><Icon size={18}/></button>; })}<div className="rail-sources">{sources.slice(0, 7).map((s) => <SourceAvatar key={s.id || s.name} source={s.name || s.id} status={s.status} compact/>)}</div><button className={activePanel === 'knowledge' ? 'active bottom' : 'bottom'} title="Knowledge Bank" onClick={() => setActivePanel('knowledge')}><KnowledgeIcon size={18}/></button></aside>;
}
