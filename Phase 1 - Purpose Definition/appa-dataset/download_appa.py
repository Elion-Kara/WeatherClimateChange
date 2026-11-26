#!/usr/bin/env python3
"""Download APPA Trento hourly observations, retaining original responses.
API documentation: https://bollettino.appa.tn.it/aria/scarica
Run: python -m pip install requests
     python download_appa.py
"""
import csv
import hashlib
import io
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

START = date(2017, 1, 2)
END = date(2025, 12, 31)
STATIONS = '2,4'  # Parco Santa Chiara, Via Bolzano; all available pollutants
BASE = 'https://bollettino.appa.tn.it/aria/opendata/csv'
ROOT = Path('appa_trento_2017_2025')
RAW = ROOT / 'raw'
OUTPUT = ROOT / 'appa_hourly.csv'
MANIFEST = ROOT / 'manifest.csv'


def parse_csv(payload):
    try:
        text = payload.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = payload.decode('cp1252')
    if not text.strip() or text.lstrip().startswith('<'):
        raise ValueError('Empty response or HTML/XML instead of CSV')
    dialect = csv.Sniffer().sniff(text[:8192], delimiters=',;\t')
    rows = [r for r in csv.reader(io.StringIO(text), dialect) if any(c.strip() for c in r)]
    if len(rows) < 2 or len(rows[0]) < 2:
        raise ValueError('CSV missing header or data')
    if any(len(r) != len(rows[0]) for r in rows[1:]):
        raise ValueError('Inconsistent CSV row widths')
    return rows[0], rows[1:]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=Retry(
        total=5, backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods={'GET'}, respect_retry_after_header=True)))
    manifest = []
    header = None
    start = START
    temp = OUTPUT.with_suffix('.csv.tmp')
    with temp.open('w', encoding='utf-8', newline='') as out:
        writer = csv.writer(out)
        while start <= END:
            end = min(start + timedelta(days=89), END)  # inclusive: <=90 days
            url = f'{BASE}/{start},{end}/{STATIONS}'
            path = RAW / f'{start}_{end}.csv'
            if path.exists():
                payload = path.read_bytes()
                print(f'Cached: {path.name}')
            else:
                print(f'Downloading: {url}', flush=True)
                response = session.get(url, timeout=(15, 120))
                response.raise_for_status()
                payload = response.content
                parse_csv(payload)  # only cache structurally valid CSVs
                path.write_bytes(payload)
                time.sleep(1)
            current_header, rows = parse_csv(payload)
            if header is None:
                header = current_header
                writer.writerow(header)
            elif current_header != header:
                raise ValueError(f'Header changed in {path}; inspect raw files before merging')
            writer.writerows(rows)
            manifest.append([start, end, STATIONS, url, str(path.relative_to(ROOT)),
                             len(rows), hashlib.sha256(payload).hexdigest()])
            start = end + timedelta(days=1)
    temp.replace(OUTPUT)
    with MANIFEST.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['start_date', 'end_date', 'station_ids', 'source_url',
                         'raw_file', 'data_rows', 'sha256'])
        writer.writerows(manifest)
    print(f'Finished: {len(manifest)} chunks, {sum(r[5] for r in manifest):,} rows')
    print(f'Combined CSV: {OUTPUT}\nManifest: {MANIFEST}')
    print('Check actual date/station/pollutant coverage, missing values and duplicates before analysis.')


if __name__ == '__main__':
    main()
