import random
import pandas as pd

topics = [
    "Arrays", "Binary Search", "Sliding Window", "Two Pointers",
    "Graphs", "Dynamic Programming", "Greedy", "Trees",
    "Strings", "Backtracking", "Bit Manipulation",
    "Math", "Sorting", "Prefix Sum", "Hashing"
]

platforms = ["LeetCode", "Codeforces", "CSES", "AtCoder", "CodeChef"]

difficulties = ["Easy", "Medium", "Hard"]

companies = [
    "Google", "Amazon", "Microsoft", "Meta",
    "Apple", "Netflix", "Adobe", "Uber"
]

rows = []

for i in range(1, 10001):
    topic = random.choice(topics)
    difficulty = random.choice(difficulties)

    rows.append({
        "id": i,
        "title": f"{topic} Problem {i}",
        "platform": random.choice(platforms),
        "topic": topic,
        "difficulty": difficulty,
        "tags": topic.lower().replace(" ", "-"),
        "rating": random.randint(800, 2500),
        "estimated_time": random.choice([15, 20, 30, 45, 60]),
        "company": random.choice(companies),
        "description": f"Practice {topic} using {difficulty} level questions.",
        "link": f"https://example.com/problem/{i}"
    })

df = pd.DataFrame(rows)
df.to_csv("problems.csv", index=False)

print("✅ problems.csv created with 10,000 problems!")
