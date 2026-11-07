# rerank-v2 CPU export

ONNX (opset 17), int8 dynamic quantization per channel with reduce_range (onnxruntime 1.31.1). CPU: 24 logical threads. Latency includes tokenizing; median and p90 of 100 runs, for one heard text against rapidfuzz's top 10.

| file | MB |
|---|---|
| pytorch fp32 | 906 |
| onnx fp32 | 906 |
| onnx int8 | 228 |

| step | median ms | p90 ms |
|---|---|---|
| rapidfuzz shortlist (51 phrases) | 42 | 45 |
| pytorch fp32, 2 threads | 1129 | 1183 |
| onnx fp32, 2 threads | 1017 | 1078 |
| onnx int8, 2 threads | 510 | 550 |
| pytorch fp32, 4 threads | 610 | 696 |
| onnx fp32, 4 threads | 538 | 589 |
| onnx int8, 4 threads | 286 | 308 |
| pytorch fp32, 8 threads | 476 | 512 |
| onnx fp32, 8 threads | 412 | 488 |
| onnx int8, 8 threads | 250 | 314 |

Fastest int8 setting: **onnx int8, 8 threads**, 250 ms median for the model, plus 42 ms for the rapidfuzz shortlist.

| set | n | top-1 pytorch (as in eval.py) | top-1 onnx int8 (CPU) | same top-1 |
|---|---|---|---|---|
| test words | 442 | 78.3 | 70.4 | 80.5 % |
| test sentences | 1060 | 97.3 | 96.1 | 96.8 % |

real_test.csv doesn't exist yet: run this again after run_real_test.py to check the real recordings.
