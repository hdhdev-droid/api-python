"""DB 연결/디버그 로그 (메모리, 최대 100건)."""
from datetime import datetime
from typing import List, Dict, Any

MAX_LOGS = 100
_logs: List[Dict[str, Any]] = []


def add_log(msg: str, is_error: bool = False) -> None:
    entry = {
        "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "msg": str(msg),
        "isError": is_error,
    }
    _logs.append(entry)
    if len(_logs) > MAX_LOGS:
        del _logs[: len(_logs) - MAX_LOGS]
    if is_error:
        print("[DB]", msg)
    else:
        print("[DB]", msg)


def get_logs() -> List[Dict[str, Any]]:
    return _logs.copy()
