from __future__ import annotations

import os


def main() -> None:
    v = os.getenv("OPENROUTER_API_KEY")
    if v:
        print("OPENROUTER_API_KEY: exists, len=", len(v))
    else:
        print("OPENROUTER_API_KEY: MISSING")


if __name__ == "__main__":
    main()

