"""StayGenius AI - Flask API.  Run:  python app.py   ->  http://localhost:5000  (Swagger: /apidocs)"""
import os, re, json, time, datetime as dt, decimal
from functools import wraps
from flask import Flask, request, jsonify, g, send_from_directory
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
import db, ai

FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ROLES = ("guest", "staff", "manager", "admin")
STAFF = ("staff", "manager", "admin")
ROOM_STATUS = ("vacant", "occupied", "cleaning", "maintenance")
CATS = ("housekeeping", "food", "maintenance")


class Provider(DefaultJSONProvider):
    @staticmethod
    def default(o):
        if isinstance(o, (dt.date, dt.datetime)):
            return o.isoformat()
        if isinstance(o, decimal.Decimal):
            return float(o)
        return DefaultJSONProvider.default(o)


app = Flask(__name__, static_folder=None)
app.json = Provider(app)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 256
CORS(app)
ser = URLSafeTimedSerializer(os.getenv("SECRET_KEY", "dev-secret-change-me"))
FAILS = {}  # email -> [timestamps] (simple login throttle)


# ------------------------------ helpers ------------------------------
def err(msg, code=400):
    return jsonify({"error": msg}), code


def body():
    return request.get_json(silent=True) or {}


def parse_date(s):
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        raise ValueError("Dates must look like 2026-12-31.")


def auth(*roles):
    def deco(f):
        @wraps(f)
        def w(*a, **k):
            h = request.headers.get("Authorization", "")
            try:
                uid = ser.loads(h[7:] if h.startswith("Bearer ") else "", max_age=60 * 60 * 12)["uid"]
            except Exception:
                return err("Please sign in again.", 401)
            u = db.query("SELECT id,name,email,role,language FROM users WHERE id=%s AND active=1", (uid,), one=True)
            if not u:
                return err("Account not found or disabled.", 401)
            if roles and u["role"] not in roles:
                return err("Your role cannot do this.", 403)
            g.user = u
            return f(*a, **k)
        return w
    return deco


def token_response(uid, code=200):
    u = db.query("SELECT id,name,email,role,language FROM users WHERE id=%s", (uid,), one=True)
    return jsonify({"token": ser.dumps({"uid": uid}), "user": u}), code


BOOKING_SQL = """SELECT b.*, u.name guest_name, r.number room_number, rt.name room_type FROM bookings b
  JOIN users u ON u.id=b.guest_id JOIN rooms r ON r.id=b.room_id JOIN room_types rt ON rt.id=r.room_type_id"""


def get_booking(bid):
    b = db.query(BOOKING_SQL + " WHERE b.id=%s", (bid,), one=True)
    if b and g.user["role"] == "guest" and b["guest_id"] != g.user["id"]:
        return None
    return b


def nightly_prices(type_id, base, ci, co):
    ov = {r["stay_date"]: float(r["price"]) for r in db.query(
        "SELECT stay_date, price FROM price_overrides WHERE room_type_id=%s AND stay_date>=%s AND stay_date<%s", (type_id, ci, co))}
    out, d = [], ci
    while d < co:
        out.append(ov.get(d, float(base)))
        d += dt.timedelta(days=1)
    return out


FREE_ROOMS = """SELECT r.id FROM rooms r WHERE r.room_type_id=%s AND r.status<>'maintenance' AND r.id NOT IN
  (SELECT room_id FROM bookings WHERE status IN ('confirmed','checked_in') AND check_in<%s AND check_out>%s) ORDER BY r.number"""


def build_invoice(b):
    nights = (b["check_out"] - b["check_in"]).days
    svc = db.query("SELECT category, description, price FROM service_requests WHERE booking_id=%s AND price>0", (b["id"],))
    svc_total = sum(float(s["price"]) for s in svc)
    room = float(b["total"])
    tax = round(room * 0.12 + svc_total * 0.05, 2)  # GST: 12% rooms, 5% food & services
    return {"booking_id": b["id"], "guest_name": b["guest_name"], "room_number": b["room_number"], "room_type": b["room_type"],
            "check_in": b["check_in"], "check_out": b["check_out"], "nights": nights, "rate": b["rate"],
            "room_charges": room, "services": svc, "service_charges": svc_total, "tax": tax,
            "total": round(room + svc_total + tax, 2)}


# ------------------------------ auth ------------------------------
@app.post("/api/auth/register")
def register():
    """Create a guest account.
    Body: {"name":"Asha Rao","email":"asha@example.com","password":"Guest@123","phone":"9876543210","language":"en"}"""
    d = body()
    name, email, pw = str(d.get("name", "")).strip(), str(d.get("email", "")).strip().lower(), str(d.get("password", ""))
    if not 2 <= len(name) <= 100:
        return err("Enter your full name.")
    if not EMAIL.match(email) or len(email) > 150:
        return err("Enter a valid email address.")
    if len(pw) < 8:
        return err("Password needs at least 8 characters.")
    if db.query("SELECT id FROM users WHERE email=%s", (email,), one=True):
        return err("That email is already registered.", 409)
    lang = d.get("language") if d.get("language") in ai.LANG_NAMES else "en"
    uid = db.execute("INSERT INTO users(name,email,password_hash,role,language) VALUES(%s,%s,%s,'guest',%s)",
                     (name, email, generate_password_hash(pw), lang))
    db.execute("INSERT INTO guest_profiles(user_id,phone) VALUES(%s,%s)", (uid, str(d.get("phone", ""))[:20]))
    return token_response(uid, 201)


@app.post("/api/auth/login")
def login():
    """Sign in and receive a bearer token.
    Body: {"email":"guest@staygenius.com","password":"Guest@123"}"""
    d = body()
    email = str(d.get("email", "")).strip().lower()
    recent = [t for t in FAILS.get(email, []) if time.time() - t < 900]
    if len(recent) >= 5:
        return err("Too many failed attempts. Try again in 15 minutes.", 429)
    u = db.query("SELECT id,password_hash,active FROM users WHERE email=%s", (email,), one=True)
    if not u or not u["active"] or not check_password_hash(u["password_hash"], str(d.get("password", ""))):
        FAILS[email] = recent + [time.time()]
        return err("Email or password is incorrect.", 401)
    FAILS.pop(email, None)
    return token_response(u["id"])


@app.get("/api/me")
@auth()
def me():
    """Current user with guest profile."""
    p = db.query("SELECT phone, preferences FROM guest_profiles WHERE user_id=%s", (g.user["id"],), one=True) or {}
    return jsonify({**g.user, **p})


@app.put("/api/me/profile")
@auth("guest")
def update_profile():
    """Update guest preferences.
    Body: {"phone":"9876543210","preferences":["vegetarian","family"],"language":"te"}"""
    d = body()
    allowed = {"vegetarian", "family", "spa", "quiet room", "high floor", "early check-in"}
    prefs = ",".join(p for p in d.get("preferences", []) if p in allowed)
    db.execute("INSERT INTO guest_profiles(user_id,phone,preferences) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE phone=VALUES(phone), preferences=VALUES(preferences)",
               (g.user["id"], str(d.get("phone", ""))[:20], prefs))
    if d.get("language") in ai.LANG_NAMES:
        db.execute("UPDATE users SET language=%s WHERE id=%s", (d["language"], g.user["id"]))
    return jsonify({"ok": True})


# ------------------------------ users (admin) ------------------------------
@app.get("/api/users")
@auth("admin")
def users():
    """List all users."""
    return jsonify(db.query("SELECT id,name,email,role,active,created_at FROM users ORDER BY role, name LIMIT 300"))


@app.post("/api/users")
@auth("admin")
def create_user():
    """Create a user with any role.
    Body: {"name":"Ravi","email":"ravi@staygenius.com","password":"Staff@1234","role":"staff"}"""
    d = body()
    name, email, pw, role = str(d.get("name", "")).strip(), str(d.get("email", "")).strip().lower(), str(d.get("password", "")), d.get("role")
    if not name or not EMAIL.match(email) or len(pw) < 8 or role not in ROLES:
        return err("Name, valid email, role and an 8+ character password are required.")
    if db.query("SELECT id FROM users WHERE email=%s", (email,), one=True):
        return err("That email is already registered.", 409)
    uid = db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(%s,%s,%s,%s)", (name[:100], email, generate_password_hash(pw), role))
    if role == "guest":
        db.execute("INSERT INTO guest_profiles(user_id) VALUES(%s)", (uid,))
    return jsonify({"id": uid}), 201


@app.patch("/api/users/<int:uid>")
@auth("admin")
def toggle_user(uid):
    """Enable or disable a user.
    Body: {"active":false}"""
    if uid == g.user["id"]:
        return err("You cannot disable your own account.")
    db.execute("UPDATE users SET active=%s WHERE id=%s", (1 if body().get("active") else 0, uid))
    return jsonify({"ok": True})


# ------------------------------ room types, rooms ------------------------------
@app.get("/api/room-types")
def room_types():
    """List room types with base prices."""
    return jsonify(db.query("SELECT rt.*, (SELECT COUNT(*) FROM rooms WHERE room_type_id=rt.id) room_count FROM room_types rt ORDER BY base_price"))


@app.route("/api/room-types", methods=["POST"])
@auth("admin")
def add_room_type():
    """Add a room type.
    Body: {"name":"Family Suite","description":"Two bedrooms","base_price":9000,"capacity":5}"""
    d = body()
    try:
        name, price, cap = str(d["name"]).strip()[:60], float(d["base_price"]), int(d.get("capacity", 2))
    except (KeyError, ValueError):
        return err("Name and a numeric base price are required.")
    if not name or not 500 <= price <= 100000 or not 1 <= cap <= 10:
        return err("Price must be 500-100000 and capacity 1-10.")
    try:
        tid = db.execute("INSERT INTO room_types(name,description,base_price,capacity) VALUES(%s,%s,%s,%s)", (name, str(d.get("description", ""))[:255], price, cap))
    except Exception:
        return err("A room type with that name already exists.", 409)
    return jsonify({"id": tid}), 201


@app.put("/api/room-types/<int:tid>")
@auth("admin")
def edit_room_type(tid):
    """Edit base price, capacity or description of a room type.
    Body: {"base_price":4000,"capacity":3,"description":"City view"}"""
    d = body()
    try:
        price, cap = float(d["base_price"]), int(d["capacity"])
    except (KeyError, ValueError):
        return err("Base price and capacity must be numbers.")
    if not 500 <= price <= 100000 or not 1 <= cap <= 10:
        return err("Price must be 500-100000 and capacity 1-10.")
    db.execute("UPDATE room_types SET base_price=%s, capacity=%s, description=%s WHERE id=%s", (price, cap, str(d.get("description", ""))[:255], tid))
    return jsonify({"ok": True})


@app.get("/api/rooms")
@auth(*STAFF)
def rooms():
    """Room status board with current guest."""
    return jsonify(db.query("""SELECT r.id, r.number, r.floor, r.status, rt.name room_type,
        (SELECT u.name FROM bookings b JOIN users u ON u.id=b.guest_id WHERE b.room_id=r.id AND b.status='checked_in' LIMIT 1) guest_name
        FROM rooms r JOIN room_types rt ON rt.id=r.room_type_id ORDER BY r.number"""))


@app.post("/api/rooms")
@auth("admin")
def add_room():
    """Add a room.
    Body: {"number":"501","room_type_id":1,"floor":5}"""
    d = body()
    try:
        number, tid, floor = str(d["number"]).strip()[:10], int(d["room_type_id"]), int(d.get("floor", 1))
    except (KeyError, ValueError):
        return err("Room number and room type are required.")
    if not number or not db.query("SELECT id FROM room_types WHERE id=%s", (tid,), one=True):
        return err("Pick a valid room type.")
    try:
        rid = db.execute("INSERT INTO rooms(number,room_type_id,floor) VALUES(%s,%s,%s)", (number, tid, floor))
    except Exception:
        return err("That room number already exists.", 409)
    return jsonify({"id": rid}), 201


@app.patch("/api/rooms/<int:rid>/status")
@auth(*STAFF)
def room_status(rid):
    """Change room status (vacant, occupied, cleaning, maintenance).
    Body: {"status":"cleaning"}"""
    s = body().get("status")
    if s not in ROOM_STATUS:
        return err("Status must be one of: " + ", ".join(ROOM_STATUS))
    if s != "occupied" and db.query("SELECT id FROM bookings WHERE room_id=%s AND status='checked_in'", (rid,), one=True):
        return err("A guest is checked in. Check them out first.", 409)
    db.execute("UPDATE rooms SET status=%s WHERE id=%s", (s, rid))
    return jsonify({"ok": True})


# ------------------------------ availability + bookings ------------------------------
def parse_stay(src):
    ci, co = parse_date(src.get("check_in")), parse_date(src.get("check_out"))
    if ci < dt.date.today():
        raise ValueError("Check-in cannot be in the past.")
    if co <= ci or (co - ci).days > 30:
        raise ValueError("Check-out must be 1 to 30 nights after check-in.")
    return ci, co


@app.get("/api/availability")
def availability():
    """Room types available for a stay with dynamic nightly prices. Query: check_in, check_out, guests."""
    try:
        ci, co = parse_stay(request.args)
        guests = int(request.args.get("guests", 1))
    except (ValueError, TypeError) as e:
        return err(str(e))
    out = []
    for t in db.query("SELECT * FROM room_types WHERE capacity>=%s ORDER BY base_price", (guests,)):
        free = db.query(FREE_ROOMS, (t["id"], co, ci))
        prices = nightly_prices(t["id"], t["base_price"], ci, co)
        out.append({**t, "available": len(free), "avg_price": round(sum(prices) / len(prices)), "total": sum(prices), "nights": len(prices),
                    "festival_pricing": any(p != float(t["base_price"]) for p in prices)})
    return jsonify(out)


@app.post("/api/bookings")
@auth("guest")
def create_booking():
    """Book a room (double-booking safe).
    Body: {"room_type_id":1,"check_in":"2026-11-20","check_out":"2026-11-22","guests":2}"""
    d = body()
    try:
        ci, co = parse_stay(d)
        tid, guests = int(d["room_type_id"]), int(d.get("guests", 1))
    except (KeyError, ValueError, TypeError) as e:
        return err(str(e) if isinstance(e, ValueError) else "Room type, check-in and check-out are required.")
    t = db.query("SELECT * FROM room_types WHERE id=%s", (tid,), one=True)
    if not t or not 1 <= guests <= t["capacity"]:
        return err("Choose a valid room type and guest count.")
    prices = nightly_prices(tid, t["base_price"], ci, co)
    conn = db.get_conn()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id FROM rooms WHERE room_type_id=%s FOR UPDATE", (tid,))  # serialise bookings per type
        cur.fetchall()
        cur.execute(FREE_ROOMS, (tid, co, ci))
        free = cur.fetchall()
        if not free:
            conn.rollback()
            return err("Sorry, that room type was just booked for those dates.", 409)
        cur.execute("INSERT INTO bookings(guest_id,room_id,check_in,check_out,guests,rate,total) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                    (g.user["id"], free[0]["id"], ci, co, guests, round(sum(prices) / len(prices), 2), sum(prices)))
        bid = cur.lastrowid
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return jsonify(get_booking(bid)), 201


@app.get("/api/bookings")
@auth()
def list_bookings():
    """List bookings. Guests see their own. Staff query: view=upcoming|inhouse|history."""
    if g.user["role"] == "guest":
        return jsonify(db.query(BOOKING_SQL + " WHERE b.guest_id=%s ORDER BY b.check_in DESC LIMIT 50", (g.user["id"],)))
    v = request.args.get("view", "upcoming")
    where, order = {"inhouse": ("b.status='checked_in'", "r.number"),
                    "history": ("b.status IN ('checked_out','cancelled')", "b.check_out DESC"),
                    }.get(v, ("b.status='confirmed' AND b.check_in<=CURDATE()+INTERVAL 7 DAY", "b.check_in"))
    return jsonify(db.query(BOOKING_SQL + f" WHERE {where} ORDER BY {order} LIMIT 120"))


@app.post("/api/bookings/<int:bid>/cancel")
@auth()
def cancel_booking(bid):
    """Cancel a confirmed booking."""
    b = get_booking(bid)
    if not b:
        return err("Booking not found.", 404)
    if b["status"] != "confirmed":
        return err("Only confirmed bookings can be cancelled.", 409)
    db.execute("UPDATE bookings SET status='cancelled' WHERE id=%s", (bid,))
    return jsonify({"ok": True})


@app.post("/api/bookings/<int:bid>/checkin")
@auth(*STAFF)
def checkin(bid):
    """Check a guest in (room must be clean and free)."""
    b = get_booking(bid)
    if not b:
        return err("Booking not found.", 404)
    if b["status"] != "confirmed":
        return err("Booking is not awaiting check-in.", 409)
    if b["check_in"] > dt.date.today():
        return err("Guest arrives on " + b["check_in"].isoformat() + ". Check-in opens that day.", 409)
    room = db.query("SELECT status FROM rooms WHERE id=%s", (b["room_id"],), one=True)
    if room["status"] != "vacant":
        return err(f"Room {b['room_number']} is {room['status']}. Make it vacant first.", 409)
    db.execute("UPDATE bookings SET status='checked_in' WHERE id=%s", (bid,))
    db.execute("UPDATE rooms SET status='occupied' WHERE id=%s", (b["room_id"],))
    return jsonify({"ok": True})


@app.post("/api/bookings/<int:bid>/checkout")
@auth(*STAFF)
def checkout(bid):
    """Check out, generate the invoice, and schedule room cleaning."""
    b = get_booking(bid)
    if not b:
        return err("Booking not found.", 404)
    if b["status"] != "checked_in":
        return err("Guest is not checked in.", 409)
    inv = build_invoice(b)
    db.execute("UPDATE bookings SET status='checked_out' WHERE id=%s", (bid,))
    db.execute("UPDATE rooms SET status='cleaning' WHERE id=%s", (b["room_id"],))
    db.execute("INSERT INTO invoices(booking_id,room_charges,service_charges,tax,total) VALUES(%s,%s,%s,%s,%s) "
               "ON DUPLICATE KEY UPDATE total=VALUES(total)", (bid, inv["room_charges"], inv["service_charges"], inv["tax"], inv["total"]))
    db.execute("INSERT INTO service_requests(booking_id,guest_id,category,description,status,priority,auto_generated) VALUES(%s,%s,'housekeeping',%s,'pending','normal',1)",
               (bid, b["guest_id"], f"Turnover cleaning - Room {b['room_number']}"))
    return jsonify(inv)


@app.get("/api/bookings/<int:bid>/invoice")
@auth()
def invoice(bid):
    """Invoice for a booking (final after check-out, preview before)."""
    b = get_booking(bid)
    if not b:
        return err("Booking not found.", 404)
    return jsonify({**build_invoice(b), "final": b["status"] == "checked_out"})


# ------------------------------ services & requests ------------------------------
@app.get("/api/services")
def services():
    """Hotel service catalogue."""
    return jsonify(db.query("SELECT * FROM services ORDER BY category, name"))


@app.post("/api/services")
@auth("admin")
def add_service():
    """Add a catalogue service.
    Body: {"name":"Laundry","category":"housekeeping","price":150}"""
    d = body()
    try:
        name, price = str(d["name"]).strip()[:80], float(d.get("price", 0))
    except (KeyError, ValueError):
        return err("Name and numeric price are required.")
    if not name or d.get("category") not in CATS or not 0 <= price <= 20000:
        return err("Provide a name, a category and a price between 0 and 20000.")
    return jsonify({"id": db.execute("INSERT INTO services(name,category,price) VALUES(%s,%s,%s)", (name, d["category"], price))}), 201


@app.post("/api/service-requests")
@auth("guest")
def create_request():
    """Raise a housekeeping, food or maintenance request (must be checked in).
    Body: {"category":"housekeeping","description":"Two extra towels","service_id":1}"""
    d = body()
    b = db.query("SELECT id FROM bookings WHERE guest_id=%s AND status='checked_in' LIMIT 1", (g.user["id"],), one=True)
    if not b:
        return err("Service requests open once you have checked in.", 409)
    price, cat, desc = 0, d.get("category"), str(d.get("description", "")).strip()[:300]
    if d.get("service_id"):
        s = db.query("SELECT * FROM services WHERE id=%s", (d["service_id"],), one=True)
        if s:
            price, cat, desc = s["price"], s["category"], desc or s["name"]
    if cat not in CATS or not desc:
        return err("Choose a category and describe what you need.")
    rid = db.execute("INSERT INTO service_requests(booking_id,guest_id,category,description,price,priority) VALUES(%s,%s,%s,%s,%s,%s)",
                     (b["id"], g.user["id"], cat, desc, price, "high" if cat == "maintenance" else "normal"))
    return jsonify({"id": rid}), 201


@app.get("/api/service-requests")
@auth()
def list_requests():
    """List requests. Guests see their own; staff can filter with ?status=pending|in_progress|done."""
    sql = """SELECT sr.*, u.name guest_name, r.number room_number FROM service_requests sr JOIN users u ON u.id=sr.guest_id
             JOIN bookings b ON b.id=sr.booking_id JOIN rooms r ON r.id=b.room_id WHERE sr.auto_generated=0"""
    if g.user["role"] == "guest":
        return jsonify(db.query(sql + " AND sr.guest_id=%s ORDER BY sr.created_at DESC LIMIT 40", (g.user["id"],)))
    st = request.args.get("status")
    if st in ("pending", "in_progress", "done"):
        return jsonify(db.query(sql + " AND sr.status=%s ORDER BY sr.priority DESC, sr.created_at LIMIT 100", (st,)))
    return jsonify(db.query(sql + " AND sr.status<>'done' ORDER BY sr.priority DESC, sr.created_at LIMIT 100"))


@app.patch("/api/service-requests/<int:rid>")
@auth(*STAFF)
def update_request(rid):
    """Move a request through pending, in_progress, done.
    Body: {"status":"in_progress"}"""
    s = body().get("status")
    if s not in ("pending", "in_progress", "done"):
        return err("Invalid status.")
    db.execute("UPDATE service_requests SET status=%s WHERE id=%s", (s, rid))
    return jsonify({"ok": True})


@app.get("/api/housekeeping/schedule")
@auth(*STAFF)
def housekeeping():
    """Suggested cleaning order: rooms with arrivals today first, then guest requests."""
    rows = db.query("""SELECT r.id, r.number, rt.name room_type,
        (SELECT COUNT(*) FROM bookings b WHERE b.room_id=r.id AND b.status='confirmed' AND b.check_in=CURDATE()) arrival_today
        FROM rooms r JOIN room_types rt ON rt.id=r.room_type_id WHERE r.status='cleaning' ORDER BY arrival_today DESC, r.number""")
    t = dt.datetime.combine(dt.date.today(), dt.time(10, 0))
    for r in rows:
        r["slot"] = t.strftime("%I:%M %p")
        r["reason"] = "Guest arriving today" if r["arrival_today"] else "No arrival today"
        t += dt.timedelta(minutes=30)
    reqs = db.query("""SELECT sr.id, sr.description, sr.status, r.number room_number FROM service_requests sr
        JOIN bookings b ON b.id=sr.booking_id JOIN rooms r ON r.id=b.room_id
        WHERE sr.category='housekeeping' AND sr.auto_generated=0 AND sr.status<>'done' ORDER BY sr.created_at LIMIT 30""")
    return jsonify({"turnover": rows, "requests": reqs})


# ------------------------------ reviews ------------------------------
@app.post("/api/reviews")
@auth("guest")
def add_review():
    """Submit feedback; sentiment and themes are detected automatically.
    Body: {"rating":5,"comment":"Clean room and friendly staff","booking_id":1}"""
    d = body()
    try:
        rating = int(d["rating"])
    except (KeyError, ValueError):
        return err("Pick a star rating.")
    comment = str(d.get("comment", "")).strip()[:1500]
    if not 1 <= rating <= 5 or len(comment) < 3:
        return err("Rating must be 1-5 and the comment cannot be empty.")
    bid = d.get("booking_id")
    if bid and not db.query("SELECT id FROM bookings WHERE id=%s AND guest_id=%s", (bid, g.user["id"]), one=True):
        return err("Booking not found.", 404)
    sent, themes = ai.analyze(comment, rating)
    rid = db.execute("INSERT INTO reviews(guest_id,booking_id,rating,comment,sentiment,themes) VALUES(%s,%s,%s,%s,%s,%s)",
                     (g.user["id"], bid or None, rating, comment, sent, themes))
    return jsonify({"id": rid, "sentiment": sent, "themes": themes}), 201


@app.get("/api/reviews")
@auth()
def list_reviews():
    """List reviews (guests see their own)."""
    sql = "SELECT rv.*, u.name guest_name FROM reviews rv JOIN users u ON u.id=rv.guest_id"
    if g.user["role"] == "guest":
        return jsonify(db.query(sql + " WHERE rv.guest_id=%s ORDER BY rv.created_at DESC", (g.user["id"],)))
    return jsonify(db.query(sql + " ORDER BY (rv.reply IS NULL) DESC, rv.created_at DESC LIMIT 60"))


@app.get("/api/reviews/insights")
@auth("manager", "admin")
def insights():
    """GenAI summary of review sentiment, praise and complaints."""
    return jsonify(ai.review_insights())


@app.post("/api/reviews/<int:rid>/draft-reply")
@auth("manager", "admin")
def draft(rid):
    """GenAI drafts a professional reply for the manager to edit."""
    r = db.query("SELECT rv.*, u.name guest_name FROM reviews rv JOIN users u ON u.id=rv.guest_id WHERE rv.id=%s", (rid,), one=True)
    if not r:
        return err("Review not found.", 404)
    return jsonify({"draft": ai.draft_reply(r), "ai": bool(os.getenv("GEMINI_API_KEY"))})


@app.put("/api/reviews/<int:rid>/reply")
@auth("manager", "admin")
def reply(rid):
    """Publish the manager's reply.
    Body: {"reply":"Thank you for staying with us..."}"""
    text = str(body().get("reply", "")).strip()[:1500]
    if len(text) < 5:
        return err("Write a reply first.")
    db.execute("UPDATE reviews SET reply=%s, replied_at=NOW() WHERE id=%s", (text, rid))
    return jsonify({"ok": True})


# ------------------------------ pricing, forecast, dashboard ------------------------------
@app.get("/api/pricing/suggestions")
@auth("manager", "admin")
def pricing():
    """AI suggested nightly prices per room type. Query: days (7-30)."""
    days = min(max(int(request.args.get("days", 14)), 7), 30)
    return jsonify(ai.price_suggestions(days))


@app.post("/api/pricing/apply")
@auth("manager", "admin")
def apply_prices():
    """Approve prices for dates.
    Body: {"items":[{"room_type_id":1,"date":"2026-11-07","price":3500}]}"""
    items = body().get("items", [])[:400]
    n = 0
    for it in items:
        try:
            tid, d, p = int(it["room_type_id"]), parse_date(it["date"]), float(it["price"])
        except (KeyError, ValueError, TypeError):
            return err("Each item needs room_type_id, date and price.")
        if d < dt.date.today() or not 500 <= p <= 100000:
            return err("Prices must be 500-100000 and for today or later.")
        db.execute("INSERT INTO price_overrides(room_type_id,stay_date,price) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE price=VALUES(price)", (tid, d, p))
        n += 1
    return jsonify({"applied": n})


@app.get("/api/forecast")
@auth("manager", "admin")
def forecast():
    """Weekly occupancy forecast. Query: weeks (1-8)."""
    return jsonify(ai.forecast_weekly(min(max(int(request.args.get("weeks", 4)), 1), 8)))


def window_stats(start, end, group=False):
    expr = "GREATEST(0, DATEDIFF(LEAST(check_out,%s), GREATEST(check_in,%s)))"
    sql = f"SELECT COALESCE(SUM({expr}),0) nights, COALESCE(SUM(b.rate*{expr}),0) revenue FROM bookings b WHERE status<>'cancelled' AND check_in<%s AND check_out>%s"
    r = db.query(sql, (end, start, end, start, end, start), one=True)
    return float(r["nights"]), float(r["revenue"])


@app.get("/api/dashboard")
@auth("manager", "admin")
def dashboard():
    """Occupancy, ADR, RevPAR, revenue and operations metrics."""
    today, total = dt.date.today(), ai.total_rooms()
    nights, rev = window_stats(today - dt.timedelta(days=30), today)
    monthly = []
    for i in range(5, -1, -1):
        first = (today.replace(day=1) - dt.timedelta(days=30 * i)).replace(day=1)
        nxt = (first + dt.timedelta(days=32)).replace(day=1)
        n, r = window_stats(first, nxt)
        monthly.append({"label": first.strftime("%b"), "revenue": round(r), "occupancy": round(100 * n / (total * (nxt - first).days), 1)})
    by_type = db.query("""SELECT rt.name label, ROUND(SUM(b.rate*GREATEST(0,DATEDIFF(LEAST(b.check_out,%s),GREATEST(b.check_in,%s))))) revenue
        FROM bookings b JOIN rooms r ON r.id=b.room_id JOIN room_types rt ON rt.id=r.room_type_id
        WHERE b.status<>'cancelled' AND b.check_in<%s AND b.check_out>%s GROUP BY rt.name""", (today, today - dt.timedelta(days=30), today, today - dt.timedelta(days=30)))
    trend = ai.daily_occupancy(today - dt.timedelta(days=29), today)
    return jsonify({
        "total_rooms": total,
        "room_status": {r["status"]: r["c"] for r in db.query("SELECT status, COUNT(*) c FROM rooms GROUP BY status")},
        "occupancy_30d": round(100 * nights / (total * 30), 1), "adr": round(rev / nights) if nights else 0,
        "revpar": round(rev / (total * 30)), "revenue_30d": round(rev),
        "occupancy_today": round(100 * float(trend.iloc[-1]) / total, 1),
        "monthly": monthly, "revenue_by_type": by_type,
        "trend": [{"label": d.strftime("%d %b"), "value": round(100 * float(v) / total, 1)} for d, v in trend.items()],
        "requests": {r["status"]: r["c"] for r in db.query("SELECT status, COUNT(*) c FROM service_requests WHERE auto_generated=0 GROUP BY status")},
        "reviews": db.query("SELECT sentiment, COUNT(*) c, ROUND(AVG(rating),2) avg_rating FROM reviews GROUP BY sentiment"),
        "avg_rating": (db.query("SELECT ROUND(AVG(rating),2) a FROM reviews", one=True) or {}).get("a"),
    })


# ------------------------------ assistant + upsell ------------------------------
@app.post("/api/assistant")
@auth("guest")
def assistant():
    """Multilingual digital assistant; raises service requests when needed.
    Body: {"message":"Please send two towels","language":"en"}"""
    d = body()
    msg, lang = str(d.get("message", "")).strip()[:500], d.get("language", "en")
    if not msg:
        return err("Type a message first.")
    b = db.query("SELECT b.id, r.number FROM bookings b JOIN rooms r ON r.id=b.room_id WHERE b.guest_id=%s AND b.status='checked_in' LIMIT 1", (g.user["id"],), one=True)
    text, cat, req = ai.assistant(msg, lang if lang in ai.LANG_NAMES else "en", {"name": g.user["name"], "room": b and b["number"]})
    created = None
    if cat and b:
        created = db.execute("INSERT INTO service_requests(booking_id,guest_id,category,description,priority) VALUES(%s,%s,%s,%s,%s)",
                             (b["id"], g.user["id"], cat, req or msg, "high" if cat == "maintenance" else "normal"))
    elif cat:
        text += "\n(Requests open after check-in.)" if lang == "en" else ""
    return jsonify({"reply": text, "request_id": created, "category": cat, "genai": bool(os.getenv("GEMINI_API_KEY"))})


@app.get("/api/upsell")
@auth("guest")
def upsell():
    """Personalised offers based on preferences and stay history."""
    return jsonify(ai.upsell(g.user["id"]))


# ------------------------------ docs + frontend ------------------------------
@app.get("/openapi.json")
def openapi():
    paths = {}
    for r in app.url_map.iter_rules():
        if not r.rule.startswith("/api"):
            continue
        fn = app.view_functions[r.endpoint]
        doc = (fn.__doc__ or fn.__name__).strip().split("\n")
        path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", r.rule)
        for m in r.methods - {"HEAD", "OPTIONS"}:
            op = {"summary": doc[0], "tags": [r.rule.split("/")[2]], "security": [{"bearerAuth": []}], "responses": {"200": {"description": "OK"}},
                  "parameters": [{"name": a, "in": "path", "required": True, "schema": {"type": "integer"}} for a in r.arguments]}
            if m in ("POST", "PUT", "PATCH"):
                ex = {}
                for line in doc[1:]:
                    if line.strip().startswith("Body:"):
                        try:
                            ex = json.loads(line.strip()[5:])
                        except ValueError:
                            pass
                op["requestBody"] = {"content": {"application/json": {"schema": {"type": "object"}, "example": ex}}}
            paths.setdefault(path, {})[m.lower()] = op
    return jsonify({"openapi": "3.0.3", "info": {"title": "StayGenius AI API", "version": "1.0",
                    "description": "Login via /api/auth/login, copy the token, click Authorize and paste it."},
                    "paths": paths, "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}}})


@app.get("/apidocs")
def apidocs():
    return ('<!doctype html><title>StayGenius API</title><link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">'
            '<div id="ui"></div><script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>'
            '<script>SwaggerUIBundle({url:"/openapi.json",dom_id:"#ui",persistAuthorization:true})</script>')


@app.get("/")
def index():
    return send_from_directory(FRONTEND, "index.html")


@app.get("/<path:p>")
def static_files(p):
    if p.startswith("api"):
        return err("Unknown API route.", 404)
    return send_from_directory(FRONTEND, p)


@app.errorhandler(500)
def server_error(e):
    return err("Something went wrong on the server. Check the terminal for details.", 500)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
