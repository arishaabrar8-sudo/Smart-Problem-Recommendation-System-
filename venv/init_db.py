import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")

# Progress table
cursor.execute("""
CREATE TABLE IF NOT EXISTS progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    problem_code TEXT,
    title TEXT,
    topic TEXT,
    difficulty TEXT,
    platform TEXT,
    solved_date TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully!")

CREATE TABLE IF NOT EXISTS progress(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    problem_id INTEGER,
    title TEXT,
    topic TEXT,
    difficulty TEXT,
    platform TEXT,
    solved_date TEXT
);
def calculate_streak(username):

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    cursor.execute("""
    SELECT solved_date
    FROM progress
    WHERE username=?
    ORDER BY solved_date DESC
    """,(username,))


    dates = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()


    streak = 0

    today = datetime.now().date()


    for d in dates:

        day = datetime.strptime(
            d,"%Y-%m-%d"
        ).date()


        if day == today:

            streak += 1
            today = today - timedelta(days=1)

        else:
            break


    return streak

    platform_stats = cursor.execute(
"""
SELECT platform,COUNT(*)
FROM progress
WHERE username=?
GROUP BY platform
""",
(session["user"],)
).fetchall()
