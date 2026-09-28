```markdown
# ⚖️ Self-Hosted Multi-User Weight Tracker PWA

A lightweight, mobile-first Progressive Web App (PWA) built with **Python Flask**, **SQLite**, and **Chart.js**. Designed to run as a persistent background service on a **Raspberry Pi** and accessed remotely from anywhere via **Tailscale**.

---

## ✨ Features

- **Multi-User Architecture:** Separate profiles for personal and family use with isolated weight logs, goals, unit preferences (`lbs`/`kg`), and target calculations.
- **PIN-Based Authentication:** Profile login secured via PBKDF2-HMAC (SHA-256) password hashing with unique per-user salts.
- **Mobile-First PWA UI:** Dark/Light theme support, quick logging, and interactive charts featuring 7-day moving averages.
- **Goal Pace Calculator:** Dynamic feedback based on target completion date, required weekly loss velocity, and current trajectory.
- **Remote Mobile Access:** Secure cross-network access via Tailscale without exposing public router ports or port forwarding.
- **Automated Service Management:** Powered by `systemd` for auto-start on Raspberry Pi boot and automatic crash recovery.

---

## 🛠️ Prerequisites & Requirements

### Hardware & System
- **Device:** Raspberry Pi running Raspberry Pi OS or Debian Linux
- **Runtime:** Python 3.9+
- **Network:** Local home network + Tailscale mesh network

### Dependencies
- **Python Packages:** `flask`, `gunicorn`
- **Frontend Assets:** `Chart.js` (loaded via CDN)
- **Built-in Standard Libraries:** `sqlite3`, `hashlib`, `os`, `datetime`, `functools`

---

## 🚀 Installation & Setup Guide on Raspberry Pi

### 1. Project Directory & Files

Ensure your project files are located in `/home/ssmith/weight-tracker`:


```

cd /home/ssmith/weight-tracker

```

Expected directory structure:

```

weight-tracker/
├── app.py
├── weight.db
├── templates/
│   ├── index.html
│   └── login.html
└── README.md

```

---

### 2. Create Virtual Environment & Install Dependencies

Set up an isolated Python virtual environment and install `flask` and `gunicorn`:


```

cd /home/ssmith/weight-tracker

# Create virtual environment

python3 -m venv venv

# Activate virtual environment

source venv/bin/activate

# Upgrade pip & install packages

pip install --upgrade pip
pip install flask gunicorn

```

---

### 3. Initialize Profiles and Database

Initialize the database schema and default profiles (**Sean** and **Wife**) with default PIN **`1234`**:


```

source /home/ssmith/weight-tracker/venv/bin/activate
python3 -c "import app; app.init_db_users()"

```

> **Security Note:** After logging into each profile for the first time, open **⚙️ Settings** on the dashboard to set a custom 4-digit PIN.

---

### 4. Configure systemd Service for Auto-Start on Boot

Create the systemd service file:


```

sudo nano /etc/systemd/system/weight-tracker.service

```

Paste the following configuration:


```

[Unit]
Description=Weight Tracker Flask Service
After=network.target

[Service]
User=ssmith
WorkingDirectory=/home/ssmith/weight-tracker
ExecStart=/home/ssmith/weight-tracker/venv/bin/gunicorn --workers 2 --bind 0.0.0.0:5001 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

```

Enable and start the background service:


```

sudo systemctl daemon-reload
sudo systemctl enable weight-tracker.service
sudo systemctl restart weight-tracker.service
sudo systemctl status weight-tracker.service

```

---

### 5. Tailscale Remote Mobile Access Setup

To access the app securely from your phone over cellular or external Wi-Fi:

#### On the Raspberry Pi:
1. Verify Tailscale is running and retrieve your Pi's Tailscale IP:

```

tailscale status
tailscale ip -4

```

#### On Your Mobile Device:
1. Install the **Tailscale app** from the App Store or Google Play Store.
2. Log into the same account connected to your Pi.
3. Turn on Tailscale on your phone.
4. Access the web app in your mobile browser at:

```

http://:5001

```
*(Or `http://wkshop:5001` if MagicDNS is enabled).*

---

## 🔒 Recommended `.gitignore`

When pushing this project to GitHub, ensure the database and local environment files are ignored:


```

# Python virtual environments

venv/
.venv/
env/

# Databases

*.db
*.sqlite3

# Python cache

**pycache**/
*.py[cod]

# System files

.DS_Store

```

---

## 📄 License

Distributed under the MIT License. Personal homebrew project for individual and family health tracking.

```
