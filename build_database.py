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
        url = f"https://github.com/edeo/eda/blob/main/{path}"

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
