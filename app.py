"""Hugging Face Gradio Space entry point: runs src/server.py on 0.0.0.0:7860, like the Dockerfile's CMD."""
import os
import runpy
import sys

try:
    import spaces  # HF installs it on the Space; not an app dependency, so absent locally
except ImportError:
    spaces = None

if spaces is not None:
    @spaces.GPU
    def zerogpu_check():
        """Never called: ZeroGPU stops a Space that has no @spaces.GPU function at startup."""

    # spaces reports @spaces.GPU functions to ZeroGPU from gradio's launch(), which Sunn never
    # calls, so report them here; startup exists only on ZeroGPU (SPACES_ZERO_GPU set).
    startup = getattr(spaces.zero, "startup", None)
    if startup:
        startup()

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, SRC)  # src/ modules import each other by bare name (import api)
sys.argv = ["server.py", "--host", "0.0.0.0", "--port", "7860"]
runpy.run_path(os.path.join(SRC, "server.py"), run_name="__main__")
