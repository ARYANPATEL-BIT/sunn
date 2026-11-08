"""Check every file in content/trainings/ against docs/TRAININGS_CONTRACT.md: required fields and
their types, step types, the feedback rule, unique ids, references between files, and every
audio_key listed in audio.json with the text it says. Prints each problem; exits 1 if any.

    uv run scripts/validate_trainings.py
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
import trainings_content  # noqa: E402


def check(root=trainings_content.ROOT):
    """Every problem in the content at root, in plain English; [] when it all fits."""
    try:
        library = trainings_content.load(root)
    except (ValueError, OSError) as e:
        return [str(e)]
    return trainings_content.problems(library)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=trainings_content.ROOT)
    args = parser.parse_args()
    found = check(args.root)
    for problem in found:
        print(problem)
    if found:
        sys.exit(1)
    library = trainings_content.load(args.root)
    print(f"ok: {len(library.categories)} categories, {len(library.courses)} courses, {len(library.lessons)} lessons,"
          f" {len(library.steps)} steps, {len(library.sounds)} sounds, {len(library.audio)} audio keys")
