# Recording the real test set

The only honest number for the correction model comes from real recordings that went through
Prisma. We have credits for 60 Prisma calls, so: **40 recordings, one take each**, and 20 calls in
reserve to re-record a file that came out wrong. Don't spend the reserve on extra takes.

## How to record

- **Who:** split the 40 across 2-4 team members, 10-20 each. More different voices is better.
- **What:** each phrase below, once per file, in Hindi, in the style given for it:
  - **slow**: drawn out, with pauses between words
  - **slurred**: soft consonants, sounds running into each other, as if speaking is an effort
  - **quiet**: barely above a whisper, phone at arm's length
  - **mumbled**: lips barely moving, word endings swallowed

  Keep it something a listener could just about follow, not gibberish: the point is speech
  that's hard for Prisma, not speech nobody could understand.
- **How:** a phone's voice recorder is fine (m4a), and so is the Sunn web app's recording (webm)
  or wav. In a normal room, with normal home noise. Leave half a second of silence before and
  after. Each file must be 0.3-15 seconds long.
- **Names:** exactly as in the table, `<phrase in latin>_<take>.<ext>`. A different extension is
  fine (`paani_chahiye_1.wav`). If a file is bad (cut off, wrong phrase), record it again as take 2
  (`paani_chahiye_2.m4a`) and delete take 1 before running the script.
- **Where:** `ml/data/real_audio/` (git-ignored). Never commit the recordings, and never put them
  in the backend, the Docker image or the Hugging Face Space.

Then, from `ml/`:

```powershell
uv run run_real_test.py --dry-run   # converts and checks the files, sends nothing
uv run run_real_test.py             # sends each new recording to Prisma once
uv run eval.py
uv run export.py
```

## The 40 phrases

All from the app's starter bank, because the real test ranks against it. The first 25 are
phrases the model never trained on (they are in the val or test split of
`ml/data/train_all.csv`); the last 15 it trained on. eval.py reports both groups.

| # | File | Hindi | Meaning | Style | Trained on |
|---|---|---|---|---|---|
| 1 | `dard_ho_raha_hai_1.m4a` | दर्द हो रहा है | I'm in pain | slow | no (test) |
| 2 | `sir_mein_dard_hai_1.m4a` | सिर में दर्द है | My head hurts | slurred | no (test) |
| 3 | `pet_mein_dard_hai_1.m4a` | पेट में दर्द है | My stomach hurts | quiet | no (test) |
| 4 | `doctor_ko_bulao_1.m4a` | डॉक्टर को बुलाओ | Call the doctor | mumbled | no (test) |
| 5 | `thakaan_ho_rahi_hai_1.m4a` | थकान हो रही है | I feel tired | slow | no (test) |
| 6 | `chai_peeni_hai_1.m4a` | चाय पीनी है | I want tea | slurred | no (test) |
| 7 | `doodh_chahiye_1.m4a` | दूध चाहिए | I need milk | quiet | no (test) |
| 8 | `thoda_aur_do_1.m4a` | थोड़ा और दो | A little more | mumbled | no (test) |
| 9 | `garam_paani_chahiye_1.m4a` | गरम पानी चाहिए | I need warm water | slow | no (test) |
| 10 | `kuch_meetha_do_1.m4a` | कुछ मीठा दो | Give me something sweet | slurred | no (test) |
| 11 | `maa_ko_bulao_1.m4a` | माँ को बुलाओ | Call my mother | quiet | no (test) |
| 12 | `bhaiya_ko_bulao_1.m4a` | भैया को बुलाओ | Call my brother | mumbled | no (test) |
| 13 | `sab_log_kahan_hain_1.m4a` | सब लोग कहाँ हैं | Where is everyone | slow | no (test) |
| 14 | `nahin_1.m4a` | नहीं | No | slurred | no (test) |
| 15 | `maaf_karna_1.m4a` | माफ़ करना | Sorry | quiet | no (test) |
| 16 | `shubh_ratri_1.m4a` | शुभ रात्रि | Good night | mumbled | no (test) |
| 17 | `karvat_badal_do_1.m4a` | करवट बदल दो | Turn me on my side | slow | no (val) |
| 18 | `pankha_chala_do_1.m4a` | पंखा चला दो | Turn on the fan | slurred | no (val) |
| 19 | `bas_pet_bhar_gaya_1.m4a` | बस, पेट भर गया | That's enough, I'm full | quiet | no (val) |
| 20 | `namak_kam_hai_1.m4a` | नमक कम है | It needs more salt | mumbled | no (val) |
| 21 | `papa_ko_bulao_1.m4a` | पापा को बुलाओ | Call my father | slow | no (val) |
| 22 | `mujhe_akela_mat_chhodo_1.m4a` | मुझे अकेला मत छोड़ो | Don't leave me alone | slurred | no (val) |
| 23 | `namaste_1.m4a` | नमस्ते | Hello | quiet | no (val) |
| 24 | `dhanyavaad_1.m4a` | धन्यवाद | Thank you | mumbled | no (val) |
| 25 | `aap_kaise_ho_1.m4a` | आप कैसे हो | How are you | slow | no (val) |
| 26 | `madad_chahiye_1.m4a` | मदद चाहिए | I need help | slurred | yes |
| 27 | `paani_chahiye_1.m4a` | पानी चाहिए | I need water | quiet | yes |
| 28 | `bathroom_jana_hai_1.m4a` | बाथरूम जाना है | I need the bathroom | mumbled | yes |
| 29 | `mujhe_utha_do_1.m4a` | मुझे उठा दो | Help me sit up | slow | yes |
| 30 | `thand_lag_rahi_hai_1.m4a` | ठंड लग रही है | I feel cold | slurred | yes |
| 31 | `light_band_kar_do_1.m4a` | लाइट बंद कर दो | Turn off the light | quiet | yes |
| 32 | `dawai_de_do_1.m4a` | दवाई दे दो | Give me my medicine | mumbled | yes |
| 33 | `saans_lene_mein_takleef_hai_1.m4a` | सांस लेने में तकलीफ़ है | I can't breathe properly | slow | yes |
| 34 | `chakkar_aa_rahe_hain_1.m4a` | चक्कर आ रहे हैं | I feel dizzy | slurred | yes |
| 35 | `bhookh_lagi_hai_1.m4a` | भूख लगी है | I'm hungry | quiet | yes |
| 36 | `khana_de_do_1.m4a` | खाना दे दो | Give me some food | mumbled | yes |
| 37 | `beti_ko_bulao_1.m4a` | बेटी को बुलाओ | Call my daughter | slow | yes |
| 38 | `didi_ko_bulao_1.m4a` | दीदी को बुलाओ | Call my sister | slurred | yes |
| 39 | `haan_1.m4a` | हाँ | Yes | quiet | yes |
| 40 | `ek_minute_ruko_1.m4a` | एक मिनट रुको | Wait a minute | mumbled | yes |

## Be honest about what this is

Team members imitating unclear speech isn't dysarthric speech. It shows whether the model helps
on Prisma's real mistakes, which the synthetic rules only guess at, but not how it does for a
person with dysarthria. MODEL_CARD.md says so.
