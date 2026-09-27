import { Component, HostListener, computed, signal } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';

const API = '/api/v1';

type Skill = { name: string; version: string; description: string; category: string; tags: string[]; updated: number | null };
type Agent = { name: string; version: string; description: string; skills: string[] };
type Param = { name: string; type: string; required: boolean; description: string; default?: unknown; enum?: string[]; examples?: unknown[] };
type Manifest = {
  name: string; version: string; description: string; category?: string; tags?: string[];
  inputs?: Param[]; outputs?: Param[]; execution?: { entrypoint?: string; type?: string };
  skills?: string[]; workflow?: { step: string; uses?: string; description?: string }[];
};
type Sort = 'recent' | 'name' | 'category';
type View = 'dashboard' | 'skills' | 'agents' | 'publish';
type Stats = {
  skills: number; agents: number; categories: number; total_runs: number; total_downloads: number;
  category_breakdown: Record<string, number>;
  popular: { name: string; runs: number; downloads: number }[];
  per_skill: Record<string, { name: string; runs: number; downloads: number }>;
};
type UploadResult = { name: string; version: string; installed_files: string[]; warnings: string[]; github_url: string | null };

const RECENT = 7 * 24 * 3600;
const mcpUrl = () => `${window.location.origin}/mcp`;

const CLIENTS = (url: string) => [
  {
    key: 'code', icon: '⌘', name: 'Claude Code', tagline: 'One command in your terminal',
    primary: `claude mcp add --transport http marketplace ${url}`,
    config: `claude mcp add --transport http marketplace ${url}`,
    note: 'Run it, then type /mcp in a session.',
  },
  {
    key: 'desktop', icon: '🖥', name: 'Claude Desktop', tagline: 'Add as a connector',
    primary: url,
    config: `{
  "mcpServers": {
    "marketplace": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "${url}"]
    }
  }
}`,
    note: 'Settings → Developer → Edit Config → paste → restart.',
  },
  {
    key: 'vscode', icon: '</>', name: 'VS Code', tagline: 'Copilot agent mode',
    primary: url,
    config: `{
  "servers": {
    "marketplace": { "type": "http", "url": "${url}" }
  }
}`,
    note: 'Save as .vscode/mcp.json, open Copilot in Agent mode.',
  },
];

/** Port of frontend/app/page.tsx (Page + CopyBtn, ConnectorCards, Dashboard, Metric, DetailDrawer, ParamTable, TryIt, UploadPanel). */
@Component({
  selector: 'app-page',
  standalone: true,
  imports: [NgTemplateOutlet],
  templateUrl: './page.component.html',
})
export class PageComponent {
  readonly skills = signal<Skill[]>([]);
  readonly agents = signal<Agent[]>([]);
  readonly stats = signal<Stats | null>(null);
  readonly view = signal<View>('dashboard');
  readonly query = signal('');
  readonly category = signal('all');
  readonly sort = signal<Sort>('recent');
  readonly detail = signal<{ kind: 'skill' | 'agent'; name: string } | null>(null);

  readonly mcpUrl = mcpUrl();
  readonly clients = CLIENTS(this.mcpUrl);
  readonly now = Date.now() / 1000;
  readonly RECENT = RECENT;
  readonly apiBase = API;

  // ConnectorCards / CopyBtn keep their own state per rendered instance ("dash" / "drawer").
  readonly openConn = signal<Record<string, string | null>>({});
  readonly copied = signal<Record<string, boolean>>({});

  // DetailDrawer
  readonly manifest = signal<Manifest | null>(null);
  readonly detailErr = signal<string | null>(null);
  // TryIt
  readonly vals = signal<Record<string, string>>({});
  readonly out = signal<string | null>(null);
  readonly busy = signal(false);
  // UploadPanel
  readonly upKind = signal<'skill' | 'agent'>('skill');
  readonly file = signal<File | null>(null);
  readonly upBusy = signal(false);
  readonly msg = signal<{ ok: boolean; text: string } | null>(null);
  readonly result = signal<UploadResult | null>(null);

  readonly categories = computed(() => ['all', ...Array.from(new Set(this.skills().map((s) => s.category))).sort()]);

  readonly visible = computed(() => {
    const q = this.query().trim().toLowerCase();
    const category = this.category();
    const sort = this.sort();
    const list = this.skills().filter(
      (s) =>
        (category === 'all' || s.category === category) &&
        (!q || s.name.toLowerCase().includes(q) || s.description.toLowerCase().includes(q) || s.tags?.some((t) => t.toLowerCase().includes(q))),
    );
    return [...list].sort((a, b) =>
      sort === 'name'
        ? a.name.localeCompare(b.name)
        : sort === 'category'
          ? a.category.localeCompare(b.category) || a.name.localeCompare(b.name)
          : (b.updated ?? 0) - (a.updated ?? 0),
    );
  });

  readonly cats = computed(() => {
    const st = this.stats();
    return st ? Object.entries(st.category_breakdown).sort((a, b) => b[1] - a[1]) : [];
  });
  readonly maxCat = computed(() => (this.cats().length ? Math.max(...this.cats().map(([, n]) => n)) : 1));
  readonly recent = computed(() => [...this.skills()].sort((a, b) => (b.updated ?? 0) - (a.updated ?? 0)).slice(0, 6));

  constructor() {
    this.refresh();
  }

  async refresh() {
    try {
      const [s, a, st] = await Promise.all([
        fetch(`${API}/skills?limit=200`).then((r) => r.json()),
        fetch(`${API}/agents`).then((r) => r.json()),
        fetch(`${API}/stats`).then((r) => r.json()),
      ]);
      this.skills.set(Array.isArray(s) ? s : []);
      this.agents.set(Array.isArray(a) ? a : []);
      this.stats.set(st && typeof st === 'object' ? st : null);
    } catch {
      /* waking up */
    }
  }

  go(view: View) {
    // Leaving a view unmounts it in the source app: its local state starts fresh next time.
    if (view !== this.view()) {
      if (this.view() === 'dashboard') this.openConn.update((o) => ({ ...o, dash: null }));
      if (this.view() === 'publish') {
        this.upKind.set('skill');
        this.file.set(null);
        this.msg.set(null);
        this.result.set(null);
      }
    }
    this.view.set(view);
    this.closeDetail();
  }

  onSearch(value: string) {
    this.query.set(value);
    this.view.set('skills');
  }

  openDetail(kind: 'skill' | 'agent', name: string) {
    this.detail.set({ kind, name });
    this.manifest.set(null);
    this.detailErr.set(null);
    this.out.set(null);
    this.busy.set(false);
    fetch(`${API}/${kind === 'skill' ? 'skills' : 'agents'}/${name}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((m: Manifest) => {
        this.vals.set(this.initialVals(m.inputs ?? []));
        this.manifest.set(m);
      })
      .catch(() => this.detailErr.set('Could not load details.'));
  }

  closeDetail() {
    this.detail.set(null);
    this.openConn.update((o) => ({ ...o, drawer: null }));
  }

  @HostListener('window:keydown', ['$event'])
  onKey(e: KeyboardEvent) {
    if (e.key === 'Escape' && this.detail()) this.closeDetail();
  }

  toggleConn(where: string, key: string) {
    this.openConn.update((o) => ({ ...o, [where]: o[where] === key ? null : key }));
  }

  copy(id: string, text: string) {
    navigator.clipboard?.writeText(text);
    this.copied.update((c) => ({ ...c, [id]: true }));
    setTimeout(() => this.copied.update((c) => ({ ...c, [id]: false })), 1500);
  }

  // Prefill from each input's first declared example so "Run" works out of the box.
  initialVals(params: Param[]): Record<string, string> {
    const initial: Record<string, string> = {};
    for (const p of params) {
      const ex = p.examples?.[0];
      if (ex !== undefined) initial[p.name] = Array.isArray(ex) ? ex.join(', ') : String(ex);
      else if (p.default !== undefined && p.default !== null) initial[p.name] = String(p.default);
    }
    return initial;
  }

  setVal(name: string, value: string) {
    this.vals.update((v) => ({ ...v, [name]: value }));
  }

  async run(name: string, params: Param[]) {
    this.busy.set(true);
    this.out.set(null);
    const inputs: Record<string, unknown> = {};
    const vals = this.vals();
    for (const p of params) {
      const raw = vals[p.name];
      if (raw === undefined || raw === '') continue;
      if (p.type === 'integer' || p.type === 'number') inputs[p.name] = Number(raw);
      else if (p.type === 'boolean') inputs[p.name] = raw === 'true';
      else if (p.type === 'array') inputs[p.name] = raw.split(',').map((x) => x.trim()).filter(Boolean);
      else inputs[p.name] = raw;
    }
    try {
      const res = await fetch(`${API}/skills/${name}/execute`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ inputs }),
      });
      const data = await res.json();
      this.out.set(JSON.stringify(data.output ?? { error: data.error ?? data.detail }, null, 2));
    } catch (e) {
      this.out.set(String(e));
    } finally {
      this.busy.set(false);
    }
  }

  onFile(input: HTMLInputElement) {
    this.file.set(input.files?.[0] ?? null);
    this.msg.set(null);
    this.result.set(null);
  }

  async upload(action: 'validate' | 'upload') {
    const file = this.file();
    if (!file) {
      this.msg.set({ ok: false, text: 'Choose a .zip file first.' });
      return;
    }
    const base = this.upKind() === 'skill' ? 'skills' : 'agents';
    this.upBusy.set(true);
    this.msg.set(null);
    this.result.set(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${API}/${base}/${action === 'validate' ? 'validate' : 'upload'}`, { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) this.msg.set({ ok: false, text: `❌ ${data.detail || 'Request failed'}` });
      else if (action === 'validate') this.msg.set({ ok: true, text: `✅ Valid — ${data.name} v${data.version}. Click Publish.` });
      else {
        this.msg.set({ ok: true, text: `🎉 ${data.name} v${data.version} is live.` });
        this.result.set(data);
        this.refresh();
      }
    } catch (e) {
      this.msg.set({ ok: false, text: `❌ ${String(e)}` });
    } finally {
      this.upBusy.set(false);
    }
  }
}
