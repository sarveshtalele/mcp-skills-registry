"use client";

import { useEffect, useMemo, useState } from "react";

// Same-origin API (the FastAPI server serves this static app and the API).
const API = "/api/v1";

type Skill = {
  name: string;
  version: string;
  description: string;
  category: string;
  tags: string[];
};
type Agent = { name: string; version: string; description: string; skills: string[] };

export default function Page() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [query, setQuery] = useState("");
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
      /* server may be waking up */
    }
  }
  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return skills;
    return skills.filter(
      (s) =>
        s.name.toLowerCase().includes(q) ||
        s.description.toLowerCase().includes(q) ||
        s.tags?.some((t) => t.toLowerCase().includes(q)),
    );
  }, [skills, query]);

  return (
    <>
      <header className="hero">
        <span className="eyebrow">MCP Skill Registry</span>
        <h1>Skills & agents,
          <br />ready for any client.</h1>
        <p>
          Browse the catalogue, upload your own skills and agents, and run them from
          Claude Code, Claude Desktop, or GitHub Copilot.
        </p>
        <div className="stats">
          <div className="stat"><div className="n">{skills.length}</div><div className="l">Skills</div></div>
          <div className="stat"><div className="n">{agents.length}</div><div className="l">Agents</div></div>
          <div className="stat"><div className="n">MCP</div><div className="l">Streamable HTTP</div></div>
        </div>
        <div className="seg">
          <button className={tab === "browse" ? "active" : ""} onClick={() => setTab("browse")}>Browse</button>
          <button className={tab === "upload" ? "active" : ""} onClick={() => setTab("upload")}>Upload</button>
        </div>
      </header>

      <main className="wrap">
        {tab === "browse" ? (
          <>
            <div className="section">
              <h2>Skills</h2>
              <input
                className="search"
                placeholder="Search skills…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              <div className="grid">
                {filtered.map((s) => (
                  <div className="card" key={s.name}>
                    <div className="top">
                      <h3>{s.name}</h3>
                      <span className="ver">v{s.version}</span>
                    </div>
                    <p>{s.description}</p>
                    <div className="tags">
                      <span className="group-pill">{s.category}</span>
                      {s.tags?.slice(0, 3).map((t) => <span className="tag" key={t}>{t}</span>)}
                    </div>
                  </div>
                ))}
                {filtered.length === 0 && <p className="muted">No skills match “{query}”.</p>}
              </div>
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
          MCP endpoint: <code>/mcp</code> · API docs: <a href="/docs">/docs</a>
        </div>
      </main>
    </>
  );
}

function UploadPanel({ onDone }: { onDone: () => void }) {
  const [kind, setKind] = useState<"skill" | "agent">("skill");
  const [file, setFile] = useState<File | null>(null);
  const [overwrite, setOverwrite] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const validatePath = kind === "skill" ? "skills/validate" : "agents/validate";
  const uploadPath = kind === "skill" ? "skills/upload" : "agents/upload";

  async function call(path: string, withOverwrite = false) {
    if (!file) {
      setMsg({ ok: false, text: "Choose a .zip file first." });
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const url = `${API}/${path}${withOverwrite && overwrite ? "?overwrite=true" : ""}`;
      const res = await fetch(url, { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        setMsg({ ok: false, text: `❌ ${data.detail || "Request failed"}` });
      } else if (withOverwrite) {
        setMsg({ ok: true, text: `🎉 ${data.name} v${data.version} published. It is live now.` });
        onDone();
      } else {
        setMsg({ ok: true, text: `✅ Valid — ${data.name} v${data.version}. Click Publish.` });
      }
    } catch (e) {
      setMsg({ ok: false, text: `❌ ${String(e)}` });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="section">
      <h2>Upload</h2>
      <div className="seg" style={{ display: "flex" }}>
        <button className={kind === "skill" ? "active" : ""} onClick={() => setKind("skill")}>Skill / Spec-Kit skill</button>
        <button className={kind === "agent" ? "active" : ""} onClick={() => setKind("agent")}>Agent</button>
      </div>
      <div className="panel">
        <label className="drop">
          <input
            type="file"
            accept=".zip"
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setMsg(null); }}
          />
          {file ? (
            <strong>{file.name}</strong>
          ) : (
            <>
              <strong>Click to choose a {kind} .zip</strong>
              <div className="muted" style={{ marginTop: 6 }}>
                Must contain {kind === "skill" ? "SKILL.md" : "AGENT.md"} at the root or one folder deep.
              </div>
            </>
          )}
        </label>

        <div className="row">
          <button className="btn ghost" disabled={busy} onClick={() => call(validatePath)}>Validate format</button>
          <button className="btn primary" disabled={busy} onClick={() => call(uploadPath, true)}>Upload &amp; Publish</button>
          <label className="checkbox">
            <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} />
            Overwrite if it exists
          </label>
        </div>

        {msg && <div className={`result ${msg.ok ? "ok" : "err"}`}>{msg.text}</div>}
      </div>
    </div>
  );
}
