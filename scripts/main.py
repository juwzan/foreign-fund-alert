"""
외인자금 알람 파이프라인 진입점.

금융감독원 보도자료 게시판(B0000188)에서 "외국인 증권투자 동향" 제목검색 결과를 조회해
report/state.json에 저장된 마지막 확인 글번호(last_seen_no)보다 큰 글이 있으면 신규로
판단하고 각각 이메일로 알린다.

사용법:
    python scripts/main.py             # 실제 조회 + (신규 시) 메일 발송 + state.json 갱신
    python scripts/main.py --dry-run   # 메일 발송/state.json 갱신 없이 콘솔에 결과만 출력
"""
import argparse
import os
import sys

from dotenv import load_dotenv

import fss_client
import send_email
import state

SCRIPT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
STATE_PATH = os.path.join(PROJECT_ROOT, "report", "state.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="메일 발송/state.json 갱신 없이 결과만 출력")
    parser.add_argument("--test", action="store_true", help="제목에 (테스트) 접두어를 붙여 발송")
    args = parser.parse_args()

    load_dotenv()
    gmail_address = os.environ.get("GMAIL_ADDRESS")
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD")
    recipient_email = os.environ.get("RECIPIENT_EMAIL")

    posts = fss_client.fetch_list(page_index=1)
    if not posts:
        print("목록 조회 결과가 없습니다.")
        return

    latest_no = posts[0]["no"]
    last_seen_no = state.load_last_seen_no(STATE_PATH)

    if last_seen_no is None:
        print(f"최초 실행: {latest_no}번을 baseline으로 저장하고 메일은 보내지 않습니다.")
        if not args.dry_run:
            state.save_last_seen_no(STATE_PATH, latest_no)
        return

    new_posts = sorted((p for p in posts if p["no"] > last_seen_no), key=lambda p: p["no"])
    if not new_posts:
        print(f"신규 게시글 없음 (최신={latest_no}번, 마지막 확인={last_seen_no}번).")
        return

    if not args.dry_run and not (gmail_address and gmail_app_password and recipient_email):
        print("메일 발송에 필요한 환경변수(GMAIL_ADDRESS/GMAIL_APP_PASSWORD/RECIPIENT_EMAIL)가 없습니다.")
        sys.exit(1)

    for row in new_posts:
        detail = fss_client.fetch_detail(row["ntt_id"])
        post = {**row, **detail}
        print(f"[신규 {post['no']}번] {post['title']} ({post['date']})")
        print(post["body_text"])

        if args.dry_run:
            print("  [dry-run] 메일 발송 생략")
            continue

        send_email.send_alert_email(gmail_address, gmail_app_password, recipient_email, post, is_test=args.test)
        print("  -> 메일 발송 완료")

    if args.dry_run:
        print(f"[dry-run] state.json은 건드리지 않음 (현재 {last_seen_no}번 -> 최신 {latest_no}번 감지됨)")
        return

    state.save_last_seen_no(STATE_PATH, latest_no)
    print(f"state.json 갱신 완료 (last_seen_no={latest_no})")


if __name__ == "__main__":
    main()
