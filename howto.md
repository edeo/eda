# Building a TIL Blog with Datasette

Based on the pattern used by [simonw/til](https://github.com/simonw/til).

---

## The Overall Architecture

```
your-repo/
├── topic-one/
│   ├── first-post.md
│   └── second-post.md
├── topic-two/
│   └── some-post.md
├── templates/
│   └── index.html
├── build_database.py
├── metadata.yml
├── requirements.txt
└── .github/workflows/build.yml
```

Markdown files on disk → Python script builds a SQLite DB → Datasette serves it with custom templates → GitHub Actions rebuilds and redeploys on every push.

---

## 1. The Markdown Files

Simon uses a simple convention: no YAML frontmatter. The first line is the `# Title`, everything else is the body.

```markdown
# How I learned to stop worrying and love SQLite

Some content here...
```

Files live in topic subdirectories like `python/decorators.md`, `git/rebase-tricks.md`, etc. The directory name becomes the "topic" field in the DB.

---

## 2. `build_database.py`

This is the core script. It walks the filesystem and loads everything into SQLite using `sqlite-utils`:

```python
import pathlib
import sqlite_utils
import httpx
import os

root = pathlib.Path(__file__).parent.resolve()

def build_database(root):
    db = sqlite_utils.Database(root / "posts.db")
    table = db.table("til", pk="path")

    for filepath in root.glob("*/*.md"):
        fp = filepath.open()
        title = fp.readline().lstrip("#").strip()
        body = fp.read().strip()

        path = str(filepath.relative_to(root))
        path_slug = path.replace("/", "_")   # e.g. "python_decorators"
        slug = filepath.stem                  # e.g. "decorators"
        topic = path.split("/")[0]            # e.g. "python"
        url = f"https://github.com/YOU/REPO/blob/main/{path}"

        # Only re-render HTML if body changed (saves GitHub API calls)
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
            # Use GitHub's markdown API to render (handles code highlighting etc.)
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

    # Full-text search across title and body
    if "til_fts" not in db.table_names():
        table.enable_fts(["title", "body"])

if __name__ == "__main__":
    build_database(root)
```

Key things happening here:

- `sqlite-utils` creates the table automatically from the dict structure on first run
- `upsert` (not `insert`) means re-running is idempotent
- It only re-calls the GitHub markdown API if the body changed, so you don't burn your rate limit
- `enable_fts` gives you full-text search for free in Datasette

---

## 3. Custom Templates

Datasette uses Jinja2 templates. Create a `templates/` directory. The most important one is `index.html`, which overrides the default Datasette homepage.

**`templates/index.html`**:
```html
{% extends "base.html" %}

{% block content %}
<h1>My TILs</h1>

{% for row in sql("SELECT topic, title, path FROM til ORDER BY topic, title") %}
  <h2>{{ row.topic }}</h2>
  <a href="/tils/til/{{ row.path }}">{{ row.title }}</a>
{% endfor %}
{% endblock %}
```

The `sql()` function comes from `datasette-template-sql` — it lets you run SQL queries directly in Jinja2 templates. This is how Simon feeds data to the index page without needing a custom plugin.

---

## 4. `metadata.yml`

This controls Datasette's configuration, plugins, and page metadata:

```yaml
title: "My TIL"
description: "Things I've learned"
plugins:
  datasette-template-sql: {}
  datasette-render-markdown:
    columns:
      - body
databases:
  tils:
    tables:
      til:
        sort_desc: created
        facets:
          - topic
```

`datasette-render-markdown` renders the `body` column as HTML in the table view. Since you're already storing pre-rendered HTML in the `html` column, you can also use that directly in your custom templates.

---

## 5. `requirements.txt`

```
datasette
sqlite-utils
httpx
datasette-template-sql
datasette-render-markdown
```

---

## 6. GitHub Actions: `.github/workflows/build.yml`

```yaml
name: Build and Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      # Download the previously-built DB so upsert only processes changes
      - name: Download previous tils.db
        run: curl --fail -o tils.db https://YOUR_DEPLOYED_URL/tils.db
        continue-on-error: true  # First deploy won't have one yet

      - name: Build database
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python build_database.py

      # Sanity check — make sure the site actually renders
      - name: Soundness check
        run: datasette . --get / | grep "My TIL"

      - name: Deploy to Fly.io
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          pip install datasette-publish-fly
          datasette publish fly tils.db \
            --app my-til \
            --metadata metadata.yml \
            --template-dir templates/ \
            --install datasette-template-sql \
            --install datasette-render-markdown
```

The `continue-on-error: true` on the download step is important — on your first deploy there's no existing DB to download. After that, downloading the previous DB means your incremental upserts are fast and you don't re-render all markdown from scratch.

---

## 7. Deployment Options

**Fly.io** (what Simon uses now — cheapest for always-on):
```bash
pip install datasette-publish-fly
datasette publish fly tils.db --app my-til
```

**Vercel** (free tier, serverless):
```bash
pip install datasette-publish-vercel
datasette publish vercel tils.db --project my-til --token $VERCEL_TOKEN
```

**Cloud Run** (Google — scales to zero):
```bash
datasette publish cloudrun tils.db --service my-til
```

All three have corresponding `datasette-publish-*` packages that handle containerization and deployment for you.

---

## 8. Key Plugins

| Plugin | What it does |
|---|---|
| `datasette-template-sql` | Run SQL queries inside Jinja2 templates |
| `datasette-render-markdown` | Render markdown columns in table view |
| `datasette-publish-fly` / `-vercel` / `-cloudrun` | One-command deploy |
| `datasette-sitemap` | Auto-generate sitemap.xml |
| `datasette-atom` | Auto-generate Atom feed from any query |

The Atom feed plugin is particularly nice — point it at `SELECT * FROM til ORDER BY created DESC LIMIT 20` and you get an RSS feed with zero custom code.

---

## Getting Started Fast

```bash
# Set up the project
mkdir my-til && cd my-til
python -m venv .venv && source .venv/bin/activate
pip install datasette sqlite-utils httpx datasette-template-sql

# Create a test post
mkdir python
echo "# Walrus operator is actually useful\n\nFound a real use case today..." > python/walrus-operator.md

# Build the DB
python build_database.py

# Run locally
datasette . --metadata metadata.yml --template-dir templates/
```

Then visit `localhost:8001` and you'll see Datasette serving your markdown as a browsable, searchable database.