# frontend-angular

An Angular 18 port of `frontend/` (the Next.js dashboard), with the same DOM, the same CSS and the same behaviour.

The port was verified with the codebase-migration factory's skills: every page and view of the running app was screenshot in the original and in this port, under the same pinned browser settings. The result: **0% pixel difference** on all 6 states (dashboard, skills, agents, publish, skill detail, agent detail), and all 5 click edges land in the same place.

## Run it

The FastAPI server serves this build instead of `frontend/out`:

```bash
cd frontend-angular && npm install && npx ng build
```

```bash
SKILLREG_FRONTEND_DIR=frontend-angular/dist/mcp-skills-registry-ng/browser skill-registry
```

Open http://127.0.0.1:7860.

## Where things are

- `src/app/pages/page/`: the port of `frontend/app/page.tsx` (Page, Dashboard, DetailDrawer, TryIt, UploadPanel, ConnectorCards).
- `src/styles.css`: `frontend/app/globals.css`, verbatim.
