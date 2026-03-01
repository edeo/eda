# Step-by-Step: Build a Blog with Datasette

---

## Step 1 — Create the repo and folder structure

```bash
mkdir my-til
cd my-til
git init
```

Create the directories you'll need:

```bash
mkdir templates
mkdir .github
mkdir .github/workflows
mkdir python   # your first topic folder — name it whatever you want
```

---

## Step 2 — Set up your Python environment with uv

If you don't have uv yet:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # Mac/Linux
# or: pip install uv
```

Then initialize the project and add your dependencies:

```bash
uv init
uv add datasette sqlite-utils httpx datasette-template-sql datasette-render-markdown
```

This creates a `pyproject.toml` (your dependency list) and a `uv.lock` (exact pinned versions for reproducibility). You don't need a separate `requirements.txt`.

To activate the virtual environment uv creates:
```bash
source .venv/bin/activate       # Windows: .venv\Scripts\activate
```

---

## Step 3 — Write your first post

Create a markdown file inside a topic folder. The folder name = the topic. The first line = the title (no frontmatter needed).

**`python/first-post.md`**:
```markdown
# My first post

Something I want to share today...
```

---

## Step 4 — Create `build_database.py`

This script reads all your markdown files and loads them into a SQLite database.

```python
import pathlib
import sqlite_utils
import httpx
import os

root = pathlib.Path(__file__).parent.resolve()

def build_database(root):
    db = sqlite_utils.Database(root / "blog.db")
    table = db.table("posts", pk="path")

    for filepath in root.glob("*/*.md"):
        fp = filepath.open()
        title = fp.readline().lstrip("#").strip()
        body = fp.read().strip()

        path = str(filepath.relative_to(root))
        path_slug = path.replace("/", "_")
        slug = filepath.stem
        topic = path.split("/")[0]
        url = f"https://github.com/YOUR_USERNAME/YOUR_REPO/blob/main/{path}"

        # Only re-render HTML if the body changed
        try:
            row = table.get(path_slug)
            previous_body = row["body"]
            previous_html = row["html"]
        except (sqlite_utils.db.NotFoundError, KeyError):
            previous_body = None
            previous_html = None

        record = {
            "path": path_slug,
            "slug": slug,
            "topic": topic,
            "title": title,
            "url": url,
            "body": body,
        }

        if body != previous_body or not previous_html:
            headers = {}
            if os.environ.get("GITHUB_TOKEN"):
                headers = {"authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
            response = httpx.post(
                "https://api.github.com/markdown",
                json={"mode": "markdown", "text": body},
                headers=headers,
            )
            record["html"] = response.text
        else:
            record["html"] = previous_html

        table.upsert(record)

    if "posts_fts" not in db.table_names():
        table.enable_fts(["title", "body"])

if __name__ == "__main__":
    build_database(root)
```

> ⚠️ Replace `YOUR_USERNAME/YOUR_REPO` with your actual GitHub repo path.

---

## Step 5 — Run the build script and test it locally

```bash
uv run python build_database.py
```

You should now have a `blog.db` file. Start Datasette to see it:

```bash
uv run datasette blog.db
```

Visit `http://localhost:8001` — you'll see the raw Datasette UI with your data. It works, but the homepage isn't customized yet. Do that in the next steps.

---

## Step 6 — Create `metadata.yml`

This configures Datasette's title, plugins, and table display settings.

```yaml
title: "My Blog"
description: "Tutorials and posts"
plugins:
  datasette-template-sql: {}
  datasette-render-markdown:
    columns:
      - body
databases:
  blog:
    tables:
      posts:
        sort_desc: title
        facets:
          - topic
```

---

## Step 7 — Create a custom homepage template

This overrides the default Datasette index page.

**`templates/index.html`**:
```html
{% extends "base.html" %}

{% block content %}
<h1>My Blog</h1>
<p>{{ databases["blog"].execute("SELECT COUNT(*) FROM posts").fetchone()[0] }} posts so far.</p>

{% set topics = databases["blog"].execute("SELECT DISTINCT topic FROM posts ORDER BY topic").fetchall() %}
{% for topic_row in topics %}
  <h2>{{ topic_row[0] }}</h2>
  <ul>
    {% for row in databases["blog"].execute("SELECT title, path FROM posts WHERE topic = ? ORDER BY title", [topic_row[0]]).fetchall() %}
    <li><a href="/blog/posts/{{ row[1] }}">{{ row[0] }}</a></li>
    {% endfor %}
  </ul>
{% endfor %}
{% endblock %}
```

Now test with your metadata and templates:

```bash
uv run datasette blog.db --metadata metadata.yml --template-dir templates/
```

Visit `http://localhost:8001` — you should now see your custom homepage with posts listed by topic.

---

## Step 8 — Create a `.gitignore`

```
.venv/
__pycache__/
*.pyc
blog.db         # the DB is built by CI, not committed to git
```

Do commit `pyproject.toml` and `uv.lock` — both should be in version control.

---

## Step 9 — Push to GitHub

Create a new repo on GitHub (name it `my-til` or whatever you like), then:

```bash
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

---

## Step 10 — Choose a deployment target and get credentials

Pick one:

### Option A: Fly.io (recommended — cheap always-on hosting)
1. Sign up at [fly.io](https://fly.io)
2. Install the CLI: `brew install flyctl` (or see fly.io docs)
3. Run `flyctl auth login`
4. Get a deploy token: `flyctl tokens create deploy`
5. Add it to GitHub: repo → Settings → Secrets and variables → Actions → New secret → name it `FLY_API_TOKEN`

### Option B: Vercel (free tier, serverless)
1. Sign up at [vercel.com](https://vercel.com)
2. Create a token: Account Settings → Tokens
3. Add it to GitHub as `VERCEL_TOKEN`

---

## Step 11 — Create the GitHub Actions workflow

**`.github/workflows/build.yml`**:

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:       # allows manual trigger from GitHub UI

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: uv sync

      - name: Download previous blog.db
        run: curl --fail -o blog.db https://YOUR_DEPLOYED_URL/blog.db
        continue-on-error: true   # OK to fail on first deploy

      - name: Build database
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: uv run python build_database.py

      - name: Soundness check
        run: uv run datasette blog.db --get / | grep "My Blog"

      # --- Choose ONE of the deploy steps below ---

      # Option A: Fly.io
      - name: Deploy to Fly.io
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          uv pip install datasette-publish-fly
          uv run datasette publish fly blog.db \
            --app my-blog \
            --metadata metadata.yml \
            --template-dir templates/ \
            --install datasette-template-sql \
            --install datasette-render-markdown

      # Option B: Vercel (comment out A and uncomment this)
      # - name: Deploy to Vercel
      #   env:
      #     VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
      #   run: |
      #     uv pip install datasette-publish-vercel
      #     uv run datasette publish vercel blog.db \
      #       --project my-blog \
      #       --token $VERCEL_TOKEN \
      #       --metadata metadata.yml \
      #       --template-dir templates/ \
      #       --install datasette-template-sql \
      #       --install datasette-render-markdown
```

> ⚠️ Replace `YOUR_DEPLOYED_URL` with the URL of your live site after the first deploy (e.g. `https://my-til.fly.dev`). On the very first deploy, leave it as a placeholder — the `continue-on-error: true` handles it.

---

## Step 12 — Trigger the first deploy

```bash
git add .
git commit -m "Add GitHub Actions workflow"
git push
```

Go to your repo on GitHub → **Actions** tab → watch the workflow run. The first run will skip the DB download (no live site yet) and do a fresh build and deploy.

Once it succeeds, you'll get a live URL. Copy that URL and update the `curl` line in `build.yml` with it, then push again.

---

## Step 13 — Write new posts

From here on, the workflow is simple:

```bash
# Add a new topic folder and post
mkdir git
echo "# How to undo the last commit\n\nUse git reset HEAD~1 --soft to undo without losing changes." > git/undo-last-commit.md

git add .
git commit -m "Add post: how to undo the last commit"
git push
```

GitHub Actions automatically rebuilds the database and redeploys. Your post is live in ~2 minutes.

---

## Final File Structure

```
my-til/
├── .github/
│   └── workflows/
│       └── build.yml
├── python/
│   └── first-post.md
├── git/
│   └── undo-last-commit.md
├── templates/
│   └── index.html
├── build_database.py
├── metadata.yml
├── pyproject.toml
├── uv.lock
└── .gitignore
```

---

## Optional Extras

**Add an Atom/RSS feed** — install `datasette-atom` and add to metadata.yml:
```yaml
plugins:
  datasette-atom:
    sql: "SELECT path as id, title, html as content_html FROM posts ORDER BY rowid DESC LIMIT 20"
```

**Add full-text search UI** — install `datasette-search-all` and it appears automatically.

**Add created/updated timestamps** — use the GitHub API in `build_database.py` to fetch commit timestamps for each file and store them in the DB.