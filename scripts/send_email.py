"""Gmail SMTP로 신규 게시글 알림 메일(HTML 본문, 첨부 없음) 발송."""
import re
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_TIMEOUT_SEC = 30
MAX_SEND_RETRIES = 3
RETRY_DELAY_SEC = 10

# 미리보기(목업)에서 상단 요약 칩으로 보여준 순매도/순투자 문구를 본문에서 뽑아내는 패턴.
# 원문 문구("상장주식 {금액}을 {순매도|순투자}하고, 상장채권 {금액}을 {순매도|순투자}하여")가
# 바뀌면 매치가 안 될 수 있는데, 그 경우 칩 없이 본문 텍스트만 보내도록 조용히 넘어간다.
_FLOW_PATTERN = re.compile(r"(상장주식|상장채권)\s+(.+?)(?:을|를)\s*(순매도|순투자)")

_OUTFLOW_STYLE = "background:#f3e4dd;color:#9c4a34;"
_INFLOW_STYLE = "background:#dfe9e6;color:#1f4e4a;"


def build_subject(post_title, is_test=False):
    subject = f"(공유) 외국인 증권투자 동향 새 글 알림 - {post_title}"
    return f"(테스트) {subject}" if is_test else subject


def _extract_flow_chips(body_text):
    first_line = body_text.splitlines()[0] if body_text else ""
    matches = _FLOW_PATTERN.findall(first_line)
    if len(matches) < 2:
        return []
    return [{"label": label, "amount": amount.strip(), "direction": direction} for label, amount, direction in matches]


def _render_flow_strip(chips):
    if not chips:
        return ""
    cells = []
    for chip in chips:
        style = _OUTFLOW_STYLE if chip["direction"] == "순매도" else _INFLOW_STYLE
        cells.append(
            f'<td style="{style}border-radius:10px;padding:12px 14px;">'
            f'<div style="font-size:11.5px;opacity:.75;">{chip["label"]} {chip["direction"]}</div>'
            f'<div style="font-size:16px;font-weight:700;">{chip["amount"]}</div>'
            f"</td>"
        )
    spacer = '<td style="width:10px;"></td>'
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        'style="margin-bottom:20px;"><tr>' + spacer.join(cells) + "</tr></table>"
    )


def render_html(post):
    """post: {title, date, view_url, body_text, attachments:[{name, url}]}"""
    flow_strip = _render_flow_strip(_extract_flow_chips(post["body_text"]))
    body_html = post["body_text"].replace("\n", "<br>")
    attachment_links = "".join(
        f'<a href="{a["url"]}" style="margin-right:10px;color:#6b7674;">{a["name"]} ↓</a>'
        for a in post["attachments"]
    )

    return f"""
    <div style="font-family:'Malgun Gothic',맑은고딕,AppleGothic,돋움,Dotum,Helvetica,Arial,sans-serif;
                color:#33403d;max-width:600px;">
      <h2 style="font-size:17px;color:#16211f;margin:0 0 4px;">{post['title']}</h2>
      <p style="font-size:12.5px;color:#8b9694;margin:0 0 18px;">등록일 {post['date']}</p>
      {flow_strip}
      <p style="font-size:13.5px;line-height:1.9;">{body_html}</p>
      <p style="margin-top:20px;">
        <a href="{post['view_url']}" style="color:#1f4e4a;font-weight:600;">게시글 바로가기 ↗</a>
      </p>
      <p style="font-size:12.5px;">{attachment_links}</p>
      <p style="font-size:11.5px;color:#9aa6a4;border-top:1px solid #efece2;padding-top:12px;margin-top:20px;">
        금융감독원 보도자료 게시판(외국인 증권투자 동향)에 새 글이 올라와 자동으로 발송된 메일입니다
        · 외인자금 알람 파이프라인
      </p>
    </div>
    """


def send_alert_email(gmail_address, gmail_app_password, recipient_email, post, is_test=False):
    msg = MIMEMultipart()
    msg["From"] = gmail_address
    msg["To"] = recipient_email
    msg["Subject"] = build_subject(post["title"], is_test=is_test)
    msg.attach(MIMEText(render_html(post), "html", "utf-8"))

    last_error = None
    for attempt in range(1, MAX_SEND_RETRIES + 1):
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=SMTP_TIMEOUT_SEC) as server:
                server.starttls()
                server.login(gmail_address, gmail_app_password)
                server.send_message(msg)
            return
        except (smtplib.SMTPException, OSError) as e:
            last_error = e
            if attempt < MAX_SEND_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
    raise last_error
