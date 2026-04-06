#!/usr/bin/env python3
"""Parse PR labels from the GitHub event payload and print them comma-separated."""

import json
import os


def main() -> None:
    path = os.environ.get("GITHUB_EVENT_PATH", "")
    event = {}
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            event = json.load(fh)

    pr = event.get("pull_request", {}) or {}
    labels = pr.get("labels", []) or []
    names = [(label.get("name", "") or "").strip().lower() for label in labels]
    print(",".join(n for n in names if n))


if __name__ == "__main__":
    main()
