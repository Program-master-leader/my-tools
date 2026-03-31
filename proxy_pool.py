#!/usr/bin/env python3
"""
代理/IP 池（给各个数据源爬虫统一调用）

设计目标：
- 配置存放在 AppData\\Roaming\\KHY小工具，不污染项目目录
- 支持 round-robin / random 轮换
- 支持禁用某些代理、失败计数（简单熔断）
"""

from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, List, Optional


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_USER_DATA = os.path.join(os.environ.get("APPDATA", SCRIPT_DIR), "KHY小工具")
os.makedirs(_USER_DATA, exist_ok=True)

PROXY_FILE = os.path.join(_USER_DATA, "proxies.json")


def _default_config() -> Dict[str, Any]:
    return {
        "mode": "round_robin",  # round_robin | random
        "cooldown_sec": 120,    # 代理失败后冷却时间（秒）
        "items": [
            # {"name":"本地7890", "proxy":"http://127.0.0.1:7890", "enabled": True}
        ],
        "_state": {"rr_index": 0, "fail": {}},
    }


def load_config() -> Dict[str, Any]:
    if not os.path.exists(PROXY_FILE):
        cfg = _default_config()
        save_config(cfg)
        return cfg
    try:
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("bad proxies.json")
        cfg.setdefault("mode", "round_robin")
        cfg.setdefault("cooldown_sec", 120)
        cfg.setdefault("items", [])
        cfg.setdefault("_state", {"rr_index": 0, "fail": {}})
        cfg["_state"].setdefault("rr_index", 0)
        cfg["_state"].setdefault("fail", {})
        return cfg
    except Exception:
        cfg = _default_config()
        save_config(cfg)
        return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    with open(PROXY_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def list_enabled_proxies(cfg: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cfg = cfg or load_config()
    items = cfg.get("items", [])
    if not isinstance(items, list):
        return []
    now = time.time()
    fail = (cfg.get("_state") or {}).get("fail", {}) or {}
    cooldown = int(cfg.get("cooldown_sec", 120) or 120)
    enabled = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if not it.get("enabled", True):
            continue
        p = (it.get("proxy") or "").strip()
        if not p:
            continue
        k = it.get("name") or p
        last_fail = (fail.get(k) or {}).get("last_fail_ts")
        if last_fail and (now - float(last_fail)) < cooldown:
            continue
        enabled.append(it)
    return enabled


def get_next_proxy(cfg: Optional[Dict[str, Any]] = None) -> str:
    """
    返回一个 proxy 字符串（如 http://127.0.0.1:7890），没有则返回空串。
    """
    cfg = cfg or load_config()
    items = list_enabled_proxies(cfg)
    if not items:
        return ""

    mode = (cfg.get("mode") or "round_robin").strip().lower()
    state = cfg.setdefault("_state", {"rr_index": 0, "fail": {}})

    if mode == "random":
        it = random.choice(items)
        return (it.get("proxy") or "").strip()

    # round robin
    idx = int(state.get("rr_index", 0) or 0)
    it = items[idx % len(items)]
    state["rr_index"] = (idx + 1) % max(len(items), 1)
    save_config(cfg)
    return (it.get("proxy") or "").strip()


def report_proxy_failure(proxy_or_name: str, cfg: Optional[Dict[str, Any]] = None) -> None:
    cfg = cfg or load_config()
    state = cfg.setdefault("_state", {"rr_index": 0, "fail": {}})
    fail = state.setdefault("fail", {})
    key = proxy_or_name.strip()
    if not key:
        return
    rec = fail.get(key) or {"count": 0, "last_fail_ts": 0}
    rec["count"] = int(rec.get("count", 0) or 0) + 1
    rec["last_fail_ts"] = time.time()
    fail[key] = rec
    save_config(cfg)


def apply_proxy_to_env(proxy: str) -> None:
    """
    给依赖环境变量的库使用（urllib / 部分 CLI 工具）。
    """
    proxy = (proxy or "").strip()
    if not proxy:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
        os.environ.pop("ALL_PROXY", None)
        return
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy
    os.environ["ALL_PROXY"] = proxy


def normalize_proxy_value(v: str) -> str:
    """
    支持几种常见写法：
    - 空：表示不设置（由上层决定是否走代理池）
    - pool / 代理池：表示使用代理池
    - http://ip:port 等：固定代理
    """
    s = (v or "").strip()
    if not s:
        return ""
    low = s.lower()
    if low in ("pool", "代理池", "proxy_pool", "auto"):
        return "POOL"
    return s


def get_proxy_for_account(account: Optional[Dict[str, Any]] = None, cfg: Optional[Dict[str, Any]] = None) -> str:
    """
    根据账号配置返回代理：
    - account['proxy'] = 固定代理 → 返回固定代理
    - account['proxy'] = POOL/代理池/auto 或空 → 返回代理池的下一个代理（如果池为空则返回空）
    """
    cfg = cfg or load_config()
    if not account:
        return get_next_proxy(cfg)
    v = normalize_proxy_value(str(account.get("proxy", "") or ""))
    if not v or v == "POOL":
        return get_next_proxy(cfg)
    return v


def to_requests_proxies(proxy: str) -> Dict[str, str]:
    """
    给 requests / httpx 常用的 proxies 字典格式。
    """
    p = (proxy or "").strip()
    if not p:
        return {}
    return {"http": p, "https": p}

