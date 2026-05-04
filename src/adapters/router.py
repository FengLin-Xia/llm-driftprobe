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
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    local_path = config_path.with_name(f"{config_path.stem}.local{config_path.suffix}")
    if local_path.exists():
        with local_path.open("r", encoding="utf-8") as f:
            local_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, local_cfg)

    return cfg


def _deep_merge(base: Dict, override: Dict) -> Dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


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
    roles_cfg = cfg.get("roles") or {}
    local_models_cfg = cfg.get("local_models", {})

    adapters: Dict[str, BaseChatAdapter] = {}

    for provider_name, c in providers_cfg.items():
        kind = c.get("kind", "openai_compatible" if provider_name == "openrouter" else "")
        if kind != "openai_compatible":
            continue

        api_key = c.get("api_key")
        api_key_env = c.get("api_key_env")
        if not api_key and api_key_env:
            # Preferred use: api_key_env is an environment variable name.
            # Compatibility: if a config already contains a literal key here,
            # use it directly instead of treating it as an env var name.
            api_key = api_key_env if str(api_key_env).startswith("sk-") else os.getenv(api_key_env)
        if not api_key:
            # Keep adapter construction role-agnostic: a missing actor/judge key
            # should not break a target-only run, and vice versa.
            continue

        adapters[provider_name] = OpenAILikeAdapter(
            base_url=c["base_url"],
            api_key=api_key,
            provider_name=provider_name,
            default_model=c.get("default_model", "provider-selected"),
        )

    role_providers = {
        (role_cfg or {}).get("provider")
        for role_cfg in roles_cfg.values()
        if isinstance(role_cfg, dict)
    }
    local_required = "local/transformers" in role_providers or (not roles_cfg and bool(local_models_cfg))

    if local_required:
        # local adapters (transformers)
        # v0：先只创建一个共享的 local/transformers adapter（actor/judge 共享同一模型）
        for role in ("actor", "judge"):
            lm = local_models_cfg.get(role)
            if not lm:
                continue
            if lm.get("engine") == "transformers":
                # lazy import：避免用户只跑 API roles 时也要求 torch/transformers
                from .transformers_local import TransformersLocalAdapter

                adapters["local/transformers"] = TransformersLocalAdapter(
                    model_name_or_path=lm["model_name_or_path"],
                    device=lm.get("device", "auto"),
                    torch_dtype=lm.get("torch_dtype", "auto"),
                    default_max_new_tokens=lm.get("default_max_new_tokens", 512),
                )
                break

    return adapters

