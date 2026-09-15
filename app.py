import os
import sqlite3
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent

# DATABASE_URL이 설정되어 있으면 Supabase(Postgres)를 쓰고, 없으면 로컬 SQLite로 동작한다.
DATABASE_URL = os.environ.get("DATABASE_URL")
PLACEHOLDER = "%s" if DATABASE_URL else "?"

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras
else:
    # Vercel의 서버리스 함수는 코드 디렉터리가 읽기 전용이고 /tmp만 쓰기 가능하다.
    DB_PATH = Path("/tmp/todo.db") if os.environ.get("VERCEL") else BASE_DIR / "todo.db"

app = Flask(__name__)


def get_db():
    if "db" not in g:
        if DATABASE_URL:
            g.db = psycopg2.connect(
                DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor
            )
        else:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor().execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()
    else:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    done INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()


@app.route("/")
def index():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM todos ORDER BY done ASC, id DESC")
    todos = cur.fetchall()
    remaining = sum(1 for t in todos if not t["done"])
    return render_template("index.html", todos=todos, remaining=remaining)


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    if title:
        db = get_db()
        db.cursor().execute(
            f"INSERT INTO todos (title) VALUES ({PLACEHOLDER})", (title,)
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    db = get_db()
    db.cursor().execute(
        f"UPDATE todos SET done = 1 - done WHERE id = {PLACEHOLDER}", (todo_id,)
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    db = get_db()
    db.cursor().execute(
        f"DELETE FROM todos WHERE id = {PLACEHOLDER}", (todo_id,)
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/edit/<int:todo_id>", methods=["POST"])
def edit(todo_id):
    title = request.form.get("title", "").strip()
    if title:
        db = get_db()
        db.cursor().execute(
            f"UPDATE todos SET title = {PLACEHOLDER} WHERE id = {PLACEHOLDER}",
            (title, todo_id),
        )
        db.commit()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
