-- AGV 4층 VNA 섹션 방치 재고 분석용 스냅샷 추출 쿼리
-- 사용처: src/analyzer/vna_static_stock_analyzer.py
-- 출력 컬럼 순서: 스냅샷날짜, AGV코드, VNA번호, 상품코드, 유효기간, 수량, 스냅샷등록일
SELECT *
  FROM CSMS_DB_MIRROR.DBO.TB_WS_AGV_INVENTORY
 WHERE pod_vn_no NOT LIKE 'POD%'
   AND ws_inv_dt > '2026-01-01'
