#!/usr/bin/env python3

import re
import sys
from pathlib import Path


ERROR_PATTERNS = [
    (
        r"\bgame\s*:\s*GetService\(\s*[\"']Workspace[\"']\s*\)",
        "Workspace is usually accessed with workspace directly."
    ),
    (
        r"\bwait\s*\(",
        "Consider using task.wait() instead of the deprecated wait()."
    ),
    (
        r"\bspawn\s*\(",
        "Consider using task.spawn() instead of the deprecated spawn()."
    ),
    (
        r"\bdelay\s*\(",
        "Consider using task.delay() instead of the deprecated delay()."
    ),
]

REMOTE_CLIENT_PATTERNS = [
    r":FireServer\(",
    r":InvokeServer\(",
]

DANGEROUS_SERVER_PATTERNS = [
    r"PlayerAdded.*Kick",
    r"RemoteEvent.*OnServerEvent",
]


def check_file(file_path: Path) -> list[str]:
    findings: list[str] = []

    try:
        code = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["File is not valid UTF-8 text."]
    except OSError as exc:
        return [f"Could not read file: {exc}"]

    lines = code.splitlines()

    # Basic bracket matching.
    opening = {"(": ")", "[": "]", "{": "}"}
    closing = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []

    for line_number, line in enumerate(lines, start=1):
        for character in line:
            if character in opening:
                stack.append(character)
            elif character in closing:
                if not stack or stack[-1] != closing[character]:
                    findings.append(
                        f"Line {line_number}: Possible unmatched '{character}'."
                    )
                else:
                    stack.pop()

    if stack:
        findings.append(
            "Possible unmatched opening brackets: "
            + ", ".join(stack)
        )

    # Known patterns.
    for pattern, message in ERROR_PATTERNS:
        if re.search(pattern, code, flags=re.IGNORECASE | re.DOTALL):
            findings.append(message)

    # Find likely client/server mistakes.
    if ":FireServer(" in code and "LocalScript" not in code:
        findings.append(
            "FireServer() is normally called from a LocalScript."
        )

    if ":InvokeServer(" in code and "LocalScript" not in code:
        findings.append(
            "InvokeServer() is normally called from a LocalScript."
        )

    # Basic infinite-loop warning.
    if re.search(r"while\s+true\s+do", code, flags=re.IGNORECASE):
        if "task.wait" not in code and "task.delay" not in code:
            findings.append(
                "while true do was found without an obvious yield such as task.wait()."
            )

    # Basic empty wait-for-child check.
    if ":WaitForChild(" in code and re.search(
        r":WaitForChild\(\s*\)",
        code
    ):
        findings.append(
            "WaitForChild() appears to have no child name."
        )

    # Warn about suspicious global declarations.
    for line_number, line in enumerate(lines, start=1):
        if re.match(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*=", line):
            findings.append(
                f"Line {line_number}: Possible global variable assignment. "
                "Prefer local when possible."
            )

    # Remove duplicates while preserving order.
    unique_findings = []
    seen = set()

    for finding in findings:
        if finding not in seen:
            unique_findings.append(finding)
            seen.add(finding)

    return unique_findings


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python roblox_code_checker.py <file.lua>")
        return 1

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return 1

    if not file_path.is_file():
        print(f"Not a file: {file_path}")
        return 1

    findings = check_file(file_path)

    print(f"Checking: {file_path}")
    print()

    if not findings:
        print("PASS: No obvious problems were detected.")
        print("This does not guarantee the script is bug-free.")
        return 0

    print(f"Found {len(findings)} possible issue(s):")
    print()

    for index, finding in enumerate(findings, start=1):
        print(f"{index}. {finding}")

    print()
    print(
        "Review these findings before using the script in Roblox Studio."
    )

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
