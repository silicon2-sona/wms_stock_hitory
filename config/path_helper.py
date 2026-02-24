# -*- coding: utf-8 -*-
"""
경로 헬퍼 - 실행 파일 기준 상대 경로 처리
"""
import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """
    애플리케이션 디렉토리 반환
    - 빌드된 실행 파일: 실행 파일이 있는 폴더
    - 개발 환경: 프로젝트 루트
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 실행 파일
        return Path(sys.executable).parent
    else:
        # 개발 환경 (Python 스크립트)
        return Path(__file__).resolve().parent.parent


def resolve_data_path(path_str: str) -> Path:
    """
    데이터 경로 해석

    - 절대 경로면 그대로 사용
    - 상대 경로면 실행 파일 기준으로 해석
    - './data' 또는 'data' → 실행 파일 폴더의 data

    Args:
        path_str: 경로 문자열

    Returns:
        해석된 절대 경로
    """
    if not path_str:
        # 빈 문자열이면 기본값: 실행 파일 폴더의 data
        return get_app_dir() / "data"

    path = Path(path_str)

    # 절대 경로면 그대로 반환
    if path.is_absolute():
        return path

    # 상대 경로면 실행 파일 기준으로 해석
    return get_app_dir() / path


def ensure_dir(path: Path) -> Path:
    """
    디렉토리가 없으면 생성

    Args:
        path: 디렉토리 경로

    Returns:
        생성된 디렉토리 경로
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
