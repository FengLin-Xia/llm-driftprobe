from __future__ import annotations

import os


def main() -> None:
    p = r"C:\Users\Fenglin\AI\projects\qwen_test"
    print("exists:", os.path.exists(p))
    if not os.path.exists(p):
        return

    names = sorted(os.listdir(p))
    print("count:", len(names))
    for name in names[:200]:
        full = os.path.join(p, name)
        kind = "dir" if os.path.isdir(full) else "file"
        size = os.path.getsize(full) if os.path.isfile(full) else 0
        print(f"- {kind}: {name} ({size} bytes)")


if __name__ == "__main__":
    main()

