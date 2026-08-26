"""Persistência do catálogo demo (memória + JSON em backend/.demo-state/)."""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from app.demo.catalog import fresh_state

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()
_STATE: Optional[Dict[str, Any]] = None
_STATE_DIR = Path(__file__).resolve().parents[2] / ".demo-state"
_STATE_FILE = _STATE_DIR / "catalog.json"


def _load() -> Dict[str, Any]:
    global _STATE
    if _STATE is not None:
        return _STATE
    if _STATE_FILE.is_file():
        try:
            _STATE = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
            return _STATE
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Falha ao ler estado demo (%s); usando catálogo fresco", exc)
    _STATE = fresh_state()
    return _STATE


def get_state() -> Dict[str, Any]:
    with _LOCK:
        return _load()


def persist() -> None:
    with _LOCK:
        state = _load()
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            _STATE_FILE.write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("Falha ao persistir estado demo: %s", exc)


def reset_state() -> Dict[str, Any]:
    global _STATE
    with _LOCK:
        _STATE = fresh_state()
        try:
            if _STATE_FILE.is_file():
                _STATE_FILE.unlink()
        except OSError:
            pass
        return _STATE


def find_product(product_id: int) -> Optional[Dict[str, Any]]:
    for item in get_state()["products"]:
        if int(item["id"]) == int(product_id):
            return item
    return None


def find_category(category_id: int) -> Optional[Dict[str, Any]]:
    for item in get_state()["categories"]:
        if int(item["id"]) == int(category_id):
            return item
    return None


def find_page(page_id: int) -> Optional[Dict[str, Any]]:
    for item in get_state()["pages"]:
        if int(item["id"]) == int(page_id):
            return item
    return None


def find_article(article_id: int) -> Optional[Dict[str, Any]]:
    for item in get_state()["articles"]:
        if int(item["id"]) == int(article_id):
            return item
    return None


def metafields_for(kind: str, item_id: int) -> list:
    key = f"{kind}:{int(item_id)}"
    return get_state()["metafields"].setdefault(key, [])


def upsert_metafield(kind: str, item_id: int, namespace: str, key: str, value: str, mf_type: str) -> Dict[str, Any]:
    existing = metafields_for(kind, item_id)
    for mf in existing:
        if mf.get("namespace") == namespace and mf.get("key") == key:
            mf["value"] = value
            persist()
            return mf
    state = get_state()
    mf_id = int(state.get("next_metafield_id") or 10000)
    state["next_metafield_id"] = mf_id + 1
    created = {
        "id": mf_id,
        "namespace": namespace,
        "key": key,
        "value": value,
        "type": mf_type,
    }
    existing.append(created)
    persist()
    return created


def get_seo(seo_id: int) -> Optional[Dict[str, Any]]:
    seos = get_state().get("seos") or {}
    return seos.get(str(int(seo_id)))


def upsert_seo(seo_id: Optional[int], payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    seos: Dict[str, Dict[str, Any]] = state.setdefault("seos", {})
    if seo_id is None:
        seo_id = int(state.get("next_seo_id") or 600)
        state["next_seo_id"] = seo_id + 1
        record = {"id": seo_id, "title": "", "description": "", "keyword": "", **payload}
        seos[str(seo_id)] = record
        persist()
        return record
    key = str(int(seo_id))
    record = seos.get(key) or {"id": int(seo_id)}
    record.update(payload)
    record["id"] = int(seo_id)
    seos[key] = record
    persist()
    return record
