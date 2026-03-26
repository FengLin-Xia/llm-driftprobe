from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

import yaml

try:
    # 可选依赖：如果环境里装了 python-dotenv，就用它解析 .env
    from dotenv import load_dotenv  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    load_dotenv = None

from .base import BaseChatAdapter
from .openai_like import OpenAILikeAdapter


def load_model_config(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_adapters_from_config(config_path: str) -> Dict[str, BaseChatAdapter]:
    # v0：支持从项目根目录读取 `.env`（避免每次手动设置 OPENROUTER_API_KEY）
    # `.env` 已写入 `.gitignore`，不会提交到仓库。
    project_root = Path(config_path).resolve().parents[1]
    dotenv_path = project_root / ".env"
    if dotenv_path.exists():
        if load_dotenv is not None:
            load_dotenv(dotenv_path=dotenv_path, override=False)
        else:
            # fallback：最简 .env 解析（仅处理 KEY=VALUE；忽略注释/空行）
            for raw in dotenv_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value

    cfg = load_model_config(config_path)
    providers_cfg = cfg.get("providers", {})
    local_models_cfg = cfg.get("local_models", {})

    adapters: Dict[str, BaseChatAdapter] = {}

    if "openrouter" in providers_cfg:
        c = providers_cfg["openrouter"]
        api_key = os.getenv(c["api_key_env"])
        if not api_key:
            raise RuntimeError(f"Missing OpenRouter API key in env: {c['api_key_env']}")

        adapters["openrouter"] = OpenAILikeAdapter(
            base_url=c["base_url"],
            api_key=api_key,
        )

    # local adapters (transformers)
    # v0：先只创建一个共享的 local/transformers adapter（actor/judge 共享同一模型）
    for role in ("actor", "judge"):
        lm = local_models_cfg.get(role)
        if not lm:
            continue
        if lm.get("engine") == "transformers":
            # lazy import：避免用户只跑 openrouter 时也要求 torch/transformers
            from .transformers_local import TransformersLocalAdapter

            adapters["local/transformers"] = TransformersLocalAdapter(
                model_name_or_path=lm["model_name_or_path"],
                device=lm.get("device", "auto"),
                torch_dtype=lm.get("torch_dtype", "auto"),
                default_max_new_tokens=lm.get("default_max_new_tokens", 512),
            )
            break

    return adapters

