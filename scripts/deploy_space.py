"""Deploy the last commit to a Hugging Face Gradio Space (docs/DEPLOY.md).

The Space runs app.py with the packages in requirements.txt and serves the committed
web/dist as it is: nothing is built there, so after a change in web/ run `npm run build`
in web/ and commit web/dist before deploying. The Space builds on Python 3.10 (it ignores a
newer python_version), so requirements.txt is resolved for 3.10, not exported from uv.lock
(3.13); after a change to the dependencies in pyproject.toml, run this and commit the result:

    uv pip compile pyproject.toml --python-version 3.10 --python-platform linux -o requirements.txt

It reads the pydantic<=2.12.5 constraint from [tool.uv] in pyproject.toml, which the Space's
gradio[mcp] install needs.

Uploads exactly the files git tracks, as they are in the last commit, and nothing else: no
history, no ignored files. It refuses when the working tree has uncommitted changes, when a
file is one that must never leave this machine (.env*, data/, logs/, web/certs/,
web/reference/, *.db), or when a file contains a secret from the local .env (or the
environment): the API keys, JWT_SECRET, or DATABASE_URL, whose password is looked for on its own too.

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
from urllib.parse import urlparse

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
# Tracked for the local Docker build, but not uploaded: HF builds a Gradio Space with a COPY that
# respects .dockerignore, and ours leaves out web/dist, which the Space serves.
NOT_UPLOADED = [".dockerignore"]
# fnmatch's * also matches /, so "*/.env*" catches a .env file in any folder.
BLOCKED = [".env*", "*/.env*", "data/*", "logs/*", "web/certs/*", "web/reference/*", "*.db"]
# Tracked on purpose: the template with placeholder values, and the default phrase lists the
# image needs (the same exceptions as .gitignore and .dockerignore).
ALLOWED = [".env.example", "data/default_phrases_*.txt"]
SECRETS = ["GNANI_STT_API_KEY", "GNANI_TTS_API_KEY", "GNANI_API_KEY", "JWT_SECRET", "GROQ_API_KEY", "LLM_API_KEY",
           "DATABASE_URL", "DATABASE_URL_UNPOOLED"]
# Connection strings: their password is searched for as well, so a pasted URL for another Neon
# branch of the same role (production's, say) is caught even though it isn't .env's.
URL_SECRETS = {"DATABASE_URL", "DATABASE_URL_UNPOOLED"}
# Safe default placeholders from .env.example that should not be flagged as real secrets.
SAFE_PLACEHOLDERS = {
    "your-key-here",
    "your-stt-key-here",
    "your-tts-key-here",
    "your-groq-key-here",
    "generate-one-with-the-command-above",
    "change-me",
    "placeholder",
    "postgresql://USER:PASSWORD@HOST-pooler.REGION.aws.neon.tech/neondb?sslmode=require",
    "",
}


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True).stdout


def export_head(folder):
    """Write the last commit's files into folder, with the line endings they have in git (the
    working tree has CRLF ones on Windows)."""
    folder_path = Path(folder)
    archive = git("-c", "core.autocrlf=false", "archive", "HEAD")
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(folder_path, filter="data")
    # Ensure Hugging Face Spaces receives required YAML frontmatter even when repo README omits it.
    # python_version: the Python the Space builds on, which requirements.txt is resolved for.
    readme = folder_path / "README.md"
    if readme.exists():
        content = readme.read_bytes()
        if not content.startswith(b"---"):
            hf_header = (
                "---\n"
                "title: Sunn\n"
                "sdk: gradio\n"
                "sdk_version: 6.32.0\n"
                "python_version: \"3.10\"\n"
                "app_file: app.py\n"
                "pinned: false\n"
                "short_description: Speech aid for dysarthric speech, Hindi and Indian English\n"
                "---\n\n"
            )
            # Bytes, not text: write_text turns every \n into \r\n on Windows, and the front
            # matter must reach HF with \n line endings.
            readme.write_bytes(hf_header.encode("utf-8") + content)


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
        needles = [value]
        if name in URL_SECRETS and (password := urlparse(value).password) and len(password) >= 8:
            needles.append(password)
        found += [f"{f} ({name})" for f in files
                  if any(needle.encode() in (folder / f).read_bytes() for needle in needles)]
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

    # What git tracks in the last commit, the same files export_head writes, but NOT_UPLOADED.
    files = git("ls-tree", "-r", "-z", "--name-only", "HEAD").decode().split("\0")[:-1]
    files = [f for f in files if f not in NOT_UPLOADED]
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
          "  secrets:   DATABASE_URL, GNANI_STT_API_KEY, GNANI_TTS_API_KEY, JWT_SECRET, GROQ_API_KEY\n"
          "  variables: TRUST_PROXY=1, GNANI_CALL_LIMIT, GROQ_MODEL, and optionally OWNER_EMAIL,\n"
          "             STT_DAILY_LIMIT, TTS_DAILY_LIMIT, ENROLL_DAILY_LIMIT, LIMIT_EXEMPT_EMAILS")
