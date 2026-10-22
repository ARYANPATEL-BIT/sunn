"""Deploy the last commit to a Hugging Face Docker Space (docs/DEPLOY.md).

Uploads exactly the files git tracks, as they are in the last commit, and nothing else: no
history, no ignored files. It refuses when the working tree has uncommitted changes, when a
file is one that must never leave this machine (.env*, data/, logs/, web/certs/,
web/reference/, *.db), or when a file contains the GNANI_API_KEY or JWT_SECRET from the local
.env (or the environment).

    uv run scripts/deploy_space.py --space <you>/sunn
    uv run scripts/deploy_space.py --check-only    # list what would be uploaded, upload nothing

Sign in once first with `uv run hf auth login`.
"""
import argparse
import io
import os
import subprocess
import sys
import tarfile
import tempfile
from fnmatch import fnmatchcase
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
# fnmatch's * also matches /, so "*/.env*" catches a .env file in any folder.
BLOCKED = [".env*", "*/.env*", "data/*", "logs/*", "web/certs/*", "web/reference/*", "*.db"]
# Tracked on purpose: the template with placeholder values, and the default phrase lists the
# image needs (the same exceptions as .gitignore and .dockerignore).
ALLOWED = [".env.example", "data/default_phrases_*.txt"]
SECRETS = ["GNANI_API_KEY", "JWT_SECRET"]
# Safe default placeholders from .env.example that should not be flagged as real secrets.
SAFE_PLACEHOLDERS = {
    "your-key-here",
    "generate-one-with-the-command-above",
    "change-me",
    "placeholder",
}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def export_head(folder):
    """Write the last commit's files into folder, with the line endings they have in git (the
    working tree has CRLF ones on Windows)."""
    archive = git("-c", "core.autocrlf=false", "archive", "HEAD")
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(folder, filter="data")


def blocked_paths(files):
    return [f for f in files if any(fnmatchcase(f, p) for p in BLOCKED)
            and not any(fnmatchcase(f, p) for p in ALLOWED)]


def files_with_secrets(files, folder, env_path):
    """The files in folder that contain the value of one of SECRETS, from the local .env or,
    like the app, the environment."""
    env = dotenv_values(env_path)
    found = []
    for name in SECRETS:
        value = (env.get(name) or os.environ.get(name) or "").strip()
        if not value:
            print(f"note: {name} isn't in {env_path} or the environment, so no file was checked for it")
            continue
        if value in SAFE_PLACEHOLDERS:
            print(f"note: {name} is set to placeholder '{value}' in {env_path}, skipping secret leak check")
            continue
        found += [f"{f} ({name})" for f in files if value.encode() in (folder / f).read_bytes()]
    return found


def refuse(message, paths=()):
    print(f"refusing to deploy: {message}")
    for p in paths:
        print(f"  {p}")
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--space", help="the Space, as <username>/<space-name>")
    parser.add_argument("--check-only", action="store_true",
                        help="run the checks and list the files, but upload nothing")
    args = parser.parse_args()
    if not args.space and not args.check_only:
        parser.error("--space is required (or --check-only)")

    changed = git("status", "--porcelain", "--untracked-files=no").decode().splitlines()
    if changed and not args.check_only:
        refuse("there are uncommitted changes; commit them first, so the Space gets exactly a commit",
               changed)

    # What git tracks in the last commit, the same files export_head writes.
    files = git("ls-tree", "-r", "-z", "--name-only", "HEAD").decode().split("\0")[:-1]
    if bad := blocked_paths(files):
        refuse("these tracked files must never be deployed", bad)

    sha = git("rev-parse", "--short", "HEAD").decode().strip()
    with tempfile.TemporaryDirectory() as tmp:
        export_head(tmp)
        if bad := files_with_secrets(files, Path(tmp), ROOT / ".env"):
            refuse("these files contain a secret from .env", bad)

        if args.check_only:
            print("\n".join(files))
            print(f"\nchecks passed: {len(files)} files would be uploaded as \"deploy {sha}\"")
            if changed:
                print("but a real deploy would refuse these uncommitted changes:\n  " + "\n  ".join(changed))
            sys.exit(0)

        from huggingface_hub import HfApi

        api = HfApi()
        api.upload_folder(repo_id=args.space, repo_type="space", folder_path=tmp,
                          allow_patterns=files, commit_message=f"deploy {sha}")

    print(f"uploaded {len(files)} files as \"deploy {sha}\"")
    print(f"open it at {api.space_info(args.space).host} (follow the build in the Logs tab of "
          f"https://huggingface.co/spaces/{args.space})")
    print("the Space needs these in Settings > Variables and secrets:\n"
          "  secrets:   GNANI_API_KEY, JWT_SECRET, DEMO_INVITE_CODE\n"
          "  variables: TRUST_PROXY=1, GNANI_CALL_LIMIT, DAILY_CALL_CAP_PER_USER")
