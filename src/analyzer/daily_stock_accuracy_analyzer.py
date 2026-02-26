#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
📊 재고 일치율 변동 분석 도구
- CSV 파일 비교
- 마크다운 리포트 자동 생성
- Claude AI와 호환되는 형식
"""

import sys
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
import requests

# 프로젝트 루트를 sys.path에 추가 (config 모듈 import를 위해)
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 프로젝트 루트의 config.env 파일 로드 (config.local.env 우선)
load_dotenv(project_root / "config.env")
if (project_root / "config.local.env").exists():
    load_dotenv(project_root / "config.local.env", override=True)

# Windows 터미널 cp949 환경에서 이모지 출력 가능하도록 utf-8 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# SSL 인증서 검증 비활성화 (self-signed certificate 대응)
import urllib3
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========================================
# ⚙️ 설정 (여기만 수정하면 됨!)
# ========================================

# CSV 파일이 있는 폴더 - config.settings에서 가져오기
# 환경변수 DB_EXPORT_OUTPUT_DIR을 사용하거나 기본값 사용
try:
    from config.settings import DB_EXPORT_OUTPUT_DIR
    INPUT_DIR = str(DB_EXPORT_OUTPUT_DIR)
except ImportError as e:
    # config 모듈 로드 실패 시 환경변수에서 직접 읽기
    print(f"⚠️ config.settings 로드 실패: {e}")
    print(f"   환경변수에서 직접 읽습니다.")
    from config.path_helper import resolve_data_path
    INPUT_DIR = str(resolve_data_path(os.getenv("DB_EXPORT_OUTPUT_DIR", "output/daily-stock")))

# 리포트 저장 폴더
OUTPUT_DIR = "./output"

# 파일명 형식 (당신의 파일명에 맞게)
# 예: Stock2026-02-11.csv
FILE_FORMAT = "Stock_{date}.csv"

# ========================================
# 📋 CSV 컬럼명 매핑 (파일 컬럼명에 맞게 수정)
# ========================================
COL_PROD_CD   = "상품코드"
COL_PRODUCT_NAME = "상품명"
COL_BRAND        = "브랜드"
COL_CMS_QTY      = "CMS 재고"
COL_WMS_QTY      = "WMS 재고"
COL_WAITING_QTY  = "대기 수량"
COL_ACCURACY     = "일치율"    # CSV에 이미 존재하는 일치율 컬럼

print(f"🔧 설정")
print(f"  입력: {INPUT_DIR}")
print(f"  출력: {OUTPUT_DIR}")

# ========================================
# 📐 함수들
# ========================================

def calculate_accuracy(cms_qty, wms_qty, waiting_qty):
    """
    일치율 계산 정책 (JS 로직 동일 적용)

    규칙:
    - cms == 0 AND physical == 0 → 100.0
    - cms == 0 OR  physical == 0 → 0.0
    - cms <  0 OR  physical <  0 → 0.0
    - 그 외 → round(min/max * 100, 1)
      - 반올림으로 100이 됐지만 실제로 같지 않으면 → 99.9
      - 진짜 cms == physical 이면 → 100.0
    """
    try:
        cms = float(cms_qty) if pd.notna(cms_qty) else 0
        physical = float(wms_qty or 0) + float(waiting_qty or 0)

        if cms == 0 and physical == 0:
            return 100.0
        elif cms == 0 or physical == 0:
            return 0.0
        elif cms < 0 or physical < 0:
            return 0.0
        else:
            least = min(cms, physical)
            greatest = max(cms, physical)
            valid = round(least / greatest * 100, 1)
            if valid >= 100 and least != greatest:
                valid = 99.9
            return valid
    except:
        return 0.0


def load_and_prepare_data(input_dir, file_format, target_date):
    """
    CSV 파일 로드 및 컬럼 정규화

    Args:
        input_dir: CSV 파일이 있는 폴더
        file_format: 파일명 형식 (예: "Stock{date}.csv")
        target_date: 대상 날짜 (datetime)

    Returns:
        정규화된 DataFrame (컬럼: prod_cd, prod_nm, cms_qty, wms_qty, waiting_qty, accuracy)
    """
    date_str = target_date.strftime("%Y-%m-%d")

    # 파일명 생성
    filename = file_format.replace("{date}", date_str)
    filepath = os.path.join(input_dir, filename)

    print(f"\n📂 파일 로드: {filename}")

    try:
        # CSV 읽기 (한글 인코딩 - utf-8-sig는 BOM 포함 파일도 처리)
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='cp949')

        # 마지막 행 제거 (합계/요약 행)
        df = df.iloc[:-1]

        # 컬럼 정규화 (내부 처리용 이름으로 통일)
        df = df.rename(columns={
            COL_PROD_CD:     'prod_cd',
            COL_PRODUCT_NAME: 'prod_nm',
            COL_CMS_QTY:     'cms_qty',
            COL_WMS_QTY:     'wms_qty',
            COL_WAITING_QTY: 'waiting_qty',
        })

        # 수치 컬럼 강제 변환 (문자열/NaN → 숫자, 변환 불가 값은 0)
        for col in ('cms_qty', 'wms_qty', 'waiting_qty'):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 일치율: CSV에 이미 존재하면 그대로 사용, 없으면 계산
        if COL_ACCURACY in df.columns:
            # "0%" 같은 문자열이면 숫자로 변환
            df['accuracy'] = (
                df[COL_ACCURACY]
                .astype(str)
                .str.replace('%', '', regex=False)
                .str.strip()
                .apply(lambda x: float(x) if x not in ('', 'nan') else 0.0)
            )
        else:
            df['accuracy'] = df.apply(
                lambda row: calculate_accuracy(
                    row.get('cms_qty'),
                    row.get('wms_qty'),
                    row.get('waiting_qty')
                ), axis=1
            )

        print(f"  ✅ 로드 완료: {len(df)}개 상품")
        return df

    except FileNotFoundError:
        print(f"  ❌ 파일 없음: {filepath}")
        return None
    except Exception as e:
        print(f"  ❌ 오류: {str(e)}")
        return None


def compare_inventory(yesterday_df, today_df):
    """
    어제와 오늘 데이터 비교
    
    Returns:
        변동이 있는 상품들의 DataFrame
    """
    if yesterday_df is None or today_df is None:
        print("❌ 데이터 로드 실패")
        return None
    
    print("\n📊 데이터 비교 중...")
    
    # 병합 (상품코드 기준)
    comparison = today_df.merge(
        yesterday_df,
        on='prod_cd',
        suffixes=('_today', '_yesterday'),
        how='outer'
    )

    # 상품명은 오늘 데이터 우선
    if 'prod_nm_today' in comparison.columns:
        comparison['prod_nm'] = comparison['prod_nm_today']
    elif 'prod_nm_yesterday' in comparison.columns:
        comparison['prod_nm'] = comparison['prod_nm_yesterday']

    # 한쪽 날짜에 상품이 없는 경우: 재고 0, 일치율 100으로 처리
    qty_today_cols = [c for c in ['cms_qty_today', 'wms_qty_today', 'waiting_qty_today'] if c in comparison.columns]
    qty_yesterday_cols = [c for c in ['cms_qty_yesterday', 'wms_qty_yesterday', 'waiting_qty_yesterday'] if c in comparison.columns]

    for col in qty_today_cols:
        comparison[col] = pd.to_numeric(comparison[col], errors='coerce').fillna(0)
    for col in qty_yesterday_cols:
        comparison[col] = pd.to_numeric(comparison[col], errors='coerce').fillna(0)

    # 일치율: 데이터가 없는 쪽(NaN)은 100으로 채우기
    if 'accuracy_today' in comparison.columns:
        comparison['accuracy_today'] = pd.to_numeric(comparison['accuracy_today'], errors='coerce').fillna(100)
    if 'accuracy_yesterday' in comparison.columns:
        comparison['accuracy_yesterday'] = pd.to_numeric(comparison['accuracy_yesterday'], errors='coerce').fillna(100)    
    # 일치율 변동 계산
    comparison['change'] = comparison['accuracy_today'] - comparison['accuracy_yesterday']
    comparison['change_abs'] = abs(comparison['change'])

    # CMS 변화량 및 WMS수량(wms+waiting) 변화량 계산
    comparison['cms_diff'] = comparison['cms_qty_today'] - comparison['cms_qty_yesterday']
    waiting_today = comparison.get('waiting_qty_today', 0).fillna(0)
    waiting_yesterday = comparison.get('waiting_qty_yesterday', 0).fillna(0)
    comparison['physical_today'] = comparison['wms_qty_today'] + waiting_today
    comparison['physical_yesterday'] = comparison['wms_qty_yesterday'] + waiting_yesterday
    comparison['physical_diff'] = comparison['physical_today'] - comparison['physical_yesterday']

    # 변동 있는 상품만 필터 (일치율 변화 & CMS/WMS수량 변화량이 다른 것만)
    changed = comparison[
        (comparison['change_abs'] > 0.0) &
        (comparison['cms_diff'] != comparison['physical_diff'])
    ].copy()
    changed = changed.sort_values('change_abs', ascending=False)
    
    print(f"  📈 총 상품: {len(comparison)}")
    print(f"  🔄 변동 상품: {len(changed)}")
    print(f"  📊 변동 비율: {len(changed)/len(comparison)*100:.1f}%")
    
    return comparison, changed


def generate_markdown_report(comparison, changed, date_str):
    """
    마크다운 형식의 리포트 생성

    Claude AI가 읽기 쉽도록 최적화
    """

    total = len(comparison)
    change_count = len(changed)

    # 통계
    if change_count > 0:
        avg_change = changed['change_abs'].mean()
        max_change = changed['change_abs'].max()
        min_change = changed['change_abs'].min()
        increase_count = len(changed[changed['change'] > 0])
        decrease_count = len(changed[changed['change'] < 0])
    else:
        avg_change = max_change = min_change = 0
        increase_count = decrease_count = 0

    # 테스트 모드 체크
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    test_prefix = "[TEST] " if test_mode else ""

    # 마크다운 작성
    md = f"""# {test_prefix}📊 재고 일치율 변동 분석 리포트

**기준일:** {date_str}  
**생성일시:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📈 개요

| 지표 | 값 |
|------|-----|
| 총 상품 수 | {total}개 |
| 변동 상품 | {change_count}개 |
| 변동 비율 | {change_count/total*100:.1f}% |
| 평균 변동폭 | {avg_change:.2f}% |
| 최대 변동 | {max_change:.2f}% |
| 최소 변동 | {min_change:.2f}% |

---

## 🔄 변동 분석

### 변동 방향
- **증가** (일치율 상승): {increase_count}개
- **감소** (일치율 하락): {decrease_count}개

"""
    
    # 변동 상품 상세 정보
    if change_count > 0:
        md += "## ⚠️ 변동 상품 상세\n\n"

        def format_table(df, title):
            """데이터프레임을 마크다운 표로 변환"""
            if len(df) == 0:
                return ""

            # CMS URL 생성
            cms_url = os.getenv("CMS_URL", "http://localcms.siliconii.com")

            table_md = f"### {title}\n\n"
            table_md += "| No | 상품코드 | 일치율(어제) | 일치율(오늘) | 변동 | CMS재고 | CMS변동 | WMS수량 | WMS변동 |\n"
            table_md += "|---:|:---------|-------------:|-------------:|-----:|--------:|--------:|--------:|--------:|\n"

            for idx, (_, row) in enumerate(df.iterrows(), 1):
                waiting_today = float(row.get('waiting_qty_today', 0) or 0)
                waiting_yesterday = float(row.get('waiting_qty_yesterday', 0) or 0)
                cms_diff = float(row['cms_qty_today']) - float(row['cms_qty_yesterday'])
                physical_today = float(row['wms_qty_today']) + waiting_today
                physical_yesterday = float(row['wms_qty_yesterday']) + waiting_yesterday
                physical_diff = physical_today - physical_yesterday

                prod_cd = row['prod_cd']
                prod_link = f"[{prod_cd}]({cms_url}/WMS/CmsWmsStock?ProdCd={prod_cd})"

                table_md += (
                    f"| {idx} | **{prod_link}** | "
                    f"{row['accuracy_yesterday']:.1f}% | "
                    f"{row['accuracy_today']:.1f}% | "
                    f"{row['change']:+.1f}% | "
                    f"{row['cms_qty_today']:.0f} | "
                    f"{cms_diff:+.0f} | "
                    f"{physical_today:.0f} | "
                    f"{physical_diff:+.0f} |\n"
                )

            table_md += "\n"
            return table_md

        # 일치율 증가 섹션 (변동폭 큰 순)
        increased = changed[changed['change'] > 0].sort_values('change', ascending=False)
        if len(increased) > 0:
            md += format_table(increased, f"📈 일치율 증가 ({len(increased)}개)")

        # 일치율 감소 섹션 (변동폭 큰 순)
        decreased = changed[changed['change'] < 0].sort_values('change', ascending=True)
        if len(decreased) > 0:
            md += format_table(decreased, f"📉 일치율 감소 ({len(decreased)}개)")
    else:
        md += "\n✅ **변동 상품 없음** - 재고가 정상입니다.\n\n"
    
    # 마크다운 결론
    md += f"""
---

## 💡 해석

- **일치율 정의:** min(전산재고, 물류재고) / max(전산재고, 물류재고) × 100
- **높은 변동 원인:**
  - 출고/입고 후 WMS 미반영
  - 순환재고조사 실시
  - 시스템 동기화 오류
  - 반품/취소 처리

---

## 📝 다음 조치

1. **변동 상품 확인** - 우선순위순 확인
2. **원인 파악** - 출입고 이력 검토
3. **조정** - 필요시 재고 조정
4. **검증** - 다음 주기에 개선 확인

---

*이 리포트는 자동으로 생성되었습니다.*
"""
    
    return md


def generate_csv_report(changed, date_str):
    """
    CSV 형식의 리포트도 생성 (엑셀에서 열 수 있음)
    """
    if changed is None or len(changed) == 0:
        return None
    
    # 존재하는 컬럼만 선택
    base_cols = [
        'prod_cd', 'prod_nm',
        'accuracy_yesterday', 'accuracy_today', 'change',
        'cms_qty_yesterday', 'cms_qty_today',
        'wms_qty_yesterday', 'wms_qty_today',
    ]
    waiting_cols = [c for c in ['waiting_qty_yesterday', 'waiting_qty_today'] if c in changed.columns]
    select_cols = base_cols + waiting_cols
    select_cols = [c for c in select_cols if c in changed.columns]

    report = changed[select_cols].copy()

    rename_map = {
        'prod_cd':  '상품코드',
        'prod_nm':  '상품명',
        'accuracy_yesterday':  '어제_일치율(%)',
        'accuracy_today':      '오늘_일치율(%)',
        'change':              '변동(%)',
        'cms_qty_yesterday':   '어제_CMS재고',
        'cms_qty_today':       '오늘_CMS재고',
        'wms_qty_yesterday':   '어제_WMS재고',
        'wms_qty_today':       '오늘_WMS재고',
        'waiting_qty_yesterday':   '어제_대기재고',
        'waiting_qty_today':       '오늘_대기재고',
    }
    report = report.rename(columns=rename_map)
    
    return report


def save_reports(markdown_content, csv_df, date_str, output_dir):
    """
    리포트 저장 (마크다운 + CSV)
    """
    # 출력 폴더 생성
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n💾 리포트 저장 중...")
    
    # 마크다운 저장
    md_filename = f"report_{date_str}.md"
    md_path = os.path.join(output_dir, md_filename)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"  ✅ 마크다운: {md_filename}")
    
    # CSV 저장
    if csv_df is not None and len(csv_df) > 0:
        csv_filename = f"report_{date_str}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        csv_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"  ✅ CSV: {csv_filename}")
    
    print(f"\n📁 저장 경로: {os.path.abspath(output_dir)}")
    
    return md_path


# ========================================
# 🚀 메인 실행
# ========================================

def get_latest_csv_files(directory, count=2):
    """
    디렉토리에서 최신 CSV 파일들을 찾습니다.
    성능 최적화: 최근 2개월 폴더만 검색 + 상위 20개만 정렬

    Args:
        directory: CSV 파일이 있는 기본 폴더 (월별 폴더의 부모)
        count: 가져올 파일 개수 (기본 2개)

    Returns:
        최신 파일들의 경로 리스트 (최신순으로 정렬)
    """
    import glob
    import re
    from datetime import datetime, timedelta

    # 현재 월과 이전 월 계산
    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    # 이전 월 계산 (월 경계 고려)
    last_month_date = now.replace(day=1) - timedelta(days=1)
    last_month = last_month_date.strftime("%Y-%m")

    csv_files = []

    # 현재 월 폴더 검색
    current_month_dir = os.path.join(directory, current_month)
    if os.path.exists(current_month_dir):
        csv_files.extend(glob.glob(os.path.join(current_month_dir, "Stock*.csv")))

    # 이전 월 폴더 검색
    last_month_dir = os.path.join(directory, last_month)
    if os.path.exists(last_month_dir):
        csv_files.extend(glob.glob(os.path.join(last_month_dir, "Stock*.csv")))

    # 월별 폴더가 없는 경우 (레거시) - 루트에서 직접 검색
    if not csv_files:
        csv_files = glob.glob(os.path.join(directory, "Stock*.csv"))

    if not csv_files:
        return []

    def extract_datetime_from_filename(filepath):
        """
        파일명에서 날짜+시간 추출 (Stock_2026-02-23_1430.csv -> 2026-02-23_1430)
        형식: Stock_{yyyy-mm-dd}_{hhmm}.csv 또는 Stock{yyyy-mm-dd}.csv
        """
        filename = os.path.basename(filepath)

        # Stock_{yyyy-mm-dd}_{hhmm} 형식 (시간 포함)
        match = re.search(r'Stock_?(\d{4}-\d{2}-\d{2})_(\d{4})', filename)
        if match:
            return f"{match.group(1)}_{match.group(2)}"

        # Stock_{yyyy-mm-dd} 또는 Stock{yyyy-mm-dd} 형식 (시간 없음)
        match = re.search(r'Stock_?(\d{4}-\d{2}-\d{2})', filename)
        if match:
            return f"{match.group(1)}_0000"  # 시간 없으면 00:00으로 간주

        # 날짜 형식이 없으면 파일명 자체 반환
        return filename

    # 성능 최적화: 상위 20개만 정렬 후 최신 2개 선택
    try:
        # 전체를 정렬하지 않고 상위 20개만 선택
        if len(csv_files) > 20:
            # 빠른 부분 정렬 (heapq 사용)
            import heapq
            # nlargest는 내림차순이므로 reverse=True 효과
            csv_files = heapq.nlargest(20, csv_files, key=extract_datetime_from_filename)
        else:
            csv_files.sort(key=extract_datetime_from_filename, reverse=True)
    except:
        # 날짜 추출 실패 시 수정 시간으로 정렬
        csv_files.sort(key=os.path.getmtime, reverse=True)

    return csv_files[:count]


def load_csv_file_directly(filepath):
    """
    CSV 파일을 직접 로드하고 컬럼 정규화

    Args:
        filepath: CSV 파일 전체 경로

    Returns:
        정규화된 DataFrame
    """
    filename = os.path.basename(filepath)
    print(f"\n📂 파일 로드: {filename}")

    try:
        # CSV 읽기 (한글 인코딩)
        try:
            df = pd.read_csv(filepath, encoding='utf-8-sig')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='cp949')

        # 마지막 행 제거 (합계/요약 행이 있을 수 있음)
        if len(df) > 0:
            last_row = df.iloc[-1]
            # 마지막 행이 합계 행인지 확인 (상품코드가 비어있거나 숫자가 아닌 경우)
            if pd.isna(last_row.get(COL_PROD_CD)) or str(last_row.get(COL_PROD_CD)).strip() == '':
                df = df.iloc[:-1]

        # 컬럼 정규화 (한글 컬럼명과 영문 컬럼명 모두 지원)
        rename_map = {}

        # 한글 컬럼명 매핑
        if COL_PROD_CD in df.columns:
            rename_map[COL_PROD_CD] = 'prod_cd'
        if COL_PRODUCT_NAME in df.columns:
            rename_map[COL_PRODUCT_NAME] = 'prod_nm'
        if COL_CMS_QTY in df.columns:
            rename_map[COL_CMS_QTY] = 'cms_qty'
        if COL_WMS_QTY in df.columns:
            rename_map[COL_WMS_QTY] = 'wms_qty'
        if COL_WAITING_QTY in df.columns:
            rename_map[COL_WAITING_QTY] = 'waiting_qty'

        # DB export 영문 컬럼명 매핑 (이전 버전 파일 지원)
        if 'cms_total_qty' in df.columns:
            rename_map['cms_total_qty'] = 'cms_qty'
        if 'wms_total_qty' in df.columns:
            rename_map['wms_total_qty'] = 'wms_qty'

        df = df.rename(columns=rename_map)

        # 수치 컬럼 강제 변환
        for col in ('cms_qty', 'wms_qty', 'waiting_qty'):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # 일치율 처리
        if COL_ACCURACY in df.columns:
            df['accuracy'] = (
                df[COL_ACCURACY]
                .astype(str)
                .str.replace('%', '', regex=False)
                .str.strip()
                .apply(lambda x: float(x) if x not in ('', 'nan') else 0.0)
            )
        else:
            df['accuracy'] = df.apply(
                lambda row: calculate_accuracy(
                    row.get('cms_qty'),
                    row.get('wms_qty'),
                    row.get('waiting_qty')
                ), axis=1
            )

        print(f"  ✅ 로드 완료: {len(df)}개 상품")
        return df

    except Exception as e:
        print(f"  ❌ 오류: {str(e)}")
        return None


def main():
    print("=" * 60)
    print("📊 재고 일치율 변동 분석 시작")
    print("=" * 60)

    # 1. 최신 CSV 파일 2개 찾기
    print(f"\n📂 최신 파일 검색 중: {INPUT_DIR}")
    latest_files = get_latest_csv_files(INPUT_DIR, count=2)

    if len(latest_files) < 2:
        print(f"\n❌ 비교할 파일이 부족합니다. (발견: {len(latest_files)}개, 필요: 2개)")
        print(f"   경로: {INPUT_DIR}")
        return

    today_file = latest_files[0]
    yesterday_file = latest_files[1]

    # 파일명에서 날짜+시간 추출
    import re
    def get_datetime_from_filename(filepath):
        filename = os.path.basename(filepath)

        # Stock_{yyyy-mm-dd}_{hhmm} 형식 (시간 포함)
        match = re.search(r'Stock_?(\d{4}-\d{2}-\d{2})_(\d{4})', filename)
        if match:
            date_part = match.group(1)
            time_part = match.group(2)
            return f"{date_part} {time_part[:2]}:{time_part[2:]}"

        # Stock_{yyyy-mm-dd} 또는 Stock{yyyy-mm-dd} 형식 (시간 없음)
        match = re.search(r'Stock_?(\d{4}-\d{2}-\d{2})', filename)
        if match:
            return f"{match.group(1)} (시간 미상)"

        # 파일명에 날짜가 없으면 수정 시간 사용
        return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M")

    today_str = get_datetime_from_filename(today_file)
    yesterday_str = get_datetime_from_filename(yesterday_file)

    print(f"\n📋 비교 파일:")
    print(f"  최신: {os.path.basename(today_file)}")
    print(f"        일시: {today_str}")
    print(f"  이전: {os.path.basename(yesterday_file)}")
    print(f"        일시: {yesterday_str}")

    # 2. 데이터 로드
    today_df = load_csv_file_directly(today_file)
    yesterday_df = load_csv_file_directly(yesterday_file)

    if today_df is None or yesterday_df is None:
        print("\n❌ 데이터 로드 실패")
        return
    
    # 2. 데이터 비교
    comparison, changed = compare_inventory(yesterday_df, today_df)
    
    if comparison is None:
        return
    
    # 3. 리포트 생성
    print("\n📝 마크다운 리포트 생성 중...")
    # 리포트용 날짜 문자열 (파일명에 사용하기 위해 yyyy-mm-dd만 추출)
    report_date = today_str.split()[0]  # "2026-02-23 14:30" -> "2026-02-23"
    md_report = generate_markdown_report(comparison, changed, today_str)

    print("📝 CSV 리포트 생성 중...")
    csv_report = generate_csv_report(changed, report_date)

    # 4. 리포트 저장
    md_path = save_reports(md_report, csv_report, report_date, OUTPUT_DIR)

    # 5. Notion 전송 (선택적)
    notion_url = None
    send_to_notion = os.getenv("SEND_NOTION_REPORT", "false").lower() == "true"
    print(f"\n🔍 Notion 전송 체크:")
    print(f"  변동 상품 수: {len(changed)}개")
    print(f"  SEND_NOTION_REPORT: {os.getenv('SEND_NOTION_REPORT', 'false')} → {send_to_notion}")

    if send_to_notion and len(changed) > 0:
        print("\n📤 Notion 페이지 생성 중...")
        try:
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from src.reporter.notion_client import send_report_to_notion

            # 테스트 모드 체크
            test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
            test_prefix = "[TEST] " if test_mode else ""
            title = f"{test_prefix}재고 일치율 변동 분석 ({report_date})"
            result = send_report_to_notion(
                markdown_content=md_report,
                title=title
            )

            if result.get("success"):
                notion_url = result.get('url')
                print(f"✅ Notion 페이지 생성 완료")
                print(f"   URL: {notion_url}")
            else:
                print(f"⚠️ Notion 페이지 생성 실패: {result.get('error')}")

        except ImportError as e:
            print(f"⚠️ Notion 클라이언트 모듈 로드 실패: {e}")
        except Exception as e:
            print(f"⚠️ Notion 전송 실패: {e}")

    # 6. 슬랙 전송 (선택적)
    send_to_slack = os.getenv("SEND_SLACK_NOTIFICATION", "false").lower() == "true"
    print(f"\n🔍 슬랙 전송 체크:")
    print(f"  SEND_SLACK_NOTIFICATION: {os.getenv('SEND_SLACK_NOTIFICATION', 'false')} → {send_to_slack}")

    if send_to_slack and len(changed) > 0:
        print("\n📤 슬랙 메시지 전송 중...")
        try:
            from pathlib import Path
            project_root = Path(__file__).resolve().parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

            from src.reporter.slack_notifier import send_stock_report_to_slack
            result = send_stock_report_to_slack(
                md_report=md_report,
                today_str=report_date,
                yesterday_str=yesterday_str.split()[0] if ' ' in yesterday_str else yesterday_str,
                notion_url=notion_url
            )
            print(f"✅ 슬랙 전송 완료: {result}")
        except ImportError as e:
            print(f"⚠️ 슬랙 전송 모듈 로드 실패: {e}")
        except Exception as e:
            print(f"⚠️ 슬랙 전송 실패: {e}")

    # 7. 완료
    print("\n" + "=" * 60)
    print("✅ 분석 완료!")
    print("=" * 60)

    # 마크다운 미리보기 (처음 부분만)
    # print(f"\n📄 리포트 미리보기:\n")
    # print(md_report[:500] + "...\n")

    print(f"💡 마크다운 파일을 Claude AI에 복사해서 붙여넣으세요!")
    print(f"   또는 VS Code에서 {md_path} 파일을 열어보세요.")



if __name__ == "__main__":
    main()

