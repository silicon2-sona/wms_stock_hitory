#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
일일 재고 CSV 생성 모듈
SQL Server에서 재고 데이터를 조회하여 CSV 파일로 저장
"""

import os
import sys
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Windows 터미널 cp949 환경에서 이모지 출력 가능하도록 utf-8 강제 설정
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

logger = logging.getLogger(__name__)


class DBExporter:
    """
    DB에서 데이터를 조회하여 CSV 파일로 저장
    """

    def __init__(self):
        self.db_type = os.getenv("DB_TYPE", "mssql")  # mssql, mysql, postgresql
        self.db_host = os.getenv("DB_HOST", "localhost")

        # DB_PORT가 비어있으면 기본값 사용
        db_port = os.getenv("DB_PORT", "")
        if not db_port:
            # DB 타입별 기본 포트
            default_ports = {"mssql": "1433", "mysql": "3306", "postgresql": "5432"}
            self.db_port = default_ports.get(self.db_type, "1433")
        else:
            self.db_port = db_port

        self.db_name = os.getenv("DB_NAME", "")
        self.db_user = os.getenv("DB_USER", "")
        self.db_password = os.getenv("DB_PASSWORD", "")
        self.db_odbc_driver = os.getenv("DB_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

        # 연결 방식: odbc 또는 native (pymssql/pymysql/psycopg2)
        self.db_connection_method = os.getenv("DB_CONNECTION_METHOD", "native")

        self.output_dir = Path(os.getenv("DB_EXPORT_OUTPUT_DIR", "./data/raw"))

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _execute_query_odbc(self, query):
        """ODBC를 사용한 쿼리 실행"""
        import pyodbc

        # 연결 문자열 구성
        if self.db_port:
            server = f"{self.db_host},{self.db_port}"
        else:
            server = self.db_host

        conn_str = (
            f"DRIVER={{{self.db_odbc_driver}}};"
            f"SERVER={server};"
            f"DATABASE={self.db_name};"
            f"UID={self.db_user};"
            f"PWD={self.db_password};"
        )

        logger.info(f"연결 문자열: {conn_str.replace(self.db_password, '***')}")

        # DB 연결
        conn = pyodbc.connect(conn_str, timeout=30)
        cursor = conn.cursor()
        logger.info("DB 연결 성공")

        # 쿼리 실행
        logger.info(f"쿼리 실행 중...\n{query[:200]}...")
        cursor.execute(query)

        # 다중 statement에서 마지막 결과 셋으로 이동
        while cursor.description is None:
            if not cursor.nextset():
                break

        # 결과 가져오기
        if cursor.description is None:
            logger.error("쿼리 결과가 없습니다.")
            cursor.close()
            conn.close()
            return None

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        logger.info(f"쿼리 실행 완료: {len(rows)} rows")

        # DataFrame 생성
        df = pd.DataFrame.from_records(rows, columns=columns)

        cursor.close()
        conn.close()

        return df

    def _execute_query_native(self, query):
        """Native 드라이버를 사용한 쿼리 실행 (pymssql, pymysql, psycopg2)"""
        if self.db_type == "mssql":
            import pymssql

            # pymssql 연결
            conn = pymssql.connect(
                server=self.db_host,
                port=int(self.db_port) if self.db_port else 1433,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                timeout=30
            )
            logger.info("DB 연결 성공 (pymssql)")

        elif self.db_type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=self.db_host,
                port=int(self.db_port) if self.db_port else 3306,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                connect_timeout=30
            )
            logger.info("DB 연결 성공 (pymysql)")

        elif self.db_type == "postgresql":
            import psycopg2
            conn = psycopg2.connect(
                host=self.db_host,
                port=int(self.db_port) if self.db_port else 5432,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                connect_timeout=30
            )
            logger.info("DB 연결 성공 (psycopg2)")

        else:
            raise ValueError(f"지원하지 않는 DB 타입: {self.db_type}")

        cursor = conn.cursor()

        # 쿼리 실행
        logger.info(f"쿼리 실행 중...\n{query[:200]}...")
        cursor.execute(query)

        # 결과 가져오기
        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        logger.info(f"쿼리 실행 완료: {len(rows)} rows")

        # DataFrame 생성
        df = pd.DataFrame.from_records(rows, columns=columns)

        cursor.close()
        conn.close()

        return df

    def get_connection_string(self):
        """SQLAlchemy용 DB 연결 문자열 생성"""
        if self.db_type == "mssql":
            # SQL Server (SQLAlchemy + pyodbc)
            from urllib.parse import quote_plus

            # 특수문자 URL 인코딩
            encoded_password = quote_plus(self.db_password)
            encoded_user = quote_plus(self.db_user)

            # 포트가 있으면 포함, 없으면 제외
            if self.db_port:
                host_port = f"{self.db_host}:{self.db_port}"
            else:
                host_port = self.db_host

            # 드라이버 이름 URL 인코딩
            encoded_driver = quote_plus(self.db_odbc_driver)

            return (
                f"mssql+pyodbc://{encoded_user}:{encoded_password}@"
                f"{host_port}/{self.db_name}"
                f"?driver={encoded_driver}"
            )
        elif self.db_type == "mysql":
            # MySQL (pymysql 사용)
            host_port = f"{self.db_host}:{self.db_port}" if self.db_port else self.db_host
            return f"mysql+pymysql://{self.db_user}:{self.db_password}@{host_port}/{self.db_name}"
        elif self.db_type == "postgresql":
            # PostgreSQL (psycopg2 사용)
            host_port = f"{self.db_host}:{self.db_port}" if self.db_port else self.db_host
            return f"postgresql://{self.db_user}:{self.db_password}@{host_port}/{self.db_name}"
        else:
            raise ValueError(f"지원하지 않는 DB 타입: {self.db_type}")

    def export_to_csv(self, query: str, filename: str = None) -> Path:
        """
        DB 쿼리 결과를 CSV 파일로 저장

        Args:
            query: SQL 쿼리문
            filename: 저장할 파일명 (None이면 자동 생성)

        Returns:
            저장된 파일 경로
        """
        now = datetime.now()

        if filename is None:
            timestamp = now.strftime("%Y-%m-%d_%H%M")
            filename = f"Stock_{timestamp}.csv"

        # 월별 폴더 생성 (예: output/daily-stock/2026-02/)
        monthly_dir = self.output_dir / now.strftime("%Y-%m")
        monthly_dir.mkdir(parents=True, exist_ok=True)

        output_path = monthly_dir / filename

        logger.info(f"DB 데이터 조회 시작: {self.db_name}")
        logger.info(f"DB 타입: {self.db_type}")
        logger.info(f"DB 호스트: {self.db_host}:{self.db_port}")
        logger.info(f"연결 방식: {self.db_connection_method}")

        try:
            # 연결 방식에 따라 분기
            if self.db_connection_method == "odbc":
                # ODBC 방식
                logger.info("ODBC 방식으로 연결 중...")
                df = self._execute_query_odbc(query)
            else:
                # Native 방식 (pymssql, pymysql, psycopg2)
                logger.info("Native 드라이버로 연결 중...")
                df = self._execute_query_native(query)

            # 결과 확인
            if df is None or len(df) == 0:
                logger.warning("쿼리 결과가 비어있습니다.")
                return None

            # 한글 컬럼명으로 변경 및 일치율 계산
            logger.info("컬럼명 변환 및 일치율 계산 중...")

            # 필요한 컬럼만 선택하고 한글로 변경
            df_export = pd.DataFrame()
            df_export['상품코드'] = df['prod_cd']
            df_export['상품명'] = df['prod_nm']
            df_export['CMS 재고'] = df['cms_total_qty']
            df_export['WMS 재고'] = df['wms_total_qty']
            df_export['대기 수량'] = df['waiting_qty']

            # 일치율 계산: min(cms, physical) / max(cms, physical) * 100
            # physical = wms + waiting
            physical_qty = df['wms_total_qty'] + df['waiting_qty']
            cms_qty = df['cms_total_qty']

            # 0으로 나누기 방지 및 음수 체크
            accuracy = []
            for i in range(len(df)):
                cms = float(cms_qty.iloc[i]) if pd.notna(cms_qty.iloc[i]) else 0
                physical = float(physical_qty.iloc[i]) if pd.notna(physical_qty.iloc[i]) else 0

                if cms == 0 and physical == 0:
                    acc = 100.0
                elif cms == 0 or physical == 0:
                    acc = 0.0
                elif cms < 0 or physical < 0:
                    acc = 0.0
                else:
                    least = min(cms, physical)
                    greatest = max(cms, physical)
                    valid = round(least / greatest * 100, 1)
                    if valid >= 100 and least != greatest:
                        valid = 99.9
                    acc = valid

                accuracy.append(acc)

            df_export['일치율'] = accuracy

            # CSV 저장
            df_export.to_csv(output_path, index=False, encoding="utf-8-sig")
            logger.info(f"CSV 저장 완료: {output_path} ({len(df_export)} rows, {len(df_export.columns)} columns)")
            logger.info(f"컬럼: {list(df_export.columns)}")

            return output_path

        except ImportError as e:
            logger.error(f"필요한 패키지가 설치되지 않았습니다: {e}")
            logger.error("pip install sqlalchemy pyodbc 를 실행하세요")
            raise
        except Exception as e:
            logger.error(f"DB 조회 또는 CSV 저장 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise


def export_stock_data():
    """
    재고 데이터를 DB에서 조회하여 CSV로 저장
    (main.py에서 호출)
    """
    exporter = DBExporter()

    # SQL 파일 경로 (환경변수 또는 기본값)
    sql_file = os.getenv("DB_EXPORT_SQL_FILE", "repository/stock_export.sql")

    # 프로젝트 루트 기준 경로
    project_root = Path(__file__).resolve().parent.parent.parent
    sql_path = project_root / sql_file

    # SQL 파일 읽기
    if sql_path.exists():
        logger.info(f"SQL 파일 읽기: {sql_path}")
        with open(sql_path, 'r', encoding='utf-8') as f:
            query = f.read()
    else:
        # SQL 파일이 없으면 기본 쿼리 사용
        logger.warning(f"SQL 파일을 찾을 수 없습니다: {sql_path}. 기본 쿼리 사용")
        query = """
            SELECT
                prod_cd AS '상품코드',
                prod_nm AS '상품명',
                brand AS '브랜드',
                cms_total_qty AS 'CMS 재고',
                wms_total_qty AS 'WMS 재고',
                waiting_qty AS '대기 수량',
                accuracy AS '일치율'
            FROM stock_view
            WHERE is_active = 1
        """

    try:
        file_path = exporter.export_to_csv(query)
        print(f"✅ DB 데이터 CSV 저장 완료: {file_path}")
        return file_path
    except Exception as e:
        print(f"❌ DB 데이터 조회 실패: {e}")
        return None


if __name__ == "__main__":
    print(f"✅ 실행")
    export_stock_data()