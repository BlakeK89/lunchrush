"""Safe user-upload parsing for XLSX and a ZIP containing eight CSV tables."""
from __future__ import annotations
import io
import zipfile
from pathlib import PurePosixPath
from typing import Any
from .io import load_csv_tabs, load_xlsx

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 85 * 1024 * 1024
MAX_MEMBER_BYTES = 40 * 1024 * 1024


def parse_upload(name: str, payload: bytes, schema: dict[str, Any]) -> dict[str, list[dict]]:
    if not payload:
        raise ValueError('File is empty.')
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError('Maximum upload size is 25 MB.')
    extension = name.lower().rsplit('.', 1)[-1]
    if extension == 'xlsx':
        return load_xlsx(payload)
    if extension != 'zip':
        raise ValueError('Upload an Excel .xlsx workbook or a .zip containing CSV sheets.')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if len(infos) > 12:
                raise ValueError('Upload a ZIP with eight CSV tables, not an arbitrary archive.')
            if sum(i.file_size for i in infos) > MAX_UNCOMPRESSED_BYTES:
                raise ValueError('CSV archive is too large when uncompressed.')
            if any(i.file_size > MAX_MEMBER_BYTES or i.flag_bits & 1 for i in infos):
                raise ValueError('Oversized or password-protected CSV entry.')
            csv_text: dict[str, bytes] = {}
            for entry in infos:
                if entry.is_dir():
                    raise ValueError('ZIP must contain CSV files at the top level.')
                if PurePosixPath(entry.filename).name != entry.filename:
                    raise ValueError('ZIP must contain CSV files at the top level.')
                if not entry.filename.lower().endswith('.csv'):
                    raise ValueError('Only CSV files are allowed in a data ZIP.')
                tab = entry.filename[:-4]
                if tab not in schema['tables']:
                    raise ValueError(f'Unknown data table: {entry.filename}')
                if tab in csv_text:
                    raise ValueError(f'Duplicate CSV table: {tab}')
                csv_text[tab] = archive.read(entry)
            required = {k for k, v in schema['tables'].items() if v['required']}
            missing = sorted(required - set(csv_text))
            if missing:
                raise ValueError('Missing CSV tables: ' + ', '.join(missing))
            return load_csv_tabs(csv_text)
    except zipfile.BadZipFile as exc:
        raise ValueError('Not a valid ZIP archive.') from exc
