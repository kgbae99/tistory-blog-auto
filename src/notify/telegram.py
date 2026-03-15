"""텔레그램 알림 모듈 - 포스트 생성/수익 알림 발송."""

from __future__ import annotations

import os

import requests

from src.core.logger import setup_logger

logger = setup_logger("telegram")


def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """텔레그램 메시지를 발송한다.

    환경변수:
        TELEGRAM_BOT_TOKEN: 봇 토큰 (BotFather에서 생성)
        TELEGRAM_CHAT_ID: 채팅 ID
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not bot_token or not chat_id:
        logger.debug("텔레그램 설정 없음 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        resp = requests.post(url, data=data, timeout=10)
        if resp.status_code == 200:
            logger.info("텔레그램 알림 발송 완료")
            return True
        logger.warning("텔레그램 발송 실패: %s", resp.text)
        return False
    except Exception as e:
        logger.warning("텔레그램 발송 오류: %s", e)
        return False


def notify_posts_generated(posts: list[dict]) -> None:
    """포스트 생성 완료 알림을 보낸다."""
    if not posts:
        return

    lines = ["<b>📝 블로그 포스트 생성 완료</b>\n"]
    for i, p in enumerate(posts, 1):
        lines.append(f"{i}. {p.get('title', p.get('keyword', ''))}")

    lines.append(f"\n총 {len(posts)}개 포스트가 생성되었습니다.")
    lines.append("GitHub에서 확인 후 티스토리에 발행해주세요.")

    send_message("\n".join(lines))


def notify_indexing_result(result: dict) -> None:
    """색인 요청 결과 알림을 보낸다."""
    text = (
        "<b>🔍 Google 색인 요청 결과</b>\n\n"
        f"검사: {result.get('checked', 0)}개\n"
        f"색인됨: {result.get('indexed', 0)}개\n"
        f"미색인: {result.get('not_indexed', 0)}개\n"
        f"요청 성공: {result.get('index_requested', 0)}개"
    )
    send_message(text)


def notify_daily_summary(posts_count: int, indexed: int, revenue: float = 0) -> None:
    """일일 요약 알림을 보낸다."""
    text = (
        "<b>📊 건강온도사 일일 리포트</b>\n\n"
        f"📝 생성 포스트: {posts_count}개\n"
        f"🔍 색인 요청: {indexed}개\n"
        f"💰 예상 수익: ₩{revenue:,.0f}"
    )
    send_message(text)
