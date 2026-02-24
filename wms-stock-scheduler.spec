# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # SQL 파일 포함
        ('repository/stock_export.sql', 'repository'),
        # 환경 설정 파일은 빌드에서 제외 (외부 파일 사용)
        # README 파일 포함 (선택적)
        # ('README.md', '.'),
    ],
    hiddenimports=[
        # 명시적으로 포함해야 하는 모듈들
        'sqlalchemy.dialects.mssql',
        'pyodbc',
        'pymssql',  # Native SQL Server driver
        'apscheduler.schedulers.blocking',
        'apscheduler.triggers.interval',
        'apscheduler.triggers.cron',
        'loguru',
        'pandas',
        'openpyxl',
        'requests',
        'dotenv',
        # 프로젝트 모듈들
        'src.downloader.daily_stock_exporter',
        'src.analyzer.daily_stock_accuracy_analyzer',
        'src.reporter.slack_notifier',
        'src.reporter.notion_client',
        'src.reporter.notion_client_database',
        'scheduler.job_scheduler',
        'scheduler.jobs.download_job',
        'scheduler.jobs.report_job',
        'scheduler.jobs.db_export_job',
        'config.settings',
        'config.path_helper',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 제외할 불필요한 모듈들
        'matplotlib',
        'tkinter',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WMS-Stock-Scheduler',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 콘솔 창 표시 (로그 확인용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일이 있으면 경로 지정: 'icon.ico'
)
