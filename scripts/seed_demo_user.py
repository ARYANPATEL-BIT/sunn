import os
import sqlite3
import sys

sys.path.insert(0, "src")
import auth
import db

GROUP_CONTEXTS = {
    "help": "any",
    "basic needs": "home,hospital",
    "pain and health": "hospital",
    "food and drink": "home",
    "family": "home",
    "greetings and politeness": "any",
}
URGENT_PHRASES = {"मदद चाहिए", "दर्द हो रहा है", "I need help", "I'm in pain"}

def seed():
    email = "demo@sunn.app"
    password = "password123"
    
    # Remove existing demo user if present
    existing = db.row("SELECT id FROM users WHERE email = ?", (email,))
    if existing:
        db.delete_user(existing["id"])
    
    # Create user
    pw_hash = auth.hash_password(password)
    db.execute(
        """INSERT INTO users (name, email, password_hash, language, consent_given_at, caregiver_name, caregiver_phone, use_own_voice)
           VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?)""",
        ("Asha", email, pw_hash, "en", "Dr. Ananya", "+919876543210", 0)
    )
    user = db.row("SELECT * FROM users WHERE email = ?", (email,))
    uid = user["id"]
    print(f"Created demo user id {uid}")

    # Add default phrases for en
    with open("data/default_phrases_en.txt", encoding="utf-8") as f:
        contexts = "any"
        for line in f:
            text = " ".join(line.split())
            if line.startswith("#"):
                header = line.strip("# \n").lower()
                contexts = GROUP_CONTEXTS.get(header, "any")
            elif text:
                urgent = 1 if text in URGENT_PHRASES else 0
                db.execute(
                    "INSERT INTO phrases (user_id, text, contexts, urgent) VALUES (?, ?, ?, ?)",
                    (uid, text, contexts, urgent)
                )

    phrases = db.rows("SELECT id, text FROM phrases WHERE user_id = ?", (uid,))
    print(f"Added {len(phrases)} phrases")

    # Add 3 enroll samples per phrase so all are ready and Speak is unlocked
    for p in phrases:
        for i in range(3):
            db.execute(
                """INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at, language, speech_source)
                   VALUES (?, ?, ?, ?, 'enroll', datetime('now', '-' || ? || ' days'), 'en', 'pilot')""",
                (uid, p["id"], f"audio/sample_{p['id']}_{i}.wav", p["text"], i)
            )

    # Add usage records for progress screen
    for i, p in enumerate(phrases[:12]):
        for j in range(i + 2):
            db.execute(
                "INSERT INTO uses (user_id, phrase_id, created_at) VALUES (?, ?, datetime('now', '-' || ? || ' hours'))",
                (uid, p["id"], j * 4)
            )

    print("Demo account successfully seeded!")

if __name__ == "__main__":
    seed()
