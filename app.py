"""Hugging Face Gradio Space entry point: runs src/server.py on 0.0.0.0:7860, like the Dockerfile's CMD."""
import os
import runpy
import sys

SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
sys.path.insert(0, SRC)  # src/ modules import each other by bare name (import api)
sys.argv = ["server.py", "--host", "0.0.0.0", "--port", "7860"]
runpy.run_path(os.path.join(SRC, "server.py"), run_name="__main__")
