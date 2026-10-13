"""Builds api/data/places.tsv.gz from a GeoNames dump.

    curl -LO https://download.geonames.org/export/dump/cities15000.zip && unzip cities15000.zip
    curl -LO https://download.geonames.org/export/dump/countryInfo.txt
    python scripts/build_places.py cities15000.txt countryInfo.txt

GeoNames data is licensed CC BY 4.0 (https://www.geonames.org). The output
keeps five columns: ASCII name, country code, latitude, longitude, population.
It also writes web/src/data/cities.json, the city labels of the offline basemap.
"""

from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "api" / "data"


def main(cities_path: str, countries_path: str) -> None:
    rows: list[tuple[str, str, str, str, int]] = []
    for line in Path(cities_path).read_text(encoding="utf-8").splitlines():
        cols = line.split("\t")
        name, lat, lon, country, population = cols[2], cols[4], cols[5], cols[8], int(cols[14] or 0)
        if not name or not country:
            continue
        rows.append((name, country, f"{float(lat):.4f}", f"{float(lon):.4f}", population))
    rows.sort(key=lambda r: (r[1], r[0], r[2], r[3]))

    countries: dict[str, str] = {}
    for line in Path(countries_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        countries[cols[0]] = cols[4]

    body = "".join(f"{n}\t{c}\t{la}\t{lo}\t{p}\n" for n, c, la, lo, p in rows)
    # mtime=0 keeps the archive byte-identical between runs.
    with open(OUT_DIR / "places.tsv.gz", "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as out:
        out.write(body.encode("utf-8"))
    (OUT_DIR / "countries.json").write_text(json.dumps(countries, ensure_ascii=False, sort_keys=True, indent=0) + "\n", encoding="utf-8")
    # A short list of big cities for the labels on the offline basemap: at most
    # four per country so the map is not all China and India.
    per_country: dict[str, int] = {}
    labels: list[list[object]] = []
    for name, country, lat, lon, population in sorted(rows, key=lambda r: -r[4]):
        if per_country.get(country, 0) >= 4 or population < 400_000:
            continue
        per_country[country] = per_country.get(country, 0) + 1
        labels.append([name, float(lat), float(lon), len(labels)])
        if len(labels) >= 260:
            break
    web_data = OUT_DIR.parent.parent / "web" / "src" / "data"
    web_data.mkdir(parents=True, exist_ok=True)
    (web_data / "cities.json").write_text(json.dumps(labels, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(rows)} places, {len(countries)} countries, {len(labels)} map labels")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
