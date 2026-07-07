import { fileTypeIcons } from '../icons/AppIcons';

const files = [
  ['markdown', 'Wall notes.md'], ['pdf', 'Research packet.pdf'], ['image', 'Screenshot capture.png'], ['audio', 'Voice memo.wav'], ['video', 'Demo clip.mp4'], ['transcript', 'Meeting transcript'], ['folder', 'Project sources']
];

export function KnowledgePanel() { return <section><h3>Knowledge Bank</h3><div className="knowledge-grid">{files.map(([type, name]) => { const Icon = fileTypeIcons[type]; return <button className="knowledge-file" key={name}><Icon size={16}/><span>{name}</span><small>{type}</small></button>; })}</div></section>; }
