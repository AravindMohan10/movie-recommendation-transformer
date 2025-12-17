# Deploy CineAI: Vercel (frontend) + Fly.io (backend)

This guide walks through deploying the frontend on Vercel and the backend on Fly.io. You need a GitHub account, a Vercel account, and a Fly.io account (all free to sign up).

---

## Part 1: Deploy the backend on Fly.io

### 1.1 Install Fly CLI

- **macOS (Homebrew):** `brew install flyctl`
- **Windows:** `powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"`
- **Linux:** `curl -L https://fly.io/install.sh | sh`

Then log in:

```bash
fly auth login
```

A browser window will open; sign in or create a Fly account.

### 1.2 Prepare the backend for Fly

The repo has a Dockerfile at the project root that builds the backend with Checkpoints and data. From the **project root** (not `backend/`), run `fly launch --no-deploy`. When prompted: app name (e.g. `cineai-api`), region, say No to Postgres. This creates `fly.toml`.

### 1.3 Persistent storage (SQLite) on Fly

To keep the SQLite DB across deploys:

```bash
fly volumes create cineai_data --region <your-region> --size 1
```

In `fly.toml` add:

```toml
[mounts]
  source = "cineai_data"
  destination = "/data"
```

The repo’s `fly.toml` sets `DATABASE_PATH=/data/cineai.db` in `[env]` so the backend uses the volume. Ensure the volume exists (see above); no secret needed for `DATABASE_PATH` unless you override it.

### 1.4 Set secrets (env) on Fly

Do **not** put secrets in `fly.toml`. Use:

```bash
fly secrets set SECRET_KEY="your-long-random-secret"
fly secrets set ENV=production
fly secrets set GROQ_API_KEY="your-groq-key"
fly secrets set TMDB_API_KEY="your-tmdb-key"
# If you use Resend for email:
fly secrets set RESEND_API_KEY="your-resend-key"
```

Generate a safe `SECRET_KEY` with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**CORS:** `fly.toml` already sets `ALLOWED_ORIGINS` to `https://cineai-flame.vercel.app` plus localhost. If your frontend URL is different, set: `fly secrets set ALLOWED_ORIGINS="https://your-app.vercel.app"` (secrets override `fly.toml` [env]).

### 1.5 Deploy

From the **project root**:

```bash
fly deploy
```

When it’s done, Fly shows the app URL (e.g. `https://cineai-api.fly.dev`). The API is under `/api`, so use `https://cineai-api.fly.dev/api` as `VITE_API_BASE` in the frontend.

### 1.6 Health checks

- **Liveness:** `GET https://your-app.fly.dev/health` (process is up).
- **Readiness:** `GET https://your-app.fly.dev/ready` (DB is reachable).

Use `/ready` for readiness and `/health` for liveness in Fly (or any load balancer).

---

## Part 2: Deploy the frontend on Vercel

### 2.1 Push code to GitHub

If the project isn’t on GitHub yet:

1. Create a new repo on GitHub.
2. In your project folder:

   ```bash
   git remote add origin https://github.com/your-username/your-repo.git
   git push -u origin main
   ```

### 2.2 Import the project in Vercel

1. Go to [vercel.com](https://vercel.com) and sign in (e.g. with GitHub).
2. Click **Add New** → **Project**.
3. Import your GitHub repo. Select the repo and continue.
4. **Root Directory:** set to `frontend` (so Vercel builds the Vite app).
5. **Framework Preset:** Vite (should be auto-detected).
6. **Build Command:** `npm run build` (default).
7. **Output Directory:** `dist` (default for Vite).

### 2.3 Set environment variable for the API

In the Vercel project, go to **Settings** → **Environment Variables**. Add:

- **Name:** `VITE_API_BASE`
- **Value:** `https://cineai-api.fly.dev/api` (your Fly backend URL; no trailing slash if your app doesn’t expect it).
- **Environment:** Production (and Preview if you want).

Save. Redeploy the project (Deployments → … → Redeploy) so the build picks up the variable.

### 2.4 Deploy

Trigger a deploy (e.g. push to `main` or click **Deploy** in Vercel). When it’s done, Vercel gives you a URL like `https://your-project.vercel.app`. That’s your **frontend URL**.

### 2.5 CORS (already in fly.toml)

`fly.toml` [env] sets `ALLOWED_ORIGINS` to `https://cineai-flame.vercel.app` and localhost. If your Vercel URL is different, run `fly secrets set ALLOWED_ORIGINS="https://your-project.vercel.app"` and redeploy.

---

## Part 3: Troubleshooting

### "Origin … is not allowed by Access-Control-Allow-Origin" or 502

- **CORS:** Ensure your Vercel frontend URL is in `ALLOWED_ORIGINS`. It’s set in `fly.toml` [env]; override with `fly secrets set ALLOWED_ORIGINS="https://your-app.vercel.app"`.
- **502:** The proxy got no valid response from the app. Check `fly logs` for crashes (e.g. `ModuleNotFoundError`, DB errors). Ensure the Fly volume exists (`fly volumes list`) and the app has `DATABASE_PATH=/data/cineai.db` (already in `fly.toml`). Redeploy with `fly deploy --no-cache` after changing the Dockerfile (e.g. `COPY models`).

### Genres / onboarding / only fallback recommendations

- Genre chips and onboarding status come from the API; if those requests fail (CORS or 502), the UI falls back (no chips, show onboarding). Fix CORS and 502 first.
- If you still see only "Popular picks", the recommendation model isn’t loading on Fly. Ensure the Dockerfile includes `COPY models /app/models` and redeploy.

---

## Part 4: Quick checklist

- [ ] Fly CLI installed, `fly auth login` done.
- [ ] Dockerfile and `fly.toml` at project root; volume created and mounted (see 1.3).
- [ ] Fly secrets set: `SECRET_KEY`, `ENV=production`, `GROQ_API_KEY`, `TMDB_API_KEY`, etc. (`ALLOWED_ORIGINS` and `DATABASE_PATH` are in `fly.toml`.)
- [ ] `fly deploy` from project root; backend URL works and `/health` and `/ready` return 200.
- [ ] Repo on GitHub; Vercel project created with root `frontend`.
- [ ] `VITE_API_BASE` set in Vercel to your Fly API URL (e.g. `https://movie-recommendation-transformer.fly.dev/api`).
- [ ] Frontend deployed; you can open the app and see recommendations (after login/setup).

If something fails, check Fly logs: `fly logs`, and Vercel build logs in the dashboard.
