"""Creates the database tables and fills them with SYNTHETIC data (no real guest data).
Run once:  python seed.py      (re-running resets everything)"""
import os, random, datetime as dt
import mysql.connector
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
import ai, db

load_dotenv()
random.seed(7)
TODAY = dt.date.today()
HERE = os.path.dirname(__file__)

# 1) create schema ---------------------------------------------------------
root = mysql.connector.connect(**db.CFG)
cur = root.cursor()
cur.execute(f"CREATE DATABASE IF NOT EXISTS {db.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
cur.execute(f"USE {db.DB_NAME}")
sql = open(os.path.join(HERE, "..", "database", "schema.sql"), encoding="utf8").read()
for stmt in sql.split(";"):
    lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
    s = "\n".join(lines).strip()
    if s and not s.upper().startswith(("CREATE DATABASE", "USE ")):
        cur.execute(s)
root.commit()
print("Tables created.")

# 2) users -------------------------------------------------------------------
pw = generate_password_hash("Admin@123")
gpw = generate_password_hash("Guest@123")
users = [("Hotel Admin", "admin@staygenius.com", pw, "admin"), ("Meera Nair (Manager)", "manager@staygenius.com", pw, "manager"),
         ("Ravi Kumar (Front Desk)", "frontdesk@staygenius.com", pw, "staff"), ("Demo Guest", "guest@staygenius.com", gpw, "guest")]
first = "Aarav Vivaan Aditya Sai Arjun Krishna Rohan Ishaan Ananya Diya Meera Kavya Lakshmi Priya Sneha Divya Harsha Teja Charan Pranav Nikhil Swathi".split()
last = "Reddy Naidu Sharma Rao Kumar Iyer Nair Patel Gupta Chowdary Varma Singh Menon Das Joshi".split()
for i in range(60):
    users.append((f"{random.choice(first)} {random.choice(last)}", f"guest{i + 1}@example.com", gpw, "guest"))
cur.executemany("INSERT INTO users(name,email,password_hash,role,language) VALUES(%s,%s,%s,%s,'en')", [u[:4] for u in users])
cur.execute("SELECT id FROM users WHERE role='guest' ORDER BY id")
guest_ids = [r[0] for r in cur.fetchall()]
tags = ["vegetarian", "family", "spa", "quiet room", "high floor", "early check-in"]
cur.executemany("INSERT INTO guest_profiles(user_id,phone,preferences) VALUES(%s,%s,%s)",
                [(g, "9" + "".join(random.choices("0123456789", k=9)), ",".join(random.sample(tags, random.randint(0, 2)))) for g in guest_ids])
demo_guest = guest_ids[0]
cur.execute("UPDATE guest_profiles SET preferences='vegetarian,family' WHERE user_id=%s", (demo_guest,))

# 3) room types, rooms, services ----------------------------------------------
types = [("Standard", "Queen bed, AC, city view", 2500, 2, 50), ("Deluxe", "King bed, work desk, hill view", 3800, 3, 40),
         ("Executive", "Large room with lounge corner", 5200, 4, 20), ("Suite", "Bedroom and living room, temple-hill view", 8500, 5, 10)]
rooms, n = [], 0
for t in types:
    cur.execute("INSERT INTO room_types(name,description,base_price,capacity) VALUES(%s,%s,%s,%s)", t[:4])
    tid = cur.lastrowid
    for _ in range(t[4]):
        floor = n // 24 + 1
        num = f"{floor}{n % 24 + 1:02d}"
        cur.execute("INSERT INTO rooms(number,room_type_id,floor) VALUES(%s,%s,%s)", (num, tid, floor))
        rooms.append((cur.lastrowid, tid, float(t[2])))
        n += 1
cur.executemany("INSERT INTO services(name,category,price) VALUES(%s,%s,%s)", [
    ("Extra towels", "housekeeping", 0), ("Room cleaning", "housekeeping", 0), ("Laundry (per bag)", "housekeeping", 150),
    ("Breakfast (idli, dosa, pongal)", "food", 250), ("Veg thali", "food", 350), ("Filter coffee", "food", 60), ("Tiffin box", "food", 180),
    ("AC not cooling", "maintenance", 0), ("TV or Wi-Fi issue", "maintenance", 0), ("Plumbing or leak", "maintenance", 0)])

# 4) bookings: 400 days of history + 45 days ahead -------------------------------
free_from = {r[0]: TODAY - dt.timedelta(days=401) for r in rooms}
rows = []
for off in range(-400, 46):
    d = TODAY + dt.timedelta(days=off)
    pickup = 1.0 if off <= 0 else max(0.25, 1 - off / 60)
    target = ai.demand_curve(d) * pickup * len(rooms) + random.randint(-4, 4)
    busy = sum(1 for v in free_from.values() if v > d)
    avail = [r for r in rooms if free_from[r[0]] <= d]
    random.shuffle(avail)
    for rid, tid, base in avail[:max(0, int(target - busy))]:
        nights = random.choice([1, 1, 2, 2, 3, 4]) + (1 if ai.festival(d) else 0)
        co = d + dt.timedelta(days=nights)
        free_from[rid] = co
        rate = round(base * (1 + (0.15 if ai.festival(d) else 0) + (0.08 if d.weekday() >= 4 else 0) + random.uniform(-.04, .04)), 2)
        status = "checked_out" if co <= TODAY else "checked_in" if d <= TODAY else "confirmed"
        rows.append((random.choice(guest_ids[1:]), rid, d, co, random.randint(1, 2), rate, rate * nights, status))
    if random.random() < .5 and avail:  # a few cancelled bookings
        rid, tid, base = random.choice(rooms)
        rows.append((random.choice(guest_ids), rid, d, d + dt.timedelta(days=2), 2, base, base * 2, "cancelled"))
cur.executemany("INSERT INTO bookings(guest_id,room_id,check_in,check_out,guests,rate,total,status) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", rows)
# give the demo guest a current stay, a past stay and an upcoming stay
for st in ("checked_in", "checked_out", "confirmed"):
    cur.execute("UPDATE bookings SET guest_id=%s WHERE status=%s ORDER BY id DESC LIMIT 1", (demo_guest, st))
cur.execute("UPDATE rooms SET status='occupied' WHERE id IN (SELECT room_id FROM bookings WHERE status='checked_in')")
cur.execute("""UPDATE rooms SET status='cleaning' WHERE status='vacant' AND id NOT IN
               (SELECT room_id FROM bookings WHERE status='confirmed') ORDER BY RAND() LIMIT 6""")
cur.execute("""UPDATE rooms SET status='maintenance' WHERE status='vacant' AND id NOT IN
               (SELECT room_id FROM bookings WHERE status IN ('confirmed','checked_in')) ORDER BY RAND() LIMIT 3""")
root.commit()

# 5) in-stay requests and reviews ----------------------------------------------
cur.execute("SELECT id, guest_id FROM bookings WHERE status='checked_in' ORDER BY RAND() LIMIT 14")
reqs = [("housekeeping", "Two extra towels please"), ("food", "Veg thali to room 7 PM"), ("maintenance", "AC is not cooling"),
        ("housekeeping", "Room cleaning"), ("food", "Filter coffee x2"), ("maintenance", "Bathroom tap is leaking")]
for bid, gid in cur.fetchall():
    c, dsc = random.choice(reqs)
    cur.execute("INSERT INTO service_requests(booking_id,guest_id,category,description,status,priority) VALUES(%s,%s,%s,%s,%s,%s)",
                (bid, gid, c, dsc, random.choice(["pending", "pending", "in_progress", "done"]), "high" if c == "maintenance" else "normal"))
texts = [(5, "Very clean room and friendly staff. The hotel is near the temple and the breakfast was tasty."),
         (5, "Excellent stay, helpful reception and quick check-in. Comfortable bed and peaceful location."),
         (4, "Good value for money. Spacious room, nice food, easy walk to the station."),
         (4, "Polite staff and clean bathroom. Wifi could be faster."),
         (3, "Average stay. The room was fine but breakfast was cold and service was slow."),
         (2, "AC was not working and we waited a long time for maintenance. Bathroom smell was bad."),
         (1, "Rude behaviour at the reception and a dirty room. Overpriced during the festival days."),
         (2, "Very noisy corridor at night and slow room service. Disappointed."),
         (5, "Amazing hospitality during Brahmotsavam, the team helped with darshan information. Best hotel in Tirupati."),
         (3, "Location is great but the lift was slow and the towels were not changed.")]
cur.execute("SELECT id, guest_id FROM bookings WHERE status='checked_out' ORDER BY RAND() LIMIT 70")
for bid, gid in cur.fetchall():
    rating, text = random.choice(texts)
    s, th = ai.analyze(text, rating)
    reply = "Thank you for your feedback. We appreciate you choosing us and hope to host you again." if random.random() < .4 else None
    cur.execute("INSERT INTO reviews(guest_id,booking_id,rating,comment,sentiment,themes,reply,replied_at,created_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (gid, bid, rating, text, s, th, reply, TODAY if reply else None, TODAY - dt.timedelta(days=random.randint(0, 120))))
root.commit()
cur.execute("SELECT COUNT(*) FROM bookings")
print("Seeded", len(rooms), "rooms,", cur.fetchone()[0], "bookings. Done.")
print("Logins:  admin@staygenius.com / manager@staygenius.com / frontdesk@staygenius.com -> Admin@123 ;  guest@staygenius.com -> Guest@123")
