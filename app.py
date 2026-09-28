from datetime import datetime, timedelta
from functools import wraps
import hashlib
import os
import sqlite3
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

app = Flask(__name__)

# Use a strong secret key for signing session cookies
app.secret_key = os.urandom(24)
DB_PATH = "weight.db"


def get_db():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  conn.execute("PRAGMA foreign_keys = ON;")
  return conn


def login_required(f):

  @wraps(f)
  def decorated_function(*args, **kwargs):
    if "user_id" not in session:
      if request.is_json or request.path.startswith("/api/"):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
      return redirect(url_for("login_page"))
    return f(*args, **kwargs)

  return decorated_function


def hash_pin(pin: str):
  """Generates a salt and PBKDF2 hash for a given 4-digit PIN."""
  salt = os.urandom(16)
  key = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100000)
  return key.hex(), salt.hex()


def verify_pin(pin: str, stored_hash: str, salt_hex: str) -> bool:
  if not stored_hash or not salt_hex:
    return False
  try:
    salt = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, 100000)
    return key.hex() == stored_hash
  except ValueError:
    return False


def init_db_users():
  """Ensures default users exist with valid PBKDF2 hashes."""
  db = get_db()
  # Create users table if it doesn't exist
  db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            pin_hash TEXT,
            salt TEXT,
            start_weight REAL DEFAULT 0,
            target_weight REAL DEFAULT 0,
            target_date TEXT DEFAULT '',
            weekly_rate REAL DEFAULT 0.45,
            display_unit TEXT DEFAULT 'lbs'
        )
    """)

  default_users = ["Sean", "Wife"]
  for name in default_users:
    user = db.execute(
        "SELECT id, pin_hash, salt FROM users WHERE name = ?", (name,)
    ).fetchone()
    if not user:
      pin_hash, salt = hash_pin("1234")
      db.execute(
          "INSERT INTO users (name, pin_hash, salt) VALUES (?, ?, ?)",
          (name, pin_hash, salt),
      )
      print(f"Created profile '{name}' with default PIN 1234")
    elif not user["pin_hash"] or not user["salt"]:
      pin_hash, salt = hash_pin("1234")
      db.execute(
          "UPDATE users SET pin_hash = ?, salt = ? WHERE id = ?",
          (pin_hash, salt, user["id"]),
      )
      print(f"Reset profile '{name}' PIN to 1234")

  db.commit()
  db.close()


@app.route("/login")
def login_page():
  return render_template("login.html")


@app.route("/logout")
def logout():
  session.clear()
  return redirect(url_for("login_page"))


@app.route("/api/users", methods=["GET"])
def get_users_list():
  """Returns public profile list (names and IDs only) for the login picker."""
  db = get_db()
  users = db.execute("SELECT id, name FROM users ORDER BY name ASC").fetchall()
  db.close()
  return jsonify([{"id": u["id"], "name": u["name"]} for u in users])


@app.route("/api/login", methods=["POST"])
def api_login():
  data = request.get_json() or {}
  user_id = data.get("user_id")
  pin = str(data.get("pin", ""))

  if not user_id or not pin:
    return jsonify({"status": "error", "message": "Missing user or PIN"}), 400

  db = get_db()
  user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
  db.close()

  if user and user["pin_hash"] and user["salt"]:
    if verify_pin(pin, user["pin_hash"], user["salt"]):
      session["user_id"] = user["id"]
      session["user_name"] = user["name"]
      return jsonify({"status": "success", "user_name": user["name"]})

  return jsonify({"status": "error", "message": "Invalid PIN"}), 401


@app.route("/")
@login_required
def index():
  return render_template("index.html", user_name=session.get("user_name"))


@app.route("/api/user/profile", methods=["GET", "POST"])
@login_required
def user_profile():
  db = get_db()
  user_id = session["user_id"]

  if request.method == "GET":
    user = db.execute(
        "SELECT name, start_weight, target_weight, target_date, weekly_rate,"
        " display_unit FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    db.close()
    return jsonify(dict(user))

  data = request.get_json() or {}
  try:
    start_w = float(data.get("start_weight", 0.0))
    target_w = float(data.get("target_weight", 0.0))
    weekly_r = float(data.get("weekly_rate", 0.5))
    target_d = data.get("target_date", "")
    unit = data.get("display_unit", "lbs")
    if unit not in ["lbs", "kg"]:
      unit = "lbs"
  except ValueError:
    db.close()
    return jsonify(
        {"status": "error", "message": "Invalid numeric values"}
    ), 400

  db.execute(
      """
        UPDATE users
        SET start_weight = ?, target_weight = ?, target_date = ?, weekly_rate = ?, display_unit = ?
        WHERE id = ?
    """,
      (start_w, target_w, target_d, weekly_r, unit, user_id),
  )
  db.commit()
  db.close()

  return jsonify({"status": "success"})


@app.route("/api/user/change-pin", methods=["POST"])
@login_required
def change_pin():
  data = request.get_json() or {}
  new_pin = str(data.get("pin", "")).strip()

  if not new_pin or len(new_pin) != 4 or not new_pin.isdigit():
    return (
        jsonify({
            "status": "error",
            "message": "PIN must be exactly 4 numeric digits.",
        }),
        400,
    )

  pin_hash, salt = hash_pin(new_pin)
  db = get_db()
  db.execute(
      "UPDATE users SET pin_hash = ?, salt = ? WHERE id = ?",
      (pin_hash, salt, session["user_id"]),
  )
  db.commit()
  db.close()

  return jsonify({"status": "success", "message": "PIN updated successfully!"})


@app.route("/api/weights", methods=["GET", "POST"])
@login_required
def handle_weights():
  db = get_db()
  user_id = session["user_id"]

  if request.method == "GET":
    rows = db.execute(
        "SELECT date, weight, notes FROM weights WHERE user_id = ? ORDER BY"
        " date ASC",
        (user_id,),
    ).fetchall()
    db.close()
    return jsonify([
        {"date": r["date"], "weight": r["weight"], "notes": r["notes"]}
        for r in rows
    ])

  data = request.get_json() or {}
  date_str = data.get("date") or datetime.now().strftime("%Y-%m-%d")
  notes = data.get("notes", "")

  try:
    weight_val = float(data["weight"])
  except (KeyError, ValueError):
    db.close()
    return jsonify(
        {"status": "error", "message": "Valid weight value required"}
    ), 400

  db.execute(
      """
        INSERT INTO weights (user_id, date, weight, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, date) DO UPDATE SET weight=excluded.weight, notes=excluded.notes
    """,
      (user_id, date_str, weight_val, notes),
  )

  db.commit()
  db.close()
  return jsonify({"status": "success"})


@app.route("/api/weights/<date_str>", methods=["DELETE"])
@login_required
def delete_weight(date_str):
  db = get_db()
  db.execute(
      "DELETE FROM weights WHERE user_id = ? AND date = ?",
      (session["user_id"], date_str),
  )
  db.commit()
  db.close()
  return jsonify({"status": "success"})


if __name__ == "__main__":
  init_db_users()
  # Bound to port 5001 to avoid conflicting with existing workshop app on port 5000
  app.run(host="0.0.0.0", port=5001, debug=True)
