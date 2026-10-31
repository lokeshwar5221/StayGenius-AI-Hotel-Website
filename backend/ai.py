"""StayGenius AI features.

Classic AI / ML (scikit-learn + pandas)
  1. Occupancy forecasting  - GradientBoostingRegressor trained on the hotel's own booking history
  2. Dynamic room pricing   - forecast occupancy + festival calendar -> suggested nightly price
  3. Review sentiment/themes - lexicon NLP scoring combined with the star rating

GenAI (Google Gemini API, optional key - rule-based fallbacks keep the app working offline)
  1. Review reply drafting for the hotel manager
  2. Review insight summaries
  3. Multilingual guest assistant that also raises service requests (intent detection)
"""
import os, re, json, datetime as dt
from collections import Counter
import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import GradientBoostingRegressor
from db import query

# ---- Approximate Tirupati demand calendar (demo data, not an official calendar) ----
FESTIVALS = [((1, 10), (1, 20), "Sankranti / Vaikunta Ekadasi"), ((3, 25), (4, 6), "Ugadi / Sri Rama Navami"),
             ((6, 1), (6, 20), "Summer holidays"), ((9, 15), (9, 30), "Brahmotsavam"),
             ((10, 10), (10, 20), "Navaratri / Dussehra"), ((11, 5), (11, 12), "Diwali"),
             ((12, 20), (12, 31), "Year-end holidays")]


def festival(d):
    for a, b, name in FESTIVALS:
        if a <= (d.month, d.day) <= b:
            return name
    return None


def demand_curve(d):
    """Synthetic 'true' demand used only by seed.py to generate fake history."""
    v = 0.40 + {4: 0.15, 5: 0.22, 6: 0.10}.get(d.weekday(), 0)
    v += 0.35 if festival(d) else 0
    v += 0.08 if d.month in (5, 6, 12) else 0
    return min(v, 0.97)


def total_rooms():
    return query("SELECT COUNT(*) c FROM rooms", one=True)["c"] or 1


def daily_occupancy(start, end):
    """Rooms occupied per day (pandas Series indexed by date), start/end inclusive."""
    rows = query("SELECT check_in, check_out FROM bookings WHERE status<>'cancelled' AND check_out>%s AND check_in<=%s",
                 (start, end))
    idx = pd.date_range(start, end)
    occ = np.zeros(len(idx))
    t0 = pd.Timestamp(start)
    for r in rows:
        a = max((pd.Timestamp(r["check_in"]) - t0).days, 0)
        b = min((pd.Timestamp(r["check_out"]) - t0).days, len(idx))
        if b > a:
            occ[a:b] += 1
    return pd.Series(occ, index=idx)


def _features(idx):
    return pd.DataFrame({"dow": idx.dayofweek, "month": idx.month, "doy": idx.dayofyear,
                         "fest": [1 if festival(d) else 0 for d in idx]})


_model, _stamp = None, None


def _get_model():
    global _model, _stamp
    today = dt.date.today()
    if _stamp != today:
        hist = daily_occupancy(today - dt.timedelta(days=420), today - dt.timedelta(days=1))
        _model, _stamp = None, today
        if hist.sum() > 0:
            _model = GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=1)
            _model.fit(_features(hist.index), hist.values / total_rooms())
    return _model


def forecast_daily(days):
    """Forecast occupancy (0-1) for today .. today+days-1. Uses max(model, rooms already booked)."""
    start = dt.date.today()
    end = start + dt.timedelta(days=days - 1)
    idx = pd.date_range(start, end)
    otb = daily_occupancy(start, end).values / total_rooms()
    m = _get_model()
    pred = np.clip(m.predict(_features(idx)), 0, 1) if m else np.full(len(idx), 0.5)
    occ = np.maximum(pred, otb)
    return [{"date": d.date(), "occupancy": round(float(o), 3), "on_the_books": round(float(b), 3),
             "festival": festival(d)} for d, o, b in zip(idx, occ, otb)]


def forecast_weekly(weeks):
    daily = forecast_daily(weeks * 7)
    out = []
    for i in range(weeks):
        chunk = daily[i * 7:(i + 1) * 7]
        out.append({"week_start": chunk[0]["date"], "occupancy": round(sum(c["occupancy"] for c in chunk) / len(chunk), 3),
                    "on_the_books": round(sum(c["on_the_books"] for c in chunk) / len(chunk), 3),
                    "festival": next((c["festival"] for c in chunk if c["festival"]), None)})
    return out


def price_multiplier(occ, fest):
    if occ >= .85: m, why = .30, "very high demand"
    elif occ >= .70: m, why = .15, "high demand"
    elif occ >= .50: m, why = 0, "normal demand"
    elif occ >= .35: m, why = -.10, "soft demand"
    else: m, why = -.20, "weak demand, fill rooms"
    if fest:
        m += .10
        why += f" + {fest}"
    return m, why


def price_suggestions(days):
    start = dt.date.today()
    end = start + dt.timedelta(days=days)
    types = query("SELECT id,name,base_price FROM room_types ORDER BY base_price")
    ov = {(r["room_type_id"], r["stay_date"]): float(r["price"]) for r in
          query("SELECT * FROM price_overrides WHERE stay_date>=%s AND stay_date<%s", (start, end))}
    rows = []
    for f in forecast_daily(days):
        mult, why = price_multiplier(f["occupancy"], f["festival"])
        prices = {}
        for t in types:
            base = float(t["base_price"])
            sug = round(min(max(base * (1 + mult), base * .7), base * 1.6) / 50) * 50
            prices[t["id"]] = {"current": ov.get((t["id"], f["date"]), base), "suggested": sug}
        rows.append({**f, "reason": why, "change_pct": round(mult * 100), "prices": prices})
    return {"room_types": types, "days": rows}


# ------------------------------ Reviews NLP ------------------------------
POS = set("great good excellent clean friendly helpful comfortable amazing lovely perfect best nice quick tasty polite spacious wonderful peaceful".split())
NEG = set("dirty rude slow noisy bad poor worst smell broken late cold overpriced delay unhelpful leak small uncomfortable waited disappointed".split())
THEMES = {"cleanliness": "clean dirty smell towel bathroom", "staff": "staff rude friendly helpful reception polite manager",
          "food": "food breakfast dinner tasty restaurant thali", "location": "location temple tirumala darshan station near walk",
          "value for money": "price overpriced value cost expensive cheap", "noise": "noise noisy loud sleep",
          "facilities": "wifi ac tv water geyser lift parking", "service speed": "slow wait waited delay late quick"}


def analyze(text, rating):
    toks = set(re.findall(r"[a-z]+", text.lower()))
    score = len(toks & POS) - len(toks & NEG) + (rating - 3)
    sentiment = "positive" if score >= 2 else "negative" if score <= -1 else "neutral"
    themes = [k for k, w in THEMES.items() if toks & set(w.split())]
    return sentiment, ",".join(themes)


# ------------------------------ GenAI (Gemini) ------------------------------
def gemini(prompt, system=None, as_json=False):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if as_json:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    try:
        r = requests.post(
            url,
            json=body,
            headers={"x-goog-api-key": key},
            timeout=15
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        print(f"Gemini unavailable (HTTP {status}). Check GEMINI_API_KEY and GEMINI_MODEL.")
    except requests.RequestException:
        print("Gemini unavailable (network error).")
    except (KeyError, IndexError, TypeError, ValueError):
        print("Gemini returned an unexpected response.")
        return None
    return None


def draft_reply(review):
    first = review["guest_name"].split()[0]
    themes = [t for t in (review.get("themes") or "").split(",") if t]
    txt = gemini(f"Guest review ({review['rating']}/5): \"{review['comment']}\"\nGuest name: {first}",
                 system="You are the general manager of a 120-room hotel in Tirupati, India. Write a warm, professional, "
                        "concise (60-90 words) public reply to the review. Thank the guest, address specific points, "
                        "apologise sincerely if negative and offer to make it right, no made-up compensation. Sign as 'General Manager'.")
    if txt:
        return txt.strip()
    about = " and ".join(themes[:2]) or "your stay"
    if review["sentiment"] == "negative":
        return (f"Dear {first},\n\nThank you for telling us about your experience, and we are sorry we fell short, especially "
                f"around {about}. We have shared your comments with the team and would like to make this right. Please write to "
                f"us at guestcare@staygenius.example so we can follow up personally.\n\nRegards,\nGeneral Manager")
    return (f"Dear {first},\n\nThank you for the kind words about {about}. We are delighted you enjoyed your stay in Tirupati "
            f"and look forward to welcoming you again.\n\nWarm regards,\nGeneral Manager")


def review_insights():
    rows = query("SELECT rating, comment, sentiment, themes FROM reviews ORDER BY created_at DESC LIMIT 200")
    if not rows:
        return {"count": 0, "summary": "No reviews yet."}
    sent = Counter(r["sentiment"] for r in rows)
    praise, issues = Counter(), Counter()
    for r in rows:
        for t in (r["themes"] or "").split(","):
            if t:
                (issues if r["sentiment"] == "negative" else praise if r["sentiment"] == "positive" else Counter())[t] += 1
    avg = round(sum(r["rating"] for r in rows) / len(rows), 2)
    stats = {"count": len(rows), "average_rating": avg, "sentiment": dict(sent),
             "top_praise": praise.most_common(3), "top_issues": issues.most_common(3)}
    summary = gemini("Summarise these hotel review statistics and recent comments for the manager in 3 short sentences, then "
                     "give 2 concrete actions.\nStats: " + json.dumps(stats) + "\nRecent comments: " +
                     " | ".join(r["comment"] for r in rows[:25]),
                     system="You are a hospitality analyst. Be specific and brief.")
    if not summary:
        p = ", ".join(t for t, _ in stats["top_praise"]) or "n/a"
        i = ", ".join(t for t, _ in stats["top_issues"]) or "none flagged"
        summary = (f"Average rating is {avg}/5 across {len(rows)} reviews ({sent.get('positive', 0)} positive, "
                   f"{sent.get('negative', 0)} negative). Guests praise: {p}. Recurring complaints: {i}. "
                   f"Suggested action: review the complaint themes with the shift leads this week.")
    return {**stats, "summary": summary.strip()}


# ------------------------------ Guest assistant ------------------------------
INTENTS = {"housekeeping": "towel clean housekeeping blanket pillow laundry soap bedsheet toiletries room service cleaning",
           "food": "food hungry breakfast lunch dinner thali coffee tea tiffin idli dosa order eat",
           "maintenance": "ac wifi leak tap geyser light fan broken not working remote flush plumber",
           "complaint": "complaint complain unhappy disappointed bad experience issue problem feedback"}
ACK = {"en": "I have raised a {c} request for you. The team will be with you shortly.",
       "hi": "मैंने आपके लिए {c} अनुरोध दर्ज कर दिया है। हमारी टीम जल्द ही आपके पास पहुँचेगी।",
       "te": "మీ కోసం {c} అభ్యర్థనను నమోదు చేశాను. మా బృందం త్వరలో మీ వద్దకు వస్తుంది.",
       "ta": "உங்களுக்காக {c} கோரிக்கையைப் பதிவு செய்துள்ளேன். எங்கள் குழு விரைவில் வரும்."}
LANG_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil", "kn": "Kannada", "ml": "Malayalam"}
PLACES = (
    "Sri Venkateswara Temple (Tirumala)",
    "Sri Padmavathi Ammavari Temple (Tiruchanur)",
    "Sri Govindaraja Swamy Temple",
    "Kapila Theertham",
    "ISKCON Tirupati",
    "Chandragiri Fort"
)


def _request_intent(message):
    text = message.lower()
    words = set(re.findall(r"[a-z]+", text))
    complaint_cues = (
        "complaint", "complain", "unhappy", "disappointed", "bad experience",
        "problem", "issue", "dirty", "broken", "not working", "doesn't work",
        "does not work", "leaking", "rude", "wrong order", "cold food"
    )
    if any(cue in text for cue in complaint_cues):
        if words & set("ac wifi leak tap geyser light fan broken plumber flush".split()):
            return "maintenance"
        if words & set("towel towels blanket blankets pillow pillows bedsheet toiletries clean cleaning".split()):
            return "housekeeping"
        if words & set("food breakfast dinner lunch thali coffee tea dosa idli".split()):
            return "food"
        return "complaint"

    action_cues = (
        "please send", "send me", "bring me", "please bring", "order me",
        "place an order", "i want", "i need", "can i get", "could i get",
        "i would like", "i'd like", "can you send", "could you send",
        "can you bring", "could you bring", "please arrange", "request a",
        "request an"
    )
    if not any(cue in text for cue in action_cues):
        return None

    if words & set("towel towels blanket blankets pillow pillows bedsheet toiletries housekeeping clean".split()):
        return "housekeeping"
    if words & set("food breakfast dinner lunch thali coffee tea dosa idli tiffin".split()):
        return "food"
    if words & set("ac wifi leak tap geyser light fan remote flush plumber".split()):
        return "maintenance"
    return None


def _local_guest_answer(message, ctx):
    text = message.lower()

    if any(word in text for word in ("menu", "food options", "what food", "food do you", "eat", "hungry")):
        menu = ctx.get("menu", [])
        if menu:
            items = "\n".join(
                f"- {item['name']}: ₹{float(item['price']):.0f}"
                for item in menu
            )
            return "Here are the food items currently listed by the hotel:\n" + items + "\nTell me what you would like to order."
        return "I can’t retrieve the current menu right now. Please contact the front desk for today’s food options."

    if any(word in text for word in ("temple", "darshan", "nearby", "near me", "places to visit", "places nearby", "attractions", "sightseeing", "visit")):
        places = "\n".join(f"- {place}" for place in PLACES)
        return ("Popular places to consider in and around Tirupati include:\n" + places +
                "\nTirumala darshan access and timings can change, so check the official TTD updates before travelling.")

    if any(word in text for word in ("check out", "checkout", "check-out")):
        return "Check-out time is 11:00 AM. If you need a later check-out, I can ask the front desk to check availability."

    if any(word in text for word in ("service", "services", "laundry", "housekeeping", "room service", "wifi", "wi-fi", "maintenance")):
        services = ctx.get("services", [])
        if services:
            items = "\n".join(
                f"- {item['name']}" + (f" (₹{float(item['price']):.0f})" if float(item["price"]) > 0 else "")
                for item in services
            )
            return "Here are the services currently listed by the hotel:\n" + items + "\nTell me what you need and I can send a request to the team."
        return "I can help with food, housekeeping, and maintenance requests. Tell me what you need."

    if re.search(r"\b(hi|hello|hey|good morning|good evening)\b", text):
        guest = ctx.get("name", "")
        first = guest.split()[0] if guest else "there"
        return (f"Hello {first}! I can answer questions about the hotel, show the current food menu, "
                "suggest Tirupati temples and places to visit, or send a request or complaint to the staff. What can I help with?")

    return ("Our live AI assistant is temporarily unavailable, but I can still help with the hotel’s current food menu, "
            "housekeeping and maintenance, check-out, Tirupati temples and local places, or a request or complaint for staff. "
            "Tell me a little more about what you need.")


def assistant(message, lang, ctx, history=None):
    """Return (reply, request category, staff summary, used_gemini)."""
    menu = ctx.get("menu", [])
    services = ctx.get("services", [])
    safe_history = [
        {"role": item["role"], "content": str(item["content"])[:500]}
        for item in (history or [])[-8:]
        if isinstance(item, dict)
        and item.get("role") in ("user", "assistant")
        and item.get("content")
    ]
    sys = (
        f"You are StayGenius, the conversational guest concierge for a hotel in Tirupati, India. "
        f"Guest: {ctx.get('name')}. Room: {ctx.get('room') or 'not checked in'}; check-out is 11:00 AM. "
        f"Reply only in {LANG_NAMES.get(lang, 'English')}, naturally and directly, using prior turns for context. "
        f"Use only the supplied live menu and hotel service catalogue for hotel prices/services. "
        f"For Tirupati recommendations, you may suggest: {', '.join(PLACES)}. Do not invent distances, opening hours, "
        "darshan availability, hotel policies, or services; advise checking official TTD updates for current temple access. "
        "Answer informational questions without creating a request. Create an intent only when the guest explicitly asks "
        "staff to do something or reports a complaint/problem. Never claim a request was sent; the application confirms that. "
        "Return JSON with reply, intent (none|housekeeping|food|maintenance|complaint), and request_text (short English staff summary)."
    )
    prompt = json.dumps({
        "food_menu": menu,
        "hotel_services": services,
        "conversation_history": safe_history,
        "latest_guest_message": message
    }, ensure_ascii=False)
    raw = gemini(prompt, system=sys, as_json=True)
    if raw:
        try:
            j = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip()).strip())
            cat = j.get("intent") if j.get("intent") in INTENTS else None
            reply = str(j.get("reply", "")).strip()
            if reply:
                return reply, cat, str(j.get("request_text") or message)[:280], True
        except Exception:
            pass

    cat = _request_intent(message)
    reply = _local_guest_answer(message, ctx)
    if cat:
        return reply, cat, message[:280], False
    return reply, None, "", False


# ------------------------------ Personalised upsell ------------------------------
def upsell(user_id):
    prof = query("SELECT preferences FROM guest_profiles WHERE user_id=%s", (user_id,), one=True)
    prefs = set(filter(None, (prof["preferences"] if prof else "").split(",")))
    stays = query("SELECT COUNT(*) c FROM bookings WHERE guest_id=%s AND status='checked_out'", (user_id,), one=True)["c"]
    nxt = query("""SELECT b.check_in, b.check_out, rt.id type_id, rt.name type_name, rt.base_price FROM bookings b
                   JOIN rooms r ON r.id=b.room_id JOIN room_types rt ON rt.id=r.room_type_id
                   WHERE b.guest_id=%s AND b.status IN ('confirmed','checked_in') AND b.check_out>=CURDATE()
                   ORDER BY b.check_in LIMIT 1""", (user_id,), one=True)
    offers = []
    if "family" in prefs:
        offers.append((9, "Family darshan assistance", 900, "Help with special-entry ticket booking and a timed morning transfer.", "You travel with family"))
    if "vegetarian" in prefs:
        offers.append((8, "Satvik thali dinner", 350, "Freshly prepared pure-vegetarian thali delivered to your room.", "You prefer vegetarian food"))
    if "spa" in prefs:
        offers.append((8, "Ayurvedic massage (45 min)", 1500, "Relaxing after temple queues.", "You like spa and wellness"))
    if "early check-in" in prefs:
        offers.append((7, "Guaranteed early check-in", 500, "Room ready from 9 AM.", "You prefer early arrival"))
    if stays >= 2:
        offers.append((9, "Complimentary late check-out until 2 PM", 0, "Our thank-you for being a returning guest.", f"You have stayed with us {stays} times"))
    if nxt:
        up = query("SELECT id,name,base_price FROM room_types WHERE base_price>%s ORDER BY base_price LIMIT 1", (nxt["base_price"],), one=True)
        if up:
            diff = float(up["base_price"]) - float(nxt["base_price"])
            offers.append((7, f"Upgrade to {up['name']}", diff, "More space and a better view, per night, subject to availability.", f"Your booking is a {nxt['type_name']}"))
    offers += [(5, "Breakfast for two", 450, "Idli, dosa, pongal and filter coffee.", "Popular with guests heading to darshan"),
               (4, "Railway station / airport transfer", 700, "Fixed-price cab between Tirupati and the hotel.", "Popular with pilgrims")]
    offers.sort(key=lambda o: -o[0])
    return [{"title": t, "price": float(p), "description": d, "reason": r} for _, t, p, d, r in offers[:4]]
