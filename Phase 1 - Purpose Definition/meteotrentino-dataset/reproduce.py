#!/usr/bin/env python3
"""Download the archived Meteotrentino files and rebuild the study-window extracts."""

import argparse
import csv
from datetime import datetime
import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tempfile
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
CSV_COLUMNS = ("station_id", "series_code", "timestamp", "value", "quality_code")
MISSING_CODES = {151, 255}


def download(source, raw_dir):
    path = raw_dir / source["url"].rsplit("/", 1)[1]
    if not path.exists():
        request = Request(source["url"], headers={"User-Agent": "meteotrentino-trento-reproduce/1.0"})
        with tempfile.NamedTemporaryFile(dir=raw_dir, delete=False) as temp:
            temporary_path = Path(temp.name)
        try:
            with urlopen(request, timeout=60) as response, temporary_path.open("wb") as stream:
                shutil.copyfileobj(response, stream)
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)
    return path

def write_rows(stream, sources, start, end):
    import pyarrow as arrow
    import pyarrow.parquet as parquet

    time_type = arrow.timestamp("ms", tz="Etc/GMT-1")
    start = arrow.scalar(start, type=time_type)
    end = arrow.scalar(end, type=time_type)
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    count = 0
    for source, path in sources:
        table = parquet.read_table(
            path,
            columns=["time", "value", "quality"],
            filters=[("time", ">=", start), ("time", "<", end)],
        )
        for batch in table.to_batches(max_chunksize=8192):
            timestamps, values, qualities = (column.to_pylist() for column in batch.columns)
            for timestamp, value, quality in zip(timestamps, values, qualities):
                writer.writerow((
                    source["station_id"],
                    source["series_code"],
                    timestamp.isoformat(timespec="seconds"),
                    None if quality in MISSING_CODES else value,
                    quality,
                ))
        count += table.num_rows
    return count


def build_extracts(sources, manifest, output_dir):
    start = datetime.fromisoformat(manifest["study_start"])
    end = datetime.fromisoformat(manifest["study_end_exclusive"])
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = {
        "daily": [item for item in sources if item[0]["resolution"] == "daily"],
        "subdaily": [item for item in sources if item[0]["resolution"] == "subdaily"],
    }

    with tempfile.TemporaryDirectory(dir=output_dir) as staging:
        daily = Path(staging) / "daily.csv"
        subdaily = Path(staging) / "subdaily.csv.gz"
        with daily.open("w", encoding="utf-8", newline="") as stream:
            daily_count = write_rows(stream, groups["daily"], start, end)
        with subdaily.open("wb") as stream:
            with gzip.GzipFile(filename="", fileobj=stream, mode="wb", mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                    subdaily_count = write_rows(text, groups["subdaily"], start, end)
        daily.replace(output_dir / daily.name)
        subdaily.replace(output_dir / subdaily.name)

    print(f"daily.csv: {daily_count:,} rows")
    print(f"subdaily.csv.gz: {subdaily_count:,} rows")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / ".cache" / "meteotrentino")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    sources = []
    for source in manifest["files"]:
        path = download(source, args.raw_dir)
        sources.append((source, path))
        print(f"Verified {path.name}", flush=True)
        build_extracts(sources, manifest, args.output_dir)


if __name__ == "__main__":
    main()
