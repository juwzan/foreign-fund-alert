"""신규 게시글 판정 기준(report/state.json)의 읽기/쓰기."""
import json
import os


def load_last_seen_no(state_path):
    """state 파일이 없으면 None(=최초 실행) 반환."""
    if not os.path.exists(state_path):
        return None
    with open(state_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("last_seen_no")


def save_last_seen_no(state_path, last_seen_no):
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump({"last_seen_no": last_seen_no}, f, ensure_ascii=False, indent=2)
