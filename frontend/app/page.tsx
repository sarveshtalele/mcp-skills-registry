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
type Sort = "recent" | "name" | "category";

const RECENT_WINDOW = 7 * 24 * 3600; // 7 days in seconds

export default function Page() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string>("all");
  const [sort, setSort] = useState<Sort>("recent");
  const [tab, setTab] = useState<"browse" | "upload">("browse");

  async function refresh() {
    try {
      const [s, a] = await Promise.all([
        fetch(`${API}/skills?limit=100`).then((r) => r.json()),
        fetch(`${API}/agents`).then((r) => r.json()),
      ]);
      setSkills(Array.isArray(s) ? s : []);
      setAgents(Array.isArray(a) ? a : []);
    } catch {
      /* server waking up */
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
    let list = skills.filter((s) => {
      const matchesCat = category === "all" || s.category === category;
      const matchesQ =
        !q ||
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags?.some((t) => t.toLowerCase().includes(q));
      return matchesCat && matchesQ;
    });
    list = [...list].sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      if (sort === "category") return a.category.localeCompare(b.category) || a.name.localeCompare(b.name);
      return (b.updated ?? 0) - (a.updated ?? 0); // recent
    });
    return list;
  }, [skills, query, category, sort]);

  const now = Date.now() / 1000;

  return (
    <>
      <header className="hero">
        <span className="eyebrow">MCP Skill Registry</span>
        <h1>Discover, run &amp; share<br />MCP skills.</h1>
        <p>
          A curated catalogue of skills and agents for Claude Code, Claude Desktop, and
          GitHub Copilot — browse, filter, download, or publish your own.
        </p>
        <div className="stats">
          <div className="stat"><div className="n">{skills.length}</div><div className="l">Skills</div></div>
          <div className="stat"><div className="n">{agents.length}</div><div className="l">Agents</div></div>
          <div className="stat"><div className="n">{categories.length - 1}</div><div className="l">Categories</div></div>
        </div>
        <div className="seg">
          <button className={tab === "browse" ? "active" : ""} onClick={() => setTab("browse")}>Browse</button>
          <button className={tab === "upload" ? "active" : ""} onClick={() => setTab("upload")}>Publish</button>
        </div>
      </header>

      <main className="wrap">
        {tab === "browse" ? (
          <>
            <div className="toolbar">
              <input
                className="search"
                placeholder="Search skills…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <select className="sort" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                <option value="recent">Recently updated</option>
                <option value="name">Name (A–Z)</option>
                <option value="category">Category</option>
              </select>
            </div>

            <div className="chips">
              {categories.map((c) => (
                <button
                  key={c}
                  className={`chip ${category === c ? "on" : ""}`}
                  onClick={() => setCategory(c)}
                >
                  {c === "all" ? "All" : c}
                </button>
              ))}
            </div>

            <div className="grid">
              {visible.map((s) => (
                <div className="card" key={s.name}>
                  <div className="top">
                    <h3>{s.name}</h3>
                    <span className="ver">v{s.version}</span>
                  </div>
                  <div className="meta">
                    <span className="group-pill">{s.category}</span>
                    {s.updated && now - s.updated < RECENT_WINDOW && <span className="new">NEW</span>}
                  </div>
                  <p>{s.description}</p>
                  <div className="tags">
                    {s.tags?.slice(0, 4).map((t) => <span className="tag" key={t}>{t}</span>)}
                  </div>
                  <div className="actions">
                    <a className="btn small primary" href={`${API}/skills/${s.name}/download`}>⬇ Download</a>
                    <a className="btn small ghost" href={`${API}/skills/${s.name}`} target="_blank" rel="noreferrer">Details</a>
                  </div>
                </div>
              ))}
              {visible.length === 0 && <p className="muted">No skills match your filters.</p>}
            </div>

            <div className="section">
              <h2>Agents</h2>
              <div className="grid">
                {agents.map((a) => (
                  <div className="card" key={a.name}>
                    <div className="top">
                      <h3>{a.name}</h3>
                      <span className="ver">v{a.version}</span>
                    </div>
                    <p>{a.description}</p>
                    <div className="tags">
                      {a.skills?.map((sk) => <span className="tag" key={sk}>{sk}</span>)}
                    </div>
                  </div>
                ))}
                {agents.length === 0 && <p className="muted">No agents yet.</p>}
              </div>
            </div>
          </>
        ) : (
          <UploadPanel onDone={refresh} />
        )}

        <div className="foot">
          MCP endpoint: <code>/mcp</code> · REST API: <code>/api/v1</code>
        </div>
      </main>
    </>
  );
}

type UploadResult = {
  name: string;
  version: string;
  installed_files: string[];
  warnings: string[];
  github_url: string | null;
};

function UploadPanel({ onDone }: { onDone: () => void }) {
  const [kind, setKind] = useState<"skill" | "agent">("skill");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [result, setResult] = useState<UploadResult | null>(null);

  const base = kind === "skill" ? "skills" : "agents";

  async function go(action: "validate" | "upload") {
    if (!file) {
      setMsg({ ok: false, text: "Choose a .zip file first." });
      return;
    }
    setBusy(true);
    setMsg(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const path = action === "validate" ? `${base}/validate` : `${base}/upload`;
      const res = await fetch(`${API}/${path}`, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        setMsg({ ok: false, text: `❌ ${data.detail || "Request failed"}` });
      } else if (action === "validate") {
        setMsg({ ok: true, text: `✅ Valid — ${data.name} v${data.version}. Click Publish.` });
      } else {
        setMsg({ ok: true, text: `🎉 ${data.name} v${data.version} is live.` });
        setResult(data as UploadResult);
        onDone();
      }
    } catch (e) {
      setMsg({ ok: false, text: `❌ ${String(e)}` });
    } finally {
      setBusy(false);
    }
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
              <span className="muted">
                Must contain {kind === "skill" ? "SKILL.md" : "AGENT.md"} at the root or one folder deep — a wrapper folder is detected automatically.
              </span>
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
            {result.warnings.length > 0 && (
              <>
                <div className="report-h">Advisories</div>
                <ul className="warn">{result.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
              </>
            )}
            {result.github_url && (
              <p className="muted">Committed to GitHub — <a href={result.github_url}>view commit</a>. The Space will redeploy.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
