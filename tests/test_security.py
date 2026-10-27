"""The session cookie's flags, no cross-origin access, and the login lockout."""
from http.cookies import SimpleCookie


def signup(client, email="asha@example.com"):
    return client.post("/auth/signup", json={"name": "Asha", "email": email, "password": "password123",
                                             "language": "hi", "consent": True})


def test_the_session_cookie_is_httponly_secure_and_lax(env):
    client = env.client()
    for response in (signup(client), client.post("/auth/login", json={"email": "asha@example.com",
                                                                        "password": "password123"})):
        cookie = SimpleCookie(response.headers["set-cookie"])["sunn_session"]
        assert cookie["httponly"] and cookie["secure"]
        assert cookie["samesite"].lower() == "lax" and cookie["path"] == "/"


def test_no_other_origin_can_use_the_api(env):
    """No CORS at all: the app and the API share one origin, so a browser never lets another
    site read an answer, with the cookie or without."""
    client = env.client()
    signup(client)
    evil = {"Origin": "https://evil.example"}
    answer = client.get("/auth/me", headers=evil)
    assert "access-control-allow-origin" not in answer.headers
    assert "access-control-allow-credentials" not in answer.headers
    preflight = client.options("/me", headers={**evil, "Access-Control-Request-Method": "DELETE"})
    assert preflight.status_code != 200 and "access-control-allow-origin" not in preflight.headers


def test_five_wrong_passwords_lock_that_email_only(env):
    client = env.client()
    signup(client)
    signup(env.client(), "ravi@example.com")
    login = lambda email, password: env.client().post("/auth/login", json={"email": email, "password": password})  # noqa: E731

    assert login("asha@example.com", "wrong-one").status_code == 401
    assert login("asha@example.com", "password123").status_code == 200  # a success clears the count
    for _ in range(5):
        assert login("asha@example.com", "wrong-one").json()["error"] == "bad_login"
    locked = login("asha@example.com", "password123")  # even the right password, while locked
    assert locked.status_code == 429 and locked.json()["error"] == "too_many_attempts"
    assert 0 < locked.json()["retry_after"] <= 15 * 60
    assert login("ASHA@example.com", "password123").status_code == 429  # emails are matched lowercased
    assert login("ravi@example.com", "password123").status_code == 200  # another email isn't locked
