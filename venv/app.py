import os
import sqlite3
from datetime import datetime
import matplotlib
matplotlib.use("Agg")  # Prevents GUI thread crashes in Flask
import matplotlib.pyplot as plt
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# -----------------------------------------------------------------------------
# Database Initialization
# -----------------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)
    
    # Progress Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        problem_code TEXT,
        title TEXT NOT NULL,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        platform TEXT,
        solved_date TEXT NOT NULL
    )
    """)
    
    # Badges Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        badge TEXT NOT NULL,
        earned_date TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# Load & Process Dataset
# -----------------------------------------------------------------------------
df = pd.read_csv("problems.csv")
df.columns = df.columns.str.strip()

for col in df.columns:
    if df[col].dtype == "object":
        df[col] = df[col].fillna("").str.strip()

# Create dynamic features column for TF-IDF
df["features"] = (
    df["topic"].astype(str) + " " +
    df["difficulty"].astype(str) + " " +
    df["title"].astype(str)
)

vectorizer = TfidfVectorizer(stop_words="english")
tfidf_matrix = vectorizer.fit_transform(df["features"])
similarity = cosine_similarity(tfidf_matrix)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------
def recommend_problem(problem_title, top_n=5):
    index = df[df["title"] == problem_title].index

    if len(index) == 0:
        return []

    index = index[0]
    scores = list(enumerate(similarity[index]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = scores[1:top_n+1]

    recommendations = []
    for i, score in scores:
        recommendations.append(df.iloc[i])

    return recommendations

def generate_chart(username):
    os.makedirs("static/charts", exist_ok=True)

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT topic, COUNT(*)
    FROM progress
    WHERE username=?
    GROUP BY topic
    """, (username,))

    data = cursor.fetchall()
    conn.close()

    if not data:
        return

    topics = [row[0] for row in data]
    counts = [row[1] for row in data]

    plt.figure(figsize=(6, 4))
    plt.bar(topics, counts)
    plt.title("Solved Problems by Topic")
    plt.xlabel("Topic")
    plt.ylabel("Solved")
    plt.tight_layout()

    # User-specific filename prevents cross-user overwriting
    chart_path = f"static/charts/progress_{username}.png"
    plt.savefig(chart_path)
    plt.close()

def check_badges(username):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    count = cursor.execute(
        "SELECT COUNT(*) FROM progress WHERE username=?",
        (username,)
    ).fetchone()[0]

    if count >= 100:
        badge = "Gold"
    elif count >= 50:
        badge = "Silver"
    elif count >= 10:
        badge = "Bronze"
    else:
        conn.close()
        return

    cursor.execute(
        "SELECT * FROM badges WHERE username=? AND badge=?",
        (username, badge)
    )

    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO badges(username, badge, earned_date) VALUES (?, ?, ?)",
            (username, badge, datetime.now().strftime("%Y-%m-%d"))
        )
        conn.commit()

    conn.close()

# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users(username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Email already exists. Please use another email."

        conn.close()
        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session["user"] = user[1]
            return redirect(url_for("dashboard"))

        return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM progress WHERE username=?",
        (session["user"],)
    )
    solved = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT topic, COUNT(*)
        FROM progress
        WHERE username=?
        GROUP BY topic
        ORDER BY COUNT(*) DESC
        LIMIT 1
        """,
        (session["user"],)
    )

    favorite = cursor.fetchone()
    conn.close()

    generate_chart(session["user"])

    favorite_topic = favorite[0] if favorite else "None"
    chart_filename = f"charts/progress_{session['user']}.png"

    return render_template(
        "dashboard.html",
        username=session["user"],
        solved=solved,
        favorite_topic=favorite_topic,
        chart_filename=chart_filename
    )

@app.route("/solve", methods=["POST"])
def solve_form():
    if "user" not in session:
        return redirect(url_for("login"))

    title = request.form["title"]
    topic = request.form["topic"]
    difficulty = request.form["difficulty"]
    platform = request.form.get("platform", "N/A")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM progress WHERE username=? AND title=?",
        (session["user"], title)
    )

    if cursor.fetchone():
        conn.close()
        return redirect(url_for("dashboard"))

    cursor.execute(
        """
        INSERT INTO progress
        (username, title, topic, difficulty, platform, solved_date)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session["user"],
            title,
            topic,
            difficulty,
            platform,
            datetime.now().strftime("%Y-%m-%d")
        )
    )

    conn.commit()
    conn.close()

    check_badges(session["user"])
    return redirect(url_for("dashboard"))

@app.route("/solve/<problem_code>")
def solve_by_code(problem_code):
    if "user" not in session:
        return redirect(url_for("login"))

    matched = df[df["problem_code"].astype(str) == str(problem_code)]
    if matched.empty:
        return "Problem not found", 404

    problem = matched.iloc[0]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM progress WHERE username=? AND title=?",
        (session["user"], problem["title"])
    )

    if cursor.fetchone():
        conn.close()
        return redirect(url_for("dashboard"))

    cursor.execute(
        """
        INSERT INTO progress
        (username, problem_code, title, topic, difficulty, platform, solved_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["user"],
            str(problem["problem_code"]),
            problem["title"],
            problem["topic"],
            problem["difficulty"],
            problem.get("platform", "N/A"),
            datetime.now().strftime("%Y-%m-%d")
        )
    )

    conn.commit()
    conn.close()

    check_badges(session["user"])
    return redirect(url_for("dashboard"))

@app.route("/recommend", methods=["POST"])
def recommend():
    topic = request.form["topic"]
    difficulty = request.form["difficulty"]

    result = df[
        (df["topic"] == topic) &
        (df["difficulty"] == difficulty)
    ]
    
    if "rating" in result.columns:
        result = result.sort_values(by="rating")

    recommendations = result.to_dict(orient="records")

    return render_template(
        "recommended.html",
        recommendations=recommendations,
        topic=topic,
        difficulty=difficulty
    )

@app.route("/recommend_ml", methods=["POST"])
def recommend_ml():
    title = request.form["title"]
    recommendations = recommend_problem(title)
    recommendations = [row.to_dict() for row in recommendations]

    return render_template(
        "recommended.html",
        recommendations=recommendations,
        title=title
    )

if __name__ == "__main__":
    app.run(debug=True)
