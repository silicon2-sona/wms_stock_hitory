import os
import sys
import json
import re
import logging
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setStream(sys.stdout)  # UTF-8로 재설정된 stdout 사용
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class SlackNotificationService:
    """
    슬랙 DM 메시지 전송 서비스
    공통 API를 통한 슬랙 알림
    """

    def __init__(self):
        self.base_url = os.getenv("COMMON_API_PATH", "")
        if not self.base_url:
            logger.warning("COMMON_API_PATH 환경변수가 설정되지 않았습니다.")

    def send_dm_message(self, payload_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        슬랙 DM 메시지 전송

        Args:
            payload_items: 페이로드 아이템 리스트
                [
                    {
                        "msgType": "daily-stock-report",
                        "additionalData": {
                            "targets": [...]
                        }
                    }
                ]

        Returns:
            전송 결과
        """
        if not self.base_url:
            return {
                "onResult": -1,
                "ovErrDesc": "COMMON_API_PATH가 설정되지 않았습니다."
            }

        url = f"{self.base_url}/api/slack/dm"

        try:
            logger.info(f"슬랙 메시지 전송: {url}")

            # SSL 검증 비활성화 (개발 환경 self-signed certificate 대응)
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            response = requests.post(
                url,
                json=payload_items,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=30,
                verify=False  # SSL 인증서 검증 비활성화
            )

            response.raise_for_status()

            logger.info(f"슬랙 DM 전송 완료: {response.text}")
            return {
                "onResult": 1,
                "ovErrDesc": f"Slack DM 전송 완료: {response.text}"
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"슬랙 DM API 호출 실패: {e}")
            return {
                "onResult": -1,
                "ovErrDesc": f"Slack DM API 호출 실패: {str(e)}"
            }


def convert_markdown_to_slack_blocks(md_report: str) -> List[Dict[str, Any]]:
    """
    마크다운 레포트를 슬랙 Block Kit 형식으로 변환

    Args:
        md_report: 마크다운 레포트 내용

    Returns:
        슬랙 블록 리스트
    """
    blocks = []
    lines = md_report.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # 빈 줄 스킵
        if not line:
            i += 1
            continue

        # 헤더 (# 제목)
        if line.startswith('# '):
            blocks.append({
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": line[2:].strip()[:150],  # 슬랙 헤더 최대 150자
                    "emoji": True
                }
            })
            blocks.append({"type": "divider"})

        # 서브헤더 (## 제목)
        elif line.startswith('## '):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{line[3:].strip()}*"
                }
            })

        # 서브서브헤더 (### 제목)
        elif line.startswith('### '):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{line[4:].strip()}*"
                }
            })

        # 구분선 (---)
        elif line.startswith('---'):
            blocks.append({"type": "divider"})

        # 리스트 항목 (-, *, 숫자.)
        elif line.startswith(('-', '*', '1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
            # 연속된 리스트 항목 수집
            list_items = []
            while i < len(lines) and lines[i].strip():
                item_line = lines[i].strip()
                if item_line.startswith(('-', '*')) or re.match(r'^\d+\.', item_line):
                    # 마크다운 **굵게** 처리 유지
                    list_items.append(item_line)
                    i += 1
                else:
                    break
            i -= 1  # 다음 루프를 위해 조정

            if list_items:
                # 최대 3000자 제한 (슬랙 블록 제한)
                text = '\n'.join(list_items)[:3000]
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text
                    }
                })

        # 일반 텍스트
        else:
            if line:
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": line[:3000]
                    }
                })

        i += 1

    # 슬랙 블록 최대 50개 제한
    return blocks[:50]


def send_stock_report_to_slack(
    md_report: str,
    today_str: str,
    yesterday_str: str,
    dm_receiver: str = None
):
    """
    재고 일치율 변동 레포트를 슬랙으로 전송 (현재 테스트 모드)

    Args:
        md_report: 마크다운 레포트 전체 내용
        today_str: 오늘 날짜 문자열
        yesterday_str: 어제 날짜 문자열
        dm_receiver: DM 수신자 이메일 (None이면 환경변수에서 가져옴)
    """
    slack = SlackNotificationService()

    if dm_receiver is None:
        dm_receiver = os.getenv("SLACK_DM_RECEIVER", "sona@siliconii.net")

    if not dm_receiver:
        logger.warning("슬랙 수신자가 설정되지 않았습니다. (SLACK_DM_RECEIVER)")
        return

    # TODO: 테스트 완료 후 실제 블록 변환 활성화
    # slack_blocks = convert_markdown_to_slack_blocks(md_report)

    # 테스트용 간단한 메시지
    test_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "TEST"
            }
        }
    ]


    title = f"📈 Stock Report ({today_str} vs {yesterday_str})"
    contents = f"*{title}*\n\n" + _truncate_for_slack(md_report)

    # 페이로드 구성
    payload_items = [
        {
            "msgType": "daily-stock-report",
            "additionalData": {
                "dmReceiver": dm_receiver,
                "date_from": yesterday_str,
                "date_to": today_str,
                "contents": contents
            }
        }
    ]

    # 전송
    result = slack.send_dm_message(payload_items)

    if result["onResult"] == 0:
        logger.info(f"슬랙 테스트 메시지 전송 완료: {dm_receiver}")
    else:
        logger.error(f"슬랙 테스트 메시지 전송 실패: {result['ovErrDesc']}")

    return result



def _truncate_for_slack(text: str, limit: int = 35000) -> str:
    # Slack/중간 게이트웨이에서 길이 제한에 걸릴 수 있어서 안전하게 컷
    if text is None:
        return ""
    return text if len(text) <= limit else text[:limit] + "\n\n…(내용이 길어 일부만 전송됨)"