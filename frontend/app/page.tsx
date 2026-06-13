"use client";

import { useEffect, useMemo, useState } from "react";

const API = "/api/v1";

type Skill = {
  name: string;
  version: string;
  description: string;
  category: string;
  tags: string[];
  updated: number | null;
};
type Agent = { name: string; version: string; description: string; skills: string[] };
type Param = {
  name: string;
  type: string;
  required: boolean;
  description: string;
  default?: unknown;
  enum?: string[];
  examples?: unknown[];
};
type Manifest = {
  name: string;
  version: string;
  description: string;
  category?: string;
  tags?: string[];
  inputs?: Param[];
  outputs?: Param[];
  execution?: { entrypoint?: string; type?: string };
  skills?: string[];
  workflow?: { step: string; uses?: string; description?: string }[];
};
type Sort = "recent" | "name" | "category";
type View = "dashboard" | "skills" | "agents" | "publish";

const RECENT = 7 * 24 * 3600;
const mcpUrl = () => (typeof window !== "undefined" ? `${window.location.origin}/mcp` : "/mcp");

type Stats = {
  skills: number; agents: number; categories: number;
  total_runs: number; total_downloads: number;
  category_breakdown: Record<string, number>;
  popular: { name: string; runs: number; downloads: number }[];
  per_skill: Record<string, { name: string; runs: number; downloads: number }>;
};

export default function Page() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [view, setView] = useState<View>("dashboard");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [sort, setSort] = useState<Sort>("recent");
  const [detail, setDetail] = useState<{ kind: "skill" | "agent"; name: string } | null>(null);

  async function refresh() {
    try {
      const [s, a, st] = await Promise.all([
        fetch(`${API}/skills?limit=200`).then((r) => r.json()),
        fetch(`${API}/agents`).then((r) => r.json()),
        fetch(`${API}/stats`).then((r) => r.json()),
      ]);
      setSkills(Array.isArray(s) ? s : []);
      setAgents(Array.isArray(a) ? a : []);
      setStats(st && typeof st === "object" ? st : null);
    } catch {
      /* waking up */
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  const categories = useMemo(
    () => ["all", ...Array.from(new Set(skills.map((s) => s.category))).sort()],
    [skills],
  );

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = skills.filter(
      (s) =>
        (category === "all" || s.category === category) &&
        (!q ||
          s.name.toLowerCase().includes(q) ||
          s.description.toLowerCase().includes(q) ||
          s.tags?.some((t) => t.toLowerCase().includes(q))),
    );
    list = [...list].sort((a, b) =>
      sort === "name"
        ? a.name.localeCompare(b.name)
        : sort === "category"
          ? a.category.localeCompare(b.category) || a.name.localeCompare(b.name)
          : (b.updated ?? 0) - (a.updated ?? 0),
    );
    return list;
  }, [skills, query, category, sort]);

  const now = Date.now() / 1000;

  return (
    <>
      {/* Top navigation */}
      <nav className="nav">
        <div className="nav-in">
          <div className="brand" onClick={() => { setView("skills"); setDetail(null); }}>
            <span className="logo">🧩</span> MCP Marketplace
          </div>
          <input
            className="nav-search"
            placeholder="Search skills, tags, categories…"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setView("skills"); }}
          />
          <div className="nav-links">
            <button className={view === "dashboard" ? "on" : ""} onClick={() => { setView("dashboard"); setDetail(null); }}>Dashboard</button>
            <button className={view === "skills" ? "on" : ""} onClick={() => { setView("skills"); setDetail(null); }}>Skills</button>
            <button className={view === "agents" ? "on" : ""} onClick={() => { setView("agents"); setDetail(null); }}>Agents</button>
            <button className={view === "publish" ? "on" : ""} onClick={() => { setView("publish"); setDetail(null); }}>Publish</button>
          </div>
        </div>
      </nav>

      {(view === "skills" || view === "agents") && (
        <header className="hero">
          <span className="eyebrow">One MCP server · {skills.length} tools</span>
          <h1>The marketplace for<br />MCP skills &amp; agents.</h1>
          <p>Browse, try, and add tools to Claude Code, Claude Desktop, or VS Code — from a single endpoint.</p>
        </header>
      )}

      <main className="wrap">
        {view === "dashboard" && (
          <Dashboard stats={stats} skills={skills} agents={agents} onOpen={(n) => setDetail({ kind: "skill", name: n })} onBrowse={() => setView("skills")} />
        )}

        {view === "skills" && (
          <>
            <div className="toolbar">
              <div className="chips">
                {categories.map((c) => (
                  <button key={c} className={`chip ${category === c ? "on" : ""}`} onClick={() => setCategory(c)}>
                    {c === "all" ? "All" : c}
                  </button>
                ))}
              </div>
              <select className="sort" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                <option value="recent">Recently updated</option>
                <option value="name">Name (A–Z)</option>
                <option value="category">Category</option>
              </select>
            </div>
            <div className="count">{visible.length} skill{visible.length === 1 ? "" : "s"}</div>
            <div className="grid">
              {visible.map((s) => (
                <button className="card" key={s.name} onClick={() => setDetail({ kind: "skill", name: s.name })}>
                  <div className="top">
                    <h3>{s.name}</h3>
                    <span className="ver">v{s.version}</span>
                  </div>
                  <div className="meta">
                    <span className="group-pill">{s.category}</span>
                    {s.updated && now - s.updated < RECENT && <span className="new">NEW</span>}
                  </div>
                  <p>{s.description}</p>
                  <div className="tags">{s.tags?.slice(0, 3).map((t) => <span className="tag" key={t}>{t}</span>)}</div>
                  <div className="card-stats">
                    <span>⬇ {stats?.per_skill[s.name]?.downloads ?? 0}</span>
                    <span>▶ {stats?.per_skill[s.name]?.runs ?? 0}</span>
                  </div>
                </button>
              ))}
              {visible.length === 0 && <p className="muted">No skills match your filters.</p>}
            </div>
          </>
        )}

        {view === "agents" && (
          <>
            <div className="count">{agents.length} agent{agents.length === 1 ? "" : "s"}</div>
            <div className="grid">
              {agents.map((a) => (
                <button className="card" key={a.name} onClick={() => setDetail({ kind: "agent", name: a.name })}>
                  <div className="top">
                    <h3>{a.name}</h3>
                    <span className="ver">v{a.version}</span>
                  </div>
                  <p>{a.description}</p>
                  <div className="tags">{a.skills?.map((sk) => <span className="tag" key={sk}>{sk}</span>)}</div>
                </button>
              ))}
            </div>
          </>
        )}

        {view === "publish" && <UploadPanel onDone={refresh} />}

        <div className="foot">Single MCP endpoint: <code>{mcpUrl()}</code></div>
      </main>

      {detail && <DetailDrawer kind={detail.kind} name={detail.name} onClose={() => setDetail(null)} />}
    </>
  );
}

function CopyBtn({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      className="copy"
      onClick={() => { navigator.clipboard?.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); }}
    >
      {done ? "Copied" : "Copy"}
    </button>
  );
}

const CLIENTS = (url: string) => [
  {
    key: "code", icon: "⌘", name: "Claude Code", tagline: "One command in your terminal",
    primary: `claude mcp add --transport http marketplace ${url}`,
    config: `claude mcp add --transport http marketplace ${url}`,
    note: "Run it, then type /mcp in a session.",
  },
  {
    key: "desktop", icon: "🖥", name: "Claude Desktop", tagline: "Add as a connector",
    primary: url,
    config: `{
  "mcpServers": {
    "marketplace": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "${url}"]
    }
  }
}`,
    note: "Settings → Developer → Edit Config → paste → restart.",
  },
  {
    key: "vscode", icon: "</>", name: "VS Code", tagline: "Copilot agent mode",
    primary: url,
    config: `{
  "servers": {
    "marketplace": { "type": "http", "url": "${url}" }
  }
}`,
    note: "Save as .vscode/mcp.json, open Copilot in Agent mode.",
  },
];

function ConnectorCards() {
  const url = mcpUrl();
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className="connectors">
      {CLIENTS(url).map((c) => (
        <div className="conn-card" key={c.key}>
          <div className="conn-icon">{c.icon}</div>
          <div className="conn-name">{c.name}</div>
          <div className="conn-tag">{c.tagline}</div>
          <div className="conn-actions">
            <CopyBtn text={c.config} />
            <button className="conn-toggle" onClick={() => setOpen(open === c.key ? null : c.key)}>
              {open === c.key ? "Hide config" : "View config"}
            </button>
          </div>
          {open === c.key && <pre className="snippet-code">{c.config}</pre>}
          <div className="conn-note">{c.note}</div>
        </div>
      ))}
    </div>
  );
}

function Dashboard({
  stats, skills, agents, onOpen, onBrowse,
}: {
  stats: Stats | null; skills: Skill[]; agents: Agent[];
  onOpen: (name: string) => void; onBrowse: () => void;
}) {
  const cats = stats ? Object.entries(stats.category_breakdown).sort((a, b) => b[1] - a[1]) : [];
  const maxCat = cats.length ? Math.max(...cats.map(([, n]) => n)) : 1;
  const recent = useMemo(
    () => [...skills].sort((a, b) => (b.updated ?? 0) - (a.updated ?? 0)).slice(0, 6),
    [skills],
  );
  const fmt = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);

  return (
    <div className="dash">
      {/* Product hero */}
      <section className="home-hero">
        <span className="eyebrow">Model Context Protocol · Marketplace</span>
        <h1>One server.<br />Every skill your agent needs.</h1>
        <p>Connect once and your client gets {stats?.skills ?? skills.length} ready-to-run tools — spec-driven development, code analysis, modernization, and integrations.</p>
        <div className="home-cta">
          <button className="btn primary" onClick={onBrowse}>Explore skills</button>
          <a className="btn ghost" href="#connect">Connect a client</a>
        </div>
      </section>

      {/* Metric tiles */}
      <div className="metrics">
        <Metric n={fmt(stats?.total_downloads ?? 0)} label="Downloads" icon="⬇" />
        <Metric n={fmt(stats?.total_runs ?? 0)} label="Runs" icon="▶" />
        <Metric n={`${stats?.skills ?? skills.length}`} label="Skills" icon="🧩" />
        <Metric n={`${stats?.agents ?? agents.length}`} label="Agents" icon="🤖" />
        <Metric n={`${stats?.categories ?? 0}`} label="Categories" icon="🗂" />
      </div>

      {/* Connect */}
      <section id="connect" className="home-sec">
        <h3>Add to your client</h3>
        <p className="muted">Pick your tool — copy the connector, you're live in seconds.</p>
        <ConnectorCards />
      </section>

      {/* Popular + categories */}
      <div className="dash-cols">
        <section className="dash-card">
          <h4>Popular skills</h4>
          {(stats?.popular ?? []).map((p, i) => (
            <button className="rank-row" key={p.name} onClick={() => onOpen(p.name)}>
              <span className="rank">{i + 1}</span>
              <span className="rank-name">{p.name}</span>
              <span className="rank-stat">⬇ {p.downloads} · ▶ {p.runs}</span>
            </button>
          ))}
          {!stats?.popular?.length && <p className="muted">No activity yet — be the first to run a skill.</p>}
        </section>
        <section className="dash-card">
          <h4>By category</h4>
          {cats.map(([c, n]) => (
            <div className="bar-row" key={c}>
              <span className="bar-label">{c}</span>
              <span className="bar"><span style={{ width: `${(n / maxCat) * 100}%` }} /></span>
              <span className="bar-n">{n}</span>
            </div>
          ))}
        </section>
      </div>

      <section className="home-sec">
        <h4>Recently updated</h4>
        <div className="grid">
          {recent.map((s) => (
            <button className="card" key={s.name} onClick={() => onOpen(s.name)}>
              <div className="top"><h3>{s.name}</h3><span className="ver">v{s.version}</span></div>
              <div className="meta"><span className="group-pill">{s.category}</span></div>
              <p>{s.description}</p>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metric({ n, label, icon }: { n: string; label: string; icon: string }) {
  return (
    <div className="metric">
      <div className="metric-icon">{icon}</div>
      <div className="metric-n">{n}</div>
      <div className="metric-l">{label}</div>
    </div>
  );
}

function DetailDrawer({ kind, name, onClose }: { kind: "skill" | "agent"; name: string; onClose: () => void }) {
  const [m, setM] = useState<Manifest | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    fetch(`${API}/${kind === "skill" ? "skills" : "agents"}/${name}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setM)
      .catch(() => setErr("Could not load details."));
  }, [kind, name]);

  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);

  return (
    <div className="overlay" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="close" onClick={onClose}>✕</button>
        {!m && !err && <p className="muted">Loading…</p>}
        {err && <p className="result err">{err}</p>}
        {m && (
          <>
            <div className="d-head">
              <h2>{m.name}</h2>
              <span className="ver">v{m.version}</span>
            </div>
            <div className="meta">
              {m.category && <span className="group-pill">{m.category}</span>}
              {(m.tags ?? []).map((t) => <span className="tag" key={t}>{t}</span>)}
            </div>
            <p className="d-desc">{m.description}</p>

            <div className="d-sec">
              <h4>Use in your client</h4>
              <p className="muted">Exposed as the MCP tool <code>{m.name}</code> on the single server below.</p>
              <ConnectorCards />
            </div>

            {kind === "skill" && (
              <>
                <div className="d-sec">
                  <h4>Inputs</h4>
                  <ParamTable params={m.inputs ?? []} />
                </div>
                <div className="d-sec">
                  <h4>Outputs</h4>
                  <ParamTable params={m.outputs ?? []} />
                </div>
                <TryIt name={m.name} params={m.inputs ?? []} />
                <div className="d-sec d-actions">
                  <a className="btn primary" href={`${API}/skills/${m.name}/download`}>⬇ Download skill</a>
                </div>
              </>
            )}

            {kind === "agent" && (
              <div className="d-sec">
                <h4>Workflow</h4>
                <ol className="workflow">
                  {(m.workflow ?? []).map((w, i) => (
                    <li key={i}><strong>{w.step}</strong>{w.uses ? <> → <code>{w.uses}</code></> : null}{w.description ? <div className="muted">{w.description}</div> : null}</li>
                  ))}
                </ol>
                <h4>Skills used</h4>
                <div className="tags">{(m.skills ?? []).map((s) => <span className="tag" key={s}>{s}</span>)}</div>
              </div>
            )}
          </>
        )}
      </aside>
    </div>
  );
}

function ParamTable({ params }: { params: Param[] }) {
  if (!params.length) return <p className="muted">—</p>;
  return (
    <table className="kv">
      <thead><tr><th>Name</th><th>Type</th><th>Req</th><th>Description</th></tr></thead>
      <tbody>
        {params.map((p) => (
          <tr key={p.name}>
            <td><code>{p.name}</code></td><td>{p.type}</td><td>{p.required ? "✓" : "—"}</td><td>{p.description}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TryIt({ name, params }: { name: string; params: Param[] }) {
  // Prefill from each input's first declared example so "Run" works out of the box.
  const initial: Record<string, string> = {};
  for (const p of params) {
    const ex = p.examples?.[0];
    if (ex !== undefined) initial[p.name] = Array.isArray(ex) ? ex.join(", ") : String(ex);
    else if (p.default !== undefined && p.default !== null) initial[p.name] = String(p.default);
  }
  const [vals, setVals] = useState<Record<string, string>>(initial);
  const [out, setOut] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true); setOut(null);
    const inputs: Record<string, unknown> = {};
    for (const p of params) {
      const raw = vals[p.name];
      if (raw === undefined || raw === "") continue;
      if (p.type === "integer" || p.type === "number") inputs[p.name] = Number(raw);
      else if (p.type === "boolean") inputs[p.name] = raw === "true";
      else if (p.type === "array") inputs[p.name] = raw.split(",").map((x) => x.trim()).filter(Boolean);
      else inputs[p.name] = raw;
    }
    try {
      const res = await fetch(`${API}/skills/${name}/execute`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ inputs }),
      });
      const data = await res.json();
      setOut(JSON.stringify(data.output ?? { error: data.error ?? data.detail }, null, 2));
    } catch (e) {
      setOut(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="d-sec">
      <h4>Try it</h4>
      <div className="tryform">
        {params.map((p) => (
          <label key={p.name} className="field">
            <span>{p.name}{p.required && <em>*</em>}</span>
            {p.enum ? (
              <select value={vals[p.name] ?? ""} onChange={(e) => setVals({ ...vals, [p.name]: e.target.value })}>
                <option value="">—</option>
                {p.enum.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            ) : (
              <input
                placeholder={p.type + (p.type === "array" ? " (comma-separated)" : "")}
                value={vals[p.name] ?? ""}
                onChange={(e) => setVals({ ...vals, [p.name]: e.target.value })}
              />
            )}
          </label>
        ))}
      </div>
      <button className="btn primary" disabled={busy} onClick={run}>{busy ? "Running…" : "Run skill"}</button>
      {out && <pre className="output">{out}</pre>}
    </div>
  );
}

type UploadResult = { name: string; version: string; installed_files: string[]; warnings: string[]; github_url: string | null };

function UploadPanel({ onDone }: { onDone: () => void }) {
  const [kind, setKind] = useState<"skill" | "agent">("skill");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);
  const base = kind === "skill" ? "skills" : "agents";

  async function go(action: "validate" | "upload") {
    if (!file) { setMsg({ ok: false, text: "Choose a .zip file first." }); return; }
    setBusy(true); setMsg(null); setResult(null);
    try {
      const fd = new FormData(); fd.append("file", file);
      const res = await fetch(`${API}/${base}/${action === "validate" ? "validate" : "upload"}`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) setMsg({ ok: false, text: `❌ ${data.detail || "Request failed"}` });
      else if (action === "validate") setMsg({ ok: true, text: `✅ Valid — ${data.name} v${data.version}. Click Publish.` });
      else { setMsg({ ok: true, text: `🎉 ${data.name} v${data.version} is live.` }); setResult(data); onDone(); }
    } catch (e) { setMsg({ ok: false, text: `❌ ${String(e)}` }); } finally { setBusy(false); }
  }

  return (
    <div className="section">
      <h2>Publish a {kind}</h2>
      <div className="seg left">
        <button className={kind === "skill" ? "active" : ""} onClick={() => setKind("skill")}>Skill / Spec-Kit</button>
        <button className={kind === "agent" ? "active" : ""} onClick={() => setKind("agent")}>Agent</button>
      </div>
      <div className="panel">
        <label className="drop">
          <input type="file" accept=".zip" onChange={(e) => { setFile(e.target.files?.[0] ?? null); setMsg(null); setResult(null); }} />
          {file ? <strong>{file.name}</strong> : (
            <>
              <strong>Click to choose a {kind} .zip</strong>
              <span className="muted">Must contain {kind === "skill" ? "SKILL.md" : "AGENT.md"} at the root or one folder deep.</span>
            </>
          )}
        </label>
        <div className="row">
          <button className="btn ghost" disabled={busy} onClick={() => go("validate")}>Validate format</button>
          <button className="btn primary" disabled={busy} onClick={() => go("upload")}>Upload &amp; Publish</button>
        </div>
        {msg && <div className={`result ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>}
        {result && (
          <div className="report">
            <div className="report-h">Installed files</div>
            <ul className="tree">{result.installed_files.map((f) => <li key={f}><code>{f}</code></li>)}</ul>
            {result.github_url && <p className="muted">Committed to GitHub — <a href={result.github_url}>view commit</a>.</p>}
          </div>
        )}
      </div>
    </div>
  );
}
