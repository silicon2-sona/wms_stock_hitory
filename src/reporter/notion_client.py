# -*- coding: utf-8 -*-
import os
import sys
import logging
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv
from pathlib import Path

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트의 config.env 파일 로드
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / "config.env")

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

    def create_page(
        self,
        parent_page_id: str,
        title: str,
        markdown_content: str
    ) -> Dict[str, Any]:
        """
        부모 페이지 하위에 새 페이지 생성

        Args:
            parent_page_id: 부모 페이지 ID
            title: 페이지 제목
            markdown_content: 마크다운 컨텐츠

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

        # 페이지 속성 구성 (일반 페이지는 'title' 속성 사용)
        properties = {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        }

        # 부모 페이지 설정
        payload = {
            "parent": {
                "page_id": parent_page_id
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

            # 테이블 (Notion 테이블로 변환)
            elif line.strip().startswith("|") and i + 1 < len(lines) and "|---" in lines[i + 1]:
                # 테이블 헤더와 데이터 파싱
                header_line = line.strip()
                i += 1  # 구분선 스킵
                i += 1  # 데이터 행으로 이동

                # 헤더 파싱
                headers = [h.strip() for h in header_line.split("|") if h.strip()]

                # 데이터 행 수집
                table_rows = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    row_data = [cell.strip() for cell in lines[i].strip().split("|") if cell.strip()]
                    if row_data:
                        table_rows.append(row_data)
                    i += 1
                i -= 1  # 마지막 라인 조정

                # Notion 테이블 생성 (table 블록)
                table_width = len(headers)
                table_block = {
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": table_width,
                        "has_column_header": True,
                        "has_row_header": False,
                        "children": []
                    }
                }

                # 헤더 행 추가
                header_cells = []
                for header in headers:
                    header_cells.append(self._parse_rich_text(header))
                table_block["table"]["children"].append({
                    "object": "block",
                    "type": "table_row",
                    "table_row": {
                        "cells": header_cells
                    }
                })

                # 데이터 행 추가
                for row_data in table_rows:
                    # 셀 수를 헤더 수에 맞춤
                    while len(row_data) < table_width:
                        row_data.append("")
                    row_data = row_data[:table_width]

                    row_cells = []
                    for cell in row_data:
                        row_cells.append(self._parse_rich_text(cell))
                    table_block["table"]["children"].append({
                        "object": "block",
                        "type": "table_row",
                        "table_row": {
                            "cells": row_cells
                        }
                    })

                blocks.append(table_block)

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
        텍스트를 Notion rich_text 형식으로 파싱 (볼드, 링크 처리)
        """
        import re

        rich_text = []

        # 1단계: 링크와 볼드를 함께 처리
        # 패턴: **[텍스트](URL)** 또는 [텍스트](URL) 또는 **텍스트**
        pattern = r'(\*\*\[([^\]]+)\]\(([^)]+)\)\*\*|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*)'

        last_end = 0
        for match in re.finditer(pattern, text):
            # 매칭 전 일반 텍스트
            if match.start() > last_end:
                plain_text = text[last_end:match.start()]
                if plain_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": plain_text}
                    })

            # **[텍스트](URL)** 형태 (볼드 + 링크)
            if match.group(2) and match.group(3):
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": match.group(2),
                        "link": {"url": match.group(3)}
                    },
                    "annotations": {"bold": True}
                })
            # [텍스트](URL) 형태 (링크만)
            elif match.group(4) and match.group(5):
                rich_text.append({
                    "type": "text",
                    "text": {
                        "content": match.group(4),
                        "link": {"url": match.group(5)}
                    }
                })
            # **텍스트** 형태 (볼드만)
            elif match.group(6):
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(6)},
                    "annotations": {"bold": True}
                })

            last_end = match.end()

        # 마지막 남은 텍스트
        if last_end < len(text):
            remaining_text = text[last_end:]
            if remaining_text:
                rich_text.append({
                    "type": "text",
                    "text": {"content": remaining_text}
                })

        # 빈 경우 기본 텍스트 추가
        if not rich_text:
            rich_text = [{"type": "text", "text": {"content": text}}]

        return rich_text


def send_report_to_notion(
    markdown_content: str,
    title: str,
    parent_page_id: str = None
) -> Dict[str, Any]:
    """
    재고 리포트를 Notion 페이지로 전송

    Args:
        markdown_content: 마크다운 리포트 전체 내용
        title: 페이지 제목
        parent_page_id: 부모 페이지 ID (None이면 환경변수에서 가져옴)

    Returns:
        생성 결과
    """
    client = NotionClient()

    if parent_page_id is None:
        parent_page_id = os.getenv("NOTION_PAGE_ID", "")

    if not parent_page_id:
        logger.warning("Notion 페이지 ID가 설정되지 않았습니다. (NOTION_PAGE_ID)")
        return {"success": False, "error": "부모 페이지 ID 없음"}

    result = client.create_page(
        parent_page_id=parent_page_id,
        title=title,
        markdown_content=markdown_content
    )

    if result.get("success"):
        logger.info(f"Notion 페이지 생성 완료: {result.get('url')}")
    else:
        logger.error(f"Notion 페이지 생성 실패: {result.get('error')}")

    return result
