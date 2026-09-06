#!/usr/bin/env python3
"""Reject mutable remote action references in GitHub workflow files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


USES_PATTERN = re.compile(r"^\s*(?:-\s*)?uses\s*:\s*(?P<value>.+?)\s*$")
FULL_COMMIT_PATTERN = re.compile(r"^[^\s/@]+/[^\s@]+@[0-9a-fA-F]{40}$")
DOCKER_DIGEST_PATTERN = re.compile(r"^docker://[^\s@]+@sha256:[0-9a-fA-F]{64}$")


def strip_yaml_comment(value: str) -> str:
    """Strip an unquoted YAML comment and surrounding scalar quotes."""
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote == '"':
            escaped = True
            continue
        if character in {"'", '"'}:
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
            continue
        if character == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            value = value[:index]
            break
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1].strip()
    return value


def validate_reference(reference: str) -> str | None:
    if reference.startswith("./"):
        return None
    if reference.startswith("docker://"):
        if DOCKER_DIGEST_PATTERN.fullmatch(reference):
            return None
        return "Docker action must use an immutable sha256 digest"
    if FULL_COMMIT_PATTERN.fullmatch(reference):
        return None
    return "remote action or reusable workflow must use a full 40-character commit SHA"


def workflow_files(root: Path) -> list[Path]:
    workflow_root = root / ".github" / "workflows"
    return sorted((*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml")))


def validate_workflow(path: Path) -> list[str]:
    violations: list[str] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        match = USES_PATTERN.match(line)
        if not match:
            continue
        reference = strip_yaml_comment(match.group("value"))
        problem = validate_reference(reference)
        if problem:
            violations.append(f"{path}:{line_number}: {problem}: {reference}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    files = workflow_files(args.root)
    if not files:
        print("No GitHub workflow files found", file=sys.stderr)
        return 1

    violations = [violation for path in files for violation in validate_workflow(path)]
    if violations:
        print("\n".join(violations), file=sys.stderr)
        return 1

    print(f"Validated immutable action references in {len(files)} workflow file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
