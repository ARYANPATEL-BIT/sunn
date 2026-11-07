# Correction model: comparison (2026-11-07)

## Real test: our recordings through Prisma (the only honest number)

**Not run yet: no recordings.** Record them as in ml/RECORDING.md, then run `uv run run_real_test.py` and `uv run eval.py` again. Until then there is no evidence that the model helps on real Prisma output.

## Synthetic test sets

> **Synthetic numbers are not evidence.** The mistakes below were made by our own rules, so a model can learn the rules rather than Prisma's real mistakes. They show the code works and how the sources compare, nothing more.

| set | n | shortlist recall@10 | rapidfuzz top-1 | words only top-1 | sentences only top-1 | both (rerank-v2) top-1 | rapidfuzz top-3 | words only top-3 | sentences only top-3 | both (rerank-v2) top-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| test words | 442 | 95.2 | 56.8 | 69.5 | 54.5 | 78.3 | 73.5 | 87.1 | 82.6 | 91.9 |
| test sentences | 1060 | 99.5 | 96.5 | 87.6 | 93.2 | 97.3 | 98.2 | 94.5 | 98.5 | 99.4 |
| composed test | 24 | 100.0 | 91.7 | 70.8 | 83.3 | 95.8 | 100.0 | 95.8 | 91.7 | 100.0 |

A model only reorders rapidfuzz's top 10, so shortlist recall@10 is the most any of them can reach. Models are scored in fp32: their logits saturate near the classifier's bound (about ±2.1, after BERT's tanh pooler), and bf16 rounds the top candidates into ties, which count as misses (rerank-v2 on test words: 75.8 in bf16, 78.3 in fp32).

### Top-1 per severity (%)

**test words**

| system | clean (n=34) | mild (n=174) | moderate (n=197) | severe (n=37) |
|---|---|---|---|---|
| rapidfuzz | 100.0 | 66.7 | 42.1 | 48.6 |
| words only | 94.1 | 78.2 | 58.9 | 62.2 |
| sentences only | 82.4 | 60.9 | 46.7 | 40.5 |
| both (rerank-v2) | 100.0 | 87.9 | 66.5 | 75.7 |

**test sentences**

| system | clean (n=53) | mild (n=371) | moderate (n=371) | severe (n=265) |
|---|---|---|---|---|
| rapidfuzz | 100.0 | 98.9 | 97.3 | 91.3 |
| words only | 100.0 | 94.3 | 88.1 | 75.1 |
| sentences only | 98.1 | 96.5 | 94.9 | 85.3 |
| both (rerank-v2) | 100.0 | 99.5 | 98.4 | 92.1 |

**composed test**

| system | clean (n=1) | mild (n=10) | moderate (n=10) | severe (n=3) |
|---|---|---|---|---|
| rapidfuzz | 100.0 | 100.0 | 80.0 | 100.0 |
| words only | 100.0 | 80.0 | 60.0 | 66.7 |
| sentences only | 100.0 | 80.0 | 80.0 | 100.0 |
| both (rerank-v2) | 100.0 | 100.0 | 90.0 | 100.0 |

## When to ask the LLM judge: the top1-top2 margin

A threshold is the smallest margin at which accepted predictions are right at least 98 % of the time on val; below it, the LLM judge decides. rapidfuzz margins are points out of 100, model margins softmax probability over the 10 candidates, which can't exceed about 0.88 because the logits are bounded. Cells are "% sent to the LLM / top-1 of the rest".

**On val.** One threshold for words and sentences together doesn't hold for words: val alone shows it, so each kind gets its own threshold, also picked on val.

| system | one threshold | val words at it | val sentences at it | val words: own threshold, then at it | val sentences: own threshold, then at it |
|---|---|---|---|---|---|
| rapidfuzz | 13.333 | 41.9 / 94.5 | 20.2 / 100.0 | 25.556: 76.3 / 98.4 | 1.538: 2.9 / 98.1 |
| words only | 0.028 | 87.5 / 98.0 | 99.5 / 100.0 | 0.028: 87.5 / 98.0 | 0.011: 44.7 / 98.1 |
| sentences only | 0.006 | 78.7 / 93.1 | 21.3 / 99.0 | 0.020: 91.4 / 98.6 | 0.000: 8.9 / 98.1 |
| both (rerank-v2) | 0.478 | 36.5 / 95.1 | 10.8 / 99.5 | 0.662: 50.2 / 98.0 | 0.000: 1.4 / 98.0 |

**On test**, with the per-kind thresholds from val, unchanged (words for test words, sentences for the rest):

| system | test words (margin p10 / p50 / p90) | test sentences (margin p10 / p50 / p90) | composed test (margin p10 / p50 / p90) |
|---|---|---|---|
| rapidfuzz | 81.7 / 100.0 (p10 0.00, p50 13.33, p90 33.33) | 2.1 / 98.1 (p10 6.24, p50 20.53, p90 37.11) | 0.0 / 91.7 (p10 7.18, p50 15.59, p90 28.00) |
| words only | 92.8 / 96.9 (p10 0.00, p50 0.00, p90 0.03) | 47.3 / 97.9 (p10 0.00, p50 0.01, p90 0.03) | 58.3 / 90.0 (p10 0.00, p50 0.00, p90 0.03) |
| sentences only | 91.0 / 90.0 (p10 0.00, p50 0.00, p90 0.02) | 10.2 / 97.2 (p10 0.00, p50 0.02, p90 0.02) | 29.2 / 94.1 (p10 0.00, p50 0.01, p90 0.02) |
| both (rerank-v2) | 60.0 / 98.9 (p10 0.02, p50 0.53, p90 0.87) | 0.7 / 97.7 (p10 0.41, p50 0.87, p90 0.88) | 0.0 / 95.8 (p10 0.40, p50 0.85, p90 0.88) |

## Ablation: does combining the sources help?

| system | best epoch | epochs run | train min | val top-1 words | val top-1 sentences | val score | test words top-1 | test sentences top-1 | composed test top-1 |
|---|---|---|---|---|---|---|---|---|---|
| words only | 1 | 3 | 3.2 | 75.1 | 86.9 | 81.0 | 69.5 | 87.6 | 70.8 |
| sentences only | 1 | 3 | 3.1 | 66.0 | 93.0 | 79.5 | 54.5 | 93.2 | 83.3 |
| both (rerank-v2) | 3 | 5 | 12.1 | 83.4 | 96.0 | 89.7 | 78.3 | 97.3 | 95.8 |
| rapidfuzz | - | - | - | 67.1 | 95.6 | 81.3 | 56.8 | 96.5 | 91.7 |

Every run uses the same train/val/test split (ml/data/train_all.csv) and picks its best epoch by the same val score (mean of val top-1 on words and on sentences), with patience 2. One run per setup (seed 7): GPU training isn't bit-reproducible, and two runs of rerank-v2 with the same seed differed by up to 18 points of val words top-1 at the same epoch (epoch 2: 59.1 vs 77.1), so gaps of a few points between runs are noise.
