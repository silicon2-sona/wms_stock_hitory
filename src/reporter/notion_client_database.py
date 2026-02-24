# -*- coding: utf-8 -*-
import os
import sys
import logging
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# 로거 설정
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setStream(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class NotionClient:
    """
    Notion API 클라이언트
    """

    def __init__(self):
        self.api_token = os.getenv("NOTION_API_TOKEN", "")
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }

        if not self.api_token:
            logger.warning("NOTION_API_TOKEN 환경변수가 설정되지 않았습니다.")

    def create_page_in_database(
        self,
        database_id: str,
        title: str,
        markdown_content: str,
        date_str: str = None
    ) -> Dict[str, Any]:
        """
        데이터베이스에 새 페이지 생성

        Args:
            database_id: Notion 데이터베이스 ID
            title: 페이지 제목
            markdown_content: 마크다운 컨텐츠
            date_str: 날짜 문자열 (선택, YYYY-MM-DD 형식)

        Returns:
            생성된 페이지 정보
        """
        if not self.api_token:
            return {
                "success": False,
                "error": "NOTION_API_TOKEN이 설정되지 않았습니다."
            }

        url = f"{self.base_url}/pages"

        # 마크다운을 Notion 블록으로 변환
        all_blocks = self._markdown_to_notion_blocks(markdown_content)

        # Notion API는 한 번에 최대 100개 블록만 허용
        # 초기 생성 시 처음 100개만 포함하고, 나머지는 나중에 추가
        initial_blocks = all_blocks[:100] if len(all_blocks) > 100 else all_blocks

        # 데이터베이스 페이지 속성 구성
        properties = {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        }

        # 날짜 속성 추가 (데이터베이스에 Date 속성이 있는 경우)
        if date_str:
            properties["Date"] = {
                "date": {
                    "start": date_str
                }
            }

        # 데이터베이스 부모 설정
        payload = {
            "parent": {
                "database_id": database_id
            },
            "properties": properties,
            "children": initial_blocks
        }

        try:
            logger.info(f"Notion 페이지 생성 중: {title}")
            logger.info(f"전체 블록 수: {len(all_blocks)}, 초기 전송: {len(initial_blocks)}")

            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            # 상세 에러 정보 로깅
            if not response.ok:
                logger.error(f"Notion API 응답 상태: {response.status_code}")
                logger.error(f"응답 내용: {response.text}")

            response.raise_for_status()

            result = response.json()
            page_id = result.get("id")
            logger.info(f"Notion 페이지 생성 완료: {result.get('url', 'N/A')}")

            # 나머지 블록이 있으면 추가
            if len(all_blocks) > 100:
                logger.info(f"나머지 블록 추가 중: {len(all_blocks) - 100}개")
                remaining_blocks = all_blocks[100:]

                # 100개씩 나눠서 추가
                for i in range(0, len(remaining_blocks), 100):
                    chunk = remaining_blocks[i:i+100]
                    self._append_blocks_to_page(page_id, chunk)
                    logger.info(f"블록 추가 완료: {i+len(chunk)}/{len(remaining_blocks)}")

            return {
                "success": True,
                "page_id": page_id,
                "url": result.get("url"),
                "data": result
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Notion API 호출 실패: {e}")
            # 응답이 있는 경우 상세 정보 출력
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"상세 에러: {error_detail}")
                except:
                    logger.error(f"응답 본문: {e.response.text}")
            return {
                "success": False,
                "error": str(e)
            }

    def _append_blocks_to_page(self, page_id: str, blocks: List[Dict[str, Any]]) -> bool:
        """
        페이지에 블록 추가 (100개 제한)
        """
        url = f"{self.base_url}/blocks/{page_id}/children"

        try:
            response = requests.patch(
                url,
                headers=self.headers,
                json={"children": blocks},
                timeout=30
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"블록 추가 실패: {e}")
            return False

    def _markdown_to_notion_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        마크다운을 Notion 블록으로 변환
        """
        blocks = []
        lines = markdown.splitlines()

        i = 0
        while i < len(lines):
            line = lines[i]

            # 제목
            if line.startswith("# "):
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{"type": "text", "text": {"content": line[2:].strip()}}]
                    }
                })
            elif line.startswith("## "):
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{"type": "text", "text": {"content": line[3:].strip()}}]
                    }
                })
            elif line.startswith("### "):
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": line[4:].strip()}}]
                    }
                })

            # 구분선
            elif line.strip() == "---":
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })

            # 테이블 (간단 구현 - 테이블을 코드 블록으로 변환)
            elif line.strip().startswith("|") and i + 1 < len(lines) and "|---" in lines[i + 1]:
                # 테이블 전체를 코드 블록으로 변환
                table_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip().startswith("|"):
                    table_lines.append(lines[i])
                    i += 1
                i -= 1  # 마지막 라인 조정

                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": "\n".join(table_lines)}}],
                        "language": "plain text"
                    }
                })

            # 리스트
            elif line.strip().startswith("- "):
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": self._parse_rich_text(line.strip()[2:])
                    }
                })

            # 번호 리스트
            elif line.strip() and line.strip()[0].isdigit() and ". " in line:
                content = line.strip().split(". ", 1)[1] if ". " in line else line.strip()
                blocks.append({
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": self._parse_rich_text(content)
                    }
                })

            # 빈 줄
            elif line.strip() == "":
                pass  # Notion은 빈 블록을 자동으로 처리

            # 일반 텍스트
            else:
                if line.strip():
                    blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": self._parse_rich_text(line)
                        }
                    })

            i += 1

        return blocks

    def _parse_rich_text(self, text: str) -> List[Dict[str, Any]]:
        """
        텍스트를 Notion rich_text 형식으로 파싱 (볼드 처리)
        """
        rich_text = []
        parts = text.split("**")

        for idx, part in enumerate(parts):
            if part:
                is_bold = idx % 2 == 1  # 홀수 인덱스는 볼드
                rich_text.append({
                    "type": "text",
                    "text": {"content": part},
                    "annotations": {"bold": is_bold} if is_bold else {}
                })

        # 빈 경우 기본 텍스트 추가
        if not rich_text:
            rich_text = [{"type": "text", "text": {"content": text}}]

        return rich_text


def send_report_to_notion(
    markdown_content: str,
    title: str,
    database_id: str = None,
    date_str: str = None
) -> Dict[str, Any]:
    """
    재고 리포트를 Notion 데이터베이스에 페이지로 추가

    Args:
        markdown_content: 마크다운 리포트 전체 내용
        title: 페이지 제목
        database_id: Notion 데이터베이스 ID (None이면 환경변수에서 가져옴)
        date_str: 날짜 문자열 (YYYY-MM-DD 형식)

    Returns:
        생성 결과
    """
    client = NotionClient()

    if database_id is None:
        database_id = os.getenv("NOTION_DATABASE_ID", "")

    if not database_id:
        logger.warning("Notion 데이터베이스 ID가 설정되지 않았습니다. (NOTION_DATABASE_ID)")
        return {"success": False, "error": "데이터베이스 ID 없음"}

    result = client.create_page_in_database(
        database_id=database_id,
        title=title,
        markdown_content=markdown_content,
        date_str=date_str
    )

    if result.get("success"):
        logger.info(f"Notion 페이지 생성 완료: {result.get('url')}")
    else:
        logger.error(f"Notion 페이지 생성 실패: {result.get('error')}")

    return result
