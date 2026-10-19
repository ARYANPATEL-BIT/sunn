from datetime import datetime

import matcher


def candidate(key, *fingerprints, contexts=("any",)):
    return {"key": key, "fingerprints": list(fingerprints), "contexts": list(contexts)}


def at(hour):
    return datetime(2026, 10, 19, hour).astimezone()  # that hour, local time


def test_devanagari_and_romanized_normalize_alike():
    assert matcher.normalize("पानी चाहिए") == matcher.normalize("pAnI chAhie") == "pani chahie"
    assert matcher.similarity("पानी चाहिए", "Pani Chahie!") == 100


def test_normalize_drops_punctuation_but_keeps_words_whole():
    assert matcher.normalize("मैं ठीक हूँ।") == "maim thika hun"  # danda gone, chandrabindu kept in its word
    assert matcher.normalize("  I'm   fine. ") == "im fine"


def test_similarity_always_beats_every_boost():
    close, far = candidate(1, "pani chahie"), candidate(2, "chaya chahie", contexts=["home"])
    priors = {2: (1.0, 1.0)}
    top, second = matcher.rank("pani chahie", [far, close], context="home", priors=priors)
    assert top["key"] == 1
    assert second["parts"]["context"] + second["parts"]["freq"] + second["parts"]["time"] == 13
    assert top["score"] > second["score"]


def test_boosts_settle_a_tie_and_parts_add_up():
    home, hospital = candidate(1, "dard hai", contexts=["home"]), candidate(2, "dard hai", contexts=["home", "hospital"])
    top, second = matcher.rank("dard hai", [home, hospital], context="hospital", priors={1: (0.5, 0.0)})
    assert top["key"] == 2
    assert top["parts"] == {"similarity": 100.0, "context": matcher.CONTEXT_BOOST, "freq": 0.0, "time": 0.0}
    assert second["parts"] == {"similarity": 100.0, "context": 0, "freq": matcher.FREQ_BOOST * 0.5, "time": 0.0}
    for c in (top, second):
        assert c["score"] == round(sum(c["parts"].values()), 1)


def test_any_context_and_no_context_boost_nothing():
    tagged = [candidate(1, "haan", contexts=["any"]), candidate(2, "haan", contexts=["market"])]
    for context in (None, "any"):
        assert all(c["parts"]["context"] == 0 for c in matcher.rank("haan", tagged, context=context))


def test_candidates_without_fingerprints_are_skipped_and_k_is_kept():
    ranked = matcher.rank("a", [candidate(1), *[candidate(n, "a") for n in range(2, 7)]], k=3)
    assert [c["key"] for c in ranked] == [2, 3, 4]


def test_usage_priors_are_shares_of_the_most_used():
    uses = [(1, at(8))] * 4 + [(2, at(22))] * 2 + [(2, at(9))]
    assert matcher.usage_priors(uses, "morning") == {1: (1.0, 1.0), 2: (0.75, 0.25)}
    assert matcher.usage_priors(uses, "afternoon") == {1: (1.0, 0.0), 2: (0.75, 0.0)}
    assert matcher.usage_priors([], "night") == {}


def test_time_buckets():
    assert [matcher.time_bucket(at(h)) for h in (4, 5, 11, 12, 16, 17, 20, 21, 23)] == [
        "night", "morning", "morning", "afternoon", "afternoon", "evening", "evening", "night", "night"]


def test_parse_template():
    assert matcher.parse_template("{item} चाहिए") == ("item", "चाहिए", True)
    assert matcher.parse_template(" Call  {person} ") == ("person", "Call", False)
    for bad in ("मुझे {item} दो", "{item} {person}", "{item}", "चाहिए", "{thing} चाहिए"):
        assert matcher.parse_template(bad) is None


def test_compose_follows_the_template_word_order():
    assert matcher.compose(True, "पानी", "चाहिए") == "पानी चाहिए"
    assert matcher.compose(False, "the doctor", "Call") == "Call the doctor"
