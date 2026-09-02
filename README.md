# Memorum

A fast, low-memory, cross-platform chat client — Discord's shape (server rail,
channels, real-time messages) reimagined as **a hive**: hexagonal server
icons and avatars, a honeycomb rail, and a honey/teal duotone instead of
Discord's blurple.

```
┌────┐ ┌───────────────┐ ┌─────────────────────────────┐ ┌──────────────┐
│ ⬡⬡ │ │ #general      │ │  Ari  Hey, is the migration  │ │ Online — 4   │
│ ⬡⬡ │ │ #off-topic    │ │        script done?          │ │  ⬡ Ari       │
│ ⬡⬡ │ │ + Add channel │ │  You  Yep, pushed it 🐝      │ │  ⬡ Sam       │
│ ⬡+ │ │               │ │  [ Message #general      ]   │ │  ⬡ Lee       │
└────┘ └───────────────┘ └─────────────────────────────┘ └──────────────┘
 rail       sidebar                 chat main                 members
```

## Architecture

Memorum is a **client/server** app, the same shape as Discord itself — one
backend, many clients — not a peer-to-peer or embedded-database app. That
matters for the CockroachDB credential: **only the backend ever holds it.**
The desktop client never sees a database connection string; it only speaks
HTTPS/WebSocket to the backend's public API.

```
 ┌─────────────────────┐        ┌──────────────────────┐        ┌───────────────┐
 │ Memorum desktop app  │  REST  │  Memorum backend       │  SQL   │  CockroachDB    │
 │ (Tauri + React)      │◄──────►│  (FastAPI, Python)     │◄──────►│  (managed)      │
 │ Windows / macOS       │  WS    │  JWT auth, WS gateway  │        │                 │
 └─────────────────────┘        └──────────────────────┘        └───────────────┘
```

- **Backend** — `backend/`: FastAPI, async SQLAlchemy + `asyncpg` (CockroachDB
  is wire-compatible with Postgres), JWT auth, a WebSocket gateway for
  real-time messages/typing/presence, Alembic migrations.
- **Frontend** — `frontend/`: React + TypeScript + Vite, Zustand for state,
  a hand-written CSS design system (no component library) in
  `frontend/src/styles/global.css`.
- **Desktop shell** — `frontend/src-tauri/`: Tauri wraps the built React app
  in a native OS webview. This is *why* it's fast and light — Tauri ships
  the OS's own WebView2 (Windows) / WKWebView (macOS) instead of bundling a
  full Chromium + Node runtime the way Electron does, so the installed app
  is tens of megabytes rather than hundreds, and idles at a fraction of the
  memory.

## Repository layout

```
memorum/
├── backend/                 FastAPI service
│   ├── app/
│   │   ├── core/            config, db session, JWT/password helpers, auth deps
│   │   ├── models/          SQLAlchemy models
│   │   ├── routers/         REST endpoints (auth, servers, channels, messages, friends)
│   │   ├── ws/               WebSocket gateway + connection manager
│   │   └── main.py           app factory
│   ├── alembic/               migrations
│   ├── tests/                  pytest suite (run in CI against real CockroachDB)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/                  React app + Tauri shell
│   ├── src/
│   │   ├── components/         ServerRail, ChannelSidebar, ChatView, MemberList, ...
│   │   ├── store/                zustand auth/chat stores
│   │   ├── lib/                   REST client, WS client, color helpers
│   │   └── styles/global.css      design tokens + all component styles
│   ├── src-tauri/                Rust/Tauri desktop shell + generated icon set
│   └── .env.example
└── .github/workflows/build.yml   CI: backend tests + Windows/macOS builds
```

## Running it locally

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: paste your CockroachDB connection string into DATABASE_URL,
# and set JWT_SECRET to a long random string.
alembic upgrade head
uvicorn app.main:app --reload
```

The backend health-checks at `http://localhost:8000/api/health`, and its
interactive API docs are at `http://localhost:8000/docs`.

### 2. Frontend (browser, for quick iteration)

```bash
cd frontend
npm install
cp .env.example .env      # defaults already point at localhost:8000
npm run dev
```

### 3. Desktop app (Tauri)

Requires the [Rust toolchain](https://rustup.rs) in addition to Node:

```bash
cd frontend
npm install
npm run tauri dev     # live-reloading desktop window
npm run tauri build   # produces a native installer under src-tauri/target/release/bundle
```

## CockroachDB setup

Any CockroachDB cluster works (CockroachDB Cloud, CockroachDB Serverless, or
self-hosted). Grab the connection string from the CockroachDB console — it
looks like:

```
postgresql://<user>:<password>@<host>:26257/defaultdb?sslmode=verify-full
```

Put that in `backend/.env` as `DATABASE_URL` for local dev. `alembic upgrade
head` creates the schema (users, servers, channels, messages, membership,
friendships) — see `backend/alembic/versions/0001_initial_schema.py`.

## Setting up the GitHub Actions secret

The CI workflow (`.github/workflows/build.yml`) runs the backend test suite
against a real CockroachDB connection and builds the desktop app for Windows
and macOS. It reads the connection string from a **repository secret**, never
from a committed file:

1. On GitHub: **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `DATABASE_URL`, value: your CockroachDB connection string.
3. (Recommended) add a second secret, `JWT_SECRET`, a long random string —
   if you skip this, CI falls back to a throwaway value so the workflow
   still runs, but you should set a real one before deploying the backend
   anywhere real.
4. (Optional) under the **Variables** tab (not Secrets — these aren't
   sensitive), add `MEMORUM_API_URL` and `MEMORUM_WS_URL` pointing at your
   deployed backend, so desktop builds produced by CI point at it instead of
   `localhost`.

The workflow never logs, echoes, or writes `DATABASE_URL` to a file — it's
only ever exported as an environment variable to the two processes that use
it (`alembic upgrade head` and `pytest`).

> **Rotate the credential you shared while building this.** A CockroachDB
> password that was ever pasted into a chat, a screenshot, or a non-secret
> file should be treated as compromised — regenerate it from the CockroachDB
> console's SQL Users page and only put the new one into the GitHub secret
> above.

## Deploying the backend

Desktop clients need a real backend to connect to (they don't embed
CockroachDB credentials themselves). `backend/Dockerfile` builds a container
image; run it anywhere that takes `DATABASE_URL` and `JWT_SECRET` as runtime
environment variables (a VPS, Fly.io, Railway, Render, ECS, etc.) — for
example:

```bash
docker build -t memorum-backend ./backend
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://..." \
  -e JWT_SECRET="..." \
  -e CORS_ORIGINS="tauri://localhost,https://your-domain" \
  memorum-backend
```

Then point the desktop build at it via `MEMORUM_API_URL` / `MEMORUM_WS_URL`
(see above) before running `npm run tauri build`.

## What's implemented

- Account creation / login (JWT), servers ("hives") with invite codes,
  multiple text channels per server, real-time messaging, typing indicators,
  online/offline presence, a member list, 1:1 direct messages, friend
  requests.

## What's intentionally out of scope (next steps)

- **Voice/video channels** — Discord's WebRTC voice stack is a project of
  its own; the schema and gateway are structured so a `voice` channel kind
  could be added without reshaping what's here.
- **Granular permissions** — currently owner/admin/member; Discord's
  per-channel permission bitfields aren't implemented.
- **Message editing/deletion, reactions, attachments, search** — the
  `messages` table has an `edited_at` column ready for edit support, but the
  UI and endpoints for edit/delete/react/upload aren't built yet.
- **Horizontal scaling** — the WebSocket connection manager
  (`backend/app/ws/manager.py`) is in-memory and works great for one backend
  process. Scaling to multiple instances needs a shared pub/sub layer
  (Redis is the natural fit); the manager's public methods are written as
  the seam where that would plug in.
- **Rate limiting / abuse prevention** — not implemented; add before opening
  this up publicly.
