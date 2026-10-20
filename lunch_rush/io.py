"""Read Lunch Rush XLSX/CSV using the Shelf Life V1 hardened stdlib reader.

Adapted from bpa/io.py in the supplied Shelf Life V1 source.


This parser intentionally reads values, not formulas. It raises for unsupported
sheet structures instead of silently returning incorrect data.
"""
from __future__ import annotations

import csv
import io
import posixpath
import re
import zipfile
from defusedxml import ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import BinaryIO

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'p': 'http://schemas.openxmlformats.org/package/2006/relationships'}
_DATE_EPOCH = date(1899, 12, 30)

# Public-upload defense in depth. The UI/server caps compressed uploads at
# 15 MiB; guard against oversized archives and decompression bombs here too.
MAX_WORKBOOK_BYTES = 25 * 1024 * 1024
MAX_UNCOMPRESSED_WORKBOOK_BYTES = 200 * 1024 * 1024
MAX_UNCOMPRESSED_MEMBER_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 256


def _check_archive_limits(z: zipfile.ZipFile) -> None:
    members = z.infolist()
    if (len(members) > MAX_ARCHIVE_MEMBERS or
            sum(item.file_size for item in members) > MAX_UNCOMPRESSED_WORKBOOK_BYTES or
            any(item.file_size > MAX_UNCOMPRESSED_MEMBER_BYTES for item in members)):
        raise ValueError(
            'Workbook is too large to process safely. Try a smaller Excel file.'
        )
    if any(item.flag_bits & 1 for item in members):
        raise ValueError('Password-protected Excel workbooks are not supported.')


def as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return _DATE_EPOCH + timedelta(days=int(value))
    if isinstance(value, str):
        s = value.strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
            return date.fromisoformat(s)
        if re.fullmatch(r'\d+(?:\.0*)?', s):
            return _DATE_EPOCH + timedelta(days=int(float(s)))
    raise ValueError(f'Invalid date: {value!r}; use YYYY-MM-DD or Excel dates')


def _cell_value(cell: ET.Element, shared_strings: list[str]) -> object:
    kind = cell.get('t')
    v = cell.find('m:v', NS)
    if kind == 'inlineStr':
        return ''.join(x.text or '' for x in cell.findall('.//m:t', NS))
    if v is None or v.text is None:
        # Formula without cached value must not be misinterpreted as zero.
        if cell.find('m:f', NS) is not None:
            raise ValueError(f'Formula without saved result in cell {cell.get("r")}')
        return None
    if kind == 's':
        return shared_strings[int(v.text)]
    if kind in ('str', 'e'):
        if kind == 'e':
            raise ValueError(f'Excel error in {cell.get("r")}: {v.text}')
        return v.text
    if kind == 'b':
        return v.text == '1'
    try:
        return float(v.text) if ('.' in v.text or 'e' in v.text.lower()) else int(v.text)
    except ValueError:
        return v.text


def _column_index(ref: str) -> int:
    m = re.match(r'([A-Z]+)', ref)
    if not m:
        raise ValueError(f'Invalid cell reference {ref}')
    n = 0
    for letter in m.group(1):
        n = n * 26 + ord(letter) - ord('A') + 1
    return n - 1


def load_xlsx(source: str | Path | bytes | BinaryIO) -> dict[str, list[dict]]:
    """Return {tab_name: [row_dict, ...]}, preserving blanks as None.

    Data sheets in the V1 input contract have a single header row.
    Instruction and QA sheets are also parsed but not used as facts.
    """
    if isinstance(source, bytes) and len(source) > MAX_WORKBOOK_BYTES:
        raise ValueError('Excel file is too large. Maximum upload size is 25 MB.')
    if isinstance(source, (str, Path)) and Path(source).stat().st_size > MAX_WORKBOOK_BYTES:
        raise ValueError('Excel file is too large. Maximum upload size is 25 MB.')
    payload = io.BytesIO(source) if isinstance(source, bytes) else source
    with zipfile.ZipFile(payload) as z:
        _check_archive_limits(z)
        try:
            book = ET.fromstring(z.read('xl/workbook.xml'))
            rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        except KeyError as e:
            raise ValueError('Not a valid .xlsx workbook') from e
        targets = {rel.get('Id'): rel.get('Target') for rel in rels}
        strings: list[str] = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared_root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in shared_root.findall('m:si', NS):
                strings.append(''.join(t.text or '' for t in si.findall('.//m:t', NS)))
        result: dict[str, list[dict]] = {}
        for desc in book.findall('m:sheets/m:sheet', NS):
            name = desc.get('name')
            rid = desc.get('{' + NS['r'] + '}id')
            target = targets.get(rid)
            if not target:
                raise ValueError(f'Missing worksheet for {name}')
            path = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join('xl', target))
            if path not in z.namelist():
                raise ValueError(f'Missing worksheet XML for {name}: {path}')
            root = ET.fromstring(z.read(path))
            raw_rows: list[list[object]] = []
            for row in root.findall('m:sheetData/m:row', NS):
                mapping = {}
                for c in row.findall('m:c', NS):
                    mapping[_column_index(c.get('r', 'A1'))] = _cell_value(c, strings)
                if mapping:
                    raw_rows.append([mapping.get(i) for i in range(max(mapping) + 1)])
            if not raw_rows:
                result[name] = []
                continue
            headers = [str(h or '').strip() for h in raw_rows[0]]
            if len(set(headers)) != len(headers):
                raise ValueError(f'Duplicate header in {name}')
            records = []
            for row in raw_rows[1:]:
                if all(v is None or v == '' for v in row):
                    continue
                records.append({h: row[i] if i < len(row) else None for i, h in enumerate(headers) if h})
            result[name] = records
        return result


def load_csv_tabs(files: dict[str, str | bytes]) -> dict[str, list[dict]]:
    """CSV tab inputs: mapping tab name -> UTF-8 text or bytes."""
    result = {}
    for tab, value in files.items():
        text = value.decode('utf-8-sig') if isinstance(value, bytes) else value
        result[tab] = list(csv.DictReader(io.StringIO(text)))
    return result
