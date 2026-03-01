# here are the claude instructions

I have to work through and test everything but here it is to start.

# How to Build a Blog with Datasette, Fly.io, and GitHub Actions

A step-by-step guide for Mac users. By the end, you'll have a blog powered by Datasette where you just write markdown files, push to GitHub, and your site automatically rebuilds and deploys.

## What You're Building

The architecture is simple: markdown files on disk → a Python script builds a SQLite database → Datasette serves it with custom templates → Fly.io hosts it → GitHub Actions automates the whole thing.

---

## Part 1: Build and Deploy the Blog Manually

### Prerequisites

Make sure you have the following installed:

- **Homebrew**: https://brew.sh
- **Python 3.11+**: `brew install python`
- **uv** (recommended) or pip: `brew install uv`
- **Git**: `brew install git`
- **Fly.io CLI**: `brew install flyctl`
- **GitHub CLI**: `brew install gh`

### Step 1: Install Datasette and Plugins

If using uv (recommended):

```bash
uv tool install datasette --with datasette-template-sql --with datasette-publish-fly
```

If using pip:

```bash
pip install datasette datasette-template-sql datasette-publish-fly
```

Verify installation:

```bash
datasette --version
```

You'll also need sqlite-utils and markdown:

```bash
pip install sqlite-utils markdown
```

### Step 2: Create Your Project Structure

```bash
mkdir my-blog
cd my-blog
git init
```

Create the directory structure:

```bash
mkdir -p daily
mkdir -p templates/pages/post
```

Your project will look like this:

```
my-blog/
├── daily/
│   ├── post1.md
│   ├── post2.md
│   └── ...
├── templates/
│   ├── index.html
│   └── pages/
│       ├── home.html
│       └── post/
│           └── {slug}.html
├── build_database.py
└── .gitignore
```

### Step 3: Write Some Blog Posts

Blog posts are markdown files that live in topic folders (like `daily/`). The first line is the title (starting with `#`), and everything after is the body.

Create your first post:

```bash
cat > daily/my-first-post.md << 'EOF'
# My First Blog Post

This is my first post on my new Datasette-powered blog. 
It's built from plain markdown files and served with SQLite.
Pretty neat!
EOF
```

Create a second post:

```bash
cat > daily/hello-world.md << 'EOF'
# Hello World

Welcome to my blog. I built this using Datasette, Fly.io, 
and GitHub Actions. Every time I push a new markdown file, 
the site automatically rebuilds.
EOF
```

You can create as many topic folders as you want (e.g., `daily/`, `tech/`, `travel/`). The folder name becomes the "topic" field in the database.

### Step 4: Create the Build Script

This Python script reads all your markdown files and builds a SQLite database from them.

Create `build_database.py`:

```python
import pathlib
import sqlite_utils
import markdown

root = pathlib.Path(__file__).parent.resolve()

def build_database(root):
    db = sqlite_utils.Database(root / "blog.db")

    table = db.table("posts", pk="path")

    posts = []
    for filepath in root.glob("*/*.md"):
        fp = filepath.open()
        title = fp.readline().lstrip("#").strip()
        body = fp.read().strip()

        path = str(filepath.relative_to(root))
        slug = filepath.stem
        topic = filepath.parent.name
        url = f"https://github.com/YOUR_USERNAME/YOUR_REPO/blob/main/{path}"
        html = markdown.markdown(body)

        posts.append({
            "path": path,
            "slug": slug,
            "topic": topic,
            "title": title,
            "url": url,
            "body": body,
            "html": html,
        })

    if posts:
        table.insert_all(posts, replace=True)

    print(f"Built blog.db with {len(posts)} posts")

if __name__ == "__main__":
    build_database(root)
```

**Important:** Replace `YOUR_USERNAME/YOUR_REPO` with your actual GitHub username and repo name.

Build the database:

```bash
python build_database.py
```

You should see: `Built blog.db with 2 posts`

### Step 5: Create the Templates

You need three template files.

**templates/index.html** — Redirects `/` to your blog homepage:

```html
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0;url=/home">
</head>
<body>
  <a href="/home">Redirecting to blog...</a>
</body>
</html>
```

**templates/pages/home.html** — Your blog homepage:

```html
{% extends "base.html" %}

{% block content %}
<div style="max-width: 700px; margin: 2em auto; padding: 0 1em;">

  <h1>My Blog</h1>
  <p style="color: #666;">{{ sql("SELECT COUNT(*) FROM posts", database="blog")[0][0] }} posts so far.</p>

  <hr>

  {% for post in sql("SELECT title, slug, topic, html FROM posts ORDER BY rowid DESC LIMIT 5", database="blog") %}
  <article style="margin-bottom: 3em;">

    <h2><a href="/post/{{ post.slug }}" style="text-decoration: none;">{{ post.title }}</a></h2>
    <p style="color: #666; font-size: 0.9em;">Topic: <strong>{{ post.topic }}</strong></p>

    <div class="blog-content">
      {{ post.html | safe }}
    </div>

    <p><a href="/post/{{ post.slug }}">&rarr; Read more</a></p>
    <hr>

  </article>
  {% endfor %}

  <h2>All Posts by Topic</h2>
  {% for topic in sql("SELECT DISTINCT topic FROM posts ORDER BY topic", database="blog") %}
    <h3>{{ topic[0] }}</h3>
    <ul>
      {% for link in sql("SELECT title, slug FROM posts WHERE topic = ?", [topic[0]], database="blog") %}
      <li><a href="/post/{{ link.slug }}">{{ link.title }}</a></li>
      {% endfor %}
    </ul>
  {% endfor %}

</div>
{% endblock %}
```

**templates/pages/post/{slug}.html** — Individual post pages:

```html
{% extends "base.html" %}

{% block content %}
<div style="max-width: 700px; margin: 2em auto; padding: 0 1em;">

  {% for post in sql("SELECT title, topic, html FROM posts WHERE slug = ?", [slug], database="blog") %}
    <h1>{{ post.title }}</h1>
    <p style="color: #666; font-size: 0.9em;">Topic: <strong>{{ post.topic }}</strong></p>
    <div class="blog-content">
      {{ post.html | safe }}
    </div>
  {% endfor %}

  <p><a href="/home">&larr; Back to all posts</a></p>

</div>
{% endblock %}
```

### Step 6: Test Locally

```bash
datasette serve blog.db --template-dir templates/
```

Visit http://localhost:8001/ — it should redirect to `/home` and show your blog.

Click on a post title to see the individual post page. Use Ctrl+C to stop the server when you're done.

### Step 7: Deploy to Fly.io

First, log in to Fly.io (create an account at https://fly.io if you don't have one):

```bash
fly auth login
```

Create your app:

```bash
fly apps create your-app-name
```

Deploy:

```bash
datasette publish fly blog.db \
  --app your-app-name \
  --template-dir templates/ \
  --install datasette-template-sql
```

Your blog is now live at `https://your-app-name.fly.dev/`

### Step 8: Create .gitignore

```bash
cat > .gitignore << 'EOF'
blog.db
__pycache__/
*.pyc
.DS_Store
EOF
```

---

## Part 2: Automate with GitHub Actions

Now we'll set it up so that every time you push a new markdown file to GitHub, the blog automatically rebuilds and deploys.

### Step 1: Create a GitHub Repository

Go to https://github.com/new and create a new repo, or use the CLI:

```bash
gh repo create your-repo-name --public --source=. --remote=origin
```

### Step 2: Get Your Fly.io API Token

```bash
fly tokens create deploy --app your-app-name
```

Copy the token that's printed.

### Step 3: Add the Token as a GitHub Secret

Go to your repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**

- Name: `FLY_API_TOKEN`
- Value: paste the token from the previous step

### Step 4: Create the GitHub Actions Workflow

```bash
mkdir -p .github/workflows
```

Create `.github/workflows/deploy.yml`:

```yaml
name: Build and Deploy Blog

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install sqlite-utils markdown datasette datasette-template-sql datasette-publish-fly

      - name: Build database
        run: python build_database.py

      - name: Install flyctl
        uses: superfly/flyctl-actions/setup-flyctl@master

      - name: Deploy to Fly.io
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
        run: |
          datasette publish fly blog.db \
            --app your-app-name \
            --template-dir templates/ \
            --install datasette-template-sql
```

**Important:** Replace `your-app-name` with your actual Fly.io app name.

### Step 5: Push Everything

If you haven't already authenticated git with the right permissions for pushing workflow files:

```bash
gh auth login
```

Select **GitHub.com** and **HTTPS** when prompted.

Then push:

```bash
git add .
git commit -m "Initial blog setup with GitHub Actions"
git push -u origin main
```

### Step 6: Watch It Deploy

Go to `https://github.com/YOUR_USERNAME/YOUR_REPO/actions` to watch the workflow run. It should take 2-3 minutes.

---

## Daily Workflow

From now on, publishing a new blog post is this simple:

```bash
# Write a new post
cat > daily/my-new-post.md << 'EOF'
# My New Post Title

Write your content here in markdown.
EOF

# Push it
git add daily/my-new-post.md
git commit -m "New post: My New Post Title"
git push
```

GitHub Actions will automatically rebuild the database and deploy to Fly.io. Your new post will be live in about 2-3 minutes.

---

## Troubleshooting

**"sql is undefined" error**: Make sure you've installed the `datasette-template-sql` plugin. This provides the `sql()` function used in templates.

**Templates not loading**: Make sure you're passing `--template-dir templates/` when running Datasette.

**Homepage shows default Datasette view instead of your blog**: The `templates/index.html` redirect only works as a template override (not in `pages/`). Make sure `templates/index.html` exists at the top level and `templates/pages/home.html` has your blog content.

**Port already in use**: Kill the existing process with `lsof -ti :8001 | xargs kill` or use a different port with `--port 8002`.

**GitHub Actions can't push workflow files**: Run `gh auth login` and re-authenticate with HTTPS to get the right permissions.

**Fly.io "app not found"**: You need to create the app first with `fly apps create your-app-name` before deploying.

**Deploy fails with "No such command 'fly'"**: Make sure `datasette-publish-fly` is in your pip install list and that the workflow includes the "Install flyctl" step.
