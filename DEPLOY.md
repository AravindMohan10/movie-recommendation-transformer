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

Set the app’s SQLite path via a secret: `fly secrets set DATABASE_PATH=/data/cineai.db`. The backend reads `DATABASE_PATH` and uses it when set.

### 1.4 Set secrets (env) on Fly

Do **not** put secrets in `fly.toml`. Use:

```bash
fly secrets set SECRET_KEY="your-long-random-secret"
fly secrets set ENV=production
fly secrets set ALLOWED_ORIGINS="https://your-app.vercel.app"
fly secrets set GROQ_API_KEY="your-groq-key"
fly secrets set TMDB_API_KEY="your-tmdb-key"
# If you use Resend for email:
fly secrets set RESEND_API_KEY="your-resend-key"
```

Generate a safe `SECRET_KEY` with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use your **real** Vercel frontend URL for `ALLOWED_ORIGINS` (no trailing slash). After you deploy the frontend (Part 2), come back and set it if you haven’t yet.

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

### 2.5 Point backend CORS at the frontend

Back on Fly, set the frontend URL as the only allowed origin (or comma-separated list):

```bash
fly secrets set ALLOWED_ORIGINS="https://your-project.vercel.app"
```

Redeploy the backend if needed: `fly deploy` from the project root.

---

## Part 3: Quick checklist

- [ ] Fly CLI installed, `fly auth login` done.
- [ ] Dockerfile and `fly.toml` at project root (and volume if using SQLite).
- [ ] Fly secrets set: `SECRET_KEY`, `ENV=production`, `ALLOWED_ORIGINS`, `GROQ_API_KEY`, `TMDB_API_KEY`, etc.
- [ ] `fly deploy` from project root; backend URL works and `/health` and `/ready` return 200.
- [ ] Repo on GitHub; Vercel project created with root `frontend`.
- [ ] `VITE_API_BASE` set in Vercel to your Fly API URL.
- [ ] Frontend deployed; you can open the app and see recommendations (after login/setup).
- [ ] `ALLOWED_ORIGINS` on Fly set to your Vercel frontend URL.

If something fails, check Fly logs: `fly logs`, and Vercel build logs in the dashboard.
