"""Checks that torch sees the GPU and can run bf16 on it."""
import torch

print("torch", torch.__version__, "cuda", torch.version.cuda)
if not torch.cuda.is_available():
    raise SystemExit("CUDA is not available: torch will train on the CPU")
props = torch.cuda.get_device_properties(0)
print(f"{props.name}, {props.total_memory / 2**30:.1f} GiB, compute capability {props.major}.{props.minor}")
print("bf16 supported:", torch.cuda.is_bf16_supported())
x = torch.randn(1024, 1024, device="cuda", dtype=torch.bfloat16)
print("bf16 matmul ok:", torch.isfinite(x @ x).all().item())
