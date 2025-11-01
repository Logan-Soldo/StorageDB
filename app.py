import sqlite3
import qrcode
import os
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DB = "storage.db"
QR_DIR = "static/qr"
os.makedirs(QR_DIR, exist_ok=True)

# --- Database setup ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS boxes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_name TEXT NOT NULL,
            description TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            box_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            notes TEXT,
            FOREIGN KEY (box_id) REFERENCES boxes(id)
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect(DB)

# --- Helper: Generate QR ---
def generate_qr(box_id, ip_address="localhost"):
    url = f"http://{ip_address}:5000/box/{box_id}"
    qr_path = os.path.join(QR_DIR, f"box_{box_id}.png")
    if not os.path.exists(qr_path):
        qrcode.make(url).save(qr_path)
    return qr_path

# --- Routes ---

@app.route("/")
def list_boxes():
    conn = get_db()
    boxes = conn.execute("SELECT id, box_name, description FROM boxes").fetchall()
    conn.close()
    return render_template("boxes.html", boxes=boxes)

@app.route("/add_box", methods=["POST"])
def add_box():
    box_name = request.form["box_name"]
    desc = request.form.get("description", "")
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO boxes (box_name, description) VALUES (?, ?)", (box_name, desc))
    box_id = c.lastrowid
    conn.commit()
    conn.close()
    # Generate QR using local IP
    generate_qr(box_id, request.host.split(":")[0])
    return redirect(url_for("list_boxes"))

@app.route("/box/<int:box_id>")
def view_box(box_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT box_name, description FROM boxes WHERE id=?", (box_id,))
    box = c.fetchone()
    c.execute("SELECT * FROM items WHERE box_id=?", (box_id,))
    items = c.fetchall()
    conn.close()
    return render_template("box.html", box_id=box_id, box=box, items=items)

@app.route("/box/<int:box_id>/add_item", methods=["POST"])
def add_item(box_id):
    name = request.form["item_name"]
    qty = int(request.form["quantity"])
    notes = request.form.get("notes", "")
    conn = get_db()
    conn.execute("INSERT INTO items (box_id, item_name, quantity, notes) VALUES (?, ?, ?, ?)",
                 (box_id, name, qty, notes))
    conn.commit()
    conn.close()
    return redirect(url_for("view_box", box_id=box_id))

@app.route("/edit_item/<int:item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    conn = get_db()
    c = conn.cursor()
    if request.method == "POST":
        name = request.form["item_name"]
        qty = int(request.form["quantity"])
        notes = request.form.get("notes", "")
        c.execute("UPDATE items SET item_name=?, quantity=?, notes=? WHERE id=?",
                  (name, qty, notes, item_id))
        conn.commit()
        conn.close()
        box_id = request.form["box_id"]
        return redirect(url_for("view_box", box_id=box_id))
    else:
        c.execute("SELECT id, box_id, item_name, quantity, notes FROM items WHERE id=?", (item_id,))
        item = c.fetchone()
        conn.close()
        return render_template("edit_item.html", item=item)

@app.route("/delete_item/<int:item_id>/<int:box_id>")
def delete_item(item_id, box_id):
    conn = get_db()
    conn.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_box", box_id=box_id))

# --- Run ---
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
