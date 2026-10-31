# StayGenius AI

Guest experience and dynamic room pricing platform for a 120-room hotel in Tirupati (Codegnan hackathon, problem CCC-11, team 11 Code Cortex Crew).

Stack: HTML + CSS + JavaScript (frontend), Flask (backend), MySQL (database), scikit-learn + pandas (AI/ML), Google Gemini API (GenAI, optional).

## Run it in VS Code (Windows)

1. Install Python 3.10+ (tick "Add Python to PATH"), MySQL Server 8 and VS Code.
2. Unzip the project and open the `staygenius-ai` folder in VS Code (File > Open Folder).
3. Open a terminal in VS Code (Ctrl + `) and run:
   ```
   cd backend
   python -m venv venv
   venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
   pip install -r requirements.txt
   ```
4. Copy `backend/.env.example` to `backend/.env` and set `DB_PASSWORD` to your MySQL root password. Optional: paste a Gemini key in `GEMINI_API_KEY`.
   For Razorpay test checkout, set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_MODE=test`, and `PAYMENTS_REQUIRED=true` in `backend/.env`. Use a newly generated test secret; never commit `.env` or expose live credentials.
5. Make sure MySQL is running, then create the tables and synthetic data (takes about 20-60 seconds):
   ```
   python seed.py
   ```
   (Alternative: run `database/schema.sql` in MySQL Workbench, then `python seed.py`.)
   For an existing database, install the new dependency with `pip install -r requirements.txt` from `backend`, then run `database/razorpay_migration.sql` against the `staygenius` database. Do not rerun `seed.py` on a database with data because it recreates demo data.
6. Start the server:
   ```
   python app.py
   ```
7. Open http://localhost:5000 (app) and http://localhost:5000/apidocs (Swagger).

If you prefer VS Code Live Server for `frontend/index.html`, keep Flask running on port 5000; the frontend then calls `http://localhost:5000` (CORS is enabled).

## Demo logins

| Role | Email | Password |
|---|---|---|
| Guest | guest@staygenius.com | Guest@123 |
| Front office | frontdesk@staygenius.com | Admin@123 |
| Hotel manager | manager@staygenius.com | Admin@123 |
| Admin | admin@staygenius.com | Admin@123 |

## Requirements checklist

| Requirement | Where |
|---|---|
| Secure login, role-based access (4 roles) | `app.py` `auth()` decorator, hashed passwords, signed expiring tokens, login throttling |
| Room inventory and booking | `/api/room-types`, `/api/rooms`, `/api/availability`, `/api/bookings` (row-locked transaction prevents double booking) |
| Check-in / check-out with room status | Front office > Arrivals and stays; room status board |
| In-stay service requests | Guest > My stays > Request a service; staff queue |
| Guest feedback | Guest > Leave feedback |
| Guest profiles with stay history and preferences | `guest_profiles`, My preferences, booking history |
| Room status board | Room board (vacant, occupied, cleaning, maintenance) |
| Invoice at check-out | `POST /api/bookings/<id>/checkout` (GST 12% rooms, 5% services) |
| 2+ AI features | Occupancy forecast (GradientBoosting), dynamic pricing, review sentiment/theme NLP |
| 2+ GenAI features | Review reply drafting, review insight summary, multilingual concierge that raises requests |
| Admin dashboard | Occupancy, ADR, RevPAR, revenue by month and room type, operations |
| Synthetic data only | `seed.py` generates everything |
| Bonus | Multilingual assistant (EN/HI/TE/TA/KN/ML), personalised upsell offers, housekeeping scheduling |

## AI notes

- Forecast: `ai.py` trains a GradientBoostingRegressor on daily occupancy (day of week, month, day of year, festival flag) from the bookings table. The forecast never drops below rooms already booked.
- Pricing: forecast occupancy maps to -20% ... +30%, plus 10% on festival dates, capped at 70%-160% of base price. The manager approves prices; approved prices are stored in `price_overrides` and shown to guests.
- GenAI uses Gemini when `GEMINI_API_KEY` is set; otherwise rule-based fallbacks keep every screen working. If your Gemini model name is rejected, change `GEMINI_MODEL` in `.env`.
- The festival calendar is an approximate demo calendar, not official dates.

## Project layout

```
backend/   app.py (API) · ai.py (AI/GenAI) · db.py · seed.py · requirements.txt · .env.example
frontend/  index.html · css/style.css · js/app.js
database/  schema.sql
docs/      architecture.md · presentation-outline.md
```
