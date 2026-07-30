#!/usr/bin/env python3
"""Deterministically parse archived manager holdings files for the Data Gate."""

from __future__ import annotations

import csv
import io
import json
import math
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree


class SourceParseError(ValueError):
    pass


SOURCE_FORMATS = {
    "SPYM": "ssga-xlsx-v1",
    "QQQM": "invesco-json-v1",
    "SOXX": "ishares-csv-v1",
}
DATE_PATTERNS = (
    re.compile(
        r"(?:holdings|portfolio)\s*:?\s*as\s+of[,:]?\s*[\"']?"
        r"(\d{1,2}-[A-Za-z]{3,9}-\d{4})",
        re.I,
    ),
    re.compile(r"(?:holdings|portfolio)\s+as\s+of[,:]?\s*[\"']?([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})", re.I),
    re.compile(r"(?:holdings|portfolio)\s+as\s+of[,:]?\s*[\"']?(\d{1,2}/\d{1,2}/\d{4})", re.I),
    re.compile(r"(?:as\s+of|asofdate)[,:]?\s*[\"']?(\d{4}-\d{2}-\d{2})", re.I),
)
DATE_FORMATS = (
    "%d-%b-%Y",
    "%d-%B-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y",
    "%Y-%m-%d",
)
IDENTIFIER_COLUMNS = ("cusip", "isin", "sedol", "identifier")
PLACEHOLDER_TICKERS = {
    "",
    "-",
    "--",
    "---",
    "N/A",
    "NA",
    "NONE",
    "NULL",
    "CASH",
    "-CASH-",
}
HEADER_ALIASES = {
    "ticker": {"ticker", "symbol", "holding ticker"},
    "name": {
        "name",
        "company",
        "security name",
        "securityname",
        "holding name",
        "description",
    },
    "identifier": {"identifier", "security identifier"},
    "cusip": {"cusip"},
    "isin": {"isin"},
    "sedol": {"sedol"},
    "date": {"date", "as of date", "holding date", "holdings date"},
    "sector": {"sector", "gics sector"},
    "industry": {"industry", "gics industry"},
    "asset_class": {
        "asset class",
        "assetclass",
        "security type",
        "holding type",
        "type",
    },
    "weight": {
        "weight",
        "% weight",
        "weight (%)",
        "weight(%)",
        "portfolio weight",
        "portfolio weight (%)",
        "fund weight",
        "fund weight (%)",
        "% of fund",
        "percent of fund",
        "percentage of fund",
        "holding weight",
        "% tna",
    },
    "market_value": {"market value", "marketvalue"},
    "notional_value": {"notional value", "notionalvalue", "notional"},
}


def _fail(message: str) -> None:
    raise SourceParseError(message)


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\ufeff", "").strip().split())


def _header(value: object) -> str:
    return _clean(value).lower()


def _number(value: object, label: str) -> float:
    text = _clean(value).replace(",", "").replace("$", "").replace("%", "")
    if text in {"", "-", "—", "N/A", "n/a"}:
        return 0.0
    try:
        result = float(text)
    except ValueError as exc:
        raise SourceParseError(f"{label} is not numeric: {value!r}") from exc
    if not math.isfinite(result):
        _fail(f"{label} must be finite")
    return result


def _parse_date_value(raw: str) -> str | None:
    raw = _clean(raw)
    if re.match(r"^\d{4}-\d{2}-\d{2}(?:[T\s].*)?$", raw):
        try:
            return date.fromisoformat(raw[:10]).isoformat()
        except ValueError:
            pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def _parse_date(
    text: str,
    rows: list[list[object]],
    header_row: int,
    columns: dict[str, int],
) -> str:
    if "date" in columns:
        dates = set()
        for row_number, row in enumerate(rows[header_row + 1 :], start=header_row + 2):
            if not (_cell(row, columns, "name") or _cell(row, columns, "weight")):
                continue
            parsed = _parse_date_value(_cell(row, columns, "date"))
            if parsed is None:
                _fail(f"source row {row_number} has no recognized holdings date")
            dates.add(parsed)
        if len(dates) == 1:
            return dates.pop()
        if len(dates) > 1:
            _fail("archived source contains multiple holdings dates")
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        parsed = _parse_date_value(match.group(1))
        if parsed is not None:
            return parsed
    _fail("archived source does not contain a recognized holdings as-of date")


def _column_map(row: list[object]) -> dict[str, int]:
    result: dict[str, int] = {}
    normalized = [_header(item) for item in row]
    for logical, aliases in HEADER_ALIASES.items():
        matches = [index for index, value in enumerate(normalized) if value in aliases]
        if len(matches) > 1:
            _fail(f"holdings header has duplicate {logical} columns")
        if matches:
            result[logical] = matches[0]
    return result


def _find_table(rows: list[list[object]]) -> tuple[int, dict[str, int]]:
    for index, row in enumerate(rows):
        columns = _column_map(row)
        if (
            "name" in columns
            and "weight" in columns
            and ("ticker" in columns or any(key in columns for key in IDENTIFIER_COLUMNS))
        ):
            return index, columns
    _fail("archived source does not contain a recognized holdings header")


def _cell(row: list[object], columns: dict[str, int], key: str) -> str:
    index = columns.get(key)
    return _clean(row[index]) if index is not None and index < len(row) else ""


def _instrument(asset_class: str, ticker: str, name: str) -> str:
    value = f"{asset_class} {ticker} {name}".lower()
    if any(token in value for token in ("future", "option", "swap", "forward")):
        return "derivative"
    if any(token in value for token in ("cash collateral", "margin", "cash", "currency")):
        return "cash"
    if any(token in value for token in ("money market", "mutual fund", " etf", "fund")):
        return "fund"
    if any(token in value for token in ("equity", "stock", "common", "adr")):
        return "equity"
    if not asset_class and ticker:
        return "equity"
    return "other"


def _typed_identifier(kind: str, value: str) -> str | None:
    canonical = re.sub(r"[\s-]+", "", value).upper()
    if not canonical:
        return None
    if (kind == "isin" and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}\d", canonical)) or (
        kind == "identifier" and re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}\d", canonical)
    ):
        return f"ISIN:{canonical}"
    if (kind == "cusip" and re.fullmatch(r"[A-Z0-9*@#]{9}", canonical)) or (
        kind == "identifier" and re.fullmatch(r"[A-Z0-9*@#]{9}", canonical)
    ):
        return f"CUSIP:{canonical}"
    if (kind == "sedol" and re.fullmatch(r"[A-Z0-9]{7}", canonical)) or (
        kind == "identifier" and re.fullmatch(r"[A-Z0-9]{7}", canonical)
    ):
        return f"SEDOL:{canonical}"
    if kind == "identifier":
        manager_id = re.sub(r"[^A-Z0-9./-]+", "-", value.upper()).strip("-")
        if manager_id:
            return f"MANAGER:{manager_id}"
    return None


def _security_ids(
    row: list[object],
    columns: dict[str, int],
    row_number: int,
    instrument: str,
    name: str,
) -> tuple[str, list[str]]:
    candidates: dict[str, str] = {}
    for kind in IDENTIFIER_COLUMNS:
        value = _cell(row, columns, kind)
        if value and (typed := _typed_identifier(kind, value)) is not None:
            identifier_type = typed.split(":", 1)[0]
            previous = candidates.setdefault(identifier_type, typed)
            if previous != typed:
                _fail(
                    f"source row {row_number} has conflicting {identifier_type} identifiers"
                )
    ordered = [
        candidates[identifier_type]
        for identifier_type in ("CUSIP", "ISIN", "SEDOL", "MANAGER")
        if identifier_type in candidates
    ]
    for identifier_type in ("CUSIP", "ISIN", "SEDOL", "MANAGER"):
        if identifier_type in candidates:
            return candidates[identifier_type], ordered

    ticker = re.sub(r"\s+", "", _cell(row, columns, "ticker")).upper()
    if ticker not in PLACEHOLDER_TICKERS:
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9./-]{0,31}", ticker):
            _fail(f"source row {row_number} ticker is not a stable identifier")
        security_id = f"TICKER:{ticker}"
        return security_id, [security_id]
    if instrument == "cash":
        currency = next(
            (item for item in re.findall(r"\b[A-Z]{3}\b", name.upper()) if item in {"USD"}),
            "USD",
        )
        security_id = f"CASH:{currency}"
        return security_id, [security_id]
    _fail(f"source row {row_number} has no stable non-placeholder security identifier")


def _derive_nav(
    rows: list[list[object]], columns: dict[str, int], header_row: int
) -> float | None:
    ratios = []
    if "market_value" not in columns:
        return None
    for offset, row in enumerate(rows[header_row + 1 :], start=header_row + 2):
        if not any(_clean(item) for item in row):
            continue
        weight = _number(_cell(row, columns, "weight"), f"source row {offset} weight") / 100
        market_value = _number(
            _cell(row, columns, "market_value"), f"source row {offset} market value"
        )
        if weight > 0.0001 and market_value > 0:
            ratios.append(market_value / weight)
    if not ratios:
        return None
    ratios.sort()
    return ratios[len(ratios) // 2]


def _rows_to_holdings(
    rows: list[list[object]],
    columns: dict[str, int],
    header_row: int,
) -> list[dict]:
    holdings: list[dict] = []
    nav = _derive_nav(rows, columns, header_row)
    seen: set[str] = set()
    for offset, row in enumerate(rows[header_row + 1 :], start=header_row + 2):
        if not any(_clean(item) for item in row):
            continue
        name = _cell(row, columns, "name")
        raw_weight = _cell(row, columns, "weight")
        if not name and not raw_weight:
            continue
        ticker = _cell(row, columns, "ticker")
        asset_class = _cell(row, columns, "asset_class")
        instrument = _instrument(asset_class, ticker, name)
        security_id, source_identifiers = _security_ids(
            row, columns, offset, instrument, name
        )
        duplicate = next((item for item in source_identifiers if item in seen), None)
        if duplicate is not None:
            _fail(f"archived source has duplicate security identifier: {duplicate}")
        seen.update(source_identifiers)
        market_weight = _number(raw_weight, f"source row {offset} weight") / 100
        if instrument == "cash":
            exposure_weight = 0.0
        elif instrument == "derivative":
            if "notional_value" not in columns or nav is None or nav <= 0:
                _fail(
                    f"source row {offset} derivative lacks auditable notional value or NAV basis"
                )
            exposure_weight = abs(
                _number(
                    _cell(row, columns, "notional_value"),
                    f"source row {offset} notional value",
                )
                / nav
            )
            if exposure_weight <= 0:
                _fail(f"source row {offset} derivative has zero economic exposure")
        else:
            exposure_weight = max(market_weight, 0.0)
        holdings.append(
            {
                "security_id": security_id,
                "source_identifiers": source_identifiers,
                "raw_name": name,
                "instrument_type": instrument,
                "market_weight": market_weight,
                "exposure_weight": exposure_weight,
                "raw_sector": _cell(row, columns, "sector") or None,
                "raw_industry": _cell(row, columns, "industry") or None,
            }
        )
    if not holdings:
        _fail("archived source contains no holdings rows")
    return holdings


def _csv_rows(path: Path) -> tuple[str, list[list[str]]]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise SourceParseError(f"archived CSV is not readable UTF-8: {exc}") from exc
    return text, list(csv.reader(io.StringIO(text)))


def _invesco_json_rows(path: Path) -> tuple[str, list[list[object]]]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        payload = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceParseError(f"archived Invesco JSON is not readable: {exc}") from exc
    if not isinstance(payload, dict):
        _fail("archived Invesco JSON root must be an object")
    effective_date = _clean(payload.get("effectiveDate"))
    if _parse_date_value(effective_date) is None:
        _fail("archived Invesco JSON has no recognized effectiveDate")
    holdings = payload.get("holdings")
    if not isinstance(holdings, list) or not holdings:
        _fail("archived Invesco JSON has no holdings array")
    header = [
        "Security Identifier",
        "Ticker",
        "Company",
        "Date",
        "Security Type",
        "Sector",
        "% TNA",
        "Market Value",
        "Notional Value",
    ]
    rows: list[list[object]] = [header]
    for index, item in enumerate(holdings, start=1):
        if not isinstance(item, dict):
            _fail(f"archived Invesco holding {index} must be an object")
        raw_identifier = _clean(item.get("cusip"))
        security_type_code = _clean(item.get("securityTypeCode")).upper()
        if security_type_code not in {"COM", "ADR", "DRNY", "MMT"}:
            raw_identifier = (
                f"{raw_identifier or _clean(item.get('ticker'))}.{security_type_code}"
            )
        elif not re.fullmatch(r"[A-Z0-9*@#]{9}", raw_identifier.upper()):
            raw_identifier = ""
        rows.append(
            [
                raw_identifier,
                item.get("ticker"),
                item.get("issuerName"),
                effective_date,
                item.get("securityTypeName"),
                item.get("sectorName"),
                item.get("percentageOfTotalNetAssets"),
                item.get("marketValueBase"),
                item.get("marketValueBase"),
            ]
        )
    return text, rows


def _xlsx_rows(path: Path) -> tuple[str, list[list[object]]]:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise SourceParseError(f"archived State Street file is not a valid XLSX: {exc}") from exc
    with archive:
        names = set(archive.namelist())
        if len(names) > 1_000 or sum(item.file_size for item in archive.infolist()) > 200 * 1024 * 1024:
            _fail("archived State Street XLSX expansion exceeds safety limits")
        required = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
        if not required <= names:
            _fail("archived State Street XLSX is missing workbook metadata")
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            for item in root.findall("a:si", ns):
                shared.append("".join(node.text or "" for node in item.findall(".//a:t", ns)))
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_targets = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels
            if "Id" in rel.attrib and "Target" in rel.attrib
        }
        ns = {
            "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        }
        candidate_rows: list[list[object]] | None = None
        all_text: list[str] = []
        for sheet in workbook.findall("a:sheets/a:sheet", ns):
            rel_id = sheet.attrib.get(f"{{{ns['r']}}}id")
            target = rel_targets.get(rel_id or "")
            if not target:
                continue
            sheet_path = target.lstrip("/")
            if not sheet_path.startswith("xl/"):
                sheet_path = "xl/" + sheet_path
            if sheet_path not in names:
                continue
            root = ElementTree.fromstring(archive.read(sheet_path))
            rows: list[list[object]] = []
            for row_node in root.findall(".//a:sheetData/a:row", ns):
                row: list[object] = []
                for cell in row_node.findall("a:c", ns):
                    reference = cell.attrib.get("r", "A1")
                    letters = re.match(r"[A-Z]+", reference)
                    if not letters:
                        continue
                    column = 0
                    for char in letters.group(0):
                        column = column * 26 + ord(char) - 64
                    while len(row) < column:
                        row.append("")
                    kind = cell.attrib.get("t")
                    value_node = cell.find("a:v", ns)
                    value: object = value_node.text if value_node is not None else ""
                    if kind == "s" and str(value).isdigit():
                        index = int(str(value))
                        value = shared[index] if index < len(shared) else ""
                    elif kind == "inlineStr":
                        value = "".join(
                            node.text or "" for node in cell.findall(".//a:t", ns)
                        )
                    row[column - 1] = value
                rows.append(row)
                all_text.extend(_clean(item) for item in row)
            try:
                _find_table(rows)
            except SourceParseError:
                continue
            if candidate_rows is not None:
                _fail("archived State Street XLSX contains multiple holdings-like worksheets")
            candidate_rows = rows
        if candidate_rows is None:
            _fail("archived State Street XLSX has no recognized holdings worksheet")
        return " ".join(all_text), candidate_rows


def parse_source(ticker: str, path: Path, source_format: str) -> dict:
    expected = SOURCE_FORMATS.get(ticker)
    if source_format != expected:
        _fail(f"{ticker} source_format must be {expected}")
    if ticker == "SPYM":
        if path.suffix.lower() != ".xlsx":
            _fail("SPYM archived source must be .xlsx")
        text, rows = _xlsx_rows(path)
    elif ticker == "QQQM":
        if path.suffix.lower() != ".json":
            _fail("QQQM archived source must be .json")
        text, rows = _invesco_json_rows(path)
    else:
        if path.suffix.lower() != ".csv":
            _fail(f"{ticker} archived source must be .csv")
        text, rows = _csv_rows(path)
    header_row, columns = _find_table(rows)
    return {
        "source_as_of": _parse_date(text, rows, header_row, columns),
        "holdings": _rows_to_holdings(rows, columns, header_row),
    }
