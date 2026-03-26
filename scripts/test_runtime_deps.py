from __future__ import annotations


def main() -> None:
    deps = ["yaml", "httpx", "rich"]
    for mod in deps:
        try:
            __import__(mod)
            print(f"{mod}: OK")
        except Exception as e:  # pragma: no cover
            print(f"{mod}: FAIL {repr(e)}")


if __name__ == "__main__":
    main()

