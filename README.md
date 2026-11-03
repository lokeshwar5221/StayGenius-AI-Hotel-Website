# 🏨 StayGenius AI – Smart Hotel Management & Guest Experience Platform

**An AI-powered hotel management platform designed to simplify hotel operations, enhance guest experiences, and optimize room pricing through intelligent automation.**

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python" />
  <img src="https://img.shields.io/badge/Flask-Backend-black?logo=flask" />
  <img src="https://img.shields.io/badge/MySQL-Database-blue?logo=mysql" />
  <img src="https://img.shields.io/badge/AI%2FML-Scikit--Learn-orange" />
  <img src="https://img.shields.io/badge/GenAI-Google%20Gemini-purple" />
  <img src="https://img.shields.io/badge/Status-Development-success" />
</p>

---

## 📌 Project Overview

StayGenius AI is a smart hotel management and guest experience platform developed to modernize hotel operations through Artificial Intelligence, Machine Learning, and Generative AI.

The platform is designed for a 120-room hotel in Tirupati, providing an integrated solution for room reservations, guest management, staff operations, billing, dynamic pricing, and AI-powered guest assistance.

It helps hotel administrators manage daily activities efficiently while providing guests with a smooth, personalized, and convenient hotel experience.

## 🎯 Project Objectives

- Automate hotel management operations.
- Simplify room booking and reservation management.
- Provide secure authentication with role-based access.
- Improve revenue through AI-powered dynamic room pricing.
- Predict hotel occupancy using Machine Learning.
- Analyze guest reviews using sentiment analysis.
- Provide multilingual AI-powered guest assistance.
- Streamline housekeeping and hotel service requests.
- Generate invoices and manage payments.

## ✨ Key Features

### 1. 🔐 Authentication & Role-Based Access
- Secure user authentication.
- Four different user roles:
  - Guest
  - Front Office Staff
  - Hotel Manager
  - Administrator
- Password hashing and signed, expiring authentication tokens.
- Login throttling.

### 2. 🛏️ Room & Booking Management
- View available rooms and room types.
- Check room availability.
- Create and manage reservations.
- Prevent double bookings using database transactions.
- Manage check-in and check-out operations.
- Maintain room availability and booking history.

### 3. 📊 AI-Powered Occupancy Forecasting
- Predict future hotel occupancy using Machine Learning.
- Uses Gradient Boosting Regression.
- Considers historical bookings, weekdays, months, and festival dates.
- Helps hotel managers make better operational decisions.

### 4. 💰 Dynamic Room Pricing
- AI-powered room price optimization.
- Adjust room prices based on predicted occupancy.
- Consider festival dates and demand.
- Manager approval for suggested prices.
- Store approved pricing changes in the database.

### 5. 🤖 AI Hotel Concierge
- AI-powered guest assistance using Google Gemini.
- Multilingual guest communication.
- Supports English, Hindi, Telugu, Tamil, Kannada, and Malayalam.
- Answers guest questions.
- Helps guests submit hotel service requests.
- Provides personalized guest assistance.

### 6. ⭐ Guest Feedback & Sentiment Analysis
- Collect guest reviews and feedback.
- Analyze review sentiment and common themes.
- Generate AI-assisted review replies.
- Summarize guest feedback to help improve hotel services.

### 7. 🧹 Hotel Service Management
- Guests can submit in-stay service requests.
- Housekeeping request management.
- Food and other service requests.
- Staff can view and manage pending requests.
- Track room status:
  - Vacant
  - Occupied
  - Cleaning
  - Maintenance

### 8. 🧾 Billing & Payment Management
- Generate invoices during checkout.
- Calculate applicable GST.
- Integrate Razorpay payment gateway.
- Support Razorpay test-mode checkout.
- Manage hotel billing and payment records.

### 9. 📈 Admin Dashboard
- Hotel occupancy overview.
- Average Daily Rate (ADR).
- Revenue per Available Room (RevPAR).
- Monthly revenue analysis.
- Room-type revenue insights.
- Hotel operations monitoring.

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Frontend | HTML5, CSS3, JavaScript |
| Backend | Python, Flask |
| Database | MySQL |
| AI / Machine Learning | Scikit-learn, Pandas, NumPy |
| Generative AI | Google Gemini API |
| Authentication | JWT, Password Hashing |
| Payment Gateway | Razorpay |
| API Documentation | Swagger |
| Database Hosting | Aiven MySQL |
| Version Control | Git, GitHub |

## 📂 Project Structure

```text
StayGenius-AI-Hotel-Website/
│
├── backend/
│   ├── app.py
│   ├── ai.py
│   ├── db.py
│   ├── seed.py
│   ├── requirements.txt
│   ├── .env.example
│   └── concierge.py
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── database/
│   ├── schema.sql
│   └── razorpay_migration.sql
│
├── docs/
│   ├── architecture.md
│   └── presentation-outline.md
│
├── .gitignore
└── README.md
```

## ⚙️ Installation & Setup

### Prerequisites

Install the following before running the project:

- Python 3.10 or above
- MySQL Server or Aiven MySQL
- Visual Studio Code
- Git
- Google Gemini API Key (optional)
- Razorpay API Keys (for payment integration)

### Step 1: Clone the Repository

```bash
git clone https://github.com/lokeshwar5221/StayGenius-AI-Hotel-Website.git
```

Navigate into the project:

```bash
cd StayGenius-AI-Hotel-Website
```

### Step 2: Create a Virtual Environment

```bash
cd backend
python -m venv venv
```

Activate the environment:

**Windows:**
```bash
venv\Scripts\activate
```

**Mac/Linux:**
```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
python -m pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file inside the `backend` folder.

Copy the configuration from `.env.example` and provide your credentials.

Example configuration:

```env
SECRET_KEY=your_secret_key

DB_HOST=your_mysql_host
DB_PORT=your_mysql_port
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_NAME=staygenius

GEMINI_API_KEY=your_gemini_api_key

RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_MODE=test
PAYMENTS_REQUIRED=true
```

**Important:** Never upload your `.env` file or API credentials to GitHub.

### Step 5: Initialize the Database

Make sure your MySQL database is running and configured correctly.

Run:

```bash
python seed.py
```

This creates the required database tables and inserts synthetic hotel data for demonstration.

**Note:** Do not rerun the seed script on a database containing important existing data.

### Step 6: Start the Backend Server

```bash
python app.py
```

The Flask application will run at:

```text
http://localhost:5000
```

### Step 7: Access the Application

Open your browser and visit:

**Application:**
http://localhost:5000

**Swagger API Documentation:**
http://localhost:5000/apidocs

---

## 🔑 Demo Login Credentials

| Role | Email | Password |
|---|---|---|
| Guest | guest@staygenius.com | Guest@123 |
| Front Office | frontdesk@staygenius.com | Admin@123 |
| Hotel Manager | manager@staygenius.com | Admin@123 |
| Admin | admin@staygenius.com | Admin@123 |

*These are demonstration credentials. Change them before any production deployment.*

## 🧠 AI & Machine Learning Implementation

| AI Feature | Algorithm / Technology | Purpose |
|---|---|---|
| Occupancy Forecasting | Gradient Boosting Regressor | Predict hotel occupancy |
| Dynamic Pricing | ML-based demand adjustment | Optimize room prices |
| Sentiment Analysis | NLP | Understand guest feedback |
| Review Reply Generation | Google Gemini | Generate review responses |
| Guest Concierge | Google Gemini | Provide multilingual assistance |

The application also includes rule-based fallback functionality when the Gemini API is not configured.

## ☁️ Deployment & Cloud Configuration

The project is designed to support cloud deployment using:

- **Backend:** Python Flask hosting platform.
- **Database:** Aiven MySQL.
- **AI Integration:** Google Gemini API.
- **Payment Integration:** Razorpay.

Environment variables must be configured securely in the deployment platform.

## 🚀 Future Enhancements

- Online hotel booking with real-time availability.
- Enhanced AI-powered personalized recommendations.
- Advanced revenue forecasting.
- Email and SMS booking notifications.
- Interactive hotel analytics dashboard.
- Integration with additional payment methods.
- Improved mobile-responsive guest interface.
- Advanced hotel recommendation engine.

## 👨‍💻 Project Information

**Project Name:** StayGenius AI – Smart Hotel Management & Guest Experience Platform

**Domain:** Artificial Intelligence | Machine Learning | Web Development | Hotel Management

**Hackathon:** Codegnan Hackathon

**Problem Statement:** CCC-11

**Team:** 11 – Code Cortex Crew

**Location:** Tirupati, Andhra Pradesh, India

## 👨‍💻 Developer

**GitHub:** [lokeshwar5221](https://github.com/lokeshwar5221)

**Project Repository:** [StayGenius AI Hotel Website](https://github.com/lokeshwar5221/StayGenius-AI-Hotel-Website)

---

## ⭐ Support

If you find this project interesting, consider giving the repository a ⭐ on GitHub!

**StayGenius AI – Making Hotel Management Smarter, Faster, and Better with AI.** 🏨🤖
