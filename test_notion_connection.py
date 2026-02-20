# -*- coding: utf-8 -*-
"""
Notion API 연결 테스트 스크립트
- API 토큰 유효성 확인
- 데이터베이스 접근 권한 확인
- 데이터베이스 구조 확인
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Windows 터미널 cp949 환경에서 UTF-8 출력 가능하도록 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# .env 파일 로드
load_dotenv()

NOTION_API_TOKEN = os.getenv("NOTION_API_TOKEN", "")
NOTION_PAGE_ID = os.getenv("NOTION_PAGE_ID", "")  # 부모 페이지 ID

print("=" * 60)
print("🧪 Notion API 연결 테스트 (페이지 생성)")
print("=" * 60)

# 1. 환경 변수 확인
print("\n📋 1. 환경 변수 확인")
print(f"  NOTION_API_TOKEN: {'✅ 설정됨' if NOTION_API_TOKEN else '❌ 없음'}")
print(f"  NOTION_PAGE_ID: {NOTION_PAGE_ID if NOTION_PAGE_ID else '⚠️  없음 (생략 가능)'}")

if not NOTION_API_TOKEN:
    print("\n❌ NOTION_API_TOKEN이 설정되지 않았습니다.")
    print("   .env 파일에 NOTION_API_TOKEN을 설정해주세요.")
    sys.exit(1)

# 2. API 토큰 유효성 확인
print("\n🔑 2. API 토큰 유효성 확인")
headers = {
    "Authorization": f"Bearer {NOTION_API_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

try:
    response = requests.get(
        "https://api.notion.com/v1/users/me",
        headers=headers,
        timeout=10
    )

    if response.status_code == 200:
        user_info = response.json()
        print(f"  ✅ API 토큰 유효")
        print(f"  Bot ID: {user_info.get('id')}")
        print(f"  Bot Name: {user_info.get('name', 'N/A')}")
    else:
        print(f"  ❌ API 토큰 무효")
        print(f"  상태 코드: {response.status_code}")
        print(f"  응답: {response.text}")
        sys.exit(1)

except Exception as e:
    print(f"  ❌ API 요청 실패: {e}")
    sys.exit(1)

# 3. 부모 페이지 확인 (선택적)
if NOTION_PAGE_ID:
    print(f"\n📄 3. 부모 페이지 접근 확인")
    print(f"  Page ID: {NOTION_PAGE_ID}")

    try:
        response = requests.get(
            f"https://api.notion.com/v1/pages/{NOTION_PAGE_ID}",
            headers=headers,
            timeout=10
        )

        if response.status_code == 200:
            page_info = response.json()
            print(f"  ✅ 페이지 접근 성공")

            # 제목 추출
            title_prop = page_info.get('properties', {})
            for prop_name, prop_value in title_prop.items():
                if prop_value.get('type') == 'title':
                    title_array = prop_value.get('title', [])
                    if title_array:
                        title = title_array[0].get('text', {}).get('content', 'N/A')
                        print(f"  제목: {title}")
                        break

        elif response.status_code == 404:
            print(f"  ❌ 페이지를 찾을 수 없습니다")
            print(f"\n  원인:")
            print(f"    1. Page ID가 잘못되었거나")
            print(f"    2. Integration이 페이지에 연결되지 않았습니다")
            print(f"\n  해결 방법:")
            print(f"    1. Notion에서 해당 페이지를 엽니다")
            print(f"    2. 우측 상단 '⋯' 클릭 → 'Connections' → 'Add connections'")
            print(f"    3. 'CA개발팀' Integration 선택")
            print(f"\n  ⚠️  부모 페이지 없이도 테스트를 계속 진행합니다.")
            NOTION_PAGE_ID = ""  # 부모 없이 진행

        else:
            print(f"  ❌ 접근 실패 (상태: {response.status_code})")
            print(f"  ⚠️  부모 페이지 없이도 테스트를 계속 진행합니다.")
            NOTION_PAGE_ID = ""

    except Exception as e:
        print(f"  ❌ 요청 실패: {e}")
        print(f"  ⚠️  부모 페이지 없이도 테스트를 계속 진행합니다.")
        NOTION_PAGE_ID = ""
else:
    print(f"\n📄 3. 부모 페이지 ID 없음")
    print(f"  ⚠️  워크스페이스 최상위에 페이지를 생성합니다.")

# 4. 테스트 페이지 생성 시도
print("\n📝 4. 테스트 페이지 생성")

# 부모 설정
if not NOTION_PAGE_ID:
    print(f"\n  ⚠️  NOTION_PAGE_ID가 설정되지 않았습니다.")
    print(f"\n  Notion API는 부모 페이지 없이 최상위에 페이지를 생성할 수 없습니다.")
    print(f"\n  해결 방법:")
    print(f"    1. Notion에서 테스트용 페이지를 하나 만듭니다")
    print(f"    2. 페이지 URL에서 ID를 복사합니다")
    print(f"       예: https://notion.so/My-Page-123abc456def...")
    print(f"       ID는: 123abc456def... (하이픈 제거)")
    print(f"    3. .env 파일에 추가:")
    print(f"       NOTION_PAGE_ID=복사한ID")
    print(f"    4. 해당 페이지에서 '⋯' → 'Connections' → 'song_noti' Integration 연결")
    print(f"\n  또는 데이터베이스를 사용하려면:")
    print(f"    - NOTION_DATABASE_ID를 설정하고")
    print(f"    - notion_client.py를 사용하세요")
    sys.exit(1)

parent = {"page_id": NOTION_PAGE_ID}
print(f"  부모 페이지 하위에 생성합니다")

test_payload = {
    "parent": parent,
    "properties": {
        "title": {
            "title": [
                {
                    "text": {
                        "content": "🧪 재고 일치율 테스트 (삭제 가능)"
                    }
                }
            ]
        }
    },
    "children": [
        {
            "object": "block",
            "type": "heading_1",
            "heading_1": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "재고 일치율 변동 분석 테스트"
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "이 페이지는 Notion API 연결 테스트용입니다."
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "API 토큰 정상 작동 ✅"
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "페이지 생성 성공 ✅"
                        }
                    }
                ]
            }
        },
        {
            "object": "block",
            "type": "divider",
            "divider": {}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "💡 이 페이지는 삭제해도 됩니다."
                        },
                        "annotations": {
                            "italic": True
                        }
                    }
                ]
            }
        }
    ]
}

try:
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers,
        json=test_payload,
        timeout=10
    )

    if response.status_code == 200:
        page_info = response.json()
        print(f"  ✅ 테스트 페이지 생성 성공!")
        print(f"  페이지 URL: {page_info.get('url')}")
        print(f"\n  💡 테스트 페이지는 삭제해도 됩니다.")

    else:
        print(f"  ❌ 페이지 생성 실패")
        print(f"  상태 코드: {response.status_code}")

        try:
            error_detail = response.json()
            print(f"  에러 코드: {error_detail.get('code', 'N/A')}")
            print(f"  에러 메시지: {error_detail.get('message', 'N/A')}")

            # 권한 에러인 경우
            if response.status_code == 403:
                print(f"\n  ⚠️  권한이 부족합니다.")
                print(f"  Integration이 페이지를 생성할 권한이 있는지 확인하세요.")

        except:
            print(f"  응답: {response.text}")

        print(f"\n  💡 해결 방법:")
        print(f"    - Integration 설정에서 'Content Capabilities' 확인")
        print(f"    - 'Insert content' 권한이 활성화되어 있는지 확인")
        sys.exit(1)

except Exception as e:
    print(f"  ❌ 요청 실패: {e}")
    sys.exit(1)

# 5. 완료
print("\n" + "=" * 60)
print("✅ 모든 테스트 통과!")
print("=" * 60)
print("\n💡 Notion 연결이 정상적으로 작동합니다.")
print("   이제 analyzer를 실행하면 Notion에 리포트가 자동으로 생성됩니다.\n")
