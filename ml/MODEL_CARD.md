# Model card: Sunn correction reranker (rerank-v2)

## What it is

A **text-only** correction model that sits on top of Gnani Prisma. A person with unclear speech
talks, Prisma writes what it heard (often wrong in consistent ways: "baani chaiye" for पानी चाहिए),
and this model answers one question: *the STT wrote X; which of the person's phrases did they
mean?* It never touches audio. Prisma stays the only speech-to-text and Timbre the only
text-to-speech.

- **Base:** `google/muril-base-cased` (238 M parameters), a cross-encoder with one output logit.
- **Input:** `heard [SEP] candidate_hindi / candidate_latin`, e.g. `बानी चाइए [SEP] पानी चाहिए / paani chahiye`.
- **Inference:** rapidfuzz (the backend's normalize + Levenshtein) shortlists the top 10 of the
  person's phrase bank; the model reorders those 10. It can never pick a phrase rapidfuzz left out.
- **When unsure:** if the softmax margin between its top two is below a threshold picked on val,
  hand the decision to the LLM judge (see "Margin threshold").

## Training data: all synthetic

`ml/build_dataset.py` -> `ml/data/train_all.csv`, 12,035 rows, one schema.

| source | made by | rows (train / val / test) | intended texts |
|---|---|---|---|
| word | `ml/make-word-varients.py`: rule-based mishearings of 225 Hindi words (seed 42) | 4520 / 811 / 442 | 225 |
| sentence | `ml/make_synthetic.py`: rule-based mishearings of 310 phrases in `ml/phrases.csv` (seed 7) | 4017 / 1117 / 1060 | 310 |
| composed | each word of a phrase replaced by a random word variant from the word set | 34 / 10 / 24 | 16 |

- **None of it is real Prisma output.** Every mistake comes from hand-written rules (voicing,
  aspiration, vowel length, dropped nasals and endings, merged words, real-word confusions...).
- **Composed is tiny:** only 16 of the 310 phrases have every word in the 225-word list, because
  the list has no function words (है, मुझे, को, में, दे are missing).
- **One split rule, no leaks:** a phrase containing a test word is test, else one containing a val
  word is val, else it keeps its own split. This moved 48 phrases (960 rows) out of train
  (21 to test, 26 to val, 1 from val to test); nothing moved into train. Composed rows take their
  phrase's split. Exact duplicates keep their most held-out copy.
- **Known overlap:** नहीं is a train word and a test phrase. 13 heard texts map to two intended
  texts (e.g. `haa` -> हाँ / हाथ), kept as real ambiguity.

## Training

bf16 on an RTX 5070 laptop GPU (8 GB), batch 32 groups of 8 (5.6 GB peak), AdamW lr 2e-5 with 5 %
warmup then linear decay, at most 5 epochs, best epoch by val score (mean of val top-1 on words and
on sentences), patience 2. Each example: the intended text plus 7 negatives from the same pool
(train intended texts only): 4 hard (the current model's mistakes from epoch 2, topped up with
rapidfuzz's closest), 2 of the same category, 1 of similar length. Half word rows and half sentence
rows per batch. Epoch 1 uses clean and mild rows only. `ml/results/train_log.csv` has every epoch.

## Results

### Real test: not run yet

**N = 0.** No team recordings exist yet (`ml/RECORDING.md` says how to make the 40). Until
`run_real_test.py` and `eval.py` have run on them, **there is no evidence that this model helps on
real Prisma output.** Everything below is synthetic.

### Synthetic test sets (not evidence: our rules made these mistakes)

Top-1 / top-3 in %, models scored in fp32. Candidates: all 225 words for test words; all 310
phrases for sentences. Per-severity numbers are in `ml/results/compare.md`.

| set | n | rapidfuzz | words only | sentences only | both (rerank-v2) |
|---|---|---|---|---|---|
| test words | 442 | 56.8 / 73.5 | 69.5 / 87.1 | 54.5 / 82.6 | **78.3 / 91.9** |
| test sentences | 1060 | 96.5 / 98.2 | 87.6 / 94.5 | 93.2 / 98.5 | **97.3 / 99.4** |
| composed test | 24 | 91.7 / 100 | 70.8 / 95.8 | 83.3 / 91.7 | **95.8 / 100** |

### Ablation

| run | best epoch | train min | val top-1 words | val top-1 sentences | test words | test sentences |
|---|---|---|---|---|---|---|
| words only | 1 of 3 | 3.2 | 75.1 | 86.9 | 69.5 | 87.6 |
| sentences only | 1 of 3 | 3.1 | 66.0 | 93.0 | 54.5 | 93.2 |
| both (rerank-v2) | 3 of 5 | 12.1 | 83.4 | 96.0 | 78.3 | 97.3 |
| rapidfuzz | - | - | 67.1 | 95.6 | 56.8 | 96.5 |

(Val numbers are from training, scored in bf16; test numbers in fp32.)

On synthetic data, combining helps: "both" beats either single source on every set. Each single
source is **worse than rapidfuzz** on the other kind and on sentences, and both peaked after the
easy first epoch, then got worse. One run per setup: two runs of rerank-v2 with the same seed
differed by up to 18 points of val words top-1 at the same epoch, so small gaps are noise. On
sentences, rerank-v2's 97.3 vs rapidfuzz's 96.5 is 8 rows of 1060: **too small to call a win.**
The clear gain is on single words (+21.5 points over rapidfuzz).

### Margin threshold (for the LLM judge)

Picked on val, per kind: the smallest top1-top2 softmax margin at which accepted predictions are
right at least 98 % of the time. One shared threshold didn't hold for words on val.

| kind | threshold | val: sent to LLM / top-1 of the rest | test: sent to LLM / top-1 of the rest |
|---|---|---|---|
| words | 0.662 | 50.2 % / 98.0 % | 60.0 % / 98.9 % |
| sentences | 0.000 | 1.4 % / 98.0 % | 0.7 % / 97.7 % |

On sentences the model is right 98 % of the time even at margin 0 on val, so the threshold says
"never defer"; on real speech that's unlikely to hold, so recalibrate on real recordings. The
margin can't exceed about 0.88: the logit is bounded at about ±2.1 by BERT's tanh pooler, so many
confident candidates tie near the cap (7.2 % of test-word margins are below 0.01).

### CPU export

`ml/export.py` -> `ml/models/rerank-v2-onnx/` (details in `ml/results/export.md`). Intel i7-14650HX
laptop CPU, one heard text against rapidfuzz's top 10, tokenizing included, median of 100 runs.

| model | size | latency (best thread count) | test words top-1 | test sentences top-1 |
|---|---|---|---|---|
| PyTorch fp32 | 906 MB | 476 ms (8 threads) | 78.3 | 97.3 |
| ONNX fp32 | 906 MB | 412 ms (8 threads) | 78.3 (same as PyTorch) | - |
| ONNX int8 (per channel, reduce_range) | 228 MB | 250 ms (8 threads) | **70.4** | 96.1 |

Plus 42 ms for the rapidfuzz shortlist. **Int8 is not lossless:** it changes 19.5 % of top-1 picks
on test words and costs 7.9 points there (1.2 on sentences). Default quantization was worse
(16 % agreement with fp32 on val), and ONNX Runtime's BERT optimizer couldn't fuse this graph.
Use ONNX fp32 until the saturated logits are fixed; onnxruntime's default thread count is 2-3x
slower on this hybrid CPU, so set `intra_op_num_threads` to 4-8.

## Intended use

Research and a demo of Sunn's correction step: reordering rapidfuzz's top 10 from a person's
phrase bank, with low-margin cases sent to the LLM judge. Not for clinical use, not as a speech
recognizer, and not without the person's own phrase bank.

## Limits, stated plainly

- **All training data is synthetic**, from rules we wrote. Prisma's real mistakes may look nothing
  like them, and a model can learn our rules instead of Prisma's habits.
- **No real evaluation yet** (N = 0 recordings). When it exists, it will be about 40 recordings from
  our team imitating unclear speech, which isn't dysarthric speech.
- **Not tested on real patients**, or on any person with dysarthria, aphasia or other speech
  difficulty.
- **Small vocabulary:** 225 words and 310 phrases, Hindi only. Composed sentences cover 16 phrases.
- **It can't recover what rapidfuzz misses:** shortlist recall@10 is 95.2 % on test words.
- **It prefers texts it has seen:** single-source runs got worse on new phrases with more training,
  likely by learning to favour train candidates. The app's starter bank is mostly in train, but a
  user's own new phrases won't be.
- **One seed per run**; differences of a few points aren't significant.

## Reproduce (from `ml/`)

```powershell
uv run build_dataset.py
uv run train_rerank.py --sources both
uv run train_rerank.py --sources words
uv run train_rerank.py --sources sentences
uv run run_real_test.py --dry-run; uv run run_real_test.py   # needs recordings, max 60 Prisma calls
uv run eval.py
uv run export.py
```
