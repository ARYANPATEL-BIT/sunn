def test_user_signup_default_phrase_goal(env):
    user_client = env.signup("hi")
    me = user_client.get("/auth/me").json()
    assert me["phrase_goal"] is None


def test_update_phrase_goal_success(env):
    user_client = env.signup("hi")
    res = user_client.patch("/me", json={"phrase_goal": 20})
    assert res.status_code == 200
    user = res.json()
    assert user["phrase_goal"] == 20

    # Persisted across calls
    me = user_client.get("/auth/me").json()
    assert me["phrase_goal"] == 20


def test_update_phrase_goal_validation(env):
    user_client = env.signup("hi")
    res_zero = user_client.patch("/me", json={"phrase_goal": 0})
    assert res_zero.status_code == 400
    assert res_zero.json()["error"] == "invalid_input"

    res_neg = user_client.patch("/me", json={"phrase_goal": -10})
    assert res_neg.status_code == 400
    assert res_neg.json()["error"] == "invalid_input"


def test_phrase_goal_cross_user_isolation(env):
    user1 = env.signup("hi")
    user2 = env.signup("en")

    user1.patch("/me", json={"phrase_goal": 25})
    assert user1.get("/auth/me").json()["phrase_goal"] == 25
    assert user2.get("/auth/me").json()["phrase_goal"] is None
