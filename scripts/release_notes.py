"""Generate markdown release notes from conventional-commit subjects."""

import argparse
import re
import subprocess
import sys

GROUPS: dict[str, str] = {
    "feat": "Features",
    "fix": "Bug Fixes",
    "ci": "CI",
    "docs": "Documentation",
    "chore": "Chores",
    "build": "Build",
    "other": "Other",
}

PREFIX_RE = re.compile(r"^(feat|fix|ci|docs|chore|build)(\(.+?\))?!?:")


def latest_tag() -> str | None:
    result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def commit_subjects(since_tag: str | None) -> list[str]:
    log_range = f"{since_tag}..HEAD" if since_tag else "HEAD"
    result = subprocess.run(
        ["git", "log", log_range, "--pretty=format:%s"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    lines = result.stdout.splitlines()
    return [line.strip() for line in lines if line.strip()]


def group_commits(subjects: list[str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {key: [] for key in GROUPS}
    for subject in subjects:
        match = PREFIX_RE.match(subject)
        if match:
            prefix = match.group(1)
            grouped[prefix].append(subject)
        else:
            grouped["other"].append(subject)
    return grouped


def render_markdown(
    grouped: dict[str, list[str]],
    version: str | None,
) -> str:
    lines: list[str] = []
    if version:
        lines.append(f"## {version}\n")
    for key, heading in GROUPS.items():
        commits = grouped.get(key, [])
        if not commits:
            continue
        lines.append(f"### {heading}\n")
        for subject in commits:
            lines.append(f"- {subject}")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate markdown release notes from git commits.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Release version used as the document title (optional).",
    )
    args = parser.parse_args()

    tag = latest_tag()
    subjects = commit_subjects(tag)

    if not subjects:
        print("No commits found since the last tag." if tag else "No commits found.")
        sys.exit(0)

    grouped = group_commits(subjects)
    print(render_markdown(grouped, args.version))
    sys.exit(0)


if __name__ == "__main__":
    main()
