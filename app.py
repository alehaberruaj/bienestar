from flask import Flask, request, jsonify, render_template
import sqlite3
from datetime import date, timedelta
import os

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), "calories.db")

DAILY_GOAL = 2000


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                calories INTEGER NOT NULL,
                entry_date TEXT NOT NULL DEFAULT (date('now'))
            )
        """)


@app.route("/")
def index():
    return render_template("index.html", daily_goal=DAILY_GOAL)


@app.route("/api/entries", methods=["GET"])
def get_entries():
    entry_date = request.args.get("date", str(date.today()))
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, name, calories, entry_date FROM entries WHERE entry_date = ? ORDER BY id",
            (entry_date,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/entries", methods=["POST"])
def add_entry():
    data = request.get_json(force=True)
    name = str(data.get("name", "")).strip()
    calories = data.get("calories")
    entry_date = data.get("date", str(date.today()))

    if not name:
        return jsonify({"error": "name required"}), 400
    try:
        calories = int(calories)
        if calories <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "calories must be a positive integer"}), 400

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO entries (name, calories, entry_date) VALUES (?, ?, ?)",
            (name, calories, entry_date),
        )
        new_id = cur.lastrowid
    return jsonify({"id": new_id, "name": name, "calories": calories, "entry_date": entry_date}), 201


@app.route("/api/entries/<int:entry_id>", methods=["DELETE"])
def delete_entry(entry_id):
    with get_db() as conn:
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    return jsonify({"deleted": entry_id})


@app.route("/api/summary", methods=["GET"])
def get_summary():
    days = int(request.args.get("days", 7))
    today = date.today()
    result = []
    with get_db() as conn:
        for i in range(days - 1, -1, -1):
            d = str(today - timedelta(days=i))
            row = conn.execute(
                "SELECT COALESCE(SUM(calories), 0) as total FROM entries WHERE entry_date = ?",
                (d,),
            ).fetchone()
            result.append({"date": d, "total": row["total"]})
    return jsonify({"goal": DAILY_GOAL, "days": result})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
