from __future__ import annotations


def main() -> None:
    try:
        import transformers  # noqa: F401

        print("transformers: OK")
    except Exception as e:  # pragma: no cover
        print("transformers: FAIL", repr(e))

    try:
        import torch  # noqa: F401

        print("torch: OK")
    except Exception as e:  # pragma: no cover
        print("torch: FAIL", repr(e))


if __name__ == "__main__":
    main()

