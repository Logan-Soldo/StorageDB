"""
Written by Logan Soldo

Storage Box Management Web App with QR Code Integration

Features:
- Manage boxes and their items
- Assign duration (long-term / short-term / seasonal) to boxes
- Add multiple tags (like kitchen, tools, winter gear)
- Generate QR codes for boxes
- Edit boxes and items
"""

import os
import sqlite3
import qrcode
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv

# --- Flask setup ---
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "unsafe_dev_key")

DB = "storage.db"
QR_DIR = "static/qr"
os.makedirs(QR_DIR, exist_ok=True)

# --- Database setup ---
def init_db():
    """Create the database schema"""
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # Drop old tables if you want a clean rebuild
    c.execute("DROP TABLE IF EXISTS items;")
    c.execute("DROP TABLE IF EXISTS boxes;")

    # New schema
    c.execute("""
        CREATE TABLE boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_name TEXT NOT NULL,
            description TEXT,
            duration TEXT CHECK(duration IN ('long-term', 'short-term', 'seasonal')),
            tags TEXT
        )
    """)

    c.execute("""
        CREATE TABLE items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            notes TEXT,
            FOREIGN KEY (box_id) REFERENCES boxes(id)
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database initialized with new schema.")

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row  # <-- enables dict-like access
    return conn


# --- QR code generator ---
def generate_qr(box_id, ip_address="localhost"):
    """Generate QR code for a specific box"""
    url = f"http://{ip_address}:5000/box/{box_id}"
    qr_path = os.path.join(QR_DIR, f"box_{box_id}.png")
    qrcode.make(url).save(qr_path)
    return qr_path

# --- Routes ---

@app.route("/")
def list_boxes():
    """List all boxes"""
    conn = get_db()
    boxes = conn.execute("SELECT id, box_name, description, duration, tags FROM boxes").fetchall()
    conn.close()
    return render_template("boxes.html", boxes=boxes)

@app.route("/add_box", methods=["POST"])
def add_box():
    """Add a new box"""
    box_name = request.form["box_name"]
    desc = request.form.get("description", "")
    duration = request.form.get("duration", "long-term")
    tags = request.form.getlist("tags")  # Multiple select tags
    tags_str = ", ".join(tags)

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO boxes (box_name, description, duration, tags) VALUES (?, ?, ?, ?)",
        (box_name, desc, duration, tags_str),
    )
    box_id = c.lastrowid
    conn.commit()
    conn.close()

    generate_qr(box_id, request.host.split(":")[0])
    flash("Box added successfully!", "success")
    return redirect(url_for("list_boxes"))

@app.route("/box/<int:box_id>")
def view_box(box_id):
    """View a single box and its items"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM boxes WHERE id=?", (box_id,))
    box = c.fetchone()
    c.execute("SELECT * FROM items WHERE box_id=?", (box_id,))
    items = c.fetchall()
    conn.close()
    return render_template("box.html", box_id=box_id, box=box, items=items)

@app.route("/box/<int:box_id>/add_item", methods=["POST"])
def add_item(box_id):
    """Add an item to a box"""
    name = request.form["item_name"]
    qty = int(request.form["quantity"])
    notes = request.form.get("notes", "")
    conn = get_db()
    conn.execute(
        "INSERT INTO items (box_id, item_name, quantity, notes) VALUES (?, ?, ?, ?)",
        (box_id, name, qty, notes),
    )
    conn.commit()
    conn.close()
    flash("Item added!", "success")
    return redirect(url_for("view_box", box_id=box_id))

@app.route("/edit_item/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    """Edit an existing item"""
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["item_name"]
        qty = int(request.form["quantity"])
        notes = request.form.get("notes", "")
        c.execute(
            "UPDATE items SET item_name=?, quantity=?, notes=? WHERE id=?",
            (name, qty, notes, item_id),
        )
        conn.commit()
        conn.close()
        box_id = request.form["box_id"]
        flash("Item updated successfully!", "success")
        return redirect(url_for("view_box", box_id=box_id))
    else:
        c.execute("SELECT id, box_id, item_name, quantity, notes FROM items WHERE id=?", (item_id,))
        item = c.fetchone()
        conn.close()
        return render_template("edit_item.html", item=item)

@app.route("/delete_item/<int:item_id>/<int:box_id>")
def delete_item(item_id, box_id):
    """Delete an item"""
    conn = get_db()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    flash("Item deleted.", "success")
    return redirect(url_for("view_box", box_id=box_id))

@app.route('/box/<int:box_id>/delete', methods=['POST'])
def delete_box(box_id):
    conn = get_db()
    conn.execute('DELETE FROM boxes WHERE id = ?', (box_id,))
    conn.execute('DELETE FROM items WHERE box_id = ?', (box_id,))
    conn.commit()
    conn.close()
    flash("Box deleted successfully!", "info")
    return redirect(url_for('list_boxes'))

@app.route("/box/<int:box_id>/edit", methods=["GET", "POST"])
def edit_box(box_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["box_name"]
        desc = request.form.get("description", "")
        duration = request.form.get("duration", "")
        tags = request.form.getlist("tags")  # multiple checkboxes → list
        tags_str = ",".join(tags)

        c.execute(
            "UPDATE boxes SET box_name=?, description=?, duration=?, tags=? WHERE id=?",
            (name, desc, duration, tags_str, box_id),
        )
        conn.commit()
        conn.close()
        flash("Box updated successfully!", "success")
        return redirect(url_for("view_box", box_id=box_id))
    else:
        c.execute("SELECT * FROM boxes WHERE id=?", (box_id,))
        box = c.fetchone()
        conn.close()
        return render_template("edit_box.html", box=box)

# --- Run ---
if __name__ == "__main__":
    if not os.path.exists(DB):
        init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
