from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from backend.config import (
    APP_META_PATH,
    DEFAULT_LOOP_STATE,
    DEFAULT_META,
    DEFAULT_SETTINGS,
    FRONTEND_DIR,
    HISTORY_DIR,
    LOOP_STATE_PATH,
    SETTINGS_PATH,
    SIL_LOG_PATH,
    STORAGE_DIR,
)
from backend.utils import parse_iso_timestamp, utc_now_iso


class Repository:
    def __init__(self) -> None:
        self.storage_dir = STORAGE_DIR
        self.history_dir = HISTORY_DIR
        self.frontend_dir = FRONTEND_DIR
        self.settings_path = SETTINGS_PATH
        self.loop_state_path = LOOP_STATE_PATH
        self.sil_log_path = SIL_LOG_PATH
        self.app_meta_path = APP_META_PATH

    def ensure_storage(self) -> None:
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_json_file(self.settings_path, DEFAULT_SETTINGS)
        self._ensure_json_file(self.loop_state_path, DEFAULT_LOOP_STATE)
        self._ensure_json_file(self.sil_log_path, [])
        self._ensure_json_file(self.app_meta_path, DEFAULT_META)

    def get_settings(self) -> dict[str, Any]:
        return self._read_json(self.settings_path, DEFAULT_SETTINGS)

    def save_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = {
            "base": payload.get("base", ""),
            "spoiler": payload.get("spoiler", ""),
            "style": payload.get("style", ""),
        }
        self._write_json(self.settings_path, data)
        return data

    def get_loop_state(self) -> dict[str, Any]:
        return self._read_json(self.loop_state_path, DEFAULT_LOOP_STATE)

    def save_loop_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["updated_at"] = utc_now_iso()
        self._write_json(self.loop_state_path, payload)
        return payload

    def get_sil_log(self) -> list[dict[str, Any]]:
        return self._read_json(self.sil_log_path, [])

    def append_sil_log(self, entry: dict[str, Any]) -> dict[str, Any]:
        data = self.get_sil_log()
        data.append(entry)
        self._write_json(self.sil_log_path, data[-300:])
        return entry

    def get_meta(self) -> dict[str, Any]:
        meta = self._read_json(self.app_meta_path, DEFAULT_META)
        meta.setdefault("affinity_stage", self._affinity_stage(meta))
        meta.setdefault("last_reentry_log_date", None)
        return meta

    def save_meta(self, payload: dict[str, Any]) -> dict[str, Any]:
        payload["affinity_stage"] = self._affinity_stage(payload)
        self._write_json(self.app_meta_path, payload)
        return payload

    def record_visit(self) -> tuple[dict[str, Any], str, int, bool]:
        meta = self.get_meta()
        now = datetime.now(timezone.utc)
        now_iso = utc_now_iso()

        days_away = 0
        previous_visit = parse_iso_timestamp(meta.get("last_visit_at"))
        if previous_visit:
            days_away = max(0, (now.date() - previous_visit.date()).days)

        meta["visit_count"] = int(meta.get("visit_count", 0)) + 1
        meta["last_visit_at"] = now_iso
        meta["last_return_days"] = days_away
        first_visit = not meta.get("first_visit_at")
        if first_visit:
            meta["first_visit_at"] = now_iso
            greeting = "저자님이 오셨군요. 서고가 다시 선명해지고 있어요."
        elif days_away > 0:
            meta["last_reentry_log_date"] = now.date().isoformat()
            greeting = f"{days_away}일만에 돌아오셨네요. 에코가 많이 기다렸어요."
        else:
            greeting = {
                "distant": "서고가 오늘도 저자님을 기다리고 있었습니다.",
                "warm": "루네가 조용히 원고를 붙들고 있었어요.",
                "close": "카논도, 에코도 이미 자리를 잡고 있었어요.",
            }.get(meta.get("affinity_stage"), "서고가 저자님을 맞이합니다.")

        greeting = self._build_visit_greeting(
            meta,
            days_away=days_away,
            first_visit=first_visit,
        )
        self.save_meta(meta)
        return meta, greeting, days_away, first_visit

    def _build_visit_greeting(
        self,
        meta: dict[str, Any],
        *,
        days_away: int,
        first_visit: bool,
    ) -> str:
        affinity = meta.get("affinity_stage", "distant")

        if first_visit:
            return "처음 오셨군요. 서고가 저자님의 호흡을 기준으로 조용히 정렬되고 있어요."

        if days_away >= 14:
            return {
                "distant": f"{days_away}일 만의 귀환입니다. 오래 비어 있던 책등부터 차례로 불을 켭니다.",
                "warm": f"{days_away}일 만에 돌아오셨어요. 룬이 묵혀 둔 장면부터 다시 펼치고 있어요.",
                "close": f"{days_away}일 만이네요. 카논과 에코가 오래 비어 있던 자리를 다시 맞추고 있어요.",
            }.get(affinity, f"{days_away}일 만의 귀환입니다. 서고가 다시 자리를 맞추고 있어요.")

        if days_away >= 1:
            return {
                "distant": f"{days_away}일 만에 돌아오셨네요. 지난 자리의 열기가 아직 남아 있어요.",
                "warm": f"{days_away}일 만에 돌아오셨어요. 룬이 바로 이어 쓸 수 있게 책갈피를 잡아 두었어요.",
                "close": f"{days_away}일 만이네요. 카논과 에코가 방금까지 기다리던 사람처럼 반응하고 있어요.",
            }.get(affinity, f"{days_away}일 만에 돌아오셨네요. 서고가 곧바로 응답할 준비를 마쳤어요.")

        return {
            "distant": "서고가 오늘의 자리로 다시 정렬됐어요. 바로 이어서 적어 내려가면 됩니다.",
            "warm": "룬이 방금 멈춘 문장 곁에서 다시 손을 들고 있어요.",
            "close": "카논과 에코가 이미 다음 반응을 준비해 둔 표정이네요.",
        }.get(affinity, "서고가 저자님을 다시 맞이합니다.")

    def increment_run_stats(self, completed_loops: int) -> dict[str, Any]:
        meta = self.get_meta()
        meta["total_runs"] = int(meta.get("total_runs", 0)) + 1
        meta["total_completed_loops"] = int(meta.get("total_completed_loops", 0)) + int(
            completed_loops
        )
        return self.save_meta(meta)

    def list_history(self, limit: int = 20) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(
            self.history_dir.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            payload = self._read_json(path, None)
            if payload is not None:
                payload["filename"] = path.name
                items.append(payload)
            if len(items) >= limit:
                break
        return items

    def save_history_entry(self, payload: dict[str, Any]) -> Path:
        run_id = payload["run_id"]
        loop_index = payload["loop_index"]
        safe_title = str(payload.get("title") or "untitled").strip() or "untitled"
        safe_title = re.sub(r'[<>:"/\\|?*]+', "_", safe_title)
        safe_title = re.sub(r"\s+", "_", safe_title[:24]).strip("_") or "untitled"
        filename = f"{run_id}_loop{loop_index:02d}_{safe_title}.json"
        path = self.history_dir / filename
        self._write_json(path, payload)
        return path

    def _ensure_json_file(self, path: Path, default_value: Any) -> None:
        if path.exists():
            return
        self._write_json(path, default_value)

    def _read_json(self, path: Path, default_value: Any) -> Any:
        if not path.exists():
            return json.loads(json.dumps(default_value, ensure_ascii=False))
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path.replace(path)

    def _affinity_stage(self, meta: dict[str, Any]) -> str:
        loops = int(meta.get("total_completed_loops", 0))
        if loops >= 8:
            return "close"
        if loops >= 3:
            return "warm"
        return "distant"
