import os
import sys
import json
import logging
import requests
from typing import Dict, List, Any
from dotenv import load_dotenv
from pathlib import Path

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트의 config.env 파일 로드 (config.local.env 우선)
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "config.env")
if (project_root / "config.local.env").exists():
    load_dotenv(project_root / "config.local.env", override=True)

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

    def send_channel_message(self, payload_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        슬랙 채널 메시지 전송

        Args:
            payload_items: 페이로드 아이템 리스트
                [
                    {
                        "channelType": "daily-stock-report",
                        "message": "..."
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

        url = f"{self.base_url}/api/slack/channel"

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

            logger.info(f"슬랙 채널 메시지 전송 완료: {response.text}")
            return {
                "onResult": 1,
                "ovErrDesc": f"Slack 채널 메시지 전송 완료: {response.text}"
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"슬랙 채널 API 호출 실패: {e}")
            return {
                "onResult": -1,
                "ovErrDesc": f"Slack 채널 API 호출 실패: {str(e)}"
            }


def send_stock_report_to_slack(
    md_report: str,
    notion_url: str = None
):
    """
    재고 일치율 변동 레포트를 슬랙 채널로 전송

    Args:
        md_report: 마크다운 레포트 전체 내용
        notion_url: Notion 페이지 URL (선택적)
    """
    slack = SlackNotificationService()

    channel_type = os.getenv("SLACK_CHANNEL_TYPE", "test")

    # 슬랙 메시지 포맷팅
    slack_contents = format_stock_report_for_slack(md_report)

    # Notion URL이 있으면 메시지 끝에 추가
    if notion_url:
        slack_contents += f"\n\n━━━━━━━━━━━━━━━━━━\n📄 *전체 리포트 보기*\n{notion_url}"

    # 페이로드 구성
    payload_items = [
        {
            "channelType": channel_type,
            "message": slack_contents
        }
    ]

    # 전송
    result = slack.send_channel_message(payload_items)

    if result["onResult"] == 1:
        logger.info(f"슬랙 메시지 전송 완료 (channelType={channel_type})")
    else:
        logger.error(f"슬랙 메시지 전송 실패: {result['ovErrDesc']}")

    return result


def format_stock_report_for_slack(md_report: str) -> str:
    """
    마크다운 리포트의 요약 부분만 슬랙 형식으로 변환 (개요까지만)
    """
    lines = md_report.splitlines()
    slack_lines = []

    # "변동 분석" 섹션의 "변동 방향"까지만 추출
    found_direction = False

    for line in lines:
        # "변동 분석" 이후 "변동 방향" 섹션이 끝나면 중단
        if found_direction and (line.startswith("##") or line.startswith("###")):
            break

        if "변동 방향" in line:
            found_direction = True

        # 제목 변환 (# -> *)
        if line.startswith("# "):
            slack_lines.append("*" + line[2:].strip() + "*\n")
        elif line.startswith("## "):
            slack_lines.append("\n*" + line[3:].strip() + "*")
        elif line.startswith("### "):
            slack_lines.append("\n*" + line[4:].strip() + "*")

        # 테이블 헤더 구분선 제거
        elif line.strip().startswith("|---") or line.strip().startswith("| ---"):
            continue

        # 테이블 행 변환
        elif line.strip().startswith("|"):
            cells = [cell.strip() for cell in line.split("|")[1:-1]]
            slack_lines.append("  " + " | ".join(cells))

        # 일반 리스트
        elif line.strip().startswith("- "):
            converted = line.strip()[2:].replace("**", "*")
            slack_lines.append("  • " + converted)

        # 굵은 글씨 변환 (** -> *)
        elif "**" in line:
            converted = line.replace("**", "*")
            slack_lines.append(converted)

        # 구분선
        elif line.strip() == "---":
            slack_lines.append("\n━━━━━━━━━━━━━━━━━━")

        # 빈 줄
        elif line.strip() == "":
            slack_lines.append("")

        # 일반 텍스트
        else:
            slack_lines.append(line)

    return "\n".join(slack_lines).strip()
