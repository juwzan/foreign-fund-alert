# 외인자금 알람 프로젝트 규칙

## 작업 범위
- 이 폴더(`모니터링 지표/외인자금 알람`)에서 다루는 대화/작업 내용과 그 산출물(문서, 데이터,
  스크립트 등)은 이 폴더 안에서만 저장하고 다룬다.
- 이 폴더가 git 저장소 루트다 (GitHub 연결 시에도 이 폴더 기준으로 init/커밋/푸시).
- 다른 하위 프로젝트(예: `조기경보`, `거시경제`)의 메모리(기억)나 맥락을 가져오지 않고, 이 폴더에서
  알게 된 내용도 다른 프로젝트로 내보내지 않는다.
- 상위 폴더(`모니터링 지표`)의 작업 범위·메모리 스코프 규칙도 함께 따른다.

## 프로젝트 내용

금융감독원 보도자료 게시판(B0000188)에서 "외국인 증권투자 동향"(제목검색) 글이 새로
올라오면 이메일로 알려주는 파이프라인. 평일 하루 2회(오전/오후) GitHub Actions가 목록을
확인해, 저장해둔 마지막 글번호(`report/state.json`)보다 큰 글이 있으면 그 글의 상세 페이지
본문을 그대로 가져와 메일로 보낸다. 게시판 자체가 월 1회만 갱신되므로 하루 2회 체크로
충분히 여유 있음.

**PDF/HWP 첨부파일을 다운로드하지 않는다**: 상세 페이지(`view.do`)의 `div.dbdata` 안에
보도자료 요약 본문이 이미 HTML 텍스트로 들어있어서, 그걸 그대로 메일 본문에 넣으면 됨
(첨부파일은 참고용 다운로드 링크만 메일에 포함).

### 구조
```
scripts/
  fss_client.py   # 목록(list.do) 파싱 + 상세(view.do, dbdata 본문/첨부링크) 파싱
  state.py         # report/state.json 읽기/쓰기 (last_seen_no)
  send_email.py     # Gmail SMTP 발송 (첨부 없이 HTML 본문만)
  main.py            # 진입점 (--dry-run은 state.json을 건드리지 않고 콘솔에만 출력)
report/state.json    # {"last_seen_no": N} 형태, git으로 추적 (신규 판정 기준)
.github/workflows/check_new_post.yml   # cron(평일 09:00·15:00 KST) + workflow_dispatch + state.json 커밋-백
```

### 필요한 시크릿 (.env 또는 GitHub Actions Secrets)
- `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD`: 발신 Gmail 계정 + 앱 비밀번호
- `RECIPIENT_EMAIL`: 수신 이메일 주소
- (금감원 게시판 자체는 API 키나 로그인이 필요 없음 — 서버가 완성된 HTML을 그대로 내려줌)

## 메일 발송 규칙
- 테스트 목적으로 메일을 보낼 때는 제목 맨 앞에 `(테스트)`를 붙인다.
  `send_email.build_subject(post_title, is_test=True)`로 처리.
- 실제 운영(정기 자동 발송, main.py 정상 실행)에는 이 접두어를 붙이지 않는다.
