#!/usr/bin/env python3
"""Generate test status badge for README."""

import subprocess
import sys
from pathlib import Path


def get_test_status():
    """Run tests and return status."""
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=no", "-q"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout, result.stderr


def generate_badge(passed: bool, total: int):
    """Generate badge markdown."""
    if passed:
        color = "green"
        status = "passing"
    else:
        color = "red"
        status = "failing"
    
    badge_url = f"https://img.shields.io/badge/tests-{status}-{color}"
    return f"[![Tests]({badge_url})](test-results/report.html)"


if __name__ == "__main__":
    passed, stdout, stderr = get_test_status()
    
    # Count tests from output
    lines = stdout.split("\n")
    total = 0
    for line in lines:
        if " passed" in line or " failed" in line:
            parts = line.split()
            for part in parts:
                if part.isdigit():
                    total = int(part)
                    break
    
    badge = generate_badge(passed, total)
    print(badge)
    
    sys.exit(0 if passed else 1)

