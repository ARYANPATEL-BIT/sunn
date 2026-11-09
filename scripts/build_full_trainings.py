"""Builder script for the full Sunn Trainings content according to docs/TRAININGS_CONTRACT.md and prompt A1.
Ensures every course uses all 9 step types, every sound has 6+ examples, 60 alternatives, and full audio manifests.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import trainings_content

CONTENT_DIR = os.path.join(ROOT, "content", "trainings")
COURSES_DIR = os.path.join(CONTENT_DIR, "courses")

audio_dict = {}

def track_audio(key, text, lang="hi"):
    if key in audio_dict:
        if audio_dict[key]["text"] != text or audio_dict[key]["lang"] != lang:
            raise ValueError(f"Conflicting audio key {key}: '{audio_dict[key]}' vs '{(text, lang)}'")
    else:
        audio_dict[key] = {"text": text, "lang": lang}
    return key


def build_easy_starts():
    # 4 lessons, smooth-speaking (only feedback 'none' or 'pace')
    lessons = [
        {
            "id": "easy-starts-1",
            "title": {"en": "Breath and a gentle start", "hi": "साँस और हल्की शुरुआत"},
            "minutes": 8,
            "steps": [
                {
                    "id": "easy-starts-1-welcome",
                    "type": "intro",
                    "title": {"en": "Welcome", "hi": "स्वागत है"},
                    "body": {
                        "en": "This is a quiet place to practise. There is no rush and no test. Take your time and practise at your own pace.",
                        "hi": "यह अभ्यास की एक शांत जगह है। यहाँ कोई जल्दी नहीं है और कोई परीक्षा नहीं। अपनी रफ़्तार से आराम से अभ्यास कीजिए।"
                    }
                },
                {
                    "id": "easy-starts-1-breathe",
                    "type": "breathing",
                    "title": {"en": "Relaxed breathing", "hi": "आराम से साँसें"},
                    "body": {
                        "en": "Breathe in through your nose for 4 seconds, then let the air out slowly for 6 seconds. There is no need to hold.",
                        "hi": "नाक से 4 सेकंड साँस लीजिए, फिर 6 सेकंड में धीरे-धीरे छोड़िए। साँस रोकने की ज़रूरत नहीं है।"
                    },
                    "pattern": {"in_s": 4, "out_s": 6},
                    "rounds": 4
                },
                {
                    "id": "easy-starts-1-soft-start",
                    "type": "tip",
                    "title": {"en": "Gentle start", "hi": "हल्की शुरुआत"},
                    "body": {
                        "en": "Many people find it helpful to let a little air out first. Then let the first sound begin softly, as if it rides on that breath.",
                        "hi": "कई लोग पहले थोड़ी हवा बाहर निकलने देते हैं। फिर पहली आवाज़ को हल्के से शुरू होने दीजिए, जैसे वह उसी साँस पर चल रही हो।"
                    },
                    "technique_id": "easy-start"
                },
                {
                    "id": "easy-starts-1-vowels",
                    "type": "listen_repeat",
                    "title": {"en": "Soft vowel and nasal starts", "hi": "स्वर और नाक वाली सरल शुरुआत"},
                    "items": [
                        {"id": "aam", "text": "आम", "latin": "aam", "meaning_en": "mango", "focus_sound": "nasal", "audio_key": track_audio("easy-starts-1-vowels-aam", "आम")},
                        {"id": "aaj", "text": "आज", "latin": "aaj", "meaning_en": "today", "focus_sound": "nasal", "audio_key": track_audio("easy-starts-1-vowels-aaj", "आज")},
                        {"id": "ek", "text": "एक", "latin": "ek", "meaning_en": "one", "focus_sound": "nasal", "audio_key": track_audio("easy-starts-1-vowels-ek", "एक")},
                        {"id": "oopar", "text": "ऊपर", "latin": "oopar", "meaning_en": "up", "focus_sound": "nasal", "audio_key": track_audio("easy-starts-1-vowels-oopar", "ऊपर")},
                        {"id": "achchha", "text": "अच्छा", "latin": "achchha", "meaning_en": "good", "focus_sound": "nasal", "audio_key": track_audio("easy-starts-1-vowels-achchha", "अच्छा")},
                        {"id": "naam", "text": "नाम", "latin": "naam", "meaning_en": "name", "focus_sound": "nasal", "audio_key": track_audio("easy-starts-1-vowels-naam", "नाम")}
                    ],
                    "feedback": "none"
                },
                {
                    "id": "easy-starts-1-together",
                    "type": "speak_with_me",
                    "title": {"en": "Choral practice with Sunn", "hi": "Sunn के साथ बोलिए"},
                    "text": "आज मौसम अच्छा है",
                    "latin": "aaj mausam achchha hai",
                    "meaning_en": "The weather is pleasant today.",
                    "mode": "choral",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("easy-starts-1-together-mausam", "आज मौसम अच्छा है"),
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-1-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did the gentle starts feel today?", "hi": "आज हल्की शुरुआत कैसी लगी?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "easy-starts-2",
            "title": {"en": "Light touches on sounds", "hi": "आवाज़ों पर हल्का स्पर्श"},
            "minutes": 8,
            "steps": [
                {
                    "id": "easy-starts-2-light-lips",
                    "type": "tip",
                    "title": {"en": "Light contact", "hi": "हल्का स्पर्श"},
                    "body": {
                        "en": "For sounds like p and b, many people find it helpful when the lips meet lightly and part easily, without extra tension.",
                        "hi": "प और ब जैसी आवाज़ों के लिए होंठों को हल्के से मिलने दीजिए और आराम से खुलने दीजिए।"
                    },
                    "technique_id": "light-touch"
                },
                {
                    "id": "easy-starts-2-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "Two close words", "hi": "दो मिलते-जुलते शब्द"},
                    "pairs": [
                        {
                            "id": "pal-bal",
                            "a": {"text": "पल", "latin": "pal", "audio_key": track_audio("easy-starts-2-pairs-pal", "पल")},
                            "b": {"text": "बल", "latin": "bal", "audio_key": track_audio("easy-starts-2-pairs-bal", "बल")},
                            "sound_a": "p",
                            "sound_b": "b"
                        },
                        {
                            "id": "padaa-badaa",
                            "a": {"text": "पड़ा", "latin": "padaa", "audio_key": track_audio("easy-starts-2-pairs-padaa", "पड़ा")},
                            "b": {"text": "बड़ा", "latin": "badaa", "audio_key": track_audio("easy-starts-2-pairs-badaa", "बड़ा")},
                            "sound_a": "p",
                            "sound_b": "b"
                        }
                    ]
                },
                {
                    "id": "easy-starts-2-echo",
                    "type": "speak_with_me",
                    "title": {"en": "Echo: Sunn first, then you", "hi": "पहले Sunn, फिर आप"},
                    "text": "मुझे एक कप चाय चाहिए",
                    "latin": "mujhe ek cup chaay chaahiye",
                    "meaning_en": "I would like a cup of tea.",
                    "mode": "echo",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("easy-starts-2-echo-chaay", "मुझे एक कप चाय चाहिए"),
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-2-paced",
                    "type": "speak_with_me",
                    "title": {"en": "Paced reading", "hi": "रफ़्तार के साथ चलिए"},
                    "text": "मेरे पास बोलने के लिए पूरा समय है",
                    "latin": "mere paas bolne ke liye poora samay hai",
                    "meaning_en": "I have all the time I need to speak.",
                    "mode": "paced",
                    "pace_wpm": [50, 80],
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-2-read",
                    "type": "read_aloud",
                    "title": {"en": "Read with light touches", "hi": "हल्के स्पर्श से पढ़िए"},
                    "paragraph": "सुबह की हवा ठंडी और ताज़ा है। बाहर पेड़ों पर चिड़ियाँ बोल रही हैं। आज का दिन आराम से शुरू हो रहा है।",
                    "latin": "subah ki hawa thandi aur taaza hai. baahar pedon par chidiyaan bol rahi hain. aaj ka din aaraam se shuru ho raha hai.",
                    "audio_key": track_audio("easy-starts-2-read-morning", "सुबह की हवा ठंडी और ताज़ा है। बाहर पेड़ों पर चिड़ियाँ बोल रही हैं। आज का दिन आराम से शुरू हो रहा है।"),
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-2-tea-stall",
                    "type": "dialogue",
                    "title": {"en": "At the tea stall", "hi": "चाय की दुकान पर"},
                    "scenario": {
                        "en": "You are at a tea stall. Take one relaxed breath before each turn.",
                        "hi": "आप चाय की दुकान पर हैं। अपनी हर बारी से पहले एक सहज साँस लीजिए।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते! क्या लेंगे?", "latin": "namaste! kya lenge?", "audio_key": track_audio("easy-starts-2-stall-1", "नमस्ते! क्या लेंगे?")},
                        {
                            "speaker": "you",
                            "text": "एक चाय, कम चीनी वाली।",
                            "latin": "ek chaay, kam cheeni waali.",
                            "options": [{"text": "एक चाय और दो बिस्कुट।", "latin": "ek chaay aur do biscuit."}]
                        },
                        {"speaker": "sunn", "text": "ठीक है, बीस रुपये।", "latin": "theek hai, bees rupaye.", "audio_key": track_audio("easy-starts-2-stall-2", "ठीक है, बीस रुपये।")},
                        {"speaker": "you", "text": "धन्यवाद।", "latin": "dhanyavaad."}
                    ]
                },
                {
                    "id": "easy-starts-2-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did the light touches feel?", "hi": "हल्का स्पर्श कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "easy-starts-3",
            "title": {"en": "Slow pace and phrase breaks", "hi": "धीमी चाल और ठहराव"},
            "minutes": 8,
            "steps": [
                {
                    "id": "easy-starts-3-intro",
                    "type": "intro",
                    "title": {"en": "Pausing at natural breaks", "hi": "वाक्य में छोटे ठहराव"},
                    "body": {
                        "en": "When speaking a longer thought, pausing at natural breaks gives your breath time to reset.",
                        "hi": "लंबी बात कहते समय बीच में छोटे ठहराव लेने से साँस को आराम मिलता है।"
                    }
                },
                {
                    "id": "easy-starts-3-tip",
                    "type": "tip",
                    "title": {"en": "Stretching words", "hi": "शब्दों को थोड़ा फैलाना"},
                    "body": {
                        "en": "Many people find that stretching vowel sounds slightly keeps the airflow smooth and comfortable.",
                        "hi": "कई लोगों को लगता है कि स्वरों को थोड़ा सा खींचकर बोलने से आवाज़ सहज बनी रहती है।"
                    },
                    "technique_id": "slow-pace"
                },
                {
                    "id": "easy-starts-3-breathe",
                    "type": "breathing",
                    "title": {"en": "Calm breath", "hi": "शांत साँस"},
                    "body": {
                        "en": "Take 4 slow breaths in and out before speaking phrases.",
                        "hi": "वाक्य बोलने से पहले 4 धीमी साँसें लीजिए और छोड़िए।"
                    },
                    "pattern": {"in_s": 4, "out_s": 6},
                    "rounds": 4
                },
                {
                    "id": "easy-starts-3-clusters",
                    "type": "listen_repeat",
                    "title": {"en": "Smooth clustered phrases", "hi": "जुड़े अक्षरों वाले शब्द"},
                    "items": [
                        {"id": "school", "text": "स्कूल", "latin": "school", "meaning_en": "school", "focus_sound": "clusters", "audio_key": track_audio("easy-starts-3-clusters-school", "स्कूल")},
                        {"id": "raasta", "text": "रास्ता", "latin": "raasta", "meaning_en": "path", "focus_sound": "clusters", "audio_key": track_audio("easy-starts-3-clusters-raasta", "रास्ता")},
                        {"id": "dost", "text": "दोस्त", "latin": "dost", "meaning_en": "friend", "focus_sound": "clusters", "audio_key": track_audio("easy-starts-3-clusters-dost", "दोस्त")},
                        {"id": "dhyaan", "text": "ध्यान", "latin": "dhyaan", "meaning_en": "attention", "focus_sound": "clusters", "audio_key": track_audio("easy-starts-3-clusters-dhyaan", "ध्यान")},
                        {"id": "swaad", "text": "स्वाद", "latin": "swaad", "meaning_en": "taste", "focus_sound": "clusters", "audio_key": track_audio("easy-starts-3-clusters-swaad", "स्वाद")}
                    ],
                    "feedback": "none"
                },
                {
                    "id": "easy-starts-3-choral",
                    "type": "speak_with_me",
                    "title": {"en": "Choral reading with pauses", "hi": "ठहराव के साथ बोलना"},
                    "text": "हम सब मिलकर धीरे-धीरे आगे बढ़ रहे हैं",
                    "latin": "hum sab milkar dheere-dheere aage badh rahe hain",
                    "meaning_en": "Together we are moving forward at an easy pace.",
                    "mode": "choral",
                    "pace_wpm": [55, 80],
                    "audio_key": track_audio("easy-starts-3-choral-together", "हम सब मिलकर धीरे-धीरे आगे बढ़ रहे हैं"),
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-3-read",
                    "type": "read_aloud",
                    "title": {"en": "Read with comfortable pauses", "hi": "सहज ठहराव से पढ़िए"},
                    "paragraph": "नदी किनारे ठंडी हवा चल रही है। दूर एक छोटा सा गाँव दिखाई देता है। शाम का समय बहुत शांत लगता है।",
                    "latin": "nadi kinaare thandi hawa chal rahi hai. door ek chhota sa gaanv dikhaai deta hai. shaam ka samay bahut shaant lagta hai.",
                    "audio_key": track_audio("easy-starts-3-read-river", "नदी किनारे ठंडी हवा चल रही है। दूर एक छोटा सा गाँव दिखाई देता है। शाम का समय बहुत शांत लगता है।"),
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-3-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did pausing between phrases feel?", "hi": "वाक्यों के बीच ठहराव कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "easy-starts-4",
            "title": {"en": "Speaking with confidence", "hi": "आत्मविश्वास से बोलना"},
            "minutes": 8,
            "steps": [
                {
                    "id": "easy-starts-4-intro",
                    "type": "intro",
                    "title": {"en": "Your voice matters", "hi": "आपकी आवाज़ का स्वागत है"},
                    "body": {
                        "en": "Stammering is completely okay. You deserve to be heard at your own pace. There is never any need to rush for anyone.",
                        "hi": "हकलाहट बिल्कुल स्वाभाविक है। आपको अपनी रफ़्तार से सुने जाने का पूरा अधिकार है। किसी के लिए भी जल्दी करने की ज़रूरत नहीं है।"
                    }
                },
                {
                    "id": "easy-starts-4-tip",
                    "type": "tip",
                    "title": {"en": "Taking your time", "hi": "पूरा समय लीजिए"},
                    "body": {
                        "en": "Many people find peace in remembering that listeners are glad to wait. Take a steady breath before you begin.",
                        "hi": "यह याद रखना मददगार होता है कि सुनने वाले इंतज़ार करने को तैयार हैं। शुरू करने से पहले एक सहज साँस लीजिए।"
                    },
                    "technique_id": "pausing"
                },
                {
                    "id": "easy-starts-4-choral",
                    "type": "speak_with_me",
                    "title": {"en": "Speak together with Sunn", "hi": "Sunn के साथ बोलिए"},
                    "text": "मेरी बात महत्वपूर्ण है और मैं अपनी रफ़्तार से बोलूँगा",
                    "latin": "meri baat mahatvapurna hai aur main apni raftaar se boloonga",
                    "meaning_en": "My words matter and I will speak at my own pace.",
                    "mode": "choral",
                    "pace_wpm": [55, 80],
                    "audio_key": track_audio("easy-starts-4-choral-confidence", "मेरी बात महत्वपूर्ण है और मैं अपनी रफ़्तार से बोलूँगा"),
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-4-dialogue",
                    "type": "dialogue",
                    "title": {"en": "Speaking in public without rush", "hi": "बिना जल्दबाज़ी के बातचीत"},
                    "scenario": {
                        "en": "You are talking to an acquaintance. Take your own time to reply.",
                        "hi": "आप किसी परिचित से बात कर रहे हैं। जवाब देने में अपना पूरा समय लीजिए।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते! आज आप कैसे हैं?", "latin": "namaste! aaj aap kaise hain?", "audio_key": track_audio("easy-starts-4-dialogue-1", "नमस्ते! आज आप कैसे हैं?")},
                        {
                            "speaker": "you",
                            "text": "नमस्ते, मैं बिल्कुल ठीक हूँ।",
                            "latin": "namaste, main bilkul theek hoon.",
                            "options": [{"text": "नमस्ते, सब बहुत अच्छा चल रहा है।", "latin": "namaste, sab bahut achchha chal raha hai."}]
                        },
                        {"speaker": "sunn", "text": "बहुत बढ़िया, मिलकर अच्छा लगा।", "latin": "bahut badhiya, milkar achchha laga.", "audio_key": track_audio("easy-starts-4-dialogue-2", "बहुत बढ़िया, मिलकर अच्छा लगा।")},
                        {"speaker": "you", "text": "मुझे भी आपसे बात करके अच्छा लगा।", "latin": "mujhe bhi aap se baat karke achchha laga."}
                    ]
                },
                {
                    "id": "easy-starts-4-paced",
                    "type": "speak_with_me",
                    "title": {"en": "Steady pacing", "hi": "सधी हुई गति"},
                    "text": "धीमी गति से बोलना बहुत स्वाभाविक है",
                    "latin": "dheemi gati se bolna bahut swaabhaavik hai",
                    "meaning_en": "Speaking calmly and slowly is very natural.",
                    "mode": "paced",
                    "pace_wpm": [50, 75],
                    "feedback": "pace"
                },
                {
                    "id": "easy-starts-4-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did speaking at your own pace feel today?", "hi": "आज अपनी रफ़्तार से बोलना कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        }
    ]

    course = {
        "id": "easy-starts",
        "category_id": "smooth-speaking",
        "title": {"en": "Easy starts", "hi": "आराम से शुरुआत"},
        "summary": {
            "en": "Begin words gently on a calm breath out, stretch sounds, and speak with confidence across four progressive lessons.",
            "hi": "चार पाठों में शब्दों को धीमी साँस पर शुरू करना, ठहराव लेना और आत्मविश्वास से बोलना सीखिए।"
        },
        "what_you_practise": {
            "en": [
                "Breathing out slowly before you speak",
                "Starting sounds softly with light contact",
                "Pausing at natural phrase breaks",
                "Speaking with ease and confidence at your own pace"
            ],
            "hi": [
                "बोलने से पहले धीरे-धीरे साँस छोड़ना",
                "हल्के स्पर्श के साथ आवाज़ शुरू करना",
                "वाक्यों के बीच सहज ठहराव लेना",
                "अपनी रफ़्तार से आत्मविश्वास के साथ बोलना"
            ]
        },
        "level": "beginner",
        "minutes": sum(l["minutes"] for l in lessons),
        "practice_lang": "hi",
        "lessons": lessons
    }
    return course


def build_s_and_sh():
    # 4 lessons, clear-sounds (feedback 'words')
    # Includes all 9 step types (intro, tip, breathing, listen_repeat, speak_with_me, minimal_pairs, read_aloud, dialogue, reflect)
    lessons = [
        {
            "id": "s-and-sh-1",
            "title": {"en": "S and Sh sounds", "hi": "स और श की आवाज़ें"},
            "minutes": 8,
            "steps": [
                {
                    "id": "s-and-sh-1-welcome",
                    "type": "intro",
                    "title": {"en": "Clear S and Sh", "hi": "स और श का अभ्यास"},
                    "body": {
                        "en": "Many people find it helpful to notice where the tongue rests. For s, the tip stays behind your front teeth. For sh, the tongue pulls back slightly.",
                        "hi": "स के लिए जीभ की नोक सामने के दाँतों के पीछे रहती है। श के लिए जीभ थोड़ी पीछे चली जाती है।"
                    }
                },
                {
                    "id": "s-and-sh-1-breathe",
                    "type": "breathing",
                    "title": {"en": "Steady breath", "hi": "संतुलित साँस"},
                    "body": {
                        "en": "Take 4 calm breaths in and out before practising sounds.",
                        "hi": "आवाज़ों का अभ्यास करने से पहले 4 सहज साँसें लीजिए और छोड़िए।"
                    },
                    "pattern": {"in_s": 4, "out_s": 6},
                    "rounds": 4
                },
                {
                    "id": "s-and-sh-1-tongue",
                    "type": "tip",
                    "title": {"en": "Tongue place", "hi": "जीभ की जगह"},
                    "body": {
                        "en": "Smile gently for s. Round your lips a little for sh.",
                        "hi": "स बोलते समय हल्की मुस्कान रखिए। श बोलते समय होंठों को थोड़ा गोल कीजिए।"
                    },
                    "technique_id": "tongue-place"
                },
                {
                    "id": "s-and-sh-1-words",
                    "type": "listen_repeat",
                    "title": {"en": "Listen and repeat S words", "hi": "स वाले शब्द सुनिए और दोहराइए"},
                    "items": [
                        {"id": "sab", "text": "सब", "latin": "sab", "meaning_en": "all", "focus_sound": "s", "audio_key": track_audio("s-and-sh-1-words-sab", "सब")},
                        {"id": "saal", "text": "साल", "latin": "saal", "meaning_en": "year", "focus_sound": "s", "audio_key": track_audio("s-and-sh-1-words-saal", "साल")},
                        {"id": "sona", "text": "सोना", "latin": "sona", "meaning_en": "gold or sleep", "focus_sound": "s", "audio_key": track_audio("s-and-sh-1-words-sona", "सोना")},
                        {"id": "bas", "text": "बस", "latin": "bas", "meaning_en": "bus", "focus_sound": "s", "audio_key": track_audio("s-and-sh-1-words-bas", "बस")},
                        {"id": "raasta", "text": "रास्ता", "latin": "raasta", "meaning_en": "path", "focus_sound": "s", "audio_key": track_audio("s-and-sh-1-words-raasta", "रास्ता")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-1-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "S versus Sh pairs", "hi": "स और श के जोड़े"},
                    "pairs": [
                        {
                            "id": "saadi-shaadi",
                            "a": {"text": "सादी", "latin": "saadi", "audio_key": track_audio("s-and-sh-1-pairs-saadi", "सादी")},
                            "b": {"text": "शादी", "latin": "shaadi", "audio_key": track_audio("s-and-sh-1-pairs-shaadi", "शादी")},
                            "sound_a": "s",
                            "sound_b": "sh"
                        },
                        {
                            "id": "ser-sher",
                            "a": {"text": "सेर", "latin": "ser", "audio_key": track_audio("s-and-sh-1-pairs-ser", "सेर")},
                            "b": {"text": "शेर", "latin": "sher", "audio_key": track_audio("s-and-sh-1-pairs-sher", "शेर")},
                            "sound_a": "s",
                            "sound_b": "sh"
                        }
                    ]
                },
                {
                    "id": "s-and-sh-1-echo",
                    "type": "speak_with_me",
                    "title": {"en": "Sentence full of S", "hi": "स से भरा वाक्य"},
                    "text": "सोनू सुबह सात बजे स्कूल जाता है",
                    "latin": "sonu subah saat baje school jaata hai",
                    "meaning_en": "Sonu goes to school at seven in the morning.",
                    "mode": "echo",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("s-and-sh-1-echo-sonu", "सोनू सुबह सात बजे स्कूल जाता है"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-1-read",
                    "type": "read_aloud",
                    "title": {"en": "Read the evening note", "hi": "शाम का वाक्य पढ़िए"},
                    "paragraph": "शाम को शहर की सड़कों पर बहुत चहल-पहल होती है। सब लोग आराम से घर लौटते हैं।",
                    "latin": "shaam ko shahar ki sadkon par bahut chahal-pahal hoti hai. sab log aaraam se ghar laut-te hain.",
                    "audio_key": track_audio("s-and-sh-1-read-evening", "शाम को शहर की सड़कों पर बहुत चहल-पहल होती है। सब लोग आराम से घर लौटते हैं।"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-1-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did hearing the difference between s and sh feel?", "hi": "स और श के बीच का फ़र्क़ कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "s-and-sh-2",
            "title": {"en": "R and L sounds", "hi": "र और ल की आवाज़ें"},
            "minutes": 8,
            "steps": [
                {
                    "id": "s-and-sh-2-intro",
                    "type": "intro",
                    "title": {"en": "Tongue movement for R and L", "hi": "र और ल के लिए जीभ"},
                    "body": {
                        "en": "For l, the tongue tip rests firmly behind your upper front teeth while air escapes from the sides. For r, the tongue taps lightly against the palate.",
                        "hi": "ल के लिए जीभ की नोक ऊपर के दाँतों के ठीक पीछे लगती है। र के लिए जीभ तालू पर हल्का सा छूती है।"
                    }
                },
                {
                    "id": "s-and-sh-2-tip",
                    "type": "tip",
                    "title": {"en": "Light tap for R", "hi": "र पर हल्का स्पर्श"},
                    "body": {
                        "en": "Many people find it helpful to keep the mouth relaxed so the tongue can tap lightly for r without tension.",
                        "hi": "मुँह को ढीला रखने से जीभ र बोलते समय आराम से छू सकती है।"
                    },
                    "technique_id": "tongue-place"
                },
                {
                    "id": "s-and-sh-2-words",
                    "type": "listen_repeat",
                    "title": {"en": "Repeat R and L words", "hi": "र और ल वाले शब्द"},
                    "items": [
                        {"id": "roti", "text": "रोटी", "latin": "roti", "meaning_en": "flatbread", "focus_sound": "r", "audio_key": track_audio("s-and-sh-2-words-roti", "रोटी")},
                        {"id": "raat", "text": "रात", "latin": "raat", "meaning_en": "night", "focus_sound": "r", "audio_key": track_audio("s-and-sh-2-words-raat", "रात")},
                        {"id": "laal", "text": "लाल", "latin": "laal", "meaning_en": "red", "focus_sound": "l", "audio_key": track_audio("s-and-sh-2-words-laal", "लाल")},
                        {"id": "ladka", "text": "लड़का", "latin": "ladka", "meaning_en": "boy", "focus_sound": "l", "audio_key": track_audio("s-and-sh-2-words-ladka", "लड़का")},
                        {"id": "rang", "text": "रंग", "latin": "rang", "meaning_en": "colour", "focus_sound": "r", "audio_key": track_audio("s-and-sh-2-words-rang", "रंग")},
                        {"id": "log", "text": "लोग", "latin": "log", "meaning_en": "people", "focus_sound": "l", "audio_key": track_audio("s-and-sh-2-words-log", "लोग")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-2-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "R and L word pairs", "hi": "र और ल के जोड़े"},
                    "pairs": [
                        {
                            "id": "raat-laat",
                            "a": {"text": "रात", "latin": "raat", "audio_key": track_audio("s-and-sh-2-pairs-raat", "रात")},
                            "b": {"text": "लात", "latin": "laat", "audio_key": track_audio("s-and-sh-2-pairs-laat", "लात")},
                            "sound_a": "r",
                            "sound_b": "l"
                        },
                        {
                            "id": "roop-loop",
                            "a": {"text": "रोल", "latin": "rol", "audio_key": track_audio("s-and-sh-2-pairs-rol", "रोल")},
                            "b": {"text": "लोल", "latin": "lol", "audio_key": track_audio("s-and-sh-2-pairs-lol", "लोल")},
                            "sound_a": "r",
                            "sound_b": "l"
                        }
                    ]
                },
                {
                    "id": "s-and-sh-2-choral",
                    "type": "speak_with_me",
                    "title": {"en": "Choral sentence with R and L", "hi": "र और ल का मिलाजुला वाक्य"},
                    "text": "रेल गाड़ी रात को लाल बत्ती देखकर रुकी",
                    "latin": "rel gaadi raat ko laal batti dekhkar ruki",
                    "meaning_en": "The train stopped at night seeing the red signal.",
                    "mode": "choral",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("s-and-sh-2-choral-train", "रेल गाड़ी रात को लाल बत्ती देखकर रुकी"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-2-read",
                    "type": "read_aloud",
                    "title": {"en": "Short paragraph with R and L", "hi": "र और ल का छोटा गद्यांश"},
                    "paragraph": "रमेश बाज़ार से लाल टमाटर लाया। उसने रोटी के साथ दाल और सलाद खाया। सब लोगों ने मिलकर भोजन किया।",
                    "latin": "ramesh baazaar se laal tamaatar laaya. usne roti ke saath daal aur salaad khaaya. sab logon ne milkar bhojan kiya.",
                    "audio_key": track_audio("s-and-sh-2-read-meal", "रमेश बाज़ार से लाल टमाटर लाया। उसने रोटी के साथ दाल और सलाद खाया। सब लोगों ने मिलकर भोजन किया।"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-2-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did distinguishing r and l feel?", "hi": "र और ल के बीच फ़र्क़ समझना कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "s-and-sh-3",
            "title": {"en": "Dental and retroflex sounds", "hi": "त-द और ट-ड की आवाज़ें"},
            "minutes": 8,
            "steps": [
                {
                    "id": "s-and-sh-3-intro",
                    "type": "intro",
                    "title": {"en": "Soft dental versus curled retroflex", "hi": "दाँत और तालू का फ़र्क़"},
                    "body": {
                        "en": "Dental sounds (त, द) touch the front teeth gently. Retroflex sounds (ट, ड) touch higher up as the tongue curls back slightly.",
                        "hi": "त और द बोलते समय जीभ सामने के दाँतों को छूती है। ट और ड बोलते समय जीभ थोड़ा पीछे मुड़कर तालू को छूती है।"
                    }
                },
                {
                    "id": "s-and-sh-3-tip",
                    "type": "tip",
                    "title": {"en": "Noticing tooth contact", "hi": "दाँतों के स्पर्श पर ध्यान"},
                    "body": {
                        "en": "Many people find it helpful to place the tongue gently against the back of the top teeth for त and द.",
                        "hi": "त और द के लिए जीभ को ऊपर के दाँतों के पीछे हल्के से लगाने का अभ्यास कीजिए।"
                    },
                    "technique_id": "tongue-place"
                },
                {
                    "id": "s-and-sh-3-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "Dental versus retroflex pairs", "hi": "त और ट के जोड़े"},
                    "pairs": [
                        {
                            "id": "taala-taala",
                            "a": {"text": "ताल", "latin": "taal", "audio_key": track_audio("s-and-sh-3-pairs-taal", "ताल")},
                            "b": {"text": "टाल", "latin": "taal", "audio_key": track_audio("s-and-sh-3-pairs-ttaal", "टाल")},
                            "sound_a": "t-dental",
                            "sound_b": "t-retroflex"
                        },
                        {
                            "id": "daal-daal",
                            "a": {"text": "दाल", "latin": "daal", "audio_key": track_audio("s-and-sh-3-pairs-daal", "दाल")},
                            "b": {"text": "डाल", "latin": "daal", "audio_key": track_audio("s-and-sh-3-pairs-ddaal", "डाल")},
                            "sound_a": "d",
                            "sound_b": "t-retroflex"
                        }
                    ]
                },
                {
                    "id": "s-and-sh-3-words",
                    "type": "listen_repeat",
                    "title": {"en": "Repeat dental and retroflex words", "hi": "त, द, ट, ड वाले शब्द"},
                    "items": [
                        {"id": "teen", "text": "तीन", "latin": "teen", "meaning_en": "three", "focus_sound": "t-dental", "audio_key": track_audio("s-and-sh-3-words-teen", "तीन")},
                        {"id": "taara", "text": "तारा", "latin": "taara", "meaning_en": "star", "focus_sound": "t-dental", "audio_key": track_audio("s-and-sh-3-words-taara", "तारा")},
                        {"id": "tamaatar", "text": "टमाटर", "latin": "tamaatar", "meaning_en": "tomato", "focus_sound": "t-retroflex", "audio_key": track_audio("s-and-sh-3-words-tamaatar", "टमाटर")},
                        {"id": "topi", "text": "टोपी", "latin": "topi", "meaning_en": "cap", "focus_sound": "t-retroflex", "audio_key": track_audio("s-and-sh-3-words-topi", "टोपी")},
                        {"id": "darvaaza", "text": "दरवाज़ा", "latin": "darvaaza", "meaning_en": "door", "focus_sound": "d", "audio_key": track_audio("s-and-sh-3-words-darvaaza", "दरवाज़ा")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-3-echo",
                    "type": "speak_with_me",
                    "title": {"en": "Echo sentence", "hi": "सुनकर दोहराइए"},
                    "text": "छोटे बच्चे ने टोकरी में टमाटर डाले",
                    "latin": "chhote bachche ne tokri mein tamaatar daale",
                    "meaning_en": "The little child put tomatoes into the basket.",
                    "mode": "echo",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("s-and-sh-3-echo-basket", "छोटे बच्चे ने टोकरी में टमाटर डाले"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-3-dialogue",
                    "type": "dialogue",
                    "title": {"en": "At the vegetable shop", "hi": "सब्ज़ी की दुकान पर"},
                    "scenario": {
                        "en": "You are shopping for fresh vegetables.",
                        "hi": "आप ताज़ा सब्ज़ियाँ खरीद रहे हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते! आज क्या सब्ज़ी लेंगे?", "latin": "namaste! aaj kya sabzi lenge?", "audio_key": track_audio("s-and-sh-3-dialogue-1", "नमस्ते! आज क्या सब्ज़ी लेंगे?")},
                        {
                            "speaker": "you",
                            "text": "एक किलो लाल टमाटर और ताज़ा मटर दीजिए।",
                            "latin": "ek kilo laal tamaatar aur taaza matar deejiye.",
                            "options": [{"text": "दो किलो आलू और आधा किलो टमाटर।", "latin": "do kilo aalu aur aadha kilo tamaatar."}]
                        },
                        {"speaker": "sunn", "text": "बिल्कुल, टोकरी में रख दिया है।", "latin": "bilkul, tokri mein rakh diya hai.", "audio_key": track_audio("s-and-sh-3-dialogue-2", "बिल्कुल, टोकरी में रख दिया है।")},
                        {"speaker": "you", "text": "बहुत धन्यवाद भैया।", "latin": "bahut dhanyavaad bhaiya."}
                    ]
                },
                {
                    "id": "s-and-sh-3-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did dental and retroflex sounds feel?", "hi": "दाँत और तालू के अक्षरों का अभ्यास कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "s-and-sh-4",
            "title": {"en": "Plain and aspirated sounds", "hi": "साधारण और हवा वाली आवाज़ें"},
            "minutes": 8,
            "steps": [
                {
                    "id": "s-and-sh-4-intro",
                    "type": "intro",
                    "title": {"en": "The gentle puff of air", "hi": "हवा का हल्का झोंका"},
                    "body": {
                        "en": "Some Hindi sounds have extra breath (ख, घ, फ, भ). Plain sounds (क, ग, प, ब) release gently with minimal breath.",
                        "hi": "ख, घ, फ, भ बोलते समय मुँह से थोड़ी हवा निकलती है। क, ग, प, ब बोलते समय हवा बहुत कम निकलती है।"
                    }
                },
                {
                    "id": "s-and-sh-4-tip",
                    "type": "tip",
                    "title": {"en": "Feeling the breath", "hi": "हवा को महसूस करना"},
                    "body": {
                        "en": "Many people hold a hand in front of their mouth. You can feel a warm puff of air on फ and ख.",
                        "hi": "हाथ को मुँह के आगे रखकर देखिए। फ और ख बोलते समय हथेली पर हवा का अहसास होता है।"
                    },
                    "technique_id": "easy-start"
                },
                {
                    "id": "s-and-sh-4-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "Plain and aspirated pairs", "hi": "साधारण और हवा वाले जोड़े"},
                    "pairs": [
                        {
                            "id": "pal-phal",
                            "a": {"text": "पल", "latin": "pal", "audio_key": track_audio("s-and-sh-4-pairs-pal", "पल")},
                            "b": {"text": "फल", "latin": "phal", "audio_key": track_audio("s-and-sh-4-pairs-phal", "फल")},
                            "sound_a": "p",
                            "sound_b": "aspirated"
                        },
                        {
                            "id": "kal-khal",
                            "a": {"text": "कल", "latin": "kal", "audio_key": track_audio("s-and-sh-4-pairs-kal", "कल")},
                            "b": {"text": "खल", "latin": "khal", "audio_key": track_audio("s-and-sh-4-pairs-khal", "खल")},
                            "sound_a": "k",
                            "sound_b": "aspirated"
                        }
                    ]
                },
                {
                    "id": "s-and-sh-4-words",
                    "type": "listen_repeat",
                    "title": {"en": "Aspirated words", "hi": "हवा वाली आवाज़ों का अभ्यास"},
                    "items": [
                        {"id": "khaana", "text": "खाना", "latin": "khaana", "meaning_en": "food", "focus_sound": "aspirated", "audio_key": track_audio("s-and-sh-4-words-khaana", "खाना")},
                        {"id": "ghar", "text": "घर", "latin": "ghar", "meaning_en": "home", "focus_sound": "aspirated", "audio_key": track_audio("s-and-sh-4-words-ghar", "घर")},
                        {"id": "bhaalu", "text": "भालू", "latin": "bhaalu", "meaning_en": "bear", "focus_sound": "aspirated", "audio_key": track_audio("s-and-sh-4-words-bhaalu", "भालू")},
                        {"id": "thoda", "text": "थोड़ा", "latin": "thoda", "meaning_en": "a little", "focus_sound": "aspirated", "audio_key": track_audio("s-and-sh-4-words-thoda", "थोड़ा")},
                        {"id": "kheer", "text": "खीर", "latin": "kheer", "meaning_en": "sweet pudding", "focus_sound": "aspirated", "audio_key": track_audio("s-and-sh-4-words-kheer", "खीर")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-4-choral",
                    "type": "speak_with_me",
                    "title": {"en": "Choral sentence", "hi": "साथ मिलकर बोलिए"},
                    "text": "कमल ने फल खाकर पानी पिया",
                    "latin": "kamal ne phal khaakar paani piya",
                    "meaning_en": "Kamal ate fruit and drank water.",
                    "mode": "choral",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("s-and-sh-4-choral-fruit", "कमल ने फल खाकर पानी पिया"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-4-read",
                    "type": "read_aloud",
                    "title": {"en": "Short read with aspirated sounds", "hi": "हवा वाली आवाज़ों का पाठ"},
                    "paragraph": "आज घर में गरमा-गरम खाना बना है। थाली में खीर और फल भी रखे हैं। सबने खुशी-खुशी भोजन किया।",
                    "latin": "aaj ghar mein garma-garam khaana bana hai. thaali mein kheer aur phal bhi rakhe hain. sabne khushi-khushi bhojan kiya.",
                    "audio_key": track_audio("s-and-sh-4-read-dinner", "आज घर में गरमा-गरम खाना बना है। थाली में खीर और फल भी रखे हैं। सबने खुशी-खुशी भोजन किया।"),
                    "feedback": "words"
                },
                {
                    "id": "s-and-sh-4-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did balancing plain and breathy sounds feel?", "hi": "साधारण और हवा वाली आवाज़ों का संतुलन कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        }
    ]

    course = {
        "id": "s-and-sh",
        "category_id": "clear-sounds",
        "title": {"en": "S and Sh", "hi": "स और श"},
        "summary": {
            "en": "Hear the differences between clear sounds, practice tongue placement, and build clear pronunciation step by step.",
            "hi": "स, श, र, ल और अन्य ध्वनियों का फ़र्क़ समझिए और साफ़ उच्चारण का अभ्यास कीजिए।"
        },
        "what_you_practise": {
            "en": [
                "Tongue placement for s and sh",
                "Differences between r and l sounds",
                "Dental versus retroflex consonants",
                "Gentle airflow for aspirated sounds"
            ],
            "hi": [
                "स और श के लिए जीभ की सही जगह",
                "र और ल की आवाज़ों में फ़र्क़",
                "दाँत और तालू के अक्षरों का अभ्यास",
                "हवा वाली आवाज़ों में सहज प्रवाह"
            ]
        },
        "level": "beginner",
        "minutes": sum(l["minutes"] for l in lessons),
        "practice_lang": "hi",
        "lessons": lessons
    }
    return course


def build_sound_play():
    # 4 lessons, kids-speaking (feedback ONLY 'none' or 'pace')
    # Includes all 9 step types (intro, tip, breathing, listen_repeat, speak_with_me, minimal_pairs, read_aloud, dialogue, reflect)
    lessons = [
        {
            "id": "sound-play-1",
            "title": {"en": "Animal and vehicle sounds", "hi": "जानवरों और गाड़ियों की आवाज़ें"},
            "minutes": 8,
            "steps": [
                {
                    "id": "sound-play-1-intro",
                    "type": "intro",
                    "title": {"en": "Tips for the adult", "hi": "साथी बड़े के लिए सुझाव"},
                    "body": {
                        "en": "Be patient, praise every try, and keep it short. There are no scores here. Follow the child's natural pace.",
                        "hi": "धैर्य रखिए, हर कोशिश की तारीफ कीजिए, और छोटा रखिए। यहाँ कोई नंबर नहीं हैं। बच्चे की अपनी गति के साथ चलिए।"
                    }
                },
                {
                    "id": "sound-play-1-breathe",
                    "type": "breathing",
                    "title": {"en": "Bunny breathing", "hi": "प्यारा खरगोश साँस"},
                    "body": {
                        "en": "Sniff in like a gentle bunny for 3 seconds, then breathe out softly for 5 seconds.",
                        "hi": "खरगोश की तरह 3 सेकंड नाक से साँस लीजिए, फिर 5 सेकंड में आराम से छोड़िए।"
                    },
                    "pattern": {"in_s": 3, "out_s": 5},
                    "rounds": 3
                },
                {
                    "id": "sound-play-1-animals",
                    "type": "listen_repeat",
                    "title": {"en": "Animal friends", "hi": "प्यारे जानवर"},
                    "items": [
                        {"id": "lion", "text": "शेर बोला दहाड़", "latin": "sher bola dahaad", "meaning_en": "the lion roared", "audio_key": track_audio("sound-play-1-animals-lion", "शेर बोला दहाड़")},
                        {"id": "cow", "text": "गाय बोली मूँ-मूँ", "latin": "gaay boli moo-moo", "meaning_en": "the cow says moo", "audio_key": track_audio("sound-play-1-animals-cow", "गाय बोली मूँ-मूँ")},
                        {"id": "bird", "text": "चिड़िया बोली चीं-चीं", "latin": "chidiya boli cheen-cheen", "meaning_en": "the bird chirps", "audio_key": track_audio("sound-play-1-animals-bird", "चिड़िया बोली चीं-चीं")},
                        {"id": "cat", "text": "बिल्ली बोली म्याऊँ", "latin": "billi boli myaaoon", "meaning_en": "the cat says meow", "audio_key": track_audio("sound-play-1-animals-cat", "बिल्ली बोली म्याऊँ")}
                    ],
                    "feedback": "none"
                },
                {
                    "id": "sound-play-1-tip",
                    "type": "tip",
                    "title": {"en": "Take turns", "hi": "बारी-बारी बोलिए"},
                    "body": {
                        "en": "Say the line first and smile. Then invite the child to say it with you.",
                        "hi": "पहले आप बोलिए और मुस्कुराइए। फिर बच्चे को साथ बोलने के लिए कहिए।"
                    },
                    "technique_id": "take-turns"
                },
                {
                    "id": "sound-play-1-vehicles",
                    "type": "listen_repeat",
                    "title": {"en": "Speedy vehicles", "hi": "तेज़ गाड़ियाँ"},
                    "items": [
                        {"id": "train", "text": "छुक-छुक रेल", "latin": "chhuk-chhuk rel", "meaning_en": "chug-chug train", "audio_key": track_audio("sound-play-1-vehicles-train", "छुक-छुक रेल")},
                        {"id": "car", "text": "पी-पी कार", "latin": "pee-pee car", "meaning_en": "honk-honk car", "audio_key": track_audio("sound-play-1-vehicles-car", "पी-पी कार")},
                        {"id": "bus", "text": "पूँ-पूँ बस", "latin": "poon-poon bas", "meaning_en": "beep-beep bus", "audio_key": track_audio("sound-play-1-vehicles-bus", "पूँ-पूँ बस")}
                    ],
                    "feedback": "none"
                },
                {
                    "id": "sound-play-1-choral",
                    "type": "speak_with_me",
                    "title": {"en": "Train song together", "hi": "रेल की सवारी"},
                    "text": "छुक-छुक रेल चली, पी-पी हॉर्न बजा",
                    "latin": "chhuk-chhuk rel chali, pee-pee horn baja",
                    "meaning_en": "The train rolls chug-chug, the horn goes beep-beep.",
                    "mode": "choral",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("sound-play-1-choral-train", "छुक-छुक रेल चली, पी-पी हॉर्न बजा"),
                    "feedback": "pace"
                },
                {
                    "id": "sound-play-1-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "Did you both have fun playing with animal and vehicle sounds?", "hi": "क्या आप दोनों को जानवरों और गाड़ियों की आवाज़ों में मज़ा आया?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "sound-play-2",
            "title": {"en": "Rhymes and silly games", "hi": "तुकबंदी और मज़ाकिया खेल"},
            "minutes": 8,
            "steps": [
                {
                    "id": "sound-play-2-intro",
                    "type": "intro",
                    "title": {"en": "Playful rhymes", "hi": "हँसते-गाते तुकबंदी"},
                    "body": {
                        "en": "Rhyming words help children tune in to sounds easily without feeling tested.",
                        "hi": "तुकबंदी वाले शब्दों से बच्चे खेल-खेल में आवाज़ों को पहचानना सीखते हैं।"
                    }
                },
                {
                    "id": "sound-play-2-rhyme",
                    "type": "read_aloud",
                    "title": {"en": "The little butterfly", "hi": "नन्हीं तितली"},
                    "paragraph": "तितली उड़ी बस पर चढ़ी, सीट ना मिली तो रोने लगी। ड्राइवर ने बोला आजा मेरे पास, तितली बोली ना बाबा ना!",
                    "latin": "titli udi bas par chadhi, seat na mili to rone lagi. driver ne bola aaja mere paas, titli boli na baba na!",
                    "audio_key": track_audio("sound-play-2-rhyme-butterfly", "तितली उड़ी बस पर चढ़ी, सीट ना मिली तो रोने लगी। ड्राइवर ने बोला आजा मेरे पास, तितली बोली ना बाबा ना!"),
                    "feedback": "pace"
                },
                {
                    "id": "sound-play-2-tip",
                    "type": "tip",
                    "title": {"en": "Silly voices", "hi": "मज़ाकिया आवाज़"},
                    "body": {
                        "en": "Try saying lines in a tiny whisper or a funny big voice to keep it joyful.",
                        "hi": "धीमी फुसफुसाहट या मज़ाकिया आवाज़ में बोलिए ताकि खेल में हँसी बनी रहे।"
                    },
                    "technique_id": "slow-pace"
                },
                {
                    "id": "sound-play-2-shop",
                    "type": "dialogue",
                    "title": {"en": "Pretend toy shop", "hi": "खिलौनों की दुकान"},
                    "scenario": {
                        "en": "You and Sunn are visiting a magical toy shop.",
                        "hi": "आप और Sunn खिलौनों की एक जादुई दुकान में हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते दोस्त! आपको कौन सा खिलौना चाहिए?", "latin": "namaste dost! aapko kaun sa khilauna chaahiye?", "audio_key": track_audio("sound-play-2-shop-1", "नमस्ते दोस्त! आपको कौन सा खिलौना चाहिए?")},
                        {
                            "speaker": "you",
                            "text": "मुझे वो नीली कार चाहिए।",
                            "latin": "mujhe wo neeli car chaahiye.",
                            "options": [{"text": "मुझे वो लाल गेंद चाहिए।", "latin": "mujhe wo laal gend chaahiye."}]
                        },
                        {"speaker": "sunn", "text": "ये लीजिए! बहुत प्यारा खिलौना है।", "latin": "ye leejiye! bahut pyaara khilauna hai.", "audio_key": track_audio("sound-play-2-shop-2", "ये लीजिए! बहुत प्यारा खिलौना है।")},
                        {"speaker": "you", "text": "शुक्रिया भैया, बहुत मज़ा आया!", "latin": "shukriya bhaiya, bahut maza aaya!"}
                    ]
                },
                {
                    "id": "sound-play-2-echo",
                    "type": "speak_with_me",
                    "title": {"en": "Playful monkey echo", "hi": "नटखट बंदर"},
                    "text": "नटखट बंदर डाल पर कूदा",
                    "latin": "natkhat bandar daal par kooda",
                    "meaning_en": "The playful monkey leaped on the branch.",
                    "mode": "echo",
                    "pace_wpm": [55, 85],
                    "audio_key": track_audio("sound-play-2-echo-monkey", "नटखट बंदर डाल पर कूदा"),
                    "feedback": "pace"
                },
                {
                    "id": "sound-play-2-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did the playful toy shop and rhyme feel?", "hi": "खिलौनों की दुकान और तुकबंदी में कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "sound-play-3",
            "title": {"en": "Robot and lion game", "hi": "रोबोट और शेर का खेल"},
            "minutes": 8,
            "steps": [
                {
                    "id": "sound-play-3-intro",
                    "type": "intro",
                    "title": {"en": "Characters game", "hi": "मज़ेदार किरदार"},
                    "body": {
                        "en": "Playing characters like a robot or a friendly lion lets children speak without worrying about making mistakes.",
                        "hi": "रोबोट या प्यारे शेर का किरदार निभाकर बच्चे बिना झिझक के मजे से बोलते हैं।"
                    }
                },
                {
                    "id": "sound-play-3-tip",
                    "type": "tip",
                    "title": {"en": "Big lion breath", "hi": "शेर जैसी साँस"},
                    "body": {
                        "en": "Take a big easy breath before roaring. No pressure, just big smiles.",
                        "hi": "बोलने से पहले एक गहरी और आरामदेह साँस लीजिए। मुस्कान बनाए रखिए।"
                    },
                    "technique_id": "easy-start"
                },
                {
                    "id": "sound-play-3-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "Fun sound pairs", "hi": "मज़ेदार आवाज़ों के जोड़े"},
                    "pairs": [
                        {
                            "id": "gaay-bhaalu",
                            "a": {"text": "गाय", "latin": "gaay", "audio_key": track_audio("sound-play-3-pairs-gaay", "गाय")},
                            "b": {"text": "भालू", "latin": "bhaalu", "audio_key": track_audio("sound-play-3-pairs-bhaalu", "भालू")},
                            "sound_a": "g",
                            "sound_b": "aspirated"
                        }
                    ]
                },
                {
                    "id": "sound-play-3-robot",
                    "type": "listen_repeat",
                    "title": {"en": "Talk like a robot", "hi": "रोबोट की आवाज़"},
                    "items": [
                        {"id": "hello", "text": "ह-लो दो-स्त", "latin": "ha-lo do-st", "meaning_en": "hel-lo friend", "audio_key": track_audio("sound-play-3-robot-hello", "ह-लो दो-स्त")},
                        {"id": "namaste", "text": "न-म-स्ते", "latin": "na-ma-ste", "meaning_en": "greetings", "audio_key": track_audio("sound-play-3-robot-namaste", "न-म-स्ते")},
                        {"id": "super", "text": "सु-प-र रो-बो-ट", "latin": "su-pa-r ro-bo-t", "meaning_en": "super robot", "audio_key": track_audio("sound-play-3-robot-super", "सु-प-र रो-बो-ट")}
                    ],
                    "feedback": "none"
                },
                {
                    "id": "sound-play-3-lion",
                    "type": "speak_with_me",
                    "title": {"en": "Lion roar together", "hi": "शेर की दहाड़"},
                    "text": "शेर बोला आहा, आज बड़ा मज़ा आया",
                    "latin": "sher bola aaha, aaj bada maza aaya",
                    "meaning_en": "The lion said aha, today was great fun.",
                    "mode": "echo",
                    "pace_wpm": [55, 85],
                    "audio_key": track_audio("sound-play-3-lion-roar", "शेर बोला आहा, आज बड़ा मज़ा आया"),
                    "feedback": "pace"
                },
                {
                    "id": "sound-play-3-dialogue",
                    "type": "dialogue",
                    "title": {"en": "The friendly robot chat", "hi": "रोबोट की बातचीत"},
                    "scenario": {
                        "en": "A friendly robot asks about your favorite game.",
                        "hi": "एक प्यारा रोबोट आपके पसंदीदा खेल के बारे में पूछ रहा है।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "बीप-बीप! आज हम क्या खेलेंगे?", "latin": "beep-beep! aaj hum kya khelenge?", "audio_key": track_audio("sound-play-3-dialogue-1", "बीप-बीप! आज हम क्या खेलेंगे?")},
                        {
                            "speaker": "you",
                            "text": "हम शेर और जंगल का खेल खेलेंगे।",
                            "latin": "hum sher aur jangal ka khel khelenge.",
                            "options": [{"text": "हम दौड़ लगाने का खेल खेलेंगे।", "latin": "hum daud lagaane ka khel khelenge."}]
                        },
                        {"speaker": "sunn", "text": "वाह! बीप-बीप, चलो शुरू करते हैं!", "latin": "waah! beep-beep, chalo shuru karte hain!", "audio_key": track_audio("sound-play-3-dialogue-2", "वाह! बीप-बीप, चलो शुरू करते हैं!")},
                        {"speaker": "you", "text": "चलो रोबोट दोस्त!", "latin": "chalo robot dost!"}
                    ]
                },
                {
                    "id": "sound-play-3-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "Did you like speaking like a robot and a lion?", "hi": "क्या रोबोट और शेर की आवाज़ में बोलने में मज़ा आया?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "sound-play-4",
            "title": {"en": "The little squirrel's tree", "hi": "नन्हीं गिलहरी का पेड़"},
            "minutes": 8,
            "steps": [
                {
                    "id": "sound-play-4-intro",
                    "type": "intro",
                    "title": {"en": "Storytime together", "hi": "कहानी का समय"},
                    "body": {
                        "en": "Here is a gentle story to read together. Read one sentence each and pause to look at what happens next.",
                        "hi": "यहाँ साथ मिलकर पढ़ने के लिए एक छोटी कहानी है। बारी-बारी से पढ़िए और आनंद लीजिए।"
                    }
                },
                {
                    "id": "sound-play-4-tip",
                    "type": "tip",
                    "title": {"en": "Praise the effort", "hi": "प्रयास की सराहना"},
                    "body": {
                        "en": "Every word your child tries is worth celebrating. Give a cheerful high five at the end.",
                        "hi": "बच्चे के हर बोले गए शब्द की सराहना कीजिए। कहानी के अंत में शाबाशी दीजिए।"
                    },
                    "technique_id": "take-turns"
                },
                {
                    "id": "sound-play-4-story",
                    "type": "read_aloud",
                    "title": {"en": "Munnu the little squirrel", "hi": "मुन्नू नन्हीं गिलहरी"},
                    "paragraph": "एक नन्हीं गिलहरी थी। उसका नाम मुन्नू था। मुन्नू को हरे-भरे आम के पेड़ पर चढ़ना बहुत पसंद था। वह रोज़ नए दोस्त बनाती थी।",
                    "latin": "ek nanhin gilahri thi. uska naam munnu tha. munnu ko hare-bhare aam ke ped par chadhna bahut pasand tha. wah roz naye dost banaati thi.",
                    "audio_key": track_audio("sound-play-4-story-munnu", "एक नन्हीं गिलहरी थी। उसका नाम मुन्नू था। मुन्नू को हरे-भरे आम के पेड़ पर चढ़ना बहुत पसंद था। वह रोज़ नए दोस्त बनाती थी।"),
                    "feedback": "pace"
                },
                {
                    "id": "sound-play-4-dialogue",
                    "type": "dialogue",
                    "title": {"en": "What did Munnu find?", "hi": "मुन्नू को क्या मिला?"},
                    "scenario": {
                        "en": "Sunn asks you what Munnu found on the tree branch.",
                        "hi": "Sunn पूछ रहा है कि मुन्नू को पेड़ की डाल पर क्या मिला।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "पेड़ पर मुन्नू को क्या मिला होगा?", "latin": "ped par munnu ko kya mila hoga?", "audio_key": track_audio("sound-play-4-dialogue-1", "पेड़ पर मुन्नू को क्या मिला होगा?")},
                        {
                            "speaker": "you",
                            "text": "मुन्नू को एक मीठा पीला आम मिला।",
                            "latin": "munnu ko ek meetha peela aam mila.",
                            "options": [{"text": "मुन्नू को एक नन्ही चिड़िया दोस्त मिली।", "latin": "munnu ko ek nanhi chidiya dost mili."}]
                        },
                        {"speaker": "sunn", "text": "अरे वाह! दोनों ने मिलकर खुशी मनाई।", "latin": "are waah! dono ne milkar khushi manaai.", "audio_key": track_audio("sound-play-4-dialogue-2", "अरे वाह! दोनों ने मिलकर खुशी मनाई।")},
                        {"speaker": "you", "text": "और फिर सब मिलकर हँसने लगे।", "latin": "aur phir sab milkar hansne lage."}
                    ]
                },
                {
                    "id": "sound-play-4-paced",
                    "type": "speak_with_me",
                    "title": {"en": "Celebration line", "hi": "खुशी का गीत"},
                    "text": "मुन्नू गिलहरी हँसी और ताली बजाई",
                    "latin": "munnu gilahri hansi aur taali bajaai",
                    "meaning_en": "Munnu squirrel laughed and clapped her hands.",
                    "mode": "paced",
                    "pace_wpm": [50, 75],
                    "feedback": "pace"
                },
                {
                    "id": "sound-play-4-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did reading Munnu's story together feel?", "hi": "मुन्नू की कहानी साथ में पढ़कर कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        }
    ]

    course = {
        "id": "sound-play",
        "category_id": "kids-speaking",
        "title": {"en": "Fun with sounds", "hi": "आवाज़ों से खेल"},
        "summary": {
            "en": "Short, playful sound games for children to explore together with an adult, completely free of pressure or scoring.",
            "hi": "किसी बड़े के साथ मिलकर खेलने के लिए छोटे खेल, बिना किसी दबाव या अंकों के।"
        },
        "what_you_practise": {
            "en": [
                "Imitating fun animal and vehicle sounds",
                "Rhyming words and silly voices",
                "Robot and lion character play",
                "Reading a gentle short story together"
            ],
            "hi": [
                "जानवरों और गाड़ियों की आवाज़ों की नकल",
                "तुकबंदी और मज़ाकिया आवाज़ें",
                "रोबोट और शेर के मजेदार खेल",
                "साथ मिलकर एक प्यारी कहानी पढ़ना"
            ]
        },
        "level": "beginner",
        "minutes": sum(l["minutes"] for l in lessons),
        "practice_lang": "hi",
        "lessons": lessons
    }
    return course


def build_introductions():
    # 4 lessons, everyday-talk (feedback 'words')
    # Includes all 9 step types (intro, tip, breathing, listen_repeat, speak_with_me, minimal_pairs, read_aloud, dialogue, reflect)
    lessons = [
        {
            "id": "introductions-1",
            "title": {"en": "Hello and your name", "hi": "नमस्ते और आपका नाम"},
            "minutes": 8,
            "steps": [
                {
                    "id": "introductions-1-welcome",
                    "type": "intro",
                    "title": {"en": "Simple greetings", "hi": "साधारण नमस्ते"},
                    "body": {
                        "en": "Meeting someone starts with a calm greeting. Practise saying hello and giving your name with ease.",
                        "hi": "किसी से मिलना एक शांत नमस्ते से शुरू होता है। आराम से अपना नाम बताने का अभ्यास कीजिए।"
                    }
                },
                {
                    "id": "introductions-1-breathe",
                    "type": "breathing",
                    "title": {"en": "Calm breath before greeting", "hi": "नमस्ते से पहले शांत साँस"},
                    "body": {
                        "en": "Take 4 slow breaths in and out before beginning your greeting.",
                        "hi": "अभिवादन शुरू करने से पहले 4 सहज साँसें लीजिए और छोड़िए।"
                    },
                    "pattern": {"in_s": 4, "out_s": 6},
                    "rounds": 4
                },
                {
                    "id": "introductions-1-tip",
                    "type": "tip",
                    "title": {"en": "Gentle breath first", "hi": "पहले एक हल्की साँस"},
                    "body": {
                        "en": "Many people find it helpful to take a small breath before greeting someone. There is no rush.",
                        "hi": "नमस्ते कहने से पहले एक हल्की साँस लेना मददगार होता है। कोई जल्दबाज़ी नहीं है।"
                    },
                    "technique_id": "easy-start"
                },
                {
                    "id": "introductions-1-pairs",
                    "type": "minimal_pairs",
                    "title": {"en": "Gentle greeting pairs", "hi": "मिलते-जुलते शब्द"},
                    "pairs": [
                        {
                            "id": "baat-bhaat",
                            "a": {"text": "बात", "latin": "baat", "audio_key": track_audio("introductions-1-pairs-baat", "बात")},
                            "b": {"text": "भात", "latin": "bhaat", "audio_key": track_audio("introductions-1-pairs-bhaat", "भात")},
                            "sound_a": "b",
                            "sound_b": "aspirated"
                        }
                    ]
                },
                {
                    "id": "introductions-1-greetings",
                    "type": "listen_repeat",
                    "title": {"en": "Common greetings", "hi": "रोज़ के अभिवादन"},
                    "items": [
                        {"id": "namaste", "text": "नमस्ते", "latin": "namaste", "meaning_en": "hello", "audio_key": track_audio("introductions-1-greetings-namaste", "नमस्ते")},
                        {"id": "suprabhaat", "text": "सुप्रभात", "latin": "suprabhaat", "meaning_en": "good morning", "audio_key": track_audio("introductions-1-greetings-suprabhaat", "सुप्रभात")},
                        {"id": "aap-kaise-hain", "text": "आप कैसे हैं?", "latin": "aap kaise hain?", "meaning_en": "how are you?", "audio_key": track_audio("introductions-1-greetings-aap-kaise-hain", "आप कैसे हैं?")},
                        {"id": "main-theek-hoon", "text": "मैं ठीक हूँ", "latin": "main theek hoon", "meaning_en": "I am well", "audio_key": track_audio("introductions-1-greetings-main-theek-hoon", "मैं ठीक हूँ")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "introductions-1-dialogue",
                    "type": "dialogue",
                    "title": {"en": "Meeting for the first time", "hi": "पहली मुलाक़ात"},
                    "scenario": {
                        "en": "You are meeting a new colleague or neighbor.",
                        "hi": "आप किसी नए साथी या पड़ोसी से मिल रहे हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते! मेरा नाम रोहन है।", "latin": "namaste! mera naam rohan hai.", "audio_key": track_audio("introductions-1-dialogue-1", "नमस्ते! मेरा नाम रोहन है।")},
                        {
                            "speaker": "you",
                            "text": "नमस्ते, मेरा नाम कबीर है।",
                            "latin": "namaste, mera naam kabir hai.",
                            "options": [{"text": "नमस्ते, आपसे मिलकर बहुत खुशी हुई।", "latin": "namaste, aap se milkar bahut khushi hui."}]
                        },
                        {"speaker": "sunn", "text": "आपसे मिलकर बहुत अच्छा लगा!", "latin": "aap se milkar bahut achchha laga!", "audio_key": track_audio("introductions-1-dialogue-2", "आपसे मिलकर बहुत अच्छा लगा!")},
                        {"speaker": "you", "text": "धन्यवाद, मुझे भी बहुत अच्छा लगा।", "latin": "dhanyavaad, mujhe bhi bahut achchha laga."}
                    ]
                },
                {
                    "id": "introductions-1-echo",
                    "type": "speak_with_me",
                    "title": {"en": "Introducing yourself", "hi": "अपना परिचय"},
                    "text": "नमस्ते, मेरा नाम राहुल है",
                    "latin": "namaste, mera naam rahul hai",
                    "meaning_en": "Hello, my name is Rahul.",
                    "mode": "echo",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("introductions-1-echo-rahul", "नमस्ते, मेरा नाम राहुल है"),
                    "feedback": "words"
                },
                {
                    "id": "introductions-1-read",
                    "type": "read_aloud",
                    "title": {"en": "Self introduction paragraph", "hi": "परिचय का छोटा वाक्य"},
                    "paragraph": "नमस्ते, मेरा नाम समीर है। मैं दिल्ली में रहता हूँ। मुझे नई किताबें पढ़ना और संगीत सुनना पसंद है।",
                    "latin": "namaste, mera naam sameer hai. main dilli mein rahta hoon. mujhe nayi kitaabein padhna aur sangeet sunna pasand hai.",
                    "audio_key": track_audio("introductions-1-read-intro", "नमस्ते, मेरा नाम समीर है। मैं दिल्ली में रहता हूँ। मुझे नई किताबें पढ़ना और संगीत सुनना पसंद है।"),
                    "feedback": "words"
                },
                {
                    "id": "introductions-1-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did introducing yourself feel today?", "hi": "आज अपना परिचय देना कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "introductions-2",
            "title": {"en": "At the shop and on the phone", "hi": "दुकान पर और फ़ोन पर"},
            "minutes": 8,
            "steps": [
                {
                    "id": "introductions-2-tip",
                    "type": "tip",
                    "title": {"en": "Pause before replying", "hi": "बोलने से पहले ठहराव"},
                    "body": {
                        "en": "Many people find it comfortable to pause for one beat when answering the phone or a shopkeeper.",
                        "hi": "फ़ोन उठाते समय या दुकानदार से बात करते समय एक पल का ठहराव लेना बहुत मददगार होता है।"
                    },
                    "technique_id": "pausing"
                },
                {
                    "id": "introductions-2-shop-dialogue",
                    "type": "dialogue",
                    "title": {"en": "Asking for something at a shop", "hi": "दुकान पर सामान माँगना"},
                    "scenario": {
                        "en": "You are at the corner grocery shop asking for supplies.",
                        "hi": "आप किराने की दुकान पर सामान ले रहे हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते जी, क्या चाहिए?", "latin": "namaste ji, kya chaahiye?", "audio_key": track_audio("introductions-2-shop-1", "नमस्ते जी, क्या चाहिए?")},
                        {
                            "speaker": "you",
                            "text": "दूध का एक पैकेट दीजिए।",
                            "latin": "doodh ka ek packet deejiye.",
                            "options": [{"text": "एक ब्रेड और मक्खन का पैकेट दीजिए।", "latin": "ek bread aur makkhan ka packet deejiye."}]
                        },
                        {"speaker": "sunn", "text": "यह लीजिए। कुल तीस रुपये हुए।", "latin": "yeh leejiye. kul tees rupaye hue.", "audio_key": track_audio("introductions-2-shop-2", "यह लीजिए। कुल तीस रुपये हुए।")},
                        {"speaker": "you", "text": "धन्यवाद भैया।", "latin": "dhanyavaad bhaiya."}
                    ]
                },
                {
                    "id": "introductions-2-phone-dialogue",
                    "type": "dialogue",
                    "title": {"en": "A brief phone call", "hi": "एक छोटी फ़ोन कॉल"},
                    "scenario": {
                        "en": "You receive a phone call from an office.",
                        "hi": "आपको किसी दफ़्तर से फ़ोन आया है।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "हेलो, क्या मेरी बात अमित जी से हो रही है?", "latin": "hello, kya meri baat amit ji se ho rahi hai?", "audio_key": track_audio("introductions-2-phone-1", "हेलो, क्या मेरी बात अमित जी से हो रही है?")},
                        {
                            "speaker": "you",
                            "text": "हाँ, मैं अमित बोल रहा हूँ।",
                            "latin": "haan, main amit bol raha hoon.",
                            "options": [{"text": "हाँ, बताइए मैं क्या मदद कर सकता हूँ?", "latin": "haan, bataaiye main kya madad kar sakta hoon?"}]
                        },
                        {"speaker": "sunn", "text": "आपका पार्सल आ गया है, नीचे आकर ले लीजिए।", "latin": "aapka parcel aa gaya hai, neeche aakar le leejiye.", "audio_key": track_audio("introductions-2-phone-2", "आपका पार्सल आ गया है, नीचे आकर ले लीजिए।")},
                        {"speaker": "you", "text": "ठीक है, मैं दो मिनट में आता हूँ। धन्यवाद!", "latin": "theek hai, main do minute mein aata hoon. dhanyavaad!"}
                    ]
                },
                {
                    "id": "introductions-2-english",
                    "type": "listen_repeat",
                    "title": {"en": "Polite English phrases", "hi": "अंग्रेज़ी में विनम्र वाक्य"},
                    "items": [
                        {"id": "thank-you", "text": "Thank you very much", "latin": "Thank you very much", "meaning_en": "polite thanks", "focus_sound": "th-english", "audio_key": track_audio("introductions-2-english-thank-you", "Thank you very much")},
                        {"id": "three-please", "text": "Three items please", "latin": "Three items please", "meaning_en": "ordering three", "focus_sound": "th-english", "audio_key": track_audio("introductions-2-english-three-please", "Three items please")},
                        {"id": "this-one", "text": "I would like this one", "latin": "I would like this one", "meaning_en": "pointing to item", "focus_sound": "th-english", "audio_key": track_audio("introductions-2-english-this-one", "I would like this one")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "introductions-2-choral",
                    "type": "speak_with_me",
                    "title": {"en": "Polite closing together", "hi": "विनम्र समापन"},
                    "text": "धन्यवाद, आपका दिन शुभ हो",
                    "latin": "dhanyavaad, aapka din shubh ho",
                    "meaning_en": "Thank you, have a good day.",
                    "mode": "choral",
                    "pace_wpm": [60, 90],
                    "audio_key": track_audio("introductions-2-choral-day", "धन्यवाद, आपका दिन शुभ हो"),
                    "feedback": "words"
                },
                {
                    "id": "introductions-2-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did phone and shop dialogues feel?", "hi": "दुकान और फ़ोन की बातचीत कैसी लगी?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "introductions-3",
            "title": {"en": "At the clinic", "hi": "डॉक्टर के पास"},
            "minutes": 8,
            "steps": [
                {
                    "id": "introductions-3-intro",
                    "type": "intro",
                    "title": {"en": "Explaining discomfort", "hi": "तकलीफ़ बताना"},
                    "body": {
                        "en": "At a clinic, doctors listen attentively. Take steady breaths while explaining where it hurts.",
                        "hi": "डॉक्टर के पास अपनी परेशानी आराम से बताइए। साँस को शांत रखिए और धीरे-धीरे बोलिए।"
                    }
                },
                {
                    "id": "introductions-3-tip",
                    "type": "tip",
                    "title": {"en": "Light touches on words", "hi": "शब्दों पर हल्का दबाव"},
                    "body": {
                        "en": "Many people find it easier to speak clearly when staying relaxed, especially when feeling unwell.",
                        "hi": "तबीयत खराब होने पर भी शरीर को ढीला रखकर बोलने से शब्द आसानी से निकलते हैं।"
                    },
                    "technique_id": "light-touch"
                },
                {
                    "id": "introductions-3-phrases",
                    "type": "listen_repeat",
                    "title": {"en": "Describing symptoms", "hi": "तकलीफ़ के वाक्य"},
                    "items": [
                        {"id": "sir-dard", "text": "सिर में दर्द है", "latin": "sir mein dard hai", "meaning_en": "I have a headache", "audio_key": track_audio("introductions-3-phrases-sir-dard", "सिर में दर्द है")},
                        {"id": "pet-dard", "text": "पेट में दर्द है", "latin": "pet mein dard hai", "meaning_en": "my stomach hurts", "audio_key": track_audio("introductions-3-phrases-pet-dard", "पेट में दर्द है")},
                        {"id": "dawa-chaahiye", "text": "मुझे दवा चाहिए", "latin": "mujhe dawa chaahiye", "meaning_en": "I need medicine", "audio_key": track_audio("introductions-3-phrases-dawa-chaahiye", "मुझे दवा चाहिए")},
                        {"id": "aaraam-karoonga", "text": "मैं थोड़ा आराम करूँगा", "latin": "main thoda aaraam karoonga", "meaning_en": "I will rest a little", "audio_key": track_audio("introductions-3-phrases-aaraam-karoonga", "मैं थोड़ा आराम करूँगा")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "introductions-3-clinic-dialogue",
                    "type": "dialogue",
                    "title": {"en": "Talking with the doctor", "hi": "डॉक्टर से बातचीत"},
                    "scenario": {
                        "en": "You are explaining your health concern to the doctor.",
                        "hi": "आप डॉक्टर को अपनी तकलीफ़ बता रहे हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "नमस्ते, बताइए क्या परेशानी है?", "latin": "namaste, bataaiye kya pareshaani hai?", "audio_key": track_audio("introductions-3-clinic-1", "नमस्ते, बताइए क्या परेशानी है?")},
                        {
                            "speaker": "you",
                            "text": "मुझे कल रात से सिर में दर्द है।",
                            "latin": "mujhe kal raat se sir mein dard hai.",
                            "options": [{"text": "मुझे हल्का बुखार और थकान लग रही है।", "latin": "mujhe halka bukhaar aur thakaan lag rahi hai."}]
                        },
                        {"speaker": "sunn", "text": "चिंता मत कीजिए, यह दवा ले लीजिए और आराम कीजिए।", "latin": "chinta mat kijiye, yeh dawa le leejiye aur aaraam kijiye.", "audio_key": track_audio("introductions-3-clinic-2", "चिंता मत कीजिए, यह दवा ले लीजिए और आराम कीजिए।")},
                        {"speaker": "you", "text": "धन्यवाद डॉक्टर साहब।", "latin": "dhanyavaad doctor sahab."}
                    ]
                },
                {
                    "id": "introductions-3-wait-dialogue",
                    "type": "dialogue",
                    "title": {"en": "Asking someone to wait or repeat", "hi": "रुकने या दोहराने के लिए कहना"},
                    "scenario": {
                        "en": "Someone is speaking quickly and you ask them to repeat.",
                        "hi": "कोई जल्दी-जल्दी बोल रहा है और आप उन्हें दोहराने को कहते हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "फॉर्म भरकर काउंटर नंबर तीन पर जमा करा दीजिए।", "latin": "form bharkar counter number teen par jama kara deejiye.", "audio_key": track_audio("introductions-3-wait-1", "फॉर्म भरकर काउंटर नंबर तीन पर जमा करा दीजिए।")},
                        {
                            "speaker": "you",
                            "text": "कृपया एक पल रुकिए, ज़रा फिर से कहिए।",
                            "latin": "kripya ek pal rukiye, zara phir se kahiye.",
                            "options": [{"text": "एक मिनट रुकिए, मैं समझ नहीं पाया।", "latin": "ek minute rukiye, main samajh nahin paaya."}]
                        },
                        {"speaker": "sunn", "text": "ज़रूर, काउंटर नंबर तीन पर फॉर्म देना है।", "latin": "zaroor, counter number teen par form dena hai.", "audio_key": track_audio("introductions-3-wait-2", "ज़रूर, काउंटर नंबर तीन पर फॉर्म देना है।")},
                        {"speaker": "you", "text": "समझ गया, बहुत शुक्रिया।", "latin": "samajh gaya, bahut shukriya."}
                    ]
                },
                {
                    "id": "introductions-3-echo",
                    "type": "speak_with_me",
                    "title": {"en": "Asking politely to wait", "hi": "विनम्रता से रुकने को कहना"},
                    "text": "कृपया एक पल रुकिए, मैं फिर से बताता हूँ",
                    "latin": "kripya ek pal rukiye, main phir se bataata hoon",
                    "meaning_en": "Please wait a moment, I will explain again.",
                    "mode": "echo",
                    "pace_wpm": [55, 85],
                    "audio_key": track_audio("introductions-3-echo-wait", "कृपया एक पल रुकिए, मैं फिर से बताता हूँ"),
                    "feedback": "words"
                },
                {
                    "id": "introductions-3-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did explaining symptoms and asking someone to wait feel?", "hi": "अपनी बात समझाना और रुकने के लिए कहना कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        },
        {
            "id": "introductions-4",
            "title": {"en": "Easy alternatives when stuck", "hi": "अटकने पर आसान शब्द"},
            "minutes": 8,
            "steps": [
                {
                    "id": "introductions-4-intro",
                    "type": "intro",
                    "title": {"en": "If a word gets stuck, use another one", "hi": "शब्द अटके तो दूसरा चुनिए"},
                    "body": {
                        "en": "If a word feels tricky in the moment, you can always choose another word with the same meaning. You are always in control of your words.",
                        "hi": "अगर बोलते समय कोई शब्द मुश्किल लगे, तो उसी मतलब का कोई दूसरा आसान शब्द चुन लीजिए। चुनाव हमेशा आपका है।"
                    }
                },
                {
                    "id": "introductions-4-tip",
                    "type": "tip",
                    "title": {"en": "Switching words smoothly", "hi": "सहजता से शब्द बदलना"},
                    "body": {
                        "en": "Many people find that keeping 2 or 3 favorite ways to say everyday needs makes conversations feel relaxed.",
                        "hi": "रोज़ की ज़रूरतों को कहने के दो-तीन आसान तरीके याद रखने से बातचीत आसान हो जाती है।"
                    },
                    "technique_id": "slow-pace"
                },
                {
                    "id": "introductions-4-pairs",
                    "type": "listen_repeat",
                    "title": {"en": "Equivalent phrasing pairs", "hi": "मिलते-जुलते शब्द"},
                    "items": [
                        {"id": "water-1", "text": "पानी चाहिए", "latin": "paani chaahiye", "meaning_en": "I need water", "audio_key": track_audio("introductions-4-pairs-water-1", "पानी चाहिए")},
                        {"id": "water-2", "text": "पानी मिलेगा?", "latin": "paani milega?", "meaning_en": "can I get water?", "audio_key": track_audio("introductions-4-pairs-water-2", "पानी मिलेगा?")},
                        {"id": "thanks-1", "text": "धन्यवाद", "latin": "dhanyavaad", "meaning_en": "thank you", "audio_key": track_audio("introductions-4-pairs-thanks-1", "धन्यवाद")},
                        {"id": "thanks-2", "text": "शुक्रिया", "latin": "shukriya", "meaning_en": "thanks", "audio_key": track_audio("introductions-4-pairs-thanks-2", "शुक्रिया")}
                    ],
                    "feedback": "words"
                },
                {
                    "id": "introductions-4-dialogue",
                    "type": "dialogue",
                    "title": {"en": "Using an easier word in conversation", "hi": "बातचीत में आसान विकल्प चुनना"},
                    "scenario": {
                        "en": "You are asking for a drink and choose an alternative that feels completely easy to say.",
                        "hi": "आप पानी माँग रहे हैं और जो शब्द सबसे आसान लगे उसे चुनते हैं।"
                    },
                    "turns": [
                        {"speaker": "sunn", "text": "बताइए, आपके लिए क्या लाऊँ?", "latin": "bataaiye, aapke liye kya laaoon?", "audio_key": track_audio("introductions-4-dialogue-1", "बताइए, आपके लिए क्या लाऊँ?")},
                        {
                            "speaker": "you",
                            "text": "मुझे थोड़ा पानी मिलेगा?",
                            "latin": "mujhe thoda paani milega?",
                            "options": [{"text": "एक गिलास पानी दीजिए।", "latin": "ek glass paani deejiye."}]
                        },
                        {"speaker": "sunn", "text": "अभी लाता हूँ, एक मिनट रुकिए।", "latin": "abhi laata hoon, ek minute rukiye.", "audio_key": track_audio("introductions-4-dialogue-2", "अभी लाता हूँ, एक मिनट रुकिए।")},
                        {"speaker": "you", "text": "बहुत शुक्रिया।", "latin": "bahut shukriya."}
                    ]
                },
                {
                    "id": "introductions-4-paced",
                    "type": "speak_with_me",
                    "title": {"en": "Paced freedom phrase", "hi": "आज़ादी से अपनी बात कहना"},
                    "text": "अगर एक शब्द अटक जाए तो दूसरा शब्द चुन लीजिए",
                    "latin": "agar ek shabd atak jaaye to doosra shabd chun leejiye",
                    "meaning_en": "If a word gets stuck, pick another one.",
                    "mode": "paced",
                    "pace_wpm": [50, 75],
                    "feedback": "words"
                },
                {
                    "id": "introductions-4-read",
                    "type": "read_aloud",
                    "title": {"en": "Speaking flexibly", "hi": "सहज बातचीत का नियम"},
                    "paragraph": "बोलते समय शब्द बदलना बिल्कुल स्वाभाविक है। सबसे ज़रूरी बात यह है कि आप अपनी बात आराम से कह सकें।",
                    "latin": "bolte samay shabd badalna bilkul swaabhaavik hai. sabse zaroori baat yeh hai ki aap apni बात aaraam se kah sakein.",
                    "audio_key": track_audio("introductions-4-read-flexibility", "बोलते समय शब्द बदलना बिल्कुल स्वाभाविक है। सबसे ज़रूरी बात यह है कि आप अपनी बात आराम से कह सकें।"),
                    "feedback": "words"
                },
                {
                    "id": "introductions-4-reflect",
                    "type": "reflect",
                    "title": {"en": "How was that?", "hi": "कैसा लगा?"},
                    "prompt": {"en": "How did having easier ways to say things feel?", "hi": "आसान शब्दों के विकल्प चुनना कैसा लगा?"},
                    "choices": ["easy", "okay", "hard"]
                }
            ]
        }
    ]

    course = {
        "id": "introductions",
        "category_id": "everyday-talk",
        "title": {"en": "Introductions", "hi": "परिचय"},
        "summary": {
            "en": "Practise real-world conversations: greetings, shop requests, phone calls, doctor visits, and easier ways to say words.",
            "hi": "नमस्ते, दुकान पर बात, फ़ोन कॉल, डॉक्टर के पास और अटकने पर आसान विकल्प चुनने का अभ्यास।"
        },
        "what_you_practise": {
            "en": [
                "Greeting and introducing yourself",
                "Shop conversations and phone etiquette",
                "Describing how you feel at a clinic",
                "Switching to easier alternatives when a word feels stuck"
            ],
            "hi": [
                "नमस्ते कहना और अपना परिचय देना",
                "दुकान पर बातचीत और फ़ोन कॉल",
                "डॉक्टर के पास अपनी बात समझाना",
                "अटकने पर आसान शब्दों का चुनाव करना"
            ]
        },
        "level": "beginner",
        "minutes": sum(l["minutes"] for l in lessons),
        "practice_lang": "hi",
        "lessons": lessons
    }
    return course

print("Courses builder functions defined")

def build_alternatives():
    items = []

    # 1. needs (8)
    items.append({
        "meaning_id": "need-water",
        "meaning_en": "I need water",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "पानी चाहिए", "latin": "paani chaahiye", "lang": "hi"},
            {"text": "पानी दो", "latin": "paani do", "lang": "hi"},
            {"text": "पानी मिलेगा?", "latin": "paani milega?", "lang": "hi"},
            {"text": "मुझे पानी", "latin": "mujhe paani", "lang": "hi"},
            {"text": "I need water", "latin": "I need water", "lang": "en"},
            {"text": "Water, please", "latin": "Water, please", "lang": "en"},
            {"text": "Can I have some water?", "latin": "Can I have some water?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-rest",
        "meaning_en": "I need to rest",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "आराम करना है", "latin": "aaraam karna hai", "lang": "hi"},
            {"text": "मुझे थोड़ी देर बैठना है", "latin": "mujhe thodi der baithna hai", "lang": "hi"},
            {"text": "मैं थोड़ा थक गया हूँ", "latin": "main thoda thak gaya hoon", "lang": "hi"},
            {"text": "I need to rest", "latin": "I need to rest", "lang": "en"},
            {"text": "I need a short break", "latin": "I need a short break", "lang": "en"},
            {"text": "Could I sit down?", "latin": "Could I sit down?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-bathroom",
        "meaning_en": "Where is the bathroom?",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "वॉशरूम कहाँ है?", "latin": "washroom kahaan hai?", "lang": "hi"},
            {"text": "शौचालय किधर है?", "latin": "shouchaalay kidhar hai?", "lang": "hi"},
            {"text": "बाथरूम जाना है", "latin": "bathroom jaana hai", "lang": "hi"},
            {"text": "Where is the restroom?", "latin": "Where is the restroom?", "lang": "en"},
            {"text": "Bathroom please", "latin": "Bathroom please", "lang": "en"},
            {"text": "Which way to the washroom?", "latin": "Which way to the washroom?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-medicine",
        "meaning_en": "I need my medicine",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "दवा का समय हो गया", "latin": "dawa ka samay ho gaya", "lang": "hi"},
            {"text": "मेरी दवा दीजिए", "latin": "meri dawa deejiye", "lang": "hi"},
            {"text": "मुझे गोली खानी है", "latin": "mujhe goli khaani hai", "lang": "hi"},
            {"text": "I need my medicine", "latin": "I need my medicine", "lang": "en"},
            {"text": "Time for my pills", "latin": "Time for my pills", "lang": "en"},
            {"text": "Please bring my medication", "latin": "Please bring my medication", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-chair",
        "meaning_en": "Can I sit down?",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "क्या मैं यहाँ बैठ सकता हूँ?", "latin": "kya main yahaan baith sakta hoon?", "lang": "hi"},
            {"text": "कुर्सी मिलेगी?", "latin": "kursi milegi?", "lang": "hi"},
            {"text": "बैठने की जगह चाहिए", "latin": "baithne ki jagah chaahiye", "lang": "hi"},
            {"text": "Can I take a seat?", "latin": "Can I take a seat?", "lang": "en"},
            {"text": "Is this seat free?", "latin": "Is this seat free?", "lang": "en"},
            {"text": "May I sit here?", "latin": "May I sit here?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-quiet",
        "meaning_en": "I need some quiet",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "थोड़ी शांति चाहिए", "latin": "thodi shaanti chaahiye", "lang": "hi"},
            {"text": "शोर कम कीजिए", "latin": "shor kam kijiye", "lang": "hi"},
            {"text": "यहाँ बहुत आवाज़ है", "latin": "yahaan bahut aawaaz hai", "lang": "hi"},
            {"text": "I need a quiet spot", "latin": "I need a quiet spot", "lang": "en"},
            {"text": "A little silence please", "latin": "A little silence please", "lang": "en"},
            {"text": "Could we have some quiet?", "latin": "Could we have some quiet?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-phone",
        "meaning_en": "Can I use a phone?",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "एक कॉल करना है", "latin": "ek call karna hai", "lang": "hi"},
            {"text": "फ़ोन मिलेगा?", "latin": "phone milega?", "lang": "hi"},
            {"text": "ज़रूरी बात करनी है", "latin": "zaroori baat karni hai", "lang": "hi"},
            {"text": "May I use the phone?", "latin": "May I use the phone?", "lang": "en"},
            {"text": "I need to make a call", "latin": "I need to make a call", "lang": "en"},
            {"text": "Can I borrow your phone?", "latin": "Can I borrow your phone?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "need-blanket",
        "meaning_en": "I feel cold, I need a blanket",
        "category": "needs",
        "urgent": False,
        "variants": [
            {"text": "ठंड लग रही है", "latin": "thand lag rahi hai", "lang": "hi"},
            {"text": "चादर या कंबल दीजिए", "latin": "chaadar ya kambal deejiye", "lang": "hi"},
            {"text": "थोड़ा गर्म कपड़ा चाहिए", "latin": "thoda garam kapda chaahiye", "lang": "hi"},
            {"text": "I feel cold", "latin": "I feel cold", "lang": "en"},
            {"text": "Could I have a blanket?", "latin": "Could I have a blanket?", "lang": "en"},
            {"text": "It is chilly here", "latin": "It is chilly here", "lang": "en"}
        ]
    })

    # 2. pain (8, urgent: True)
    items.append({
        "meaning_id": "pain-head",
        "meaning_en": "My head hurts",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "सिर में दर्द है", "latin": "sir mein dard hai", "lang": "hi"},
            {"text": "सिर बहुत दुख रहा है", "latin": "sir bahut dukh raha hai", "lang": "hi"},
            {"text": "सिर दर्द हो रहा है", "latin": "sir dard ho raha hai", "lang": "hi"},
            {"text": "My head hurts", "latin": "My head hurts", "lang": "en"},
            {"text": "I have a headache", "latin": "I have a headache", "lang": "en"},
            {"text": "Severe head pain", "latin": "Severe head pain", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-chest",
        "meaning_en": "My chest hurts",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "सीने में दर्द है", "latin": "seene mein dard hai", "lang": "hi"},
            {"text": "छाती में भारीपन लग रहा है", "latin": "chhaati mein bhaaripan lag raha hai", "lang": "hi"},
            {"text": "यहाँ सीने में तकलीफ़ है", "latin": "yahaan seene mein takleef hai", "lang": "hi"},
            {"text": "My chest hurts", "latin": "My chest hurts", "lang": "en"},
            {"text": "I have chest tightness", "latin": "I have chest tightness", "lang": "en"},
            {"text": "Sharp chest pain", "latin": "Sharp chest pain", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-stomach",
        "meaning_en": "My stomach hurts",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "पेट में दर्द है", "latin": "pet mein dard hai", "lang": "hi"},
            {"text": "पेट दुख रहा है", "latin": "pet dukh raha hai", "lang": "hi"},
            {"text": "पेट में बहुत ऐंठन है", "latin": "pet mein bahut ainthann hai", "lang": "hi"},
            {"text": "My stomach hurts", "latin": "My stomach hurts", "lang": "en"},
            {"text": "I have stomach ache", "latin": "I have stomach ache", "lang": "en"},
            {"text": "Stomach pain", "latin": "Stomach pain", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-throat",
        "meaning_en": "My throat hurts",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "गले में दर्द है", "latin": "gale mein dard hai", "lang": "hi"},
            {"text": "गले में खराश है", "latin": "gale mein kharaash hai", "lang": "hi"},
            {"text": "निगलने में दर्द होता है", "latin": "nigalne mein dard hota hai", "lang": "hi"},
            {"text": "My throat is sore", "latin": "My throat is sore", "lang": "en"},
            {"text": "I have throat pain", "latin": "I have throat pain", "lang": "en"},
            {"text": "Pain when swallowing", "latin": "Pain when swallowing", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-back",
        "meaning_en": "My back hurts",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "कमर में दर्द है", "latin": "kamar mein dard hai", "lang": "hi"},
            {"text": "पीठ में बहुत दर्द है", "latin": "peeth mein bahut dard hai", "lang": "hi"},
            {"text": "झुकने में दर्द होता है", "latin": "jhukne mein dard hota hai", "lang": "hi"},
            {"text": "My back hurts", "latin": "My back hurts", "lang": "en"},
            {"text": "I have back pain", "latin": "I have back pain", "lang": "en"},
            {"text": "Severe back ache", "latin": "Severe back ache", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-dizzy",
        "meaning_en": "I feel dizzy",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "चक्कर आ रहे हैं", "latin": "chakkar aa rahe hain", "lang": "hi"},
            {"text": "सिर घूम रहा है", "latin": "sir ghoom raha hai", "lang": "hi"},
            {"text": "अचानक कमजोरी लग रही है", "latin": "achaanak kamzori lag rahi hai", "lang": "hi"},
            {"text": "I feel dizzy", "latin": "I feel dizzy", "lang": "en"},
            {"text": "The room is spinning", "latin": "The room is spinning", "lang": "en"},
            {"text": "I am feeling faint", "latin": "I am feeling faint", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-breath",
        "meaning_en": "I am having trouble breathing",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "साँस लेने में तकलीफ़ है", "latin": "saans lene mein takleef hai", "lang": "hi"},
            {"text": "साँस फूल रही है", "latin": "saans phool rahi hai", "lang": "hi"},
            {"text": "साँस भारी हो रही है", "latin": "saans bhaari ho rahi hai", "lang": "hi"},
            {"text": "I cannot breathe well", "latin": "I cannot breathe well", "lang": "en"},
            {"text": "Hard to breathe", "latin": "Hard to breathe", "lang": "en"},
            {"text": "Shortness of breath", "latin": "Shortness of breath", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "pain-leg",
        "meaning_en": "My leg hurts",
        "category": "pain",
        "urgent": True,
        "variants": [
            {"text": "पैर में दर्द है", "latin": "pair mein dard hai", "lang": "hi"},
            {"text": "चलने में दर्द हो रहा है", "latin": "chalne mein dard ho raha hai", "lang": "hi"},
            {"text": "घुटने में चोट लगी है", "latin": "ghutne mein chot lagi hai", "lang": "hi"},
            {"text": "My leg hurts", "latin": "My leg hurts", "lang": "en"},
            {"text": "Pain in my leg", "latin": "Pain in my leg", "lang": "en"},
            {"text": "Trouble walking", "latin": "Trouble walking", "lang": "en"}
        ]
    })

    # 3. help (8, urgent: True)
    items.append({
        "meaning_id": "help-call-doctor",
        "meaning_en": "Please call a doctor",
        "category": "help",
        "urgent": True,
        "variants": [
            {"text": "डॉक्टर को बुलाइए", "latin": "doctor ko bulaaiye", "lang": "hi"},
            {"text": "जल्दी डॉक्टर दिखाइए", "latin": "jaldi doctor dikhaaiye", "lang": "hi"},
            {"text": "अस्पताल ले चलिए", "latin": "aspatal le chaliye", "lang": "hi"},
            {"text": "Please call a doctor", "latin": "Please call a doctor", "lang": "en"},
            {"text": "We need a doctor now", "latin": "We need a doctor now", "lang": "en"},
            {"text": "Get medical help", "latin": "Get medical help", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-emergency",
        "meaning_en": "I need emergency help",
        "category": "help",
        "urgent": True,
        "variants": [
            {"text": "मदद कीजिए!", "latin": "madad kijiye!", "lang": "hi"},
            {"text": "तुरंत सहायता चाहिए", "latin": "turant sahaayata chaahiye", "lang": "hi"},
            {"text": "यहाँ कोई मदद करो", "latin": "yahaan koi madad karo", "lang": "hi"},
            {"text": "Emergency help needed", "latin": "Emergency help needed", "lang": "en"},
            {"text": "Please help me!", "latin": "Please help me!", "lang": "en"},
            {"text": "Urgent assistance please", "latin": "Urgent assistance please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-lost",
        "meaning_en": "I am lost, please help me",
        "category": "help",
        "urgent": True,
        "variants": [
            {"text": "मैं रास्ता भूल गया हूँ", "latin": "main raasta bhool gaya hoon", "lang": "hi"},
            {"text": "रास्ता बता दीजिए", "latin": "raasta bata deejiye", "lang": "hi"},
            {"text": "मुझे यहाँ पहुँचना है", "latin": "mujhe yahaan pahunchna hai", "lang": "hi"},
            {"text": "I am lost", "latin": "I am lost", "lang": "en"},
            {"text": "Could you guide me?", "latin": "Could you guide me?", "lang": "en"},
            {"text": "Which way is this?", "latin": "Which way is this?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-fell",
        "meaning_en": "I fell down and need help",
        "category": "help",
        "urgent": True,
        "variants": [
            {"text": "मैं गिर गया हूँ", "latin": "main gir gaya hoon", "lang": "hi"},
            {"text": "उठने में मदद कीजिए", "latin": "uthne mein madad kijiye", "lang": "hi"},
            {"text": "हाथ पकड़कर उठाइए", "latin": "haath pakadkar uthaaiye", "lang": "hi"},
            {"text": "I have fallen down", "latin": "I have fallen down", "lang": "en"},
            {"text": "Please help me up", "latin": "Please help me up", "lang": "en"},
            {"text": "I need a hand", "latin": "I need a hand", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-heavy",
        "meaning_en": "Can you help me carry this?",
        "category": "help",
        "urgent": False,
        "variants": [
            {"text": "यह सामान भारी है", "latin": "yeh saamaan bhaari hai", "lang": "hi"},
            {"text": "उठाने में मदद करेंगे?", "latin": "uthaane mein madad karenge?", "lang": "hi"},
            {"text": "ज़रा हाथ लगा दीजिए", "latin": "zara haath laga deejiye", "lang": "hi"},
            {"text": "Can you help lift this?", "latin": "Can you help lift this?", "lang": "en"},
            {"text": "This is heavy", "latin": "This is heavy", "lang": "en"},
            {"text": "Could you give me a hand?", "latin": "Could you give me a hand?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-repeat",
        "meaning_en": "Please repeat that once more",
        "category": "help",
        "urgent": False,
        "variants": [
            {"text": "फिर से बोलिए", "latin": "phir se boliye", "lang": "hi"},
            {"text": "एक बार और कहेंगे?", "latin": "ek baar aur kahenge?", "lang": "hi"},
            {"text": "ज़रा धीरे से बताइए", "latin": "zara dheere se bataaiye", "lang": "hi"},
            {"text": "Could you repeat that?", "latin": "Could you repeat that?", "lang": "en"},
            {"text": "Once more please", "latin": "Once more please", "lang": "en"},
            {"text": "Say that again please", "latin": "Say that again please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-call-family",
        "meaning_en": "Please call my family",
        "category": "help",
        "urgent": True,
        "variants": [
            {"text": "घर पर फ़ोन कर दीजिए", "latin": "ghar par phone kar deejiye", "lang": "hi"},
            {"text": "परिवार को बता दीजिए", "latin": "parivaar ko bata deejiye", "lang": "hi"},
            {"text": "मेरे घर वालों को बुलाइए", "latin": "mere ghar waalon ko bulaaiye", "lang": "hi"},
            {"text": "Please call my home", "latin": "Please call my home", "lang": "en"},
            {"text": "Inform my family", "latin": "Inform my family", "lang": "en"},
            {"text": "Reach my relatives please", "latin": "Reach my relatives please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "help-wait",
        "meaning_en": "Please wait for me a moment",
        "category": "help",
        "urgent": False,
        "variants": [
            {"text": "एक मिनट रुकिए", "latin": "ek minute rukiye", "lang": "hi"},
            {"text": "थोड़ा इंतज़ार कीजिए", "latin": "thoda intezaar kijiye", "lang": "hi"},
            {"text": "मैं अभी आया", "latin": "main abhi aaya", "lang": "hi"},
            {"text": "Please wait a moment", "latin": "Please wait a moment", "lang": "en"},
            {"text": "Just one second", "latin": "Just one second", "lang": "en"},
            {"text": "Hold on please", "latin": "Hold on please", "lang": "en"}
        ]
    })

    # 4. family (7)
    items.append({
        "meaning_id": "family-call-home",
        "meaning_en": "I want to call home",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "घर बात करनी है", "latin": "ghar baat karni hai", "lang": "hi"},
            {"text": "माँ को फ़ोन लगाना है", "latin": "maa ko phone lagaana hai", "lang": "hi"},
            {"text": "घर वालों से बात करा दीजिए", "latin": "ghar waalon se baat kara deejiye", "lang": "hi"},
            {"text": "I want to call home", "latin": "I want to call home", "lang": "en"},
            {"text": "Calling my family", "latin": "Calling my family", "lang": "en"},
            {"text": "Need to reach my folks", "latin": "Need to reach my folks", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "family-coming-soon",
        "meaning_en": "I will reach home soon",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "जल्दी घर आ रहा हूँ", "latin": "jaldi ghar aa raha hoon", "lang": "hi"},
            {"text": "रास्ते में हूँ, अभी पहुँचता हूँ", "latin": "raaste mein hoon, abhi pahunchta hoon", "lang": "hi"},
            {"text": "बस दस मिनट में घर पर", "latin": "bas das minute mein ghar par", "lang": "hi"},
            {"text": "On my way home", "latin": "On my way home", "lang": "en"},
            {"text": "Reaching home shortly", "latin": "Reaching home shortly", "lang": "en"},
            {"text": "Almost there", "latin": "Almost there", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "family-how-are-you",
        "meaning_en": "How is everyone at home?",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "घर में सब कैसे हैं?", "latin": "ghar mein sab kaise hain?", "lang": "hi"},
            {"text": "सब लोग ठीक हैं?", "latin": "sab log theek hain?", "lang": "hi"},
            {"text": "घर का हाल बताइए", "latin": "ghar ka haal bataaiye", "lang": "hi"},
            {"text": "How is everyone at home?", "latin": "How is everyone at home?", "lang": "en"},
            {"text": "Is all well with family?", "latin": "Is all well with family?", "lang": "en"},
            {"text": "How are folks doing?", "latin": "How are folks doing?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "family-love-you",
        "meaning_en": "I love you all",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "आप सब बहुत याद आते हैं", "latin": "aap sab bahut yaad aate hain", "lang": "hi"},
            {"text": "मुझे आप सब से प्यार है", "latin": "mujhe aap sab se pyaar hai", "lang": "hi"},
            {"text": "आप सब हमेशा साथ हैं", "latin": "aap sab hamesha saath hain", "lang": "hi"},
            {"text": "Sending love to everyone", "latin": "Sending love to everyone", "lang": "en"},
            {"text": "Love you all", "latin": "Love you all", "lang": "en"},
            {"text": "Warm regards to all", "latin": "Warm regards to all", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "family-ate-food",
        "meaning_en": "Did you have dinner?",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "खाना खा लिया?", "latin": "khaana kha liya?", "lang": "hi"},
            {"text": "भोजन कर लिया आपने?", "latin": "bhojan kar liya aapne?", "lang": "hi"},
            {"text": "सबने खाना खाया?", "latin": "sabne khaana khaaya?", "lang": "hi"},
            {"text": "Did you have your meal?", "latin": "Did you have your meal?", "lang": "en"},
            {"text": "Have you eaten?", "latin": "Have you eaten?", "lang": "en"},
            {"text": "Did you finish dinner?", "latin": "Did you finish dinner?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "family-take-care",
        "meaning_en": "Take care of your health",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "अपना ध्यान रखिए", "latin": "apna dhyaan rakhiye", "lang": "hi"},
            {"text": "सेहत का ख्याल रखें", "latin": "sehat ka khyaal rakhein", "lang": "hi"},
            {"text": "समय पर दवा लीजिए", "latin": "samay par dawa leejiye", "lang": "hi"},
            {"text": "Take good care", "latin": "Take good care", "lang": "en"},
            {"text": "Look after your health", "latin": "Look after your health", "lang": "en"},
            {"text": "Stay healthy and safe", "latin": "Stay healthy and safe", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "family-parents-well",
        "meaning_en": "My parents are doing well",
        "category": "family",
        "urgent": False,
        "variants": [
            {"text": "माता-पिता बिल्कुल ठीक हैं", "latin": "maata-pita bilkul theek hain", "lang": "hi"},
            {"text": "मम्मी-पापा अच्छे हैं", "latin": "mummy-papa achchhe hain", "lang": "hi"},
            {"text": "घर पर सब कुशल-मंगल है", "latin": "ghar par sab kushal-mangal hai", "lang": "hi"},
            {"text": "My parents are well", "latin": "My parents are well", "lang": "en"},
            {"text": "Mom and dad are fine", "latin": "Mom and dad are fine", "lang": "en"},
            {"text": "Family is doing great", "latin": "Family is doing great", "lang": "en"}
        ]
    })

    # 5. food (8)
    items.append({
        "meaning_id": "food-hungry",
        "meaning_en": "I am feeling hungry",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "भूख लगी है", "latin": "bhookh lagi hai", "lang": "hi"},
            {"text": "कुछ खाने को दीजिए", "latin": "kuchh khaane ko deejiye", "lang": "hi"},
            {"text": "खाना तैयार है?", "latin": "khaana taiyaar hai?", "lang": "hi"},
            {"text": "I feel hungry", "latin": "I feel hungry", "lang": "en"},
            {"text": "Something to eat please", "latin": "Something to eat please", "lang": "en"},
            {"text": "Is food ready?", "latin": "Is food ready?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-tea",
        "meaning_en": "Can I have a cup of tea?",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "चाय मिलेगी?", "latin": "chaay milegi?", "lang": "hi"},
            {"text": "एक कप चाय दीजिए", "latin": "ek cup chaay deejiye", "lang": "hi"},
            {"text": "गरम चाय चाहिए", "latin": "garam chaay chaahiye", "lang": "hi"},
            {"text": "Cup of tea please", "latin": "Cup of tea please", "lang": "en"},
            {"text": "Can I get some tea?", "latin": "Can I get some tea?", "lang": "en"},
            {"text": "Hot tea please", "latin": "Hot tea please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-vegetarian",
        "meaning_en": "Do you have vegetarian food?",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "शाकाहारी भोजन मिलेगा?", "latin": "shaakaahaari bhojan milega?", "lang": "hi"},
            {"text": "शुद्ध शाकाहारी खाना है?", "latin": "shuddh shaakaahaari khaana hai?", "lang": "hi"},
            {"text": "बिना प्याज़-लहसुन का खाना", "latin": "bina pyaaz-lahsun ka khaana", "lang": "hi"},
            {"text": "Vegetarian food please", "latin": "Vegetarian food please", "lang": "en"},
            {"text": "Do you serve vegetarian?", "latin": "Do you serve vegetarian?", "lang": "en"},
            {"text": "Veg options available?", "latin": "Veg options available?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-less-spicy",
        "meaning_en": "Please make it less spicy",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "कम मिर्च वाला बनाइए", "latin": "kam mirch waala banaaiye", "lang": "hi"},
            {"text": "ज़्यादा तीखा मत कीजिए", "latin": "zyaada teekha mat kijiye", "lang": "hi"},
            {"text": "हल्के मसाले रखिएगा", "latin": "halke masaale rakhiyega", "lang": "hi"},
            {"text": "Less spicy please", "latin": "Less spicy please", "lang": "en"},
            {"text": "Mild flavor please", "latin": "Mild flavor please", "lang": "en"},
            {"text": "Not too hot please", "latin": "Not too hot please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-hot-water",
        "meaning_en": "Please give me warm water",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "गरम पानी दीजिए", "latin": "garam paani deejiye", "lang": "hi"},
            {"text": "गुनगुना पानी मिलेगा?", "latin": "gunguna paani milega?", "lang": "hi"},
            {"text": "पीने के लिए हल्का गरम पानी", "latin": "peene ke liye halka garam paani", "lang": "hi"},
            {"text": "Warm water please", "latin": "Warm water please", "lang": "en"},
            {"text": "Can I get hot water?", "latin": "Can I get hot water?", "lang": "en"},
            {"text": "Boiled drinking water please", "latin": "Boiled drinking water please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-delicious",
        "meaning_en": "The food is very tasty",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "खाना बहुत स्वादिष्ट है", "latin": "khaana bahut swaadist hai", "lang": "hi"},
            {"text": "बहुत बढ़िया बना है", "latin": "bahut badhiya bana hai", "lang": "hi"},
            {"text": "मज़ा आ गया खाकर", "latin": "maza aa gaya khaakar", "lang": "hi"},
            {"text": "Food is delicious", "latin": "Food is delicious", "lang": "en"},
            {"text": "Very tasty meal", "latin": "Very tasty meal", "lang": "en"},
            {"text": "Wonderful food", "latin": "Wonderful food", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-bill-please",
        "meaning_en": "Please bring the bill",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "बिल ले आइए", "latin": "bill le aaiye", "lang": "hi"},
            {"text": "कितने पैसे हुए?", "latin": "kitne paise hue?", "lang": "hi"},
            {"text": "चेक दीजिए भैया", "latin": "check deejiye bhaiya", "lang": "hi"},
            {"text": "The bill please", "latin": "The bill please", "lang": "en"},
            {"text": "Check please", "latin": "Check please", "lang": "en"},
            {"text": "Could we have the bill?", "latin": "Could we have the bill?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "food-sweet",
        "meaning_en": "I would like some sweets",
        "category": "food",
        "urgent": False,
        "variants": [
            {"text": "कुछ मीठा मिलेगा?", "latin": "kuchh meetha milega?", "lang": "hi"},
            {"text": "मीठे में क्या है?", "latin": "meethe mein kya hai?", "lang": "hi"},
            {"text": "खीर या हलवा दीजिए", "latin": "kheer ya halwa deejiye", "lang": "hi"},
            {"text": "Something sweet please", "latin": "Something sweet please", "lang": "en"},
            {"text": "Dessert menu please", "latin": "Dessert menu please", "lang": "en"},
            {"text": "Any sweet dishes?", "latin": "Any sweet dishes?", "lang": "en"}
        ]
    })

    # 6. shop (7)
    items.append({
        "meaning_id": "shop-how-much",
        "meaning_en": "How much does this cost?",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "यह कितने का है?", "latin": "yeh kitne ka hai?", "lang": "hi"},
            {"text": "इसकी क्या क़ीमत है?", "latin": "iski kya qeemat hai?", "lang": "hi"},
            {"text": "इसका दाम बताइए", "latin": "iska daam bataaiye", "lang": "hi"},
            {"text": "How much is this?", "latin": "How much is this?", "lang": "en"},
            {"text": "What is the price?", "latin": "What is the price?", "lang": "en"},
            {"text": "Cost of this item?", "latin": "Cost of this item?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "shop-buy-milk",
        "meaning_en": "I want to buy milk",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "दूध का पैकेट दीजिए", "latin": "doodh ka packet deejiye", "lang": "hi"},
            {"text": "ताज़ा दूध मिलेगा?", "latin": "taaza doodh milega?", "lang": "hi"},
            {"text": "एक लीटर दूध चाहिए", "latin": "ek litre doodh chaahiye", "lang": "hi"},
            {"text": "One packet of milk please", "latin": "One packet of milk please", "lang": "en"},
            {"text": "Milk please", "latin": "Milk please", "lang": "en"},
            {"text": "Do you have fresh milk?", "latin": "Do you have fresh milk?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "shop-have-change",
        "meaning_en": "Do you have change?",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "खुले पैसे हैं आपके पास?", "latin": "khule paise hain aapke paas?", "lang": "hi"},
            {"text": "सौ का छुट्टा मिलेगा?", "latin": "sau ka chhutta milega?", "lang": "hi"},
            {"text": "खुले रुपये दीजिए", "latin": "khule rupaye deejiye", "lang": "hi"},
            {"text": "Do you have change?", "latin": "Do you have change?", "lang": "en"},
            {"text": "Change for hundred please", "latin": "Change for hundred please", "lang": "en"},
            {"text": "Do you have small coins?", "latin": "Do you have small coins?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "shop-online-pay",
        "meaning_en": "Can I pay by UPI or card?",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "ऑनलाइन पेमेंट चलेगा?", "latin": "online payment chalega?", "lang": "hi"},
            {"text": "क्यूआर कोड दिखा दीजिए", "latin": "qr code dikha deejiye", "lang": "hi"},
            {"text": "कार्ड से ले लेंगे?", "latin": "card se le lenge?", "lang": "hi"},
            {"text": "Can I pay by UPI?", "latin": "Can I pay by UPI?", "lang": "en"},
            {"text": "Do you accept cards?", "latin": "Do you accept cards?", "lang": "en"},
            {"text": "QR code scanner please", "latin": "QR code scanner please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "shop-carry-bag",
        "meaning_en": "Please give me a carry bag",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "थैला दे दीजिए", "latin": "thaila de deejiye", "lang": "hi"},
            {"text": "सामान रखने की थैली मिलेगी?", "latin": "saamaan rakhne ki thaili milegi?", "lang": "hi"},
            {"text": "बैग चाहिए", "latin": "bag chaahiye", "lang": "hi"},
            {"text": "Carry bag please", "latin": "Carry bag please", "lang": "en"},
            {"text": "Could I have a bag?", "latin": "Could I have a bag?", "lang": "en"},
            {"text": "A shopping bag please", "latin": "A shopping bag please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "shop-receipt",
        "meaning_en": "Can I have a bill receipt?",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "पक्की रसीद मिलेगी?", "latin": "pakki raseed milegi?", "lang": "hi"},
            {"text": "बिल का प्रिंट दे दीजिए", "latin": "bill ka print de deejiye", "lang": "hi"},
            {"text": "रसीद बना दीजिए", "latin": "raseed bana deejiye", "lang": "hi"},
            {"text": "Can I get a receipt?", "latin": "Can I get a receipt?", "lang": "en"},
            {"text": "Printed bill please", "latin": "Printed bill please", "lang": "en"},
            {"text": "Receipt please", "latin": "Receipt please", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "shop-open-time",
        "meaning_en": "What time does the shop close?",
        "category": "shop",
        "urgent": False,
        "variants": [
            {"text": "दुकान कब तक खुली रहती है?", "latin": "dukaan kab tak khuli rahti hai?", "lang": "hi"},
            {"text": "कल कितने बजे खुलेंगे?", "latin": "kal kitne baje khulenge?", "lang": "hi"},
            {"text": "दुकान बंद होने का समय क्या है?", "latin": "dukaan band hone ka samay kya hai?", "lang": "hi"},
            {"text": "When do you close?", "latin": "When do you close?", "lang": "en"},
            {"text": "Opening hours please", "latin": "Opening hours please", "lang": "en"},
            {"text": "What time do you open tomorrow?", "latin": "What time do you open tomorrow?", "lang": "en"}
        ]
    })

    # 7. feelings (7)
    items.append({
        "meaning_id": "feelings-happy",
        "meaning_en": "I am feeling very happy today",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "आज बहुत खुशी हो रही है", "latin": "aaj bahut khushi ho rahi hai", "lang": "hi"},
            {"text": "मन बहुत प्रसन्न है", "latin": "man bahut prasann hai", "lang": "hi"},
            {"text": "आज का दिन बहुत अच्छा रहा", "latin": "aaj ka din bahut achchha raha", "lang": "hi"},
            {"text": "I feel very happy today", "latin": "I feel very happy today", "lang": "en"},
            {"text": "Great day today", "latin": "Great day today", "lang": "en"},
            {"text": "Feeling cheerful", "latin": "Feeling cheerful", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "feelings-tired",
        "meaning_en": "I am quite tired right now",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "आज बहुत थकान लग रही है", "latin": "aaj bahut thakaan lag rahi hai", "lang": "hi"},
            {"text": "शरीर में सुस्ती है", "latin": "shareer mein susti hai", "lang": "hi"},
            {"text": "थोड़ी देर आराम चाहिए", "latin": "thodi der aaraam chaahiye", "lang": "hi"},
            {"text": "I feel tired", "latin": "I feel tired", "lang": "en"},
            {"text": "A bit exhausted", "latin": "A bit exhausted", "lang": "en"},
            {"text": "Need some rest", "latin": "Need some rest", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "feelings-nervous",
        "meaning_en": "I am feeling a bit anxious",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "थोड़ी घबराहट हो रही है", "latin": "thodi ghabraahat ho rahi hai", "lang": "hi"},
            {"text": "मन थोड़ा बेचैन है", "latin": "man thoda bechain hai", "lang": "hi"},
            {"text": "मैं गहरी साँस ले रहा हूँ", "latin": "main gahri saans le raha hoon", "lang": "hi"},
            {"text": "Feeling a little anxious", "latin": "Feeling a little anxious", "lang": "en"},
            {"text": "A bit nervous right now", "latin": "A bit nervous right now", "lang": "en"},
            {"text": "Taking deep breaths", "latin": "Taking deep breaths", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "feelings-proud",
        "meaning_en": "I am proud of my effort",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "मुझे अपनी कोशिश पर गर्व है", "latin": "mujhe apni koshish par garv hai", "lang": "hi"},
            {"text": "आज मैंने अच्छा अभ्यास किया", "latin": "aaj maine achchha abhyaas kiya", "lang": "hi"},
            {"text": "मेहनत रंग लाई", "latin": "mehnat rang laai", "lang": "hi"},
            {"text": "Proud of my progress", "latin": "Proud of my progress", "lang": "en"},
            {"text": "Happy with my effort", "latin": "Happy with my effort", "lang": "en"},
            {"text": "Step by step progress", "latin": "Step by step progress", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "feelings-calm",
        "meaning_en": "I am feeling calm and peaceful",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "मन बहुत शांत है", "latin": "man bahut shaant hai", "lang": "hi"},
            {"text": "सब कुछ बहुत सहज लग रहा है", "latin": "sab kuchh bahut sahaj lag raha hai", "lang": "hi"},
            {"text": "सुकून महसूस हो रहा है", "latin": "sukoon mahsoos ho raha hai", "lang": "hi"},
            {"text": "Feeling calm and peaceful", "latin": "Feeling calm and peaceful", "lang": "en"},
            {"text": "Completely relaxed", "latin": "Completely relaxed", "lang": "en"},
            {"text": "At ease", "latin": "At ease", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "feelings-grateful",
        "meaning_en": "I feel very grateful",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "दिल से आभार", "latin": "dil se aabhaar", "lang": "hi"},
            {"text": "आपकी मदद के लिए धन्यवाद", "latin": "aapki madad ke liye dhanyavaad", "lang": "hi"},
            {"text": "बहुत उपकार हुआ", "latin": "bahut upkaar hua", "lang": "hi"},
            {"text": "Feeling very grateful", "latin": "Feeling very grateful", "lang": "en"},
            {"text": "Heartfelt thanks", "latin": "Heartfelt thanks", "lang": "en"},
            {"text": "So thankful for this", "latin": "So thankful for this", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "feelings-hopeful",
        "meaning_en": "I have good hopes for tomorrow",
        "category": "feelings",
        "urgent": False,
        "variants": [
            {"text": "आगे सब अच्छा होगा", "latin": "aage sab achchha hoga", "lang": "hi"},
            {"text": "पूरी उम्मीद है", "latin": "poori ummeed hai", "lang": "hi"},
            {"text": "नई शुरुआत की आशा है", "latin": "nayi shuruaat ki aasha hai", "lang": "hi"},
            {"text": "Full of hope", "latin": "Full of hope", "lang": "en"},
            {"text": "Looking forward to tomorrow", "latin": "Looking forward to tomorrow", "lang": "en"},
            {"text": "Positive about the future", "latin": "Positive about the future", "lang": "en"}
        ]
    })

    # 8. politeness (7)
    items.append({
        "meaning_id": "politeness-thank-you",
        "meaning_en": "Thank you very much",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "धन्यवाद", "latin": "dhanyavaad", "lang": "hi"},
            {"text": "बहुत शुक्रिया", "latin": "bahut shukriya", "lang": "hi"},
            {"text": "बहुत मेहरबानी", "latin": "bahut meharbaani", "lang": "hi"},
            {"text": "Thank you very much", "latin": "Thank you very much", "lang": "en"},
            {"text": "Much appreciated", "latin": "Much appreciated", "lang": "en"},
            {"text": "Thanks a lot", "latin": "Thanks a lot", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "politeness-welcome",
        "meaning_en": "You are very welcome",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "आपका स्वागत है", "latin": "aapka swaagat hai", "lang": "hi"},
            {"text": "कोई बात नहीं", "latin": "koi baat nahin", "lang": "hi"},
            {"text": "यह तो मेरा फ़र्ज़ था", "latin": "yeh to mera farz tha", "lang": "hi"},
            {"text": "You are welcome", "latin": "You are welcome", "lang": "en"},
            {"text": "Glad to help", "latin": "Glad to help", "lang": "en"},
            {"text": "My pleasure", "latin": "My pleasure", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "politeness-excuse-me",
        "meaning_en": "Excuse me for a moment",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "माफ़ कीजिए", "latin": "maaf kijiye", "lang": "hi"},
            {"text": "ज़रा सुनिए", "latin": "zara suniye", "lang": "hi"},
            {"text": "एक पल दीजिएगा", "latin": "ek pal deejiye-ga", "lang": "hi"},
            {"text": "Excuse me", "latin": "Excuse me", "lang": "en"},
            {"text": "Pardon me", "latin": "Pardon me", "lang": "en"},
            {"text": "May I have your attention?", "latin": "May I have your attention?", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "politeness-sorry",
        "meaning_en": "I am sorry about that",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "मुझे क्षमा करें", "latin": "mujhe kshama karein", "lang": "hi"},
            {"text": "मेरी ग़लती थी", "latin": "meri galti thi", "lang": "hi"},
            {"text": "माफ़ी चाहता हूँ", "latin": "maafi chaahta hoon", "lang": "hi"},
            {"text": "I am sorry", "latin": "I am sorry", "lang": "en"},
            {"text": "My apologies", "latin": "My apologies", "lang": "en"},
            {"text": "Sorry about that", "latin": "Sorry about that", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "politeness-nice-to-meet",
        "meaning_en": "Pleased to meet you",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "आपसे मिलकर बहुत खुशी हुई", "latin": "aap se milkar bahut khushi hui", "lang": "hi"},
            {"text": "मिलकर अच्छा लगा", "latin": "milkar achchha laga", "lang": "hi"},
            {"text": "बड़ा आनंद हुआ आपसे मिलकर", "latin": "bada aanand hua aap se milkar", "lang": "hi"},
            {"text": "Nice to meet you", "latin": "Nice to meet you", "lang": "en"},
            {"text": "Pleasure meeting you", "latin": "Pleasure meeting you", "lang": "en"},
            {"text": "Glad we met", "latin": "Glad we met", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "politeness-good-day",
        "meaning_en": "Have a wonderful day",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "आपका दिन शुभ हो", "latin": "aapka din shubh ho", "lang": "hi"},
            {"text": "दिन मंगलमय रहे", "latin": "din mangalmay rahe", "lang": "hi"},
            {"text": "खुश रहिए हमेशा", "latin": "khush rahiye hamesha", "lang": "hi"},
            {"text": "Have a nice day", "latin": "Have a nice day", "lang": "en"},
            {"text": "Have a great time", "latin": "Have a great time", "lang": "en"},
            {"text": "Take care today", "latin": "Take care today", "lang": "en"}
        ]
    })
    items.append({
        "meaning_id": "politeness-see-you-soon",
        "meaning_en": "See you again soon",
        "category": "politeness",
        "urgent": False,
        "variants": [
            {"text": "फिर मिलेंगे", "latin": "phir milenge", "lang": "hi"},
            {"text": "जल्दी ही मुलाकात होगी", "latin": "jaldi hi mulaaqaat hogi", "lang": "hi"},
            {"text": "नमस्ते, फिर मिलते हैं", "latin": "namaste, phir milte hain", "lang": "hi"},
            {"text": "See you soon", "latin": "See you soon", "lang": "en"},
            {"text": "Catch you later", "latin": "Catch you later", "lang": "en"},
            {"text": "Until next time", "latin": "Until next time", "lang": "en"}
        ]
    })

    return items


def main():
    print("Building courses...")
    easy_starts = build_easy_starts()
    s_and_sh = build_s_and_sh()
    sound_play = build_sound_play()
    introductions = build_introductions()

    courses = {
        "easy-starts": easy_starts,
        "s-and-sh": s_and_sh,
        "sound-play": sound_play,
        "introductions": introductions,
    }

    for cid, cdata in courses.items():
        path = os.path.join(COURSES_DIR, f"{cid}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cdata, f, ensure_ascii=False, indent=2)
        print(f"Wrote {path} ({len(cdata['lessons'])} lessons, {cdata['minutes']} mins)")

    # Alternatives
    print("Building alternatives...")
    alternatives = build_alternatives()
    assert len(alternatives) == 60, f"Expected 60 alternatives, got {len(alternatives)}"
    alt_path = os.path.join(CONTENT_DIR, "alternatives.json")
    with open(alt_path, "w", encoding="utf-8") as f:
        json.dump(alternatives, f, ensure_ascii=False, indent=2)
    print(f"Wrote {alt_path} ({len(alternatives)} meanings)")

    # Audio JSON
    print(f"Tracking {len(audio_dict)} audio keys...")
    audio_path = os.path.join(CONTENT_DIR, "audio.json")
    with open(audio_path, "w", encoding="utf-8") as f:
        json.dump(audio_dict, f, ensure_ascii=False, indent=2)
    print(f"Wrote {audio_path}")

    # Audio Manifest
    manifest = [{"audio_key": k, "text": v["text"], "lang": v["lang"]} for k, v in sorted(audio_dict.items())]
    manifest_path = os.path.join(CONTENT_DIR, "audio_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"Wrote {manifest_path} ({len(manifest)} keys)")

    # Validation
    print("Validating with trainings_content...")
    library = trainings_content.load(CONTENT_DIR)
    problems = trainings_content.problems(library)
    if problems:
        print("PROBLEMS FOUND:")
        for p in problems:
            print(" -", p)
        sys.exit(1)
    else:
        print("SUCCESS! All content passed validation.")
        print(f"Categories: {len(library.categories)}")
        print(f"Courses: {len(library.courses)}")
        print(f"Lessons: {len(library.lessons)}")
        print(f"Steps: {len(library.steps)}")
        print(f"Sounds: {len(library.sounds)}")
        print(f"Audio keys: {len(library.audio)}")


if __name__ == "__main__":
    main()
