#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AGV 4층 VNA 섹션 방치 재고 우선순위 분석기 (A안)

데이터 소스 (사용자가 CSMS_DB_MIRROR에서 아래 쿼리로 추출):
    SELECT *
      FROM CSMS_DB_MIRROR.DBO.TB_WS_AGV_INVENTORY
     WHERE pod_vn_no NOT LIKE 'POD%'
       AND ws_inv_dt > '2026-01-01'

입력 CSV (헤더 없음) — 컬럼 순서:
    스냅샷날짜, AGV코드, VNA번호, 상품코드, 유효기간, 수량, 스냅샷등록일

로직:
    1) 최근 ANALYSIS_MONTHS 개월 스냅샷 윈도우로 필터
    2) (상품코드, 유효기간) 조합을 하루 단위로 수량 합산 (여러 VNA 분산 저장분 포함)
    3) 최신 스냅샷의 현재 수량이 **며칠째 연속 유지됐는지** (재고보유일수) 계산
       - 직전 날짜의 수량이 다르거나 관측치가 없으면(= 재고 0 = 움직임) 스트릭 종료
       - 최신 스냅샷에 존재하고 수량 > 0 인 조합만 대상
    4) 재고보유일수 DESC → 유효기간 ASC → 수량 DESC 로 정렬해 우선순위 부여
    5) 최신 스냅샷 기준 VNA 로케이션 목록을 조인해 리포트에 표시
"""

import os
import sys
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# config.env / .env / config.local.env 로드 (NOTION_API_TOKEN, NOTION_PAGE_ID 등)
load_dotenv(project_root / "config.env")
load_dotenv(project_root / ".env", override=True)
if (project_root / "config.local.env").exists():
    load_dotenv(project_root / "config.local.env", override=True)

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ========================================
# 설정
# ========================================
INPUT_CSV = project_root / "data" / "agv4_snapshots" / "agv4_inventory_snapshots.csv"
OUTPUT_DIR = project_root / "output"

CSV_COLUMNS = [
    "snapshot_date",
    "agv_code",
    "vna_no",
    "prod_cd",
    "exp_date",
    "qty",
    "registered_at",
]

ANALYSIS_MONTHS = 3
TOP_N_REPORT = 50


def load_snapshots(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        csv_path,
        header=None,
        names=CSV_COLUMNS,
        encoding='utf-8-sig',
        dtype={'agv_code': str, 'vna_no': str, 'prod_cd': str},
    )
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date']).dt.normalize()
    df['exp_date'] = pd.to_datetime(df['exp_date']).dt.normalize()
    df['qty'] = pd.to_numeric(df['qty'], errors='coerce').fillna(0).astype(int)
    return df


def filter_analysis_window(df: pd.DataFrame):
    end = df['snapshot_date'].max()
    start = end - pd.DateOffset(months=ANALYSIS_MONTHS)
    window = df[(df['snapshot_date'] >= start) & (df['snapshot_date'] <= end)].copy()
    return window, start, end


def compute_stable_stock(window: pd.DataFrame):
    """최신 스냅샷 기준 각 (상품코드, 유효기간) 조합의 연속 무변동 일수를 계산."""
    daily_qty = (
        window.groupby(['snapshot_date', 'prod_cd', 'exp_date'])['qty']
              .sum()
              .reset_index()
    )

    # 날짜 × 조합 피벗 — 관측 없는 날은 0 (재고 없음 = 움직임 발생으로 간주)
    wide = daily_qty.pivot_table(
        index='snapshot_date',
        columns=['prod_cd', 'exp_date'],
        values='qty',
        aggfunc='sum',
        fill_value=0,
    ).sort_index()

    total_days = len(wide)
    latest_qty = wide.iloc[-1]

    # 최신 스냅샷 수량과 각 일자의 수량이 동일한지 비교
    equals_latest = wide.eq(latest_qty, axis=1)

    # 뒤집어서 cummin → 최신에서 과거로 연속 True 인 구간 길이가 곧 재고보유일수
    rev = equals_latest.iloc[::-1].astype(int)
    stable_days = rev.cummin().sum(axis=0)

    result = pd.DataFrame({
        'qty': latest_qty.values.astype(int),
        'stable_days': stable_days.values.astype(int),
    }, index=latest_qty.index).reset_index()

    # 최신 스냅샷에 현재 재고가 있는 조합만 (방치 대상)
    result = result[result['qty'] > 0].copy()
    return result[['prod_cd', 'exp_date', 'qty', 'stable_days']], total_days


def attach_latest_locations(stable: pd.DataFrame, window: pd.DataFrame) -> pd.DataFrame:
    if stable.empty:
        stable['vna_locations'] = []
        return stable

    latest_date = window['snapshot_date'].max()
    latest = window[window['snapshot_date'] == latest_date]
    locs = (
        latest.groupby(['prod_cd', 'exp_date'])['vna_no']
              .apply(lambda s: ', '.join(sorted(s.dropna().unique())))
              .reset_index()
              .rename(columns={'vna_no': 'vna_locations'})
    )
    return stable.merge(locs, on=['prod_cd', 'exp_date'], how='left')


def prioritize(stable: pd.DataFrame) -> pd.DataFrame:
    result = stable.sort_values(
        by=['stable_days', 'exp_date', 'qty'],
        ascending=[False, True, False],
    ).reset_index(drop=True)
    result.insert(0, '우선순위', range(1, len(result) + 1))
    return result


def write_outputs(result: pd.DataFrame, ctx: dict):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today_str = pd.Timestamp.today().strftime('%Y-%m-%d')
    csv_path = OUTPUT_DIR / f"vna_static_priority_{today_str}.csv"
    md_path = OUTPUT_DIR / f"vna_static_priority_{today_str}.md"
    test_prefix = "[TEST] " if os.getenv("TEST_MODE", "false").lower() == "true" else ""

    csv_out = result.rename(columns={
        'prod_cd': '상품코드',
        'exp_date': '유효기간',
        'qty': '수량',
        'stable_days': '재고보유일수',
        'vna_locations': 'VNA위치',
    })
    csv_out['유효기간'] = pd.to_datetime(csv_out['유효기간']).dt.strftime('%Y-%m-%d')
    if 'VNA위치' in csv_out.columns:
        csv_out['VNA위치'] = csv_out['VNA위치'].fillna('')
    csv_out.to_csv(csv_path, index=False, encoding='utf-8-sig')

    md_lines = [
        f"# {test_prefix}AGV 4층 VNA 방치 재고 우선순위 리포트",
        "",
        f"- 생성일: {today_str}",
        f"- 분석 기간: {ctx['start']} ~ {ctx['end']} ({ctx['total_days']}일 스냅샷)",
        f"- 판별 기준: 최신 스냅샷({ctx['end']})의 현재 수량이 며칠째 연속 유지됐는지(`재고보유일수`) 계산, 관측 중 수량 0/누락 발생 시 스트릭 종료",
        f"- 정렬: 재고보유일수 DESC → 유효기간 ASC → 수량 DESC",
        f"- 대상 건수: **{len(result)}건** (최신 스냅샷에 수량 > 0 인 조합)",
        "",
        f"## 상위 {min(TOP_N_REPORT, len(result))}건",
        "",
        "| 우선순위 | 상품코드 | 유효기간 | 수량 | 재고보유일수 | VNA 위치 |",
        "|---:|---|---|---:|---:|---|",
    ]
    for _, row in result.head(TOP_N_REPORT).iterrows():
        loc = row.get('vna_locations')
        loc_str = loc if isinstance(loc, str) and loc else '-'
        md_lines.append(
            f"| {row['우선순위']} | {row['prod_cd']} | "
            f"{pd.to_datetime(row['exp_date']).strftime('%Y-%m-%d')} | "
            f"{row['qty']} | {row['stable_days']} | {loc_str} |"
        )
    md_lines += ["", f"전체 결과: `{csv_path.name}`", ""]
    md_content = '\n'.join(md_lines)
    md_path.write_text(md_content, encoding='utf-8')

    print(f"CSV: {csv_path}")
    print(f"MD:  {md_path}")
    return md_content, today_str, test_prefix


def main():
    if not INPUT_CSV.exists():
        print(f"입력 파일 없음: {INPUT_CSV}")
        return

    df = load_snapshots(INPUT_CSV)
    print(f"로드된 행: {len(df)}")
    print(f"스냅샷 날짜 범위: {df['snapshot_date'].min().date()} ~ {df['snapshot_date'].max().date()}")
    print(f"고유 (상품코드, 유효기간) 조합: {df.groupby(['prod_cd', 'exp_date']).ngroups}")

    window, start, end = filter_analysis_window(df)
    stable, total_days = compute_stable_stock(window)
    stable = attach_latest_locations(stable, window)
    result = prioritize(stable)

    print(f"분석 기간: {start.date()} ~ {end.date()} ({total_days}일)")
    print(f"최신 스냅샷 기준 재고 보유 조합: {len(result)}건")
    if len(result) > 0:
        print(f"최대 재고보유일수: {int(result['stable_days'].max())}일 / 중앙값: {int(result['stable_days'].median())}일")

    md_content, today_str, test_prefix = write_outputs(result, {
        'start': start.date(),
        'end': end.date(),
        'total_days': total_days,
    })

    # Notion 전송 (SEND_NOTION_REPORT=true 일 때만)
    send_to_notion = os.getenv("SEND_NOTION_REPORT", "false").lower() == "true"
    print(f"\nNotion 전송 체크: SEND_NOTION_REPORT={os.getenv('SEND_NOTION_REPORT', 'false')} → {send_to_notion}")

    if send_to_notion and len(result) > 0:
        print("Notion 페이지 생성 중...")
        try:
            from src.reporter.notion_client import send_report_to_notion

            title = f"{test_prefix}vna 방치 재고 우선순위 레포트 ({today_str})"
            notion_result = send_report_to_notion(
                markdown_content=md_content,
                title=title,
            )

            if notion_result.get("success"):
                print(f"Notion 페이지 생성 완료")
                print(f"URL: {notion_result.get('url')}")
            else:
                print(f"Notion 페이지 생성 실패: {notion_result.get('error')}")

        except ImportError as e:
            print(f"Notion 클라이언트 모듈 로드 실패: {e}")
        except Exception as e:
            print(f"Notion 전송 실패: {e}")


if __name__ == '__main__':
    main()
