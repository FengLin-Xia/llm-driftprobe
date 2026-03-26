from __future__ import annotations

import glob
import os
import re


def main() -> None:
    roots = []
    home = os.path.expanduser("~")
    local_appdata = os.environ.get("LOCALAPPDATA", "")

    candidates = [
        os.path.join(home, ".cache", "huggingface", "hub"),
        os.path.join(home, ".cache", "huggingface"),
        os.path.join(local_appdata, "huggingface", "hub"),
        os.path.join(local_appdata, "huggingface"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            roots.append(c)

    print("cache_roots:", roots)

    # "Qwen2.5" 在文件路径里未必会完整出现，所以用更宽松 pattern 先定位
    qwen_pat = re.compile(r"(Qwen|qwen|Qwen2\.5|Qwen2\.5-7B|Qwen2\.5-7B-Instruct)")

    matches = []
    for root in roots:
        # 只扫描到一定深度，避免过慢；实际通常几层就能定位到目录名
        for p in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if len(matches) >= 80:
                break
            if qwen_pat.search(p):
                matches.append(p)
        if len(matches) >= 80:
            break

    print("matches_found:", len(matches))
    for m in matches[:80]:
        print(m)


if __name__ == "__main__":
    main()

