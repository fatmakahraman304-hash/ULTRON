import { useEffect, useMemo, useState } from "react";
import { Camera, Code2, Cpu, FileText, Globe, Image, Keyboard, Mic, Monitor, Package, Search, ShieldCheck, Terminal, Boxes } from "lucide-react";
import "./ultron-hud.css";

type Capability = { id: string; name: string; layer: string; status: string; tools?: string[]; safety?: string; description?: string };

const ICONS: Record<string, typeof Cpu> = {
  brain: Cpu, memory: Boxes, autonomous_tasks: Code2, voice: Mic, computer_control: Keyboard,
  web: Globe, screen_vision: Monitor, camera: Camera, image_generation: Image, pdf: FileText,
  shell: Terminal, widgets: Package, hud: Monitor, three_d: Boxes, image_viewer: Image,
  security: ShieldCheck, mesh: Package,
};

// Static fallback mirrors the backend declarative contract. It intentionally
// does not pretend provider/device-dependent adapters are live.
const fallback: Capability[] = [
  ["brain", "Brain / Planner / Supervisor", "core", "implemented", "standard"],
  ["memory", "Persistent Memory", "core", "implemented", "standard"],
  ["autonomous_tasks", "Long Tasks / Autonomous Coding", "core", "implemented", "approval"],
  ["voice", "Voice / Wake Word / TTS", "input-output", "implemented", "standard"],
  ["computer_control", "Computer Control", "automation", "implemented", "approval"],
  ["web", "Web Search / Browser Agent", "tools", "implemented", "approval"],
  ["screen_vision", "Screen Vision / OCR", "vision", "implemented", "standard"],
  ["camera", "Camera Vision", "vision", "adapter", "permission"],
  ["image_generation", "Image Generation", "multimodal", "adapter", "provider"],
  ["pdf", "PDF Workspace", "multimodal", "adapter", "standard"],
  ["shell", "Shell / PowerShell", "automation", "adapter", "approval"],
  ["widgets", "HUD Widgets", "ui", "implemented", "standard"],
  ["hud", "ULTRON HUD", "ui", "implemented", "standard"],
  ["three_d", "3D Interface", "ui", "implemented", "standard"],
  ["image_viewer", "Image Viewer / Drop Zone", "ui", "adapter", "standard"],
  ["notifications", "Proactive Notifications", "core", "implemented", "standard"],
  ["security", "Approval / Vault / Audit / Sandbox", "security", "implemented", "mandatory"],
  ["mesh", "PC / Mobile Mesh", "connectivity", "implemented", "standard"],
].map(([id, name, layer, status, safety]) => ({ id, name, layer, status, safety }));

export function UltronHUD() {
  const [items, setItems] = useState<Capability[]>(fallback);
  const [selected, setSelected] = useState("brain");
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch("/api/capabilities").then((r) => r.ok ? r.json() : Promise.reject()).then((d) => {
      if (Array.isArray(d)) setItems(d.map((row: Capability & { label?: string; detail?: string }) => ({
        ...row,
        name: row.name ?? row.label ?? row.id,
        description: row.description ?? row.detail,
        status: String(row.status ?? "unavailable").toLowerCase(),
      })));
    }).catch(() => undefined);
  }, []);

  const visible = useMemo(() => items.filter((x) => `${x.name} ${x.id} ${x.description ?? ""}`.toLowerCase().includes(query.toLowerCase())), [items, query]);
  const active = items.find((x) => x.id === selected) ?? items[0];
  const implemented = items.filter((x) => x.status === "ready").length;

  return (
    <section className="ultron-hud" aria-label="ULTRON ULTRON capability cockpit">
      <header className="ultron-head">
        <div><div className="ultron-kicker">ULTRON → ULTRON</div><h2>NEURAL COCKPIT</h2></div>
        <div className="ultron-count">{implemented}/{items.length} READY</div>
      </header>
      <div className="ultron-search"><Search size={13} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search capability…" /></div>
      <div className="ultron-grid">
        <div className="ultron-list">
          {visible.map((item) => {
            const Icon = ICONS[item.id] ?? Package;
            return <button key={item.id} className={`ultron-card ${selected === item.id ? "active" : ""}`} onClick={() => setSelected(item.id)}>
              <Icon size={15} /><span><b>{item.name}</b><small>{item.status.toUpperCase()} · {item.safety ?? "standard"}</small></span>
            </button>;
          })}
        </div>
        {active && <div className="ultron-detail">
          <div className="ultron-ring"><Boxes size={30} /></div>
          <div className="ultron-kicker">CAPABILITY</div><h3>{active.name}</h3>
          <div className={`ultron-status ${active.status}`}>{active.status.toUpperCase()}</div>
          <p>{active.description ?? "ULTRON capability module."}</p>
          <div className="ultron-meta"><span>LAYER <b>{active.layer || "runtime"}</b></span><span>SAFETY <b>{active.safety || "standard"}</b></span></div>
          {!!active.tools?.length && <div className="ultron-tools">{active.tools.map((tool) => <code key={tool}>{tool}</code>)}</div>}
        </div>}
      </div>
      <footer className="ultron-footer"><span>HUD</span><span>VOICE</span><span>VISION</span><span>COMPUTER</span><span>WEB</span><span>MEDIA</span><span>SHELL</span><span>3D</span><span>SECURITY</span></footer>
    </section>
  );
}
