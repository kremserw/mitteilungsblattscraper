# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for JKU MTB Analyzer
Creates a folder-based distribution for reliability.
"""

import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

block_cipher = None

# Collect all required packages
hiddenimports = [
    'flask',
    'jinja2',
    'jinja2.ext',
    'werkzeug',
    'werkzeug.serving',
    'werkzeug.debug',
    'sqlalchemy',
    'sqlalchemy.dialects.sqlite',
    'yaml',
    'anthropic',
    'requests',
    'beautifulsoup4',
    'bs4',
    'lxml',
    'lxml.etree',
    'lxml.html',
    'rich',
    'rich.console',
    'rich.table',
    'click',
    'dateutil',
    'dateutil.parser',
    'src',
    'src.ui',
    'src.scraper',
    'src.analyzer',
    'src.storage',
    'src.parser',
]

# Add SQLAlchemy dialects
hiddenimports += collect_submodules('sqlalchemy')

# Collect certifi data (SSL certificates)
datas = [
    ('config.example.yaml', '.'),
]

# Add certifi certificates
import certifi
datas.append((certifi.where(), 'certifi'))

a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'playwright',  # User needs to run playwright install separately
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'Pillow',
        'pdfplumber',
        'pdfminer',
        'pypdf2',
        'pypdfium2',
        'cv2',
        'torch',
        'tensorflow',
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
    [],
    exclude_binaries=True,
    name='JKU-MTB-Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JKU-MTB-Analyzer',
)
