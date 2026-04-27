# AGV 4층 VNA 섹션 — 정체 재고 우선순위 분석기

## 개정 메모 (2026-04-22)

> **A안(최근 스냅샷 기준 연속 무변동 일수)으로 변경.** 초기 설계인 "3개월 전 기간 동안 한 번도 움직이지 않은 조합만 통과"(이하 B안) 대신, **최근 스냅샷의 현재 수량이 며칠째 연속 유지되고 있는지를 측정**하는 방식으로 간다.
>
> - B안은 이진 필터라 "2월 초 입고 후 80일째 방치" 같은 확실한 방치 케이스를 놓친다.
> - A안은 "얼마나 오래 안 움직였나"를 `재고보유일수` 수치로 뽑아 1차 정렬 키로 쓸 수 있어 방치 판별에 정합적이다.
> - 판별 키 `(상품코드, 유통기한)`, 입력 CSV 구조, 출력 포맷은 기존 결정 유지.

## Context

AGV 4층 VNA 섹션에 있는 상품 중 **최근 스냅샷 기준으로 가장 오랫동안 수량 변동이 없는** 방치 재고를 찾아내고, 재고보유일수 → 유통기한 임박 → 수량 많은 순으로 우선순위를 매긴다. 재고조사/재배치/프로모션 대상 선별에 활용하기 위한 단발성 분석 스크립트다.

입력은 사용자가 직접 제공하는 **일일 재고 스냅샷 CSV**(2026-01-01부터, VNA 섹션만 사전 필터링된 상태)이며, 결과는 기존 프로젝트 컨벤션에 맞춰 **마크다운 리포트 + CSV**로 내보낸다.

## 결정 사항 (확정)

| 항목 | 값 |
|---|---|
| 입력 폴더 | `data/agv4_snapshots/` (프로젝트 루트 기준) |
| 입력 파일명 규칙 | 파일명에서 날짜 자동 파싱 (예: `Stock_2026-01-01.csv` / `VNA_2026-01-01.csv`) |
| 변동 없음 판별 키 | `(상품코드, 유통기한)` |
| 정체 판별 방식 | **A안** — 최근 스냅샷의 현재 수량이 며칠째 연속 유지됐는지(`재고보유일수`) 계산. 3개월 전 기간 무변동 강제 아님 |
| 우선순위 정렬 | ① 재고보유일수 내림차순 → ② 유통기한 오름차순 → ③ 수량 내림차순 |
| 출력 | `output/vna_static_priority_{YYYY-MM-DD}.md` + `output/vna_static_priority_{YYYY-MM-DD}.csv` |
| 스크립트 위치 | [src/analyzer/vna_static_stock_analyzer.py](src/analyzer/vna_static_stock_analyzer.py) |
| 실행 방식 | `python src/analyzer/vna_static_stock_analyzer.py` (단독 실행) |

## 구현 상세

### 1. 설정 블록 (파일 상단)

기존 [src/analyzer/daily_stock_accuracy_analyzer.py:38-70](src/analyzer/daily_stock_accuracy_analyzer.py#L38-L70) 패턴 그대로 사용:

```python
INPUT_DIR = project_root / "data" / "agv4_snapshots"
OUTPUT_DIR = project_root / "output"

# CSV 컬럼명 (한글) — 실제 파일 받아보고 1차 조정 필요
COL_PROD_CD   = "상품코드"
COL_PROD_NM   = "상품명"
COL_EXP_DATE  = "유통기한"
COL_QTY       = "수량"        # 혹은 'WMS 재고' / 'AGV4 재고'
COL_LOC       = "로케이션"     # 있으면 리포트에 표시만, 키에는 미포함

ANALYSIS_MONTHS = 3
TOP_N_REPORT   = 50            # 마크다운에는 상위 N개만, CSV는 전량
```

### 2. 데이터 로드

- `INPUT_DIR` 내 모든 `.csv` 수집 → 파일명에서 `YYYY-MM-DD` 추출 → **오늘 기준 3개월 이내** 것만 유지
- 각 CSV를 `pd.read_csv(encoding='utf-8-sig')`로 로드 후 `snapshot_date` 컬럼을 파일명 기반으로 부여
- 전체를 하나의 long-format DataFrame으로 concat
- 기존 [daily_stock_accuracy_analyzer.py](src/analyzer/daily_stock_accuracy_analyzer.py)의 `load_csv_file_directly` 스타일을 따라 한글/영문 컬럼명 호환 처리

### 3. 재고보유일수 계산 (A안)

최신 스냅샷 날짜 `D_latest`를 기준으로, 각 `(상품코드, 유통기한)` 조합의 **연속 무변동 일수**를 구한다.

```python
# 각 (prod_cd, exp_date)의 일자별 수량 (VNA 여러 곳에 분산돼 있으면 합산)
daily_qty = (
    window.groupby(['snapshot_date', 'prod_cd', 'exp_date'])['qty'].sum().reset_index()
)

# 최신 스냅샷에 존재하는 조합만 시작점으로 삼음 (현재 재고가 있어야 방치 대상)
latest_qty = daily_qty[daily_qty['snapshot_date'] == D_latest]

# 각 조합에 대해 D_latest → 과거로 walking:
#   같은 qty로 관측된 날 → 연속 카운트
#   다른 qty 또는 해당 날 관측치 부재(= 재고 0 = 움직임) → 스트릭 종료
#   카운트 결과가 재고보유일수
```

- 중간 누락일은 스트릭을 끊는다 (사용자 지적: "없다 = 재고 0 = 입출고 발생").
- 현재 수량이 0이거나 최신 스냅샷에 없는 조합은 아예 제외 (보유 없음).

### 4. 우선순위 정렬

```python
result = latest_with_streak.sort_values(
    by=['재고보유일수', '유통기한', '수량'],
    ascending=[False,       True,       False],
).reset_index(drop=True)
result.insert(0, '우선순위', range(1, len(result) + 1))
```

- 1차: 오래 방치된 것 먼저
- 2차: 동일 방치 기간 내에서는 유통기한 임박한 것 먼저
- 3차: 동일 조건에서는 수량 많은 것 먼저

VNA 위치(최신 스냅샷 기준)는 조인해서 리포트에 표시.

### 5. 출력

- **CSV** (`output/vna_static_priority_YYYY-MM-DD.csv`): 전 결과. 컬럼 = `우선순위, 상품코드, 유효기간, 수량, 재고보유일수, VNA위치`
- **마크다운** (`output/vna_static_priority_YYYY-MM-DD.md`):
  - 상단 요약: 분석 기간, 스냅샷 수, VNA 대상 상품 수, 변동 없음 상품 수, 평균 유통기한까지 남은 일수
  - 본문: 상위 `TOP_N_REPORT`개 테이블 (마크다운 파이프 테이블)
  - 하단: CSV 파일 경로 안내

## 변경할 파일

- **신규 작성**: [src/analyzer/vna_static_stock_analyzer.py](src/analyzer/vna_static_stock_analyzer.py)
- **신규 폴더**: `data/agv4_snapshots/` (사용자가 CSV를 놓을 자리 — 빈 `.gitkeep`만 추가)

기존 파일 수정 없음. `main.py`에 연동하지 않음(단발성 분석기). 필요해지면 이후 별도로 연동.

## 검증 방법

1. 사용자가 `data/agv4_snapshots/`에 2026-01-01 ~ 오늘까지의 VNA 스냅샷 CSV를 넣는다.
2. `python src/analyzer/vna_static_stock_analyzer.py` 실행.
3. 콘솔에 로드된 파일 수, 대상 (상품코드, 유통기한) 조합 수, 변동 없음 건수가 출력되는지 확인.
4. `output/vna_static_priority_{오늘}.csv` 열어서:
   - `우선순위 1`번 행의 유통기한이 가장 빠른지
   - 같은 유통기한 내에서는 수량이 많은 순인지
   - `수량` 값이 가장 최근 스냅샷 값과 일치하는지
5. 샘플 상품 1~2개를 임의로 뽑아 원본 CSV들에서 직접 값 변화를 확인해 변동 없음이 맞는지 교차검증.

## 열린 이슈 (구현 시 사용자와 함께 확인)

1. CSV 실제 컬럼명 — 한글/영문, `유통기한`의 포맷(`YYYY-MM-DD` vs `YYYYMMDD`), `수량` 컬럼명
2. 유통기한이 비어있는 상품(non-expiring) 처리 방침 — 현재 설계는 **제외**. 필요 시 별도 섹션에 따로 노출
3. 스냅샷 누락일 허용 범위 (`MIN_SNAPSHOTS` 기본값 90%가 적절한지)
