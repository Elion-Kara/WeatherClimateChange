# Meteotrentino station observations for Trento

This extract covers **2 January 2017 through 31 December 2025**, inclusive, in the provider's fixed local standard time (UTC+01:00). It contains two stations in the Trento area.

| Station ID | Station | Latitude | Longitude | Elevation |
| --- | --- | ---: | ---: | ---: |
| T0129 | Trento (Laste) | 46.0718 | 11.1357 | 312 m |
| T0135 | Trento (Roncafort) | 46.0956 | 11.1014 | 194 m |

## Files

| File | Contents |
| --- | --- |
| `data/daily.csv` | 19,719 rows of published daily precipitation and minimum and maximum air temperature. |
| `data/subdaily.csv.gz` | 2,522,061 rows of 5-minute precipitation totals and instantaneous air-temperature readings. The temperature sampling cadence comes from the source records. |
| `sources.json` | Station metadata, series codes, units, quality code definitions, date bounds, and the ten versioned upstream URLs with byte sizes and SHA-256 checksums. |
| `reproduce.py` | Downloads and verifies the upstream Parquet files and rebuilds the extracts. |
| `SHA256SUMS` | Checksums for the distributed extracts. |

Both CSVs use one row per station, series, and source timestamp. The columns are `station_id`, `series_code`, `timestamp`, `value`, and `quality_code`. Timestamps include the offset `+01:00` throughout the year. Rows are grouped by station and series, in source order.

| Series code | Quantity | Unit |
| --- | --- | --- |
| 10.00 | Precipitation total over the preceding five minutes | mm |
| 10.50 | Hydrological Yearbook daily precipitation total | mm |
| 400.00 | Instantaneous air temperature | °C |
| 400.55 | Hydrological Yearbook daily minimum air temperature | °C |
| 400.56 | Hydrological Yearbook daily maximum air temperature | °C |

## Reproduce the download and extracts

Run these commands from this directory with Python 3.12. The script also needs network access to the archive.

```sh
python -m pip install -r requirements.txt
python reproduce.py
sha256sum -c SHA256SUMS
```

On macOS, use `shasum -a 256 -c SHA256SUMS` for the checksum step. The script caches the ten source files under `.cache/meteotrentino/`, which the included `.gitignore` excludes. Every run verifies the input sizes and checksums before generating the data. You can use an existing cache or generate the extracts in another directory.

```sh
python reproduce.py --raw-dir path/to/cache --output-dir path/to/output
```

The original Parquet files contain the full archived time span. The CSVs are the study-period extracts. If a versioned URL is retired, an exact rebuild requires a copy of the corresponding Parquet file with the manifest's checksum.

## Timing and quality

- The `10.50` daily precipitation total covers the interval from 09:00 on the previous day to 09:00 on the date shown, in fixed local standard time. Align reporting intervals before comparing daily station and Open-Meteo totals. The earliest published total can include precipitation from 1 January 2017 because the crop uses each record's timestamp.
- Daily temperature extrema describe the provider's civil day (00:00 to 24:00 in fixed local standard time) and retain their published timestamps. For hour-of-day analysis, use the instantaneous temperature series. On 30 November 2024, the source has both 09:00 and 23:59 records in all three Laste daily series. Both are retained, so review that date before grouping by calendar day.
- The extracts preserve the source quality code on every row. Codes 151 and 255 mark missing observations and are represented by a blank `value`. A recorded zero with a suitable quality code remains zero. Codes 1–3 are the archive's valid category. The other codes identify cases such as estimated, uncertain, unvalidated, or missing values. See `sources.json` for the full definitions.
- The extracts use the archive's observation series. Missing intervals are left as gaps, and the archive's separate AI-reconstructed series are excluded.

## Attribution

Please attribute **Provincia Autonoma di Trento – Meteotrentino, Archivio Dati**. Source files were retrieved on 22 November 2026. The source data are licensed under Creative Commons Attribution 4.0. This extract selects two stations and five series, filters source timestamps to the study window, converts Parquet to CSV, and replaces the numeric placeholders for codes 151 and 255 with blank values. [Source archive](https://archivio.meteotrentino.it/share/) · [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

## Why this dataset

It lets the graph answer questions about differences within Trento. Your Open-Meteo weather export gives you one modeled series for the area. Meteotrentino adds measurements from two named locations at different elevations: Laste (312 m) and Roncafort (194 m). That gives the Trento restriction a concrete purpose.