# F1 Database Web Application (FastAPI + Firebase + Firestore + Cloud Storage)

This project is a Formula 1-themed web application built using:

- **Python**
- **FastAPI** (web framework)
- **Firebase Authentication** (login/signup)
- **Firestore** (NoSQL database)
- **Google Cloud Storage Bucket** (image/BLOB storage)
- **Bootstrap 5** (styling)

---

## Features

### Authentication
- Users can **sign up / log in** using **Firebase Authentication**
- A valid Firebase token is stored in a cookie
- Backend validates token before allowing protected actions

### Drivers
- View all drivers
- Add driver *(login required)*
- Edit driver *(login required)*
- Delete driver *(login required, deletes associated driver image if not placeholder)*
- Query drivers using Firestore filters
- Driver images:
  - user can upload an image
  - if no image uploaded → placeholder image is used

### Teams
- View all teams
- Add team *(login required)*
- Edit team *(login required)*
- Delete team *(login required, deletes associated logo if not placeholder)*
- Query teams using Firestore filters
- Team logos:
  - upload optional
  - placeholder used otherwise

### Other
- Compare two drivers
- Compare two teams
- Highlight stats in comparison tables
- Home page carousel using images stored in Cloud Storage
- Seed sample data auto-loads on startup (if database is empty)

---

## Project Structure

```
project01/
│
├── main.py
├── local_constants.py
├── requirements.txt
├── README.md
│
├── static/
│   ├── styles.css
│   ├── firebase-login.js
│
└── templates/
    ├── base.html
    ├── main.html
    ├── login.html
    ├── drivers_list.html
    ├── driver_details.html
    ├── add_driver.html
    ├── edit_driver.html
    ├── teams_list.html
    ├── team_details.html
    ├── add_team.html
    ├── edit_team.html
    ├── query_drivers.html
    ├── query_teams.html
    ├── compare_drivers_form.html
    ├── compare_drivers.html
    ├── compare_teams_form.html
    ├── compare_teams.html
```

---

## Requirements

- Python 3.10+
- Google Cloud SDK *(optional but useful)*
- Firebase project created
- Firestore enabled
- Cloud Storage bucket created

---

##  How to Run Locally (Step-by-Step)

### 1) Clone / Download project

```bash
git clone <REPO_URL>
cd <path to project>
```

---

### 2) Create a Python virtual environment

**Mac/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv venv
venv\Scripts\activate
```

---

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4) Create `local_constants.py`

Create a file called **local_constants.py** in the root folder:

```python
PROJECT_NAME = "project01-453218"
PROJECT_STORAGE_BUCKET = "project01-453218.appspot.com"
```

 Your values must match your Firebase/GCP project settings.

---

### 5) Configure Google Cloud authentication (Service Account)

Create a **Service Account** in Google Cloud:
- IAM & Admin → Service Accounts
- Create service account
- Create key → JSON
- Download JSON file (DO NOT PUSH TO GITHUB)

Then export credentials environment variable:

**Mac/Linux**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/full/path/to/service-account.json"
```

**Windows (PowerShell)**
```powershell
setx GOOGLE_APPLICATION_CREDENTIALS "C:\full\path\service-account.json"
```

Restart terminal after `setx`.

Verify:
```bash
echo $GOOGLE_APPLICATION_CREDENTIALS
```

---

### 6) Setup Firestore
- Firebase Console → Firestore Database → Create Database
- Use **production/test mode** depending project needs

Collections used:
- `drivers`
- `teams`
- `users`

---

### 7) Setup Cloud Storage
Upload these assets to your bucket:
- carousel images: `carousel.jpg`, `carousel2.jpg`, `carousel3.png`
- placeholder images:
  - `placeholder.png` (driver placeholder)
  - `placeholder-team.png` (team placeholder)

Make them public or configure signed URLs.

---

### 8) Run the application

```bash
uvicorn main:app --reload --port 8000
```

Then open:
```
http://localhost:8000
```

---

## Firebase Authentication Setup

In `static/firebase-login.js` update this section:

```js
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
};
```

 These values come from:
Firebase Console → Project Settings → Web App Config

---

## Seed Sample Data

On app startup, `seed_sample_data()` checks if Firestore is empty and inserts:
- sample teams
- sample drivers
with valid Cloud Storage image URLs

---


## Author

**Wesley Openda**  
F1 Database FastAPI Web Application