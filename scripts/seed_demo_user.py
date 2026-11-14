import sys
from datetime import datetime, timedelta, timezone

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


def ago(**delta):
    """An ISO timestamp that long before now, in UTC, as the app writes them."""
    return (datetime.now(timezone.utc) - timedelta(**delta)).isoformat(timespec="seconds")

def seed():
    email = "demo@sunn.app"
    password = "password123"
    
    # Remove existing demo user if present
    existing = db.row("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        db.delete_user(existing["id"])
    
    # Create user
    pw_hash = auth.hash_password(password)
    db.execute(
        """INSERT INTO users (name, email, password_hash, language, consent_given_at, caregiver_name, caregiver_phone, use_own_voice)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        ("Asha", email, pw_hash, "en", ago(), "Dr. Ananya", "+919876543210", 0)
    )
    user = db.row("SELECT * FROM users WHERE email = %s", (email,))
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
                    "INSERT INTO phrases (user_id, text, contexts, urgent) VALUES (%s, %s, %s, %s)",
                    (uid, text, contexts, urgent)
                )

    phrases = db.rows("SELECT id, text FROM phrases WHERE user_id = %s", (uid,))
    print(f"Added {len(phrases)} phrases")

    # Add 3 enroll samples per phrase so all are ready and Speak is unlocked
    for p in phrases:
        for i in range(3):
            db.execute(
                """INSERT INTO samples (user_id, phrase_id, audio_path, prisma_hypothesis, source, created_at, language, speech_source)
                   VALUES (%s, %s, %s, %s, 'enroll', %s, 'en', 'pilot')""",
                (uid, p["id"], f"audio/sample_{p['id']}_{i}.wav", p["text"], ago(days=i))
            )

    # Add usage records for progress screen
    for i, p in enumerate(phrases[:12]):
        for j in range(i + 2):
            db.execute(
                "INSERT INTO uses (user_id, phrase_id, created_at) VALUES (%s, %s, %s)",
                (uid, p["id"], ago(hours=j * 4))
            )

    # Add training progress and practice minutes
    db.execute(
        "INSERT INTO training_progress (user_id, lesson_id, step_index, completed_at, updated_at) "
        "VALUES (%s, 'easy-starts-1', 5, %s, %s)",
        (uid, ago(days=2), ago(days=2))
    )
    db.execute(
        "INSERT INTO training_progress (user_id, lesson_id, step_index, completed_at, updated_at) "
        "VALUES (%s, 'easy-starts-2', 3, NULL, %s)",
        (uid, ago(hours=1))
    )
    for d in range(5):
        db.execute(
            "INSERT INTO training_minutes (user_id, day, seconds) VALUES (%s, %s, %s)",
            (uid, ago(days=d)[:10], 420 + d * 60)
        )
    # Reflections and attempts for tricky sounds evidence ('s' and 'sh')
    for _ in range(2):
        db.execute(
            "INSERT INTO training_reflections (user_id, lesson_id, step_id, feeling, created_at) "
            "VALUES (%s, 's-and-sh-2', 's-and-sh-2-reflect', 'hard', %s)",
            (uid, ago())
        )

    print("Demo account successfully seeded!")

if __name__ == "__main__":
    seed()
