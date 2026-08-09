from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import numpy as np
import mysql.connector
from mysql.connector import Error as MySQLError
import pickle
import requests
import re
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sleep-ai-fyp-dev-secret-change-in-production")


#Configuration
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "haiderali962005"),
    "database": os.environ.get("DB_NAME", "sleep_ai_fyp_db"),
}
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral"

# Feature order MUST match the order used in train_models.py
FEATURE_KEYS = ["Age", "Sleep Hours", "Screen Time", "Caffeine Intake", "Physical Activity"]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_REGEX = re.compile(r"^[0-9+\-\s()]{7,20}$")

#Database
def get_db():
    """Open a fresh MySQL connection per call.

    Using a new connection per request (instead of one long-lived global
    connection/cursor) avoids the classic "MySQL server has gone away"
    errors that happen when a shared connection times out.
    """
    return mysql.connector.connect(**DB_CONFIG)


def init_db():
    """Create tables if they don't exist yet, and migrate older installs of
    this project (which used a different `predictions` schema: stress /
    blood-pressure columns, no user accounts, no sleep_score, etc.).

    This checks the ACTUAL current columns via INFORMATION_SCHEMA and only
    adds the ones that are truly missing. The previous approach blindly ran
    ALTER TABLE ... ADD COLUMN and silently swallowed any failure - if that
    ever failed for a reason other than "column already exists" (wrong
    privileges, a typo, an old MySQL version, etc.), the predictions table
    would be left without a required column FOREVER, and every single
    prediction save would then fail silently afterward (the app kept
    showing "success" in the browser because the ML/AI result itself was
    computed fine - only the database INSERT was quietly failing). This
    version prints exactly what it finds and what it adds, and raises
    loudly on unexpected errors instead of hiding them.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            age INT,
            email VARCHAR(150) UNIQUE NOT NULL,
            phone VARCHAR(20),
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            age FLOAT,
            sleep_hours FLOAT,
            screen_time FLOAT,
            caffeine FLOAT,
            physical FLOAT,
            sleep_score FLOAT,
            final_prediction VARCHAR(20),
            ai_analysis LONGTEXT,
            recommendations LONGTEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()

    # Required columns for the CURRENT schema, with the DDL fragment used
    # to add each one if it's missing from an older install.
    required_columns = {
        "user_id": "INT",
        "age": "FLOAT",
        "sleep_hours": "FLOAT",
        "screen_time": "FLOAT",
        "caffeine": "FLOAT",
        "physical": "FLOAT",
        "sleep_score": "FLOAT",
        "final_prediction": "VARCHAR(20)",
        "ai_analysis": "LONGTEXT",
        "recommendations": "LONGTEXT",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }

    cur.execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'predictions'
        """,
        (DB_CONFIG["database"],),
    )
    existing_columns = {row[0] for row in cur.fetchall()}

    missing = {name: ddl for name, ddl in required_columns.items() if name not in existing_columns}

    if missing:
        print(f"Migrating 'predictions' table - adding missing columns: {list(missing.keys())}")
        for name, ddl in missing.items():
            cur.execute(f"ALTER TABLE predictions ADD COLUMN {name} {ddl}")
            conn.commit()
            print(f"  Added column '{name}'.")
    else:
        print("'predictions' table schema is up to date.")

    # Verify the migration actually worked - if a required column is still
    # missing at this point, fail loudly instead of letting every future
    # INSERT fail silently.
    cur.execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'predictions'
        """,
        (DB_CONFIG["database"],),
    )
    final_columns = {row[0] for row in cur.fetchall()}
    still_missing = [name for name in required_columns if name not in final_columns]
    if still_missing:
        cur.close()
        conn.close()
        raise MySQLError(
            f"Migration failed - 'predictions' table is still missing columns {still_missing} "
            f"after ALTER TABLE. Check that the DB user has ALTER privileges on "
            f"'{DB_CONFIG['database']}'."
        )

    cur.close()
    conn.close()


def verify_predictions_schema():
    """Runs on startup (after init_db) purely to give an unmistakable,
    human-readable confirmation in the console of whether prediction saving
    will actually work - so schema problems are obvious immediately rather
    than discovered later as "nothing shows up on the dashboard".
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'predictions'
        """,
        (DB_CONFIG["database"],),
    )
    columns = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()
    required = {"user_id", "sleep_score", "final_prediction", "ai_analysis", "recommendations"}
    missing = required - columns
    if missing:
        print(f"WARNING: predictions table is missing columns {missing} - saving predictions WILL FAIL.")
    else:
        print("Prediction saving is ready: 'predictions' table has all required columns.")


db_available = True
try:
    init_db()
    verify_predictions_schema()
    print("Database connected and initialized successfully.")
except Exception as e:
    db_available = False
    print(f"Database connection error: {e}")
    print("The app will still run, but login/register/history features need a working MySQL connection.")

#Load trained models

models_available = True
try:
    with open("sleep_models_v3.pkl", "rb") as f:
        models = pickle.load(f)
    with open("label_encoder_v3.pkl", "rb") as f:
        encoder = pickle.load(f)
    model_names = list(models.keys())
    print("Models loaded successfully!")
except Exception as e:
    models_available = False
    models, encoder, model_names = {}, None, []
    print(f"Model loading error: {e}")



# Auth helpers
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated



# AI analysis / scoring engine
def calculate_sleep_score(features, final_prediction):
    """Deterministic 0-100 sleep quality score derived from lifestyle inputs,
    lightly blended with the ensemble's predicted class so the number and
    the label stay consistent with each other.
    """
    age = features["Age"]
    sleep = features["Sleep Hours"]
    screen = features["Screen Time"]
    caffeine = features["Caffeine Intake"]
    activity = features["Physical Activity"]

    if age < 18:
        ideal_low, ideal_high = 8, 10
    elif age < 65:
        ideal_low, ideal_high = 7, 9
    else:
        ideal_low, ideal_high = 7, 8

    if ideal_low <= sleep <= ideal_high:
        sleep_component = 40
    else:
        diff = (ideal_low - sleep) if sleep < ideal_low else (sleep - ideal_high)
        sleep_component = max(0, 40 - diff * 8)

    screen_component = max(0, 20 - screen * 2)
    caffeine_component = max(0, 15 - caffeine * 3)

    if 3 <= activity <= 8:
        activity_component = 25
    elif activity < 3:
        activity_component = (activity / 3) * 25
    else:
        activity_component = max(10, 25 - (activity - 8) * 1.5)

    raw_score = sleep_component + screen_component + caffeine_component + activity_component
    raw_score = max(0, min(100, raw_score))

    label_base = {"Good": 85, "Average": 60, "Poor": 35}.get(final_prediction, 50)
    final_score = (raw_score * 0.6) + (label_base * 0.4)
    return round(max(0, min(100, final_score)), 1)


def generate_ai_analysis(features, final_prediction, sleep_score):
    """Rule-based explanation engine. Always available (no network needed),
    so the dashboard always has something meaningful to show even if the
    optional local LLM (Ollama) is offline.
    """
    sleep = features["Sleep Hours"]
    screen = features["Screen Time"]
    caffeine = features["Caffeine Intake"]
    activity = features["Physical Activity"]

    factors = []

    if sleep < 6:
        factors.append({"name": "Sleep Duration", "status": "negative",
                         "detail": f"You are averaging only {sleep} hours per night, below the recommended range, which can affect recovery and focus."})
    elif sleep > 9:
        factors.append({"name": "Sleep Duration", "status": "warning",
                         "detail": f"You are sleeping {sleep} hours per night, more than most adults need, which can sometimes point to lower sleep efficiency."})
    else:
        factors.append({"name": "Sleep Duration", "status": "positive",
                         "detail": f"Your {sleep} hours of sleep falls within a healthy range."})

    if screen > 6:
        factors.append({"name": "Screen Time", "status": "negative",
                         "detail": f"{screen} hours of daily screen time is high; blue light exposure before bed can delay your body's natural sleep signal."})
    elif screen > 3:
        factors.append({"name": "Screen Time", "status": "warning",
                         "detail": f"{screen} hours of screen time is moderate; cutting evening use could still help you fall asleep faster."})
    else:
        factors.append({"name": "Screen Time", "status": "positive",
                         "detail": f"Your screen time of {screen} hours per day is well controlled."})

    if caffeine > 3:
        factors.append({"name": "Caffeine Intake", "status": "negative",
                         "detail": f"{caffeine} cups per day is high; caffeine can linger in your system for hours and disrupt deep sleep."})
    elif caffeine > 1:
        factors.append({"name": "Caffeine Intake", "status": "warning",
                         "detail": f"{caffeine} cups per day is moderate; try to have your last cup earlier in the day."})
    else:
        factors.append({"name": "Caffeine Intake", "status": "positive",
                         "detail": "Your low caffeine intake is supporting healthy sleep."})

    if activity < 2:
        factors.append({"name": "Physical Activity", "status": "negative",
                         "detail": f"Only {activity} hours of activity per week is low; regular exercise is strongly linked to deeper sleep."})
    elif activity > 12:
        factors.append({"name": "Physical Activity", "status": "warning",
                         "detail": f"{activity} hours per week is a lot of activity; avoid intense workouts too close to bedtime."})
    else:
        factors.append({"name": "Physical Activity", "status": "positive",
                         "detail": f"Your activity level of {activity} hours per week is supporting your sleep quality."})

    summaries = {
        "Good": f"Your predicted sleep quality is Good, with a score of {sleep_score}/100. Your habits around sleep duration, screen time, caffeine, and activity are largely well balanced.",
        "Average": f"Your predicted sleep quality is Average, with a score of {sleep_score}/100. A few adjustments to your daily habits could meaningfully improve your rest.",
        "Poor": f"Your predicted sleep quality is Poor, with a score of {sleep_score}/100. Several lifestyle factors appear to be working against restful sleep right now.",
    }
    summary = summaries.get(final_prediction, f"Your predicted sleep quality is {final_prediction}, with a score of {sleep_score}/100.")

    return {"summary": summary, "factors": factors}


def rule_based_recommendations(features, final_prediction):
    sleep = features["Sleep Hours"]
    screen = features["Screen Time"]
    caffeine = features["Caffeine Intake"]
    activity = features["Physical Activity"]

    recs = []
    if sleep < 7:
        recs.append("Gradually extend your sleep toward 7-9 hours by moving your bedtime 15-20 minutes earlier each night.")
    if sleep > 9:
        recs.append("Set a consistent wake-up time, even on weekends, to help regulate your sleep cycle.")
    if screen > 3:
        recs.append("Avoid screens for 30-60 minutes before bed, or enable night mode / a blue-light filter in the evening.")
    if caffeine > 1:
        recs.append("Limit caffeine after early afternoon so it doesn't interfere with falling asleep.")
    if activity < 3:
        recs.append("Add light to moderate exercise, such as a 20-30 minute walk, on most days to improve sleep depth.")
    if activity > 10:
        recs.append("Schedule intense workouts earlier in the day, leaving at least 3 hours before bedtime.")
    recs.append("Keep a consistent sleep schedule and a relaxing pre-sleep routine to reinforce healthy sleep patterns.")

    # de-duplicate while preserving order, cap at 5
    seen = set()
    unique = []
    for r in recs:
        if r not in seen:
            unique.append(r)
            seen.add(r)
    return unique[:5]


def generate_recommendations(features, final_prediction):
    """Try the local LLM (Ollama) for richer, personalized phrasing; always
    fall back to the deterministic rule-based recommendations if Ollama is
    unavailable, slow, or returns something unusable.
    """
    fallback = rule_based_recommendations(features, final_prediction)

    prompt = f"""You are a sleep health assistant. Based on this user's data, write 4-5 short, specific, and actionable recommendations to improve their sleep quality. One recommendation per line, no numbering, no preamble, no extra commentary.

User data:
- Age: {features.get('Age')} years
- Sleep Hours: {features.get('Sleep Hours')} hours/night
- Screen Time: {features.get('Screen Time')} hours/day
- Caffeine Intake: {features.get('Caffeine Intake')} cups/day
- Physical Activity: {features.get('Physical Activity')} hours/week
- Predicted Sleep Quality: {final_prediction}

Recommendations:"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "temperature": 0.7},
            timeout=60,
        )
        print(f"DEBUG Ollama status: {response.status_code}")
        if response.status_code == 200:
            text = response.json().get("response", "").strip()
            lines = [re.sub(r"^[\-\u2022\*\d\.\)\s]+", "", ln).strip() for ln in text.split("\n")]
            lines = [ln for ln in lines if len(ln) > 8]
            print(f"DEBUG Ollama lines parsed: {len(lines)}")
            if lines:
                return lines[:5], True
    except requests.exceptions.RequestException as e:
        print(f"DEBUG Ollama connection error: {e}")
    except Exception as e:
        print(f"DEBUG Ollama other error: {e}")

    return fallback, False



def format_db_datetime(value, fmt):
    """MySQL TIMESTAMP columns normally come back as datetime objects, but
    depending on connector/config they can arrive as strings. Handle both
    so date formatting never crashes a page.
    """
    if value is None:
        return "-"
    if isinstance(value, str):
        for candidate_fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
            try:
                value = datetime.strptime(value, candidate_fmt)
                break
            except ValueError:
                continue
        else:
            return value
    try:
        return value.strftime(fmt)
    except (AttributeError, ValueError):
        return str(value)


def get_insight_message(sleep_quality):
    messages = {
        "Poor": "Your sleep needs attention. Small, consistent changes can make a big difference.",
        "Average": "You're on the right track. A few tweaks could take your sleep from good to great.",
        "Good": "Great job! Your current routine is supporting healthy sleep, keep it up.",
    }
    return messages.get(sleep_quality, "Keep working toward better sleep.")



# Auth routes
@app.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        age = (request.form.get("age") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not EMAIL_REGEX.match(email):
            errors.append("Please enter a valid email address.")
        if not age.isdigit() or not (1 <= int(age) <= 120):
            errors.append("Please enter a valid age between 1 and 120.")
        if not PHONE_REGEX.match(phone):
            errors.append("Please enter a valid phone number.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form_data=request.form)

        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
            if cur.fetchone():
                flash("That username or email is already registered.", "error")
                cur.close()
                conn.close()
                return render_template("register.html", form_data=request.form)

            password_hash = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (username, age, email, phone, password_hash) VALUES (%s,%s,%s,%s,%s)",
                (username, int(age), email, phone, password_hash),
            )
            conn.commit()
            cur.close()
            conn.close()
            flash("Registration successful. Please log in to continue.", "success")
            return redirect(url_for("login"))
        except MySQLError as e:
            flash(f"Database error: {e}", "error")
            return render_template("register.html", form_data=request.form)

    return render_template("register.html", form_data={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT * FROM users WHERE username=%s OR email=%s",
                (identifier, identifier.lower()),
            )
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("dashboard"))

            flash("Invalid username/email or password.", "error")
        except MySQLError as e:
            flash(f"Database error: {e}", "error")

        return render_template("login.html")

    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))



# App routes

@app.route("/home")
@login_required
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
@login_required
def predict():
    """API endpoint for predictions. Runs the internal 5-model ensemble but
    only ever returns ONE unified result to the client.
    """
    try:
        data = request.form or request.json or {}

        features = {
            "Age": float(data.get("Age", 0)),
            "Sleep Hours": float(data.get("Sleep Hours", 0)),
            "Screen Time": float(data.get("Screen Time", 0)),
            "Caffeine Intake": float(data.get("Caffeine Intake", 0)),
            "Physical Activity": float(data.get("Physical Activity", 0)),
        }
        X_input = np.array([features[k] for k in FEATURE_KEYS]).reshape(1, -1)

        # Internal ensemble (majority vote) - individual model outputs are
        # intentionally never exposed to the client.
        votes = {}
        for name, model in models.items():
            pred_num = model.predict(X_input)[0]
            votes[name] = encoder.inverse_transform([pred_num])[0]

        final_prediction = str(max(set(votes.values()), key=list(votes.values()).count))
        sleep_score = calculate_sleep_score(features, final_prediction)
        analysis = generate_ai_analysis(features, final_prediction, sleep_score)
        recommendations, llm_used = generate_recommendations(features, final_prediction)
        insight = get_insight_message(final_prediction)

        saved = False
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO predictions
                (user_id, age, sleep_hours, screen_time, caffeine, physical,
                 sleep_score, final_prediction, ai_analysis, recommendations, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    session.get("user_id"),
                    features["Age"],
                    features["Sleep Hours"],
                    features["Screen Time"],
                    features["Caffeine Intake"],
                    features["Physical Activity"],
                    sleep_score,
                    final_prediction,
                    analysis["summary"],
                    " | ".join(recommendations),
                    datetime.now(),
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
            saved = True
        except Exception as db_error:
            import traceback
            print(f"PREDICTION SAVE FAILED for user_id={session.get('user_id')}: {db_error}")
            traceback.print_exc()

        print(f"DEBUG about to send to browser - llm_used: {llm_used}, recommendations count: {len(recommendations)}")
        return jsonify({
            "success": True,
            "final_prediction": final_prediction,
            "sleep_score": sleep_score,
            "analysis": analysis,
            "recommendations": recommendations,
            "llm_used": llm_used,
            "insight": insight,
            "saved": saved,
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    

@app.route("/results")
@login_required
def results():
    return render_template("result.html")


@app.route("/dashboard")
@login_required
def dashboard():
    history = []
    stats = {"total_predictions": 0, "avg_sleep_hours": 0, "good_sleep_count": 0, "avg_score": 0}

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM predictions WHERE user_id=%s ORDER BY id DESC LIMIT 10",
            (session["user_id"],),
        )
        history = cur.fetchall()
        for row in history:
            row["created_at_display"] = format_db_datetime(row.get("created_at"), "%b %d, %Y")

        cur.execute(
            """
            SELECT COUNT(*) AS total,
                   AVG(sleep_hours) AS avg_sleep,
                   AVG(sleep_score) AS avg_score,
                   SUM(CASE WHEN final_prediction='Good' THEN 1 ELSE 0 END) AS good_count
            FROM predictions WHERE user_id=%s
            """,
            (session["user_id"],),
        )
        row = cur.fetchone()
        if row and row["total"]:
            stats = {
                "total_predictions": row["total"],
                "avg_sleep_hours": round(float(row["avg_sleep"] or 0), 1),
                "good_sleep_count": row["good_count"] or 0,
                "avg_score": round(float(row["avg_score"] or 0), 1),
            }
        cur.close()
        conn.close()
    except Exception as e:
        import traceback
        print(f"Dashboard DB error for user_id={session.get('user_id')}: {e}")
        traceback.print_exc()
        flash("Couldn't load your prediction history right now. Check the server logs / database connection.", "error")

    return render_template("dashboard.html", history=history, stats=stats, username=session.get("username"))


@app.route("/visualize")
@login_required
def visualize():
    labels, scores = [], []
    final_pred = "N/A"
    recommendations = "No data available yet. Run an analysis first."

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM predictions WHERE user_id=%s ORDER BY id ASC LIMIT 20",
            (session["user_id"],),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            labels = [format_db_datetime(r.get("created_at"), "%b %d") for r in rows]
            scores = [round(float(r["sleep_score"] or 0), 1) for r in rows]
            last = rows[-1]
            final_pred = last.get("final_prediction") or "N/A"
            recommendations = (last.get("recommendations") or "No recommendations available.").replace(" | ", "\n")
    except Exception as e:
        import traceback
        print(f"Visualize DB error for user_id={session.get('user_id')}: {e}")
        traceback.print_exc()
        flash("Couldn't load your prediction trends right now. Check the server logs / database connection.", "error")

    return render_template(
        "visualize.html",
        labels=labels,
        scores=scores,
        final_pred=final_pred,
        recommendations=recommendations,
    )


@app.route("/about")
@login_required
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)
