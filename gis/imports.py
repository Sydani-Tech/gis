
import frappe
@frappe.whitelist(allow_guest=True)
def states():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_states.geojson'
  json_dict = read_json_as_dict(file_name)

  for state in json_dict['features']:
    geolocation = json.dumps(state)
    st = frappe.get_doc({
      'doctype': 'State',
      'state': state['properties']['statename'],
      'geolocation': geolocation
    })
    st.save()
    frappe.db.commit()
    print(state['properties']['statename'], ' -> done')
    

  # st = frappe.get_doc('State', 'Cross River')
  # print(st.geolocation)

@frappe.whitelist(allow_guest=True)
def lgas():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_lgas.geojson'
  json_dict = read_json_as_dict(file_name)

  for lga in json_dict['features']:
    geolocation = json.dumps(lga)
    lg = frappe.get_doc({
      'doctype': 'Local Government Area',
      'local_government_area': lga['properties']['lganame'],
      'state': lga['properties']['statename'],
      'geolocation': geolocation
    })
    try:
      lg.save()
      frappe.db.commit()
      print(lga['properties']['lganame'], ' -> done')
    except Exception as e:
      print(e)
    

@frappe.whitelist(allow_guest=True)
def wards():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_wards.geojson'
  json_dict = read_json_as_dict(file_name)

  for ward in json_dict['features']:
    geolocation = json.dumps(ward)
    wrd = frappe.get_doc({
      'doctype': 'Ward',
      'ward': ward['properties']['wardname'],
      'local_government_area': f"{ward['properties']['lganame']}-{ward['properties']['statename']}",
      'state': ward['properties']['statename'],
      'geolocation': geolocation
    })

    try:
      wrd.save()
      frappe.db.commit()
      print(ward['properties']['wardname'], ' -> done')
    except Exception as e:
      print(e)

@frappe.whitelist(allow_guest=True)
def facilities():
  file_dir = '/home/frappe/frappe-bench/apps/gis/gis'
  file_name = f'{file_dir}/gis_facilities.geojson'
  json_dict = read_json_as_dict(file_name)

  for facility in json_dict['features']:
    geolocation = json.dumps(facility)
    facility_address = f"{facility['properties']['prmry_name']}, {facility['properties']['wardname']} ward, {facility['properties']['lganame']} LGA, {facility['properties']['statename']} state"
    fct = frappe.get_doc({
      'doctype': 'Facility',
      'facility_name': facility['properties']['prmry_name'],
      'facility_address': facility_address,
      'ward': f"{facility['properties']['wardname']}-{facility['properties']['lganame']}-{facility['properties']['statename']}",
      'local_government_area': f"{facility['properties']['lganame']}-{facility['properties']['statename']}",
      'state': facility['properties']['statename'],
      'geolocation': geolocation,
      'country': 'Nigeria'
    })

    try:
      fct.save()
      frappe.db.commit()
      print(facility['properties']['prmry_name'], ' -> done')
    except Exception as e:
      print(e)


import io
import csv
import json
import os
import requests
import frappe

from urllib.parse import urlparse
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, make_xlsx

@frappe.whitelist()
def import_buildings_from_sheet(file_url: str = "/files/Facility upload.csv", update_if_exists: int = 0):
    """
    Import Buildings from a CSV/XLSX whose first row is the header.

    Columns expected (case-sensitive):
      building_number, building_address, street_name, describe_the_building,
      building_type, establishment_type, settlement, geolocation, status,
      project, longitude, latitude, building_picture

    Notes:
    - geolocation is already wrapped in your sheet; it is saved exactly as provided.
    - building_picture: if it's an external URL, we download and store it locally as a File,
      then set the field to the local file_url.
    - Document name is derived as "building_number - building_address". If update_if_exists=1,
      the script upserts by this name; otherwise insert-only.

    Returns:
      dict { inserted, updated, failed, failed_file_url? }
    """

    file_url = "/files/Facility upload.csv"
    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Facility upload.csv).")

    # --- load file bytes ---
    fcontent, ext = _load_file_bytes(file_url=file_url)

    # --- parse into list[dict] where keys are headers ---
    rows = _parse_rows(fcontent, ext)

    expected_cols = [
        "building_number","building_address","street_name","describe_the_building",
        "building_type","establishment_type","settlement","geolocation","status",
        "project","longitude","latitude","building_picture"
    ]
    _assert_headers(rows, expected_cols)

    failed = []
    inserted = updated = 0
    doctype = "Building"

    for row in rows:
        # keep original for failure export
        original_row = dict(row)

        # normalize blanks to None, but keep geolocation string exactly as-is
        data = {}
        for k in expected_cols:
            v = row.get(k)
            if k == "geolocation":
                data[k] = v  # save as-is
            else:
                data[k] = (v if (v not in ("", None)) else None)

        # Build docname: "building_number - building_address"
        bn = (data.get("building_number") or "").strip()
        ba = (data.get("building_address") or "").strip()
        if not bn or not ba:
            original_row["error"] = "Missing building_number or building_address (required to form name)."
            failed.append(original_row)
            continue
        docname = f"{bn} - {ba}"

        # Prepare picture if provided (external URL)
        pic_local_url = None
        if data.get("building_picture"):
            try:
                pic_local_url = _fetch_and_store_picture(data["building_picture"], docname)
            except Exception as e:
                # Non-fatal: we keep importing the row, but log error
                original_row["error"] = f"Picture import failed: {frappe.utils.cstr(e)}"

        try:
            exists = frappe.db.exists(doctype, docname)

            if exists:
                if update_if_exists:
                    # Update only fields provided (avoid wiping with None unless it’s intentional)
                    to_update = {k: v for k, v in data.items()}
                    if pic_local_url:
                        to_update["building_picture"] = pic_local_url
                    # geolocation is written as plain string (wrapped already)
                    frappe.db.set_value(doctype, docname, to_update)
                    updated += 1
                else:
                    # Treat as failure to make duplicates visible in the failures sheet
                    msg = original_row.get("error")
                    original_row["error"] = (msg + " | " if msg else "") + "Duplicate name (already exists)."
                    failed.append(original_row)
            else:
                # Insert new record
                doc = frappe.new_doc(doctype)
                # assign name explicitly to align with your naming rule
                doc.name = docname
                for k, v in data.items():
                    setattr(doc, k, v)
                if pic_local_url:
                    doc.building_picture = pic_local_url
                doc.insert(ignore_permissions=True)
                inserted += 1

        except Exception as e:
            original_row["error"] = (original_row.get("error") + " | " if original_row.get("error") else "") + frappe.utils.cstr(e)
            failed.append(original_row)

    frappe.db.commit()

    result = {"inserted": inserted, "updated": updated, "failed": len(failed)}
    if failed:
        result["failed_file_url"] = _export_failures_xlsx(failed)
    return result


# ---------------- helpers ----------------

def _load_file_bytes(file_url: str):
    """Return (bytes, ext) for a /files/... path."""
    path = get_file_path(file_url)
    with open(path, "rb") as fh:
        content = fh.read()
    ext = (file_url or "").lower().rsplit(".", 1)[-1]
    return content, ext

def _parse_rows(fcontent: bytes, ext: str):
    """Parse CSV or XLSX into list of dicts keyed by header (first row)."""
    ext = (ext or "").lower()
    if ext in ("csv", "txt"):
        sio = io.StringIO(fcontent.decode("utf-8-sig"))
        rdr = csv.DictReader(sio)
        return [dict({(k.strip() if isinstance(k, str) else k): (_strip(v) if isinstance(v, str) else v)
                      for k, v in row.items()}) for row in rdr]

    if ext in ("xlsx", "xlsm", "xls"):
        table = read_xlsx_file_from_attached_file(file_content=fcontent)
        sheet = table[0] if table else []
        if not sheet:
            return []
        headers = [str(h).strip() for h in sheet[0]]
        out = []
        for raw in sheet[1:]:
            row = {}
            for i, h in enumerate(headers):
                v = raw[i] if i < len(raw) else None
                row[h] = _strip(v) if isinstance(v, str) else v
            out.append(row)
        return out

    frappe.throw(f"Unsupported file type: .{ext}")

def _strip(s: str) -> str:
    return s.strip()

def _assert_headers(rows, expected_cols):
    if not rows:
        frappe.throw("No data rows found in the file.")
    missing = [c for c in expected_cols if c not in rows[0].keys()]
    if missing:
        frappe.throw(f"Missing columns in header: {', '.join(missing)}")

def _export_failures_xlsx(failed_rows: list) -> str:
    """Create an XLSX with the failed rows (+ error col) and attach it. Return file_url."""
    cols = []
    seen = set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)

    data = [cols]
    for r in failed_rows:
        data.append([r.get(c, "") for c in cols])

    xlsx = make_xlsx(data, "Failed Rows")
    content = xlsx.getvalue()

    fname = f"building_import_failures_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 1,
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url

def _fetch_and_store_picture(url_or_path: str, docname: str) -> str:
    """
    Download an external image and store as a Frappe File.
    Returns the resulting file_url.
    If url_or_path is already a /files/... path, just return it.
    """
    # If user already passed a local /files path, keep it
    if isinstance(url_or_path, str) and url_or_path.startswith("/files/"):
        return url_or_path

    # Basic fetch
    resp = requests.get(url_or_path, timeout=30)
    resp.raise_for_status()
    content = resp.content

    # Derive a filename
    parsed = urlparse(url_or_path)
    base = os.path.basename(parsed.path) or "building_picture"
    fname = f"{docname}_{base}"

    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)

    return fdoc.file_url





# gis/imports/fix_pictures.py

import io
import os
import re
import csv
import requests
import unicodedata
from datetime import datetime, date, timedelta
from urllib.parse import urlparse

import frappe
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, make_xlsx


# ---------------------------
# Normalization helpers
# ---------------------------

def _norm_bn(v) -> str:
    """
    Canonicalize building_number for exact matching:
    - Unicode normalize (NFKC)
    - Strip control chars; convert NBSP to space
    - Convert all unicode dashes to '-'
    - Collapse whitespace; standardize ' - ' spacing
    - If it's a pure float ending with .0 -> trim decimals (e.g., '123.0' -> '123')
    """
    if v is None:
        return ""
    s = str(v)

    # Unicode normalize
    s = unicodedata.normalize("NFKC", s)

    # Strip BOM/controls (keep tabs/newlines if present)
    s = "".join(ch for ch in s if ch == "\t" or ch == "\n" or ord(ch) >= 32)

    # NBSP -> space
    s = s.replace("\u00A0", " ")

    sv = s.strip()
    if re.fullmatch(r"\d+\.0+", sv):
        return sv.split(".", 1)[0]

    # Normalize all dash variants to ASCII '-'
    s = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    # Normalize spaces around dashes to ' - '
    s = re.sub(r"\s*-\s*", " - ", s)

    return s.strip()


def _loose_key(s: str) -> str:
    """
    Aggressive fallback key:
    - Unicode normalize
    - Uppercase
    - Remove all non A-Z/0-9
    """
    s = unicodedata.normalize("NFKC", s or "")
    s = s.upper()
    return re.sub(r"[^A-Z0-9]", "", s)


# ---------------------------
# Spreadsheet mapping loader
# ---------------------------

def _load_picture_mapping_by_bn(file_url: str) -> dict:
    """
    Load spreadsheet at /files/... and build two maps:
      {
        "exact": { normalized_building_number: building_picture_url },
        "loose": { loose_key(normalized_building_number): building_picture_url }
      }

    Requires headers: building_number, building_picture
    Supports CSV / XLSX.
    """
    if not file_url or not file_url.startswith("/files/"):
        frappe.throw("file_url must be a /files/... path (attached file).")

    path = get_file_path(file_url)
    with open(path, "rb") as fh:
        content = fh.read()

    ext = (file_url or "").lower().rsplit(".", 1)[-1]
    exact, loose = {}, {}

    def _add(bn_val, pic_val):
        bn_norm = _norm_bn(bn_val)
        pic = (str(pic_val).strip() if pic_val is not None else "")
        if bn_norm and pic:
            exact[bn_norm] = pic
            loose[_loose_key(bn_norm)] = pic

    if ext in ("csv", "txt"):
        sio = io.StringIO(content.decode("utf-8-sig"))
        rdr = csv.DictReader(sio)
        headers = [h.strip() for h in (rdr.fieldnames or [])]
        if "building_number" not in headers or "building_picture" not in headers:
            frappe.throw("Spreadsheet must include headers: building_number, building_picture")
        for row in rdr:
            _add(row.get("building_number"), row.get("building_picture"))
        return {"exact": exact, "loose": loose}

    if ext in ("xlsx", "xlsm", "xls"):
        table = read_xlsx_file_from_attached_file(file_content=content)
        sheet = table[0] if table else []
        if not sheet:
            return {"exact": {}, "loose": {}}
        headers = [str(h).strip() for h in sheet[0]]
        try:
            i_bn = headers.index("building_number")
            i_pic = headers.index("building_picture")
        except ValueError:
            frappe.throw("Spreadsheet must include headers: building_number, building_picture")
        for raw in sheet[1:]:
            bn_val = raw[i_bn] if i_bn < len(raw) else None
            pic_val = raw[i_pic] if i_pic < len(raw) else None
            _add(bn_val, pic_val)
        return {"exact": exact, "loose": loose}

    frappe.throw(f"Unsupported file type for mapping: .{ext}")


# ---------------------------
# File download & attach
# ---------------------------

def _download_to_public_file(url: str, suggested_name: str) -> str:
    """
    Download a remote file and store it as a PUBLIC File in Frappe.
    Returns the created File's file_url.
    """
    # Basic fetch (allow binary content and attachments)
    resp = requests.get(url, timeout=45)
    resp.raise_for_status()
    content = resp.content

    # Derive a filename
    parsed = urlparse(url)
    base = os.path.basename(parsed.path) or "building_picture"
    fname = f"{suggested_name}_{base}"

    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,                 # PUBLIC file
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)

    return fdoc.file_url


# ---------------------------
# Failure export
# ---------------------------

def _export_failures_xlsx(failed_rows: list) -> str:
    """Create an XLSX with the failed rows (+ error col) and attach it. Return file_url."""
    if not failed_rows:
        return ""

    cols = []
    seen = set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)

    data = [cols]
    for r in failed_rows:
        data.append([r.get(c, "") for c in cols])

    xlsx = make_xlsx(data, "Failed Rows")
    content = xlsx.getvalue()

    fname = f"fix_building_pictures_failures_{frappe.utils.now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,                 # PUBLIC for convenience
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url


# ---------------------------
# Main entry point
# ---------------------------

@frappe.whitelist()
def fix_today_building_pictures_from_excel(file_url: str = "/files/FACILITY_3 Edited.csv"):
    """
    1) Load mapping (building_number -> building_picture URL) from the provided spreadsheet.
    2) Find Buildings created TODAY whose building_picture starts with http (external).
    3) For each, match by building_number (normalized). If found:
         - download image
         - create PUBLIC File
         - set Building.building_picture = local file_url
       If not found or download fails, record failure.
    4) Commit, and return a summary (with failures_xlsx if any).
    """
    # Build the mapping from the sheet
    maps = _load_picture_mapping_by_bn(file_url)
    exact_map = maps["exact"]
    loose_map = maps["loose"]

    # Compute last 3 days window (server date)
    today = frappe.utils.getdate(frappe.utils.nowdate())
    three_days_ago = today - timedelta(days=3)
    start_ts = datetime.combine(three_days_ago, datetime.min.time())  # 00:00:00
    end_ts = datetime.combine(today, datetime.max.time())             # 23:59:59.999999

    # Fetch buildings created in last 3 days with external picture links (http/https)
    buildings = frappe.get_all(
        "Building",
        filters=[
        ["Building", "creation", ">=", start_ts],
        ["Building", "creation", "<=", end_ts],
        ["Building", "building_picture", "like", "http%"],
        ],
        fields=["name", "building_number", "building_address", "building_picture"],
        limit_page_length=100000,
    )

    updated, skipped = 0, 0
    failed = []

    for b in buildings:
        raw_bn = b.get("building_number")
        bn_norm = _norm_bn(raw_bn)

        # First try exact map, then loose fallback
        sheet_url = exact_map.get(bn_norm)
        if not sheet_url:
            sheet_url = loose_map.get(_loose_key(bn_norm))

        if not sheet_url:
            failed.append({
                "name": b["name"],
                "building_number(db)": raw_bn,
                "building_number(norm)": bn_norm,
                "building_address": b.get("building_address"),
                "existing_picture": b.get("building_picture"),
                "error": "No matching row in spreadsheet by building_number",
            })
            continue

        try:
            local_url = _download_to_public_file(sheet_url, suggested_name=b["name"])
            frappe.db.set_value("Building", b["name"], "building_picture", local_url)
            updated += 1
        except Exception as e:
            failed.append({
                "name": b["name"],
                "building_number(db)": raw_bn,
                "building_number(norm)": bn_norm,
                "building_address": b.get("building_address"),
                "sheet_picture_url": sheet_url,
                "existing_picture": b.get("building_picture"),
                "error": f"Download/attach failed: {frappe.utils.cstr(e)}",
            })

    frappe.db.commit()

    result = {
        "checked": len(buildings),
        "updated": updated,
        "skipped": skipped,
        "failed": len(failed),
    }
    if failed:
        result["failures_xlsx"] = _export_failures_xlsx(failed)

    return result






import io
import os
import csv
import json
import math
import mimetypes
import requests
import frappe

from typing import Iterable, Dict, Tuple, Optional
from urllib.parse import urlparse
from frappe.utils import now, now_datetime
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file, make_xlsx

# --- Tunables ---
BATCH_SIZE = 500                    # rows per SQL upsert batch
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB safety cap per image
DOWNLOAD_TIMEOUT = 40               # seconds total timeout per image
RETRY_COUNT = 3
RETRY_BACKOFF = 2.0                 # seconds, exponential

# Whitelist of acceptable image content-types
IMAGE_CT_OK = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/jpg"}

# ---------------- Public API ----------------

@frappe.whitelist()
def import_buildings_from_sheet_with_pictures(
    file_url: str = "/files/Building Upload.csv",
    update_if_exists: int = 1,
    batch_size: int = BATCH_SIZE
):
    """
    Stream-import Buildings from a CSV/XLSX and download 'building_picture' to local public File.
    Required columns in the sheet (case-sensitive):
      - building_number
      - building_address
      - settlement
      - geolocation
      - status
      - project
      - longitude
      - latitude
      - building_picture
      - how_many_households_occupy_this_building

    Transformations:
      - name := "building_number - building_address"
      - building_type := "Residential"
      - describe_the_building := building_address
      - street_name := building_address
      - geolocation saved exactly as provided (already wrapped in your sheet)

    Returns a dict with counts and a failure xlsx link (if any).
    """

    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Building Upload.csv).")

    # Get generator of rows (streaming, CSV or XLSX)
    row_iter, is_xlsx = _iter_rows(file_url)

    # Validate headers on the first row
    header, rows_gen = _split_header(row_iter)
    expected = [
        "building_number",
        "building_address",
        "settlement",
        "geolocation",
        "status",
        "project",
        "longitude",
        "latitude",
        "building_picture",
        "how_many_households_occupy_this_building",
    ]
    _assert_headers_present(header, expected)

    user = frappe.session.user or "Administrator"
    now_ts = now()
    failures = []
    batch = []
    wrote_count = 0

    # Prepare static SQL statements
    insert_cols = (
        "name, building_number, building_address, street_name, describe_the_building, building_type, "
        "settlement, geolocation, status, project, longitude, latitude, building_picture, "
        "how_many_households_occupy_this_building, modified, modified_by, owner, creation, docstatus, idx"
    )

    if int(update_if_exists):
        on_dup = (
            "building_number=VALUES(building_number), "
            "building_address=VALUES(building_address), "
            "street_name=VALUES(street_name), "
            "describe_the_building=VALUES(describe_the_building), "
            "building_type=VALUES(building_type), "
            "settlement=VALUES(settlement), "
            "geolocation=VALUES(geolocation), "
            "status=VALUES(status), "
            "project=VALUES(project), "
            "longitude=VALUES(longitude), "
            "latitude=VALUES(latitude), "
            "building_picture=VALUES(building_picture), "
            "how_many_households_occupy_this_building=VALUES(how_many_households_occupy_this_building), "
            "modified=VALUES(modified), "
            "modified_by=VALUES(modified_by)"
        )
    else:
        on_dup = "name=name"

    sql = f"""
        INSERT INTO `tabBuilding` ({insert_cols})
        VALUES (
            %(name)s, %(building_number)s, %(building_address)s, %(street_name)s, %(describe_the_building)s, %(building_type)s,
            %(settlement)s, %(geolocation)s, %(status)s, %(project)s, %(longitude)s, %(latitude)s, %(building_picture)s,
            %(households)s, %(modified)s, %(modified_by)s, %(owner)s, %(creation)s, %(docstatus)s, %(idx)s
        )
        ON DUPLICATE KEY UPDATE {on_dup}
    """

    # Stream rows and process one by one
    for i, row in enumerate(rows_gen, start=1):
        try:
            # Normalize -> dict with stripped keys/vals
            normalized = _normalize_row(header, row)

            bn = (normalized.get("building_number") or "").strip()
            ba = (normalized.get("building_address") or "").strip()
            if not bn or not ba:
                raise ValueError("Missing building_number or building_address")

            name = f"{bn} - {ba}"

            settlement      = _none_if_blank(normalized.get("settlement"))
            geolocation_raw = normalized.get("geolocation")  # keep exact
            status          = _none_if_blank(normalized.get("status"))
            project         = _none_if_blank(normalized.get("project"))
            longitude       = _to_float_or_none(normalized.get("longitude"))
            latitude        = _to_float_or_none(normalized.get("latitude"))
            pic_source      = _none_if_blank(normalized.get("building_picture"))
            households      = _to_int_or_none(normalized.get("how_many_households_occupy_this_building"))

            # Download picture if provided (PUBLIC)
            pic_local_url = None
            if pic_source:
                try:
                    pic_local_url = _download_and_store_public_pic(pic_source, name)
                except Exception as e:
                    # Log the failure, but continue row import
                    _append_failure(failures, normalized, f"picture_download_failed: {frappe.utils.cstr(e)}")

            # Compose insert params for this row
            params = {
                "name": name,
                "building_number": bn,
                "building_address": ba,
                "street_name": ba,                # copy from building_address
                "describe_the_building": ba,      # copy from building_address
                "building_type": "Residential",   # forced
                "settlement": settlement,
                "geolocation": geolocation_raw,
                "status": status,
                "project": project,
                "longitude": longitude,
                "latitude": latitude,
                "building_picture": pic_local_url,
                "households": households,
                "modified": now_ts,
                "modified_by": user,
                "owner": user,
                "creation": now_ts,
                "docstatus": 0,
                "idx": 0,
            }

            batch.append(params)

            if len(batch) >= int(batch_size):
                _executemany(sql, batch)
                frappe.db.commit()
                wrote_count += len(batch)
                batch.clear()

        except Exception as e:
            _append_failure(failures, row if isinstance(row, dict) else _normalize_row(header, row), frappe.utils.cstr(e))

    # Flush any remaining rows
    if batch:
        _executemany(sql, batch)
        frappe.db.commit()
        wrote_count += len(batch)
        batch.clear()

    result = {
        "written_rows": wrote_count,
        "failed": len(failures),
    }
    if failures:
        result["failed_file_url"] = _export_failures_xlsx(failures)

    return result

# ---------------- Internals ----------------

def _executemany(sql: str, params_seq):
    """Efficient executemany using the underlying DB-API cursor (PyMySQL)."""
    conn = frappe.db.get_connection()
    cur = conn.cursor()
    try:
        cur.executemany(sql, params_seq)   # supports dict-style %(key)s placeholders
        conn.commit()
    finally:
        cur.close()

def _iter_rows(file_url: str) -> Tuple[Iterable, bool]:
    """
    Returns (row_iter, is_xlsx). The iterator yields rows for CSV (list[str]) or XLSX (list).
    """
    path = get_file_path(file_url)
    ext = (file_url or "").lower().rsplit(".", 1)[-1]

    if ext in ("csv", "txt"):
        # Stream CSV with minimal memory
        # Try utf-8-sig, then fallback
        def gen():
            with open(path, "rb") as fh:
                raw = fh.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            sio = io.StringIO(text)
            rdr = csv.reader(sio)
            for row in rdr:
                yield row
        return gen(), False

    if ext in ("xlsx", "xlsm", "xls"):
        fbytes = None
        with open(path, "rb") as fh:
            fbytes = fh.read()
        table = read_xlsx_file_from_attached_file(file_content=fbytes)
        sheet = table[0] if table else []
        def gen():
            for row in sheet:
                yield row
        return gen(), True

    frappe.throw(f"Unsupported file type: .{ext}")

def _split_header(row_iter: Iterable) -> Tuple[list, Iterable]:
    it = iter(row_iter)
    try:
        header = next(it)
    except StopIteration:
        frappe.throw("File is empty.")
    # Standardize header strings
    header = [str(h).strip() for h in header]
    return header, it

def _normalize_row(header: list, row) -> Dict[str, Optional[str]]:
    out = {}
    for i, h in enumerate(header):
        val = row[i] if i < len(row) else None
        if isinstance(val, str):
            val = val.strip()
        out[h] = val
    return out

def _assert_headers_present(header: list, expected_cols: list):
    missing = [c for c in expected_cols if c not in header]
    if missing:
        frappe.throw("Missing columns in header: " + ", ".join(missing))

def _none_if_blank(v):
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def _to_float_or_none(v):
    try:
        s = str(v).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def _to_int_or_none(v):
    try:
        s = str(v).strip()
        if s == "":
            return None
        # allow "12.0" → 12
        return int(float(s))
    except Exception:
        return None

def _append_failure(failures: list, row: Dict, msg: str):
    bad = dict(row)
    bad["error"] = msg
    failures.append(bad)

def _export_failures_xlsx(failed_rows: list) -> str:
    cols = []
    seen = set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)

    data = [cols]
    for r in failed_rows:
        data.append([r.get(c, "") for c in cols])

    xlsx = make_xlsx(data, "Failed Rows")
    content = xlsx.getvalue()

    fname = f"building_import_failures_{now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 1,                 # keep failure report private
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url

# ---------------- Image download (Public) ----------------

def _download_and_store_public_pic(url: str, docname: str) -> str:
    """
    Download an external image URL and save as a PUBLIC File.
    Returns file_url (e.g., /files/xxx.jpg).
    Raises on hard failures (connectivity, size, content-type).
    """
    session = requests.Session()

    last_exc = None
    for attempt in range(1, RETRY_COUNT + 1):
        try:
            with session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as resp:
                resp.raise_for_status()

                # Check Content-Length if present
                cl = resp.headers.get("Content-Length")
                if cl is not None:
                    try:
                        if int(cl) > MAX_IMAGE_BYTES:
                            raise ValueError(f"image too large ({cl} bytes > {MAX_IMAGE_BYTES})")
                    except ValueError:
                        # If malformed length, ignore and enforce while streaming
                        pass

                # Validate content-type if present
                ctype = resp.headers.get("Content-Type", "").lower().split(";")[0].strip()
                if ctype and (ctype not in IMAGE_CT_OK):
                    # allow unknown, but if provided and non-image, reject
                    raise ValueError(f"unexpected content-type '{ctype}'")

                # Stream into memory with size cap
                buf = io.BytesIO()
                read = 0
                chunk_size = 1024 * 64
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue
                    read += len(chunk)
                    if read > MAX_IMAGE_BYTES:
                        raise ValueError(f"image exceeds max size ({read} bytes)")
                    buf.write(chunk)

                content = buf.getvalue()

            # Determine filename
            parsed = urlparse(url)
            base = os.path.basename(parsed.path) or "building_picture"
            # Add a safe prefix to help avoid name collisions
            fname = f"{_safe_slug(docname)}_{base}"

            # Derive extension if missing
            ext = os.path.splitext(fname)[1].lower()
            if not ext:
                ext = mimetypes.guess_extension(ctype or "") or ".jpg"
                fname += ext

            fdoc = frappe.get_doc({
                "doctype": "File",
                "file_name": fname,
                "content": content,
                "is_private": 0,  # PUBLIC as requested
                "folder": "Home/Attachments",
            }).insert(ignore_permissions=True)

            return fdoc.file_url

        except Exception as e:
            last_exc = e
            if attempt < RETRY_COUNT:
                frappe.db.rollback()  # ensure clean state between attempts
                frappe.utils.sleep(RETRY_BACKOFF * attempt)
            else:
                break

    raise last_exc or Exception("download failed")

def _safe_slug(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s)[:100]



import io
import os
import csv
import frappe
from typing import Iterable, Dict, Tuple, Optional
from frappe.utils import now_datetime
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

# ---------- Tunables ----------
BATCH_SIZE = 1
DEFAULT_BUILDING_ADDRESS = "Address of the residential building"

@frappe.whitelist()
def import_buildings_insert_if_new_by_response_id(
    file_url: str = "/files/BUILDING_2 edited.csv",
    batch_size: int = 1000
):
    """
    Insert-only import using response_id for existence check.

    Rules:
    - REQUIRED per row: building_number, response_id
    - If response_id already exists in tabBuilding -> skip (no update).
    - Else -> INSERT a new Building.
    - name := "<building_number> - <building_address_truncated>"
    - building_type := "Residential"
    - street_name := building_address (or default)
    - describe_the_building := building_address (or default)
    - geolocation saved as-is
    """
    DEFAULT_BUILDING_ADDRESS = "Address of the residential building"
    NAME_MAX = 140
    SEP = " - "

    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Building Upload.csv).")

    # 1) Open the sheet
    row_iter, _ = _iter_rows(file_url)
    header, rows = _split_header(row_iter)

    # 2) Require just what we need
    _assert_required_headers(header, ["building_number", "response_id"])

    # 3) Buffer rows so we can scan for response_ids once
    buffered_rows = list(rows)

    # 4) Collect response_ids from the sheet (non-empty only)
    sheet_rids = []
    for raw in buffered_rows:
        r = _normalize_row(header, raw)
        rid = (r.get("response_id") or "").strip()
        if rid:
            sheet_rids.append(rid)

    # 5) Find existing response_ids in DB (chunked query)
    existing_rid_set = set()
    if sheet_rids:
        for i in range(0, len(sheet_rids), 1000):
            chunk = sheet_rids[i:i+1000]
            placeholders = ", ".join(["%s"] * len(chunk))
            found = frappe.db.sql(
                f"SELECT response_id FROM `tabBuilding` WHERE response_id IN ({placeholders})",
                tuple(chunk),
                as_dict=True,
            )
            for row in found:
                if row.get("response_id"):
                    existing_rid_set.add(row["response_id"])

    user = frappe.session.user or "Administrator"
    now_ts = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

    # 6) Prepare INSERT SQL (no ON DUPLICATE)
    insert_cols = (
        "name, building_number, building_address, street_name, describe_the_building, building_type, "
        "settlement, geolocation, status, project, longitude, latitude, "
        "how_many_households_occupy_this_building, response_id, "
        "modified, modified_by, owner, creation, docstatus, idx"
    )
    insert_sql = f"""
        INSERT INTO `tabBuilding` ({insert_cols})
        VALUES (
            %(name)s, %(building_number)s, %(building_address)s, %(street_name)s, %(describe_the_building)s, %(building_type)s,
            %(settlement)s, %(geolocation)s, %(status)s, %(project)s, %(longitude)s, %(latitude)s,
            %(households)s, %(response_id)s,
            %(modified)s, %(modified_by)s, %(owner)s, %(creation)s, %(docstatus)s, %(idx)s
        )
    """

    failures = []
    inserts_batch = []
    inserted = 0
    skipped_existing = 0

    for raw in buffered_rows:
        try:
            r = _normalize_row(header, raw)

            bn = (r.get("building_number") or "").strip()
            rid = (r.get("response_id") or "").strip()

            if not bn or not rid:
                missing = []
                if not bn: missing.append("building_number")
                if not rid: missing.append("response_id")
                _append_failure(failures, r, "Missing required: " + ", ".join(missing))
                continue

            # Skip if this response_id already exists
            if rid in existing_rid_set:
                skipped_existing += 1
                continue

            # Optional fields
            ba_raw = (r.get("building_address") or "").strip() or DEFAULT_BUILDING_ADDRESS

            # ---- truncate building_address to fit name within 140 chars ----
            # name := "<bn> - <ba_trunc>"
            allowed_address_len = max(1, NAME_MAX - len(bn) - len(SEP))
            if len(ba_raw) > allowed_address_len:
                ba = ba_raw[:allowed_address_len]
            else:
                ba = ba_raw
            name = f"{bn}{SEP}{ba}"
            # ----------------------------------------------------------------

            settlement  = _opt_str(r.get("settlement"))
            geolocation = r.get("geolocation")  # keep as-is
            status      = _opt_str(r.get("status"))
            project     = _opt_str(r.get("project"))
            longitude   = _to_float_or_none(r.get("longitude"))
            latitude    = _to_float_or_none(r.get("latitude"))
            households  = _to_int_or_zero(r.get("how_many_households_occupy_this_building"))

            params = {
                "name": name,
                "building_number": bn,
                "building_address": ba,
                "street_name": ba,
                "describe_the_building": ba,
                "building_type": "Residential",
                "settlement": settlement,
                "geolocation": geolocation,
                "status": status,
                "project": project,
                "longitude": longitude,
                "latitude": latitude,
                "households": households,
                "response_id": rid,
                "modified": now_ts,
                "modified_by": user,
                "owner": user,
                "creation": now_ts,
                "docstatus": 0,
                "idx": 0,
            }

            inserts_batch.append(params)
            if len(inserts_batch) >= int(batch_size):
                _executemany(insert_sql, inserts_batch)
                inserted += len(inserts_batch)
                inserts_batch.clear()

        except Exception as e:
            _append_failure(failures, r if isinstance(r, dict) else {"row": raw}, frappe.utils.cstr(e))

    if inserts_batch:
        _executemany(insert_sql, inserts_batch)
        inserted += len(inserts_batch)

    out = {
        "inserted": inserted,
        "skipped_existing": skipped_existing,
        "failed": len(failures),
    }
    if failures:
        out["failed_file_url"] = _export_failures_csv(failures)
    return out


# @frappe.whitelist()
# def import_buildings_insert_if_new_by_response_id(
#     file_url: str = "/files/BUILDING_2 edited.csv",
#     batch_size: int = 1000
# ):
#     """
#     Insert-only import using response_id for existence check.

#     Rules:
#     - REQUIRED per row: building_number, response_id
#     - If response_id already exists in tabBuilding -> skip (no update).
#     - Else -> INSERT a new Building.
#     - name := "{building_number} - {building_address or default}"
#     - building_type := "Residential"
#     - street_name := building_address (or default)
#     - describe_the_building := building_address (or default)
#     - geolocation saved as-is

#     Optional columns honored if present: building_address, settlement, geolocation,
#     status, project, longitude, latitude, how_many_households_occupy_this_building.
#     """

#     DEFAULT_BUILDING_ADDRESS = "Address of the residential building"

#     if not file_url:
#         frappe.throw("Provide 'file_url' (e.g., /files/Building Upload.csv).")

#     # 1) Open the sheet
#     row_iter, _ = _iter_rows(file_url)
#     header, rows = _split_header(row_iter)

#     # 2) Require just what we need
#     _assert_required_headers(header, ["building_number", "response_id"])

#     # 3) Buffer rows so we can scan for response_ids once
#     buffered_rows = list(rows)

#     # 4) Collect response_ids from the sheet (non-empty only)
#     sheet_rids = []
#     for raw in buffered_rows:
#         r = _normalize_row(header, raw)
#         rid = (r.get("response_id") or "").strip()
#         if rid:
#             sheet_rids.append(rid)

#     # 5) Find existing response_ids in DB (chunked query)
#     existing_rid_set = set()
#     if sheet_rids:
#         for i in range(0, len(sheet_rids), 1000):
#             chunk = sheet_rids[i:i+1000]
#             placeholders = ", ".join(["%s"] * len(chunk))
#             found = frappe.db.sql(
#                 f"SELECT response_id FROM `tabBuilding` WHERE response_id IN ({placeholders})",
#                 tuple(chunk),
#                 as_dict=True,
#             )
#             for row in found:
#                 if row.get("response_id"):
#                     existing_rid_set.add(row["response_id"])

#     user = frappe.session.user or "Administrator"
#     now_ts = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")

#     # 6) Prepare INSERT SQL (no ON DUPLICATE)
#     insert_cols = (
#         "name, building_number, building_address, street_name, describe_the_building, building_type, "
#         "settlement, geolocation, status, project, longitude, latitude, "
#         "how_many_households_occupy_this_building, response_id, "
#         "modified, modified_by, owner, creation, docstatus, idx"
#     )
#     insert_sql = f"""
#         INSERT INTO `tabBuilding` ({insert_cols})
#         VALUES (
#             %(name)s, %(building_number)s, %(building_address)s, %(street_name)s, %(describe_the_building)s, %(building_type)s,
#             %(settlement)s, %(geolocation)s, %(status)s, %(project)s, %(longitude)s, %(latitude)s,
#             %(households)s, %(response_id)s,
#             %(modified)s, %(modified_by)s, %(owner)s, %(creation)s, %(docstatus)s, %(idx)s
#         )
#     """

#     failures = []
#     inserts_batch = []
#     inserted = 0
#     skipped_existing = 0

#     # 7) Walk the rows and insert only when response_id is new
#     for raw in buffered_rows:
#         try:
#             r = _normalize_row(header, raw)

#             bn = (r.get("building_number") or "").strip()
#             rid = (r.get("response_id") or "").strip()

#             if not bn or not rid:
#                 missing = []
#                 if not bn: missing.append("building_number")
#                 if not rid: missing.append("response_id")
#                 _append_failure(failures, r, "Missing required: " + ", ".join(missing))
#                 continue

#             # Skip if this response_id already exists
#             if rid in existing_rid_set:
#                 skipped_existing += 1
#                 continue

#             # Optional fields
#             ba = (r.get("building_address") or "").strip() or DEFAULT_BUILDING_ADDRESS
#             settlement  = _opt_str(r.get("settlement"))
#             geolocation = r.get("geolocation")  # keep as-is
#             status      = _opt_str(r.get("status"))
#             project     = _opt_str(r.get("project"))
#             longitude   = _to_float_or_none(r.get("longitude"))
#             latitude    = _to_float_or_none(r.get("latitude"))
#             households  = _to_int_or_zero(r.get("how_many_households_occupy_this_building"))

#             name = f"{bn} - {ba}"

#             params = {
#                 "name": name,
#                 "building_number": bn,
#                 "building_address": ba,
#                 "street_name": ba,
#                 "describe_the_building": ba,
#                 "building_type": "Residential",
#                 "settlement": settlement,
#                 "geolocation": geolocation,
#                 "status": status,
#                 "project": project,
#                 "longitude": longitude,
#                 "latitude": latitude,
#                 "households": households,
#                 "response_id": rid,
#                 "modified": now_ts,
#                 "modified_by": user,
#                 "owner": user,
#                 "creation": now_ts,
#                 "docstatus": 0,
#                 "idx": 0,
#             }

#             inserts_batch.append(params)
#             if len(inserts_batch) >= int(batch_size):
#                 _executemany(insert_sql, inserts_batch)
#                 inserted += len(inserts_batch)
#                 inserts_batch.clear()

#         except Exception as e:
#             _append_failure(failures, r if isinstance(r, dict) else {"row": raw}, frappe.utils.cstr(e))

#     # Final flush
#     if inserts_batch:
#         _executemany(insert_sql, inserts_batch)
#         inserted += len(inserts_batch)

#     out = {
#         "inserted": inserted,
#         "skipped_existing": skipped_existing,
#         "failed": len(failures),
#     }
#     if failures:
#         out["failed_file_url"] = _export_failures_csv(failures)
#     return out




# ---------- Public API ----------

@frappe.whitelist()
def import_buildings_fast_no_pictures(
    # file_url: str = "/files/Building Upload.csv",
    file_url: str = "/BUILDING_2 edited.csv",
    update_if_exists: int = 0,
    batch_size: int = BATCH_SIZE,
):
    """
    Efficiently import Buildings from CSV/XLSX.

    Input columns (case-sensitive), with `building_address` optional:
      - building_number                (required per row)
      - building_address               (optional; default applied if missing/blank)
      - settlement
      - geolocation
      - status
      - project
      - longitude
      - latitude
      - how_many_households_occupy_this_building
      - response_id

    Transformations per row:
      - name := "{building_number} - {building_address or default}"
      - building_type := "Residential"
      - street_name := building_address (or default)
      - describe_the_building := building_address (or default)
      - geolocation saved as-is

    Upsert behavior:
      - update_if_exists=1 → update all imported fields (incl. response_id)
      - update_if_exists=0 → no-op on duplicates
    """

    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Building Upload.csv).")

    row_iter, _ = _iter_rows(file_url)
    header, rows = _split_header(row_iter)

    # Only enforce that the header has at least the key fields we rely on.
    # Other columns can be absent in header; they'll just stay None.
    header_min_required = ["building_number"]
    _assert_required_headers(header, header_min_required)

    user = frappe.session.user or "Administrator"
    now_ts = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
    failures = []
    batch = []
    wrote = 0

    insert_cols = (
        "name, building_number, building_address, street_name, describe_the_building, building_type, "
        "settlement, geolocation, status, project, longitude, latitude, "
        "how_many_households_occupy_this_building, response_id, "
        "modified, modified_by, owner, creation, docstatus, idx"
    )

    if int(update_if_exists):
        on_dup = (
            "building_number=VALUES(building_number), "
            "building_address=VALUES(building_address), "
            "street_name=VALUES(street_name), "
            "describe_the_building=VALUES(describe_the_building), "
            "building_type=VALUES(building_type), "
            "settlement=VALUES(settlement), "
            "geolocation=VALUES(geolocation), "
            "status=VALUES(status), "
            "project=VALUES(project), "
            "longitude=VALUES(longitude), "
            "latitude=VALUES(latitude), "
            "how_many_households_occupy_this_building=VALUES(how_many_households_occupy_this_building), "
            "response_id=VALUES(response_id), "
            "modified=VALUES(modified), "
            "modified_by=VALUES(modified_by)"
        )
    else:
        on_dup = "name=name"

    sql = f"""
        INSERT INTO `tabBuilding` ({insert_cols})
        VALUES (
            %(name)s, %(building_number)s, %(building_address)s, %(street_name)s, %(describe_the_building)s, %(building_type)s,
            %(settlement)s, %(geolocation)s, %(status)s, %(project)s, %(longitude)s, %(latitude)s,
            %(households)s, %(response_id)s,
            %(modified)s, %(modified_by)s, %(owner)s, %(creation)s, %(docstatus)s, %(idx)s
        )
        ON DUPLICATE KEY UPDATE {on_dup}
    """

    # Per-row required values (if any of these are missing/blank, skip and export to CSV)
    row_required = ["building_number"]

    for i, raw in enumerate(rows, start=1):
        try:
            r = _normalize_row(header, raw)

            # Validate required row fields
            missing_vals = [fld for fld in row_required if not _has_value(r.get(fld))]
            if missing_vals:
                _append_failure(failures, r, f"Missing required fields: {', '.join(missing_vals)}")
                continue

            bn = _req_str(r.get("building_number"))
            ba = _opt_str(r.get("building_address")) or DEFAULT_BUILDING_ADDRESS

            name = f"{bn} - {ba}"

            settlement  = _opt_str(r.get("settlement"))
            geolocation = r.get("geolocation")  # keep as-is
            status      = _opt_str(r.get("status"))
            project     = _opt_str(r.get("project"))
            longitude   = _to_float_or_none(r.get("longitude"))
            latitude    = _to_float_or_none(r.get("latitude"))
            response_id = _opt_str(r.get("response_id"))

            # Default households to 0 if unavailable/blank
            households_raw = r.get("how_many_households_occupy_this_building")
            households = _to_int_or_zero(households_raw)

            params = {
                "name": name,
                "building_number": bn,
                "building_address": ba,
                "street_name": ba,
                "describe_the_building": ba,
                "building_type": "Residential",
                "settlement": settlement,
                "geolocation": geolocation,
                "status": status,
                "project": project,
                "longitude": longitude,
                "latitude": latitude,
                "households": households,
                "response_id": response_id,
                "modified": now_ts,
                "modified_by": user,
                "owner": user,
                "creation": now_ts,
                "docstatus": 0,
                "idx": 0,
            }

            batch.append(params)
            if len(batch) >= int(batch_size):
                _executemany(sql, batch)
                wrote += len(batch)
                batch.clear()

        except Exception as e:
            _append_failure(failures, r if isinstance(r, dict) else {"row": raw}, frappe.utils.cstr(e))

    if batch:
        _executemany(sql, batch)
        wrote += len(batch)

    out = {"written_rows": wrote, "failed": len(failures)}
    if failures:
        out["failed_file_url"] = _export_failures_csv(failures)
    return out

# ---------- DB helpers ----------

def _executemany(sql: str, params_seq):
    conn = frappe.db.get_connection()
    cur = conn.cursor()
    try:
        cur.executemany(sql, params_seq)  # dict params supported
        conn.commit()
    finally:
        cur.close()

# ---------- File / parsing helpers ----------

def _iter_rows(file_url: str) -> Tuple[Iterable, bool]:
    path = get_file_path(file_url)
    ext = (file_url or "").lower().rsplit(".", 1)[-1]

    if ext in ("csv", "txt"):
        def gen():
            with open(path, "rb") as fh:
                raw = fh.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            sio = io.StringIO(text)
            rdr = csv.reader(sio)
            for row in rdr:
                yield row
        return gen(), False

    if ext in ("xlsx", "xlsm", "xls"):
        with open(path, "rb") as fh:
            fbytes = fh.read()
        table = read_xlsx_file_from_attached_file(file_content=fbytes)
        sheet = table[0] if table else []
        def gen():
            for row in sheet:
                yield row
        return gen(), True

    frappe.throw(f"Unsupported file type: .{ext}")

def _split_header(row_iter: Iterable) -> Tuple[list, Iterable]:
    it = iter(row_iter)
    try:
        header = next(it)
    except StopIteration:
        frappe.throw("File is empty.")
    header = [str(h).strip() for h in header]
    return header, it

def _normalize_row(header: list, row) -> Dict[str, Optional[str]]:
    out = {}
    for i, h in enumerate(header):
        val = row[i] if i < len(row) else None
        if isinstance(val, str):
            val = val.strip()
        out[h] = val
    return out

def _assert_required_headers(header: list, expected_cols: list):
    missing = [c for c in expected_cols if c not in header]
    if missing:
        frappe.throw("Missing columns in header: " + ", ".join(missing))

# ---------- Value helpers ----------

def _has_value(v) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and v.strip() == "":
        return False
    return True

def _opt_str(v) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def _req_str(v) -> str:
    s = _opt_str(v)
    return s or ""

def _to_float_or_none(v):
    try:
        s = str(v).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def _to_int_or_zero(v):
    """
    Coerce to int; if missing/blank/unparseable -> 0.
    """
    try:
        if v is None:
            return 0
        s = str(v).strip()
        if s == "":
            return 0
        return int(float(s))
    except Exception:
        return 0

# ---------- Failures export (CSV, public) ----------

def _append_failure(failures: list, row: Dict, msg: str):
    bad = dict(row) if isinstance(row, dict) else {"row": row}
    bad["error"] = msg
    failures.append(bad)

def _export_failures_csv(failed_rows: list) -> str:
    # Build column union (preserve order by first occurrence)
    cols = []
    seen = set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)

    # Ensure 'error' is last for readability
    if "error" in cols:
        cols.remove("error")
    cols.append("error")

    # Create CSV in-memory
    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in failed_rows:
        writer.writerow({c: r.get(c, "") for c in cols})
    content = sio.getvalue()

    fname = f"building_import_failures_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,           # public as requested
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url



import io
import os
import csv
import mimetypes
import requests
import frappe

from typing import Iterable, Dict, Tuple, Optional
from urllib.parse import urlparse
from frappe.utils import now_datetime
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

# ---------- Tunables ----------
DOWNLOAD_TIMEOUT = 40               # seconds
RETRY_COUNT = 3
RETRY_BACKOFF = 2.0                 # seconds (exponential)
MAX_IMAGE_BYTES = 25 * 1024 * 1024  # 25 MB
IMAGE_CT_OK = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/jpg"}
BATCH_COMMIT = 200                  # commit after this many building updates

# ---------- Public API ----------

@frappe.whitelist()
def import_building_pictures_from_sheet_by_response_id_targeted(
    # file_url: str = "/files/Building Upload.csv",
    file_url: str = "/files/BUILDING_2 edited.csv",
):
    """
    Per spreadsheet row:
      1) Take response_id and building_picture (URL) from the sheet.
      2) Find exactly ONE Building where:
           - response_id = sheet.response_id
           - creation >= NOW() - 3 days
           - building_picture is empty OR http/https (external)
      3) Download the image and save as PUBLIC File; update the Building's building_picture.

    Returns:
      dict { rows_from_sheet, updated, skipped, failed, failed_file_url? }
    """
    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Building Upload.csv).")

    # Load the sheet and build response_id -> picture map
    header, iter_rows = _open_sheet(file_url)
    if "response_id" not in header:
        frappe.throw("The spreadsheet must contain a 'response_id' column.")
    if "building_picture" not in header:
        frappe.throw("The spreadsheet must contain a 'building_picture' column.")

    rid_idx = header.index("response_id")
    pic_idx = header.index("building_picture")

    # Build a compact dict; last non-empty picture per response_id wins
    rid_to_pic: Dict[str, str] = {}
    total_rows = 0
    for row in iter_rows:
        total_rows += 1
        rid = _safe_cell(row, rid_idx)
        if not rid:
            continue
        pic = _safe_cell(row, pic_idx)
        if pic:
            rid_to_pic[rid] = pic

    updated = 0
    skipped = 0
    failed_rows = []
    to_commit = 0
    user = frappe.session.user or "Administrator"

    # Prepared statements
    select_sql = """
        SELECT name, building_picture
          FROM `tabBuilding`
         WHERE response_id = %s
           AND creation >= DATE_SUB(NOW(), INTERVAL 3 DAY)
           AND (COALESCE(building_picture, '') = '' OR building_picture LIKE 'http%%')
         LIMIT 1
    """

    update_sql = """
        UPDATE `tabBuilding`
           SET building_picture = %s,
               modified = NOW(),
               modified_by = %s
         WHERE name = %s
    """

    for rid, sheet_pic in rid_to_pic.items():
        # 1) Look up the single matching Building by response_id (with filters)
        try:
            rec = frappe.db.sql(select_sql, (rid,), as_dict=True)
        except Exception as e:
            _fail(failed_rows, {"response_id": rid, "sheet_picture": sheet_pic},
                  f"select_failed: {frappe.utils.cstr(e)}")
            continue

        if not rec:
            # No candidate found that needs updating; skip
            skipped += 1
            continue

        row = rec[0]
        name = row["name"]
        current_pic = (row.get("building_picture") or "").strip()

        # 2) Download and store as PUBLIC File
        try:
            local_url = _download_and_store_public_pic(sheet_pic, name)
        except Exception as e:
            _fail(failed_rows, {"name": name, "response_id": rid, "sheet_picture": sheet_pic},
                  f"download_failed: {frappe.utils.cstr(e)}")
            skipped += 1
            continue

        # 3) Update the Building
        try:
            frappe.db.sql(update_sql, (local_url, user, name))
            updated += 1
            to_commit += 1
            if to_commit >= BATCH_COMMIT:
                frappe.db.commit()
                to_commit = 0
        except Exception as e:
            _fail(failed_rows, {"name": name, "response_id": rid, "sheet_picture": sheet_pic},
                  f"update_failed: {frappe.utils.cstr(e)}")

    # Final commit
    frappe.db.commit()

    out = {
        "rows_from_sheet": total_rows,
        "updated": updated,
        "skipped": skipped,
        "failed": len(failed_rows),
    }
    if failed_rows:
        out["failed_file_url"] = _export_failures_csv(failed_rows)
    return out

# ---------- Sheet helpers ----------

def _open_sheet(file_url: str) -> Tuple[list, Iterable[list]]:
    """Open CSV/XLSX, return (header, iterator over rows)."""
    path = get_file_path(file_url)
    ext = (file_url or "").lower().rsplit(".", 1)[-1]

    if ext in ("csv", "txt"):
        with open(path, "rb") as fh:
            raw = fh.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        sio = io.StringIO(text)
        rdr = csv.reader(sio)
        rows = list(rdr)
        if not rows:
            frappe.throw("File is empty.")
        header = [str(h).strip() for h in rows[0]]
        return header, (r for r in rows[1:])

    if ext in ("xlsx", "xlsm", "xls"):
        with open(path, "rb") as fh:
            fbytes = fh.read()
        table = read_xlsx_file_from_attached_file(file_content=fbytes)
        sheet = table[0] if table else []
        if not sheet:
            frappe.throw("File is empty.")
        header = [str(h).strip() for h in sheet[0]]
        return header, (r for r in sheet[1:])

    frappe.throw(f"Unsupported file type: .{ext}")

def _safe_cell(row, idx) -> Optional[str]:
    if idx >= len(row):
        return None
    v = row[idx]
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

# ---------- Image download + File insert (PUBLIC) ----------

def _download_and_store_public_pic(url: str, docname: str) -> str:
    """
    Download external image and save as PUBLIC File.
    Returns file_url (/files/..). Raises on failure.
    """
    session = requests.Session()
    last_exc = None

    for attempt in range(1, RETRY_COUNT + 1):
        try:
            with session.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as resp:
                resp.raise_for_status()

                # Content-Length guard (if present)
                cl = resp.headers.get("Content-Length")
                if cl:
                    try:
                        if int(cl) > MAX_IMAGE_BYTES:
                            raise ValueError(f"image too large ({cl} bytes > {MAX_IMAGE_BYTES})")
                    except ValueError:
                        pass

                # Content-Type check
                ctype = resp.headers.get("Content-Type", "").lower().split(";")[0].strip()
                if ctype and (ctype not in IMAGE_CT_OK):
                    raise ValueError(f"unexpected content-type '{ctype}'")

                # Stream with max size guard
                buf = io.BytesIO()
                read = 0
                for chunk in resp.iter_content(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    read += len(chunk)
                    if read > MAX_IMAGE_BYTES:
                        raise ValueError(f"image exceeds max size ({read} bytes)")
                    buf.write(chunk)
                content = buf.getvalue()

            # Filename
            parsed = urlparse(url)
            base = os.path.basename(parsed.path) or "building_picture"
            fname = f"{_safe_slug(docname)}_{base}"

            # Ensure extension
            ext = os.path.splitext(fname)[1].lower()
            if not ext:
                ext = mimetypes.guess_extension(ctype or "") or ".jpg"
                fname += ext

            fdoc = frappe.get_doc({
                "doctype": "File",
                "file_name": fname,
                "content": content,
                "is_private": 0,     # PUBLIC
                "folder": "Home/Attachments",
            }).insert(ignore_permissions=True)

            return fdoc.file_url

        except Exception as e:
            last_exc = e
            if attempt < RETRY_COUNT:
                frappe.db.rollback()
                frappe.utils.sleep(RETRY_BACKOFF * attempt)
            else:
                break

    raise last_exc or Exception("download failed")

def _safe_slug(s: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in s)[:100]

# ---------- Failures export (CSV, public) ----------

def _fail(failed_rows: list, row: Dict, msg: str):
    r = dict(row) if isinstance(row, dict) else {"row": row}
    r["error"] = msg
    failed_rows.append(r)

def _export_failures_csv(failed_rows: list) -> str:
    # Collect columns
    cols = []
    seen = set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                cols.append(k)
    # Place error last
    if "error" in cols:
        cols.remove("error")
    cols.append("error")

    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in failed_rows:
        w.writerow({c: r.get(c, "") for c in cols})
    content = sio.getvalue()

    fname = f"building_picture_failures_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,  # public
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url

import frappe

@frappe.whitelist()
def fix_submitted_settlements_in_lgas(
    lgas="Kontagora-Niger",
    ward_limit=None,
    dry_run: int = 0,
    batch_commit: int = 200
):
    """
    For the given LGAs (default: Katcha-Niger, Rafi-Niger, Mariga-Niger, Kontagora-Niger):
      1) Find settlements with status='Submitted'.
      2) For each submitted S_sub, look for an Approved settlement S_ok where S_ok.name CONTAINS S_sub.name (full-name containment).
      3) Print the mapping (submitted -> approved).
      4) Update Buildings:
           - If Building.settlement == submitted.name  -> set to approved.name and sync ward/LGA/state/country.
           - If Building.settlement == approved.name   -> just sync ward/LGA/state/country (safety).
      Uses Frappe APIs (no raw SQL).
    
    Args:
      lgas: list[str] or comma-separated string of LGAs. Default:
            ["Katcha-Niger", "Rafi-Niger", "Mariga-Niger", "Kontagora-Niger"]
      ward_limit: optional ward name; if provided, only settlements in this ward are considered.
      dry_run: 1 = don’t write changes, only print what would happen.
      batch_commit: commit every N building updates.
    """
    # Defaults
    if not lgas:
        lgas = ["Katcha-Niger", "Rafi-Niger", "Mariga-Niger", "Kontagora-Niger"]
    elif isinstance(lgas, str):
        # allow comma-separated
        lgas = [x.strip() for x in lgas.split(",") if x.strip()]

    # 1) Get all Submitted settlements in LGAs (optionally filtered by ward)
    sub_filters = {
        "status": "Submitted",
        "local_government_area": ["in", lgas],
    }
    if ward_limit:
        sub_filters["ward"] = ward_limit

    submitted_settlements = frappe.get_all(
        "Settlement",
        filters=sub_filters,
        fields=["name", "ward", "local_government_area", "state", "country"]
    )

    if not submitted_settlements:
        return {
            "message": "No submitted settlements found for given filters.",
            "lgas": lgas,
            "ward_limit": ward_limit
        }

    # 2) For each submitted, find an Approved containing-name match in the same LGA set
    #    (You asked to check those LGAs; we keep the search within these.)
    mappings = []  # list of dicts: {submitted:..., approved: {... fields ...}}
    for sub in submitted_settlements:
        # Find approved settlements where approved_name CONTAINS submitted_name (full-name containment)
        approved = frappe.get_all(
            "Settlement",
            filters={
                "status": "Approved",
                "local_government_area": ["in", lgas],
                "name": ["like", f"%{sub['name']}%"],
            },
            fields=["name", "ward", "local_government_area", "state", "country"]
        )
        if not approved:
            continue

        # Prefer the longest approved name (more specific)
        approved.sort(key=lambda r: len(r["name"]), reverse=True)
        best = approved[0]
        mappings.append({
            "submitted": sub["name"],
            "approved": best  # dict with name/ward/lga/state/country
        })

    if not mappings:
        return {
            "message": "No submitted→approved containment matches found.",
            "lgas": lgas,
            "ward_limit": ward_limit
        }

    # 3) Print mappings (they’ll also appear in the return payload)
    for m in mappings:
        frappe.logger().info(f"[Settlement map] Submitted: {m['submitted']}  ->  Approved: {m['approved']['name']}")

    # 4) Update Buildings using Frappe APIs
    updated_from_submitted = 0
    synced_on_approved = 0
    processed_buildings = 0
    to_commit = 0

    def sync_building_fields(bname: str, srow: dict):
        """Use frappe.db.set_value to sync ward/LGA/state/country."""
        nonlocal to_commit
        frappe.db.set_value("Building", bname, {
            "ward": srow["ward"],
            "local_government_area": srow["local_government_area"],
            "state": srow["state"],
            "country": srow["country"],
        })
        to_commit += 1

    def maybe_commit():
        nonlocal to_commit
        if to_commit >= batch_commit:
            frappe.db.commit()
            to_commit = 0

    if int(dry_run):
        # Only report what would be done
        return {
            "dry_run": True,
            "lgas": lgas,
            "ward_limit": ward_limit,
            "mappings_count": len(mappings),
            "mappings": mappings,
            "updated_from_submitted": 0,
            "synced_on_approved": 0,
        }

    for m in mappings:
        sub_name = m["submitted"]
        ok = m["approved"]
        ok_name = ok["name"]

        # a) Buildings where settlement == submitted -> set to approved + sync fields
        b_sub = frappe.get_all(
            "Building",
            filters={
                "status": "Approved",
                "settlement": sub_name
            },
            fields=["name"]
        )
        for b in b_sub:
            # set settlement to approved
            frappe.db.set_value("Building", b["name"], "settlement", ok_name)
            # sync region info
            sync_building_fields(b["name"], ok)
            updated_from_submitted += 1
            processed_buildings += 1
            maybe_commit()

        # b) Buildings where settlement == approved -> just ensure region fields are synced
        b_ok = frappe.get_all(
            "Building",
            filters={
                "status": "Approved",
                "settlement": ok_name
            },
            fields=["name"]
        )
        for b in b_ok:
            sync_building_fields(b["name"], ok)
            synced_on_approved += 1
            processed_buildings += 1
            maybe_commit()

    # final commit
    frappe.db.commit()

    return {
        "lgas": lgas,
        "ward_limit": ward_limit,
        "mappings_count": len(mappings),
        "mappings": mappings,
        "updated_from_submitted": updated_from_submitted,
        "synced_on_approved": synced_on_approved,
        "processed_buildings": processed_buildings
    }


import io, os, csv, uuid, re
import frappe
from typing import Iterable, Dict, Tuple, Optional
from frappe.utils import now_datetime
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

# ---------------- Tunables ----------------
BATCH_SIZE = 5000
HOUSEHOLD_DOCTYPE = "Household"
BUILDING_DOCTYPE  = "Building"
FAILURES_FILE_PREFIX = "household_import_failures_sql"

# ---------------- Entry Point ----------------
@frappe.whitelist()
def import_households_fast_by_response_id(
    file_url: str = "/files/Household Upload2.csv",
    total_limit: int = 0  # 0 = no limit; set 5 to test a few rows
):
    """
    Ultra-fast upsert of Households using SQL for both UPDATE and INSERT.

    Match key: response_id (unique per household).
      - If response_id exists -> batched UPDATE.
      - Else -> batched INSERT with random UUID 'name' (bypassing Frappe autoname).

    Constants:
      project = "STRICAN - Phase 2"
      status  = "Approved"
      do_you_take_your_childchildren_to_the_facility_for_ri_services = "Yes"
      if_others_specify = "Others"

    Building link:
      building := Building.name where Building.response_id == comment_to_supervisor

    Also fetch from the linked Building and set on Household:
      settlement, ward, local_government_area, state, country
    """
    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Household Upload2.csv).")

    # --- Load sheet ---
    row_iter, _ = _iter_rows(file_url)
    header, rows = _split_header(row_iter)
    _assert_required_headers(header, ["response_id"])
    idx = _Index(header)

    failures = []
    user = frappe.session.user or "Administrator"
    now_ts = now_datetime().strftime("%Y-%m-%d %H:%M:%S")

    # Buffer rows (so we can scan twice)
    buffered_rows = list(rows)
    if total_limit and total_limit > 0:
        buffered_rows = buffered_rows[:total_limit]

    # --- Collect response_ids from sheet for existence check (Household) ---
    sheet_rids = [ _cell(r, idx.response_id) for r in buffered_rows if _cell(r, idx.response_id) ]
    existing_map = {}
    if sheet_rids:
        for i in range(0, len(sheet_rids), 1000):
            chunk = sheet_rids[i:i+1000]
            placeholders = ", ".join(["%s"] * len(chunk))
            res = frappe.db.sql(
                f"SELECT name, response_id FROM `tab{HOUSEHOLD_DOCTYPE}` WHERE response_id IN ({placeholders})",
                tuple(chunk), as_dict=True
            )
            for r in res:
                existing_map[r["response_id"]] = r["name"]

    # --- Preload Building map by Building.response_id (used from comment_to_supervisor)
    #     We need: name, settlement, ward, local_government_area, state, country
    build_lookup_ids = { _cell(r, idx.comment_to_supervisor) for r in buffered_rows if _cell(r, idx.comment_to_supervisor) }
    building_map: Dict[str, Dict[str, Optional[str]]]= {}
    if build_lookup_ids:
        build_lookup_ids = list(build_lookup_ids)
        for i in range(0, len(build_lookup_ids), 1000):
            chunk = build_lookup_ids[i:i+1000]
            placeholders = ", ".join(["%s"] * len(chunk))
            res = frappe.db.sql(
                f"""
                SELECT
                    name, response_id, settlement, ward, local_government_area, state, country
                FROM `tab{BUILDING_DOCTYPE}`
                WHERE response_id IN ({placeholders})
                """,
                tuple(chunk), as_dict=True
            )
            for r in res:
                building_map[r["response_id"]] = {
                    "name": r["name"],
                    "settlement": r.get("settlement"),
                    "ward": r.get("ward"),
                    "local_government_area": r.get("local_government_area"),
                    "state": r.get("state"),
                    "country": r.get("country"),
                }

    # --- SQL statements ---
    update_sql = """
        UPDATE `tabHousehold`
           SET name_of_household_head = %(name_of_household_head)s,
               gender_of_household_head = %(gender_of_household_head)s,
               date_of_birth_of_household_head = %(date_of_birth_of_household_head)s,
               phone_number = %(phone_number)s,
               educational_level_of_household_head = %(educational_level_of_household_head)s,
               is_the_household_head_employed = %(is_the_household_head_employed)s,
               industry_of_employment = %(industry_of_employment)s,
               average_monthly_income = %(average_monthly_income)s,
               is_the_household_residing_in_a_rented_apartment = %(is_the_household_residing_in_a_rented_apartment)s,
               are_there_any_pregnant_women_in_the_household = %(are_there_any_pregnant_women_in_the_household)s,
               how_many_pregnant_women_are_there = %(how_many_pregnant_women_are_there)s,
               how_many_household_members_are_above_18 = %(how_many_household_members_are_above_18)s,
               how_many_household_members_are_below_5 = %(how_many_household_members_are_below_5)s,
               how_many_people_live_in_the_household = %(how_many_people_live_in_the_household)s,
               how_many_household_members_are_between_9_and_14_years = %(how_many_household_members_are_between_9_and_14_years)s,
               most_common_illness_within_the_last_year = %(most_common_illness_within_the_last_year)s,
               do_you_take_your_childchildren_to_the_facility_for_ri_services = %(do_you_take_your_childchildren_to_the_facility_for_ri_services)s,
               building = %(building)s,
               project = %(project)s,
               status = %(status)s,
               comment_to_supervisor = %(comment_to_supervisor)s,
               settlement = %(settlement)s,
               ward = %(ward)s,
               local_government_area = %(local_government_area)s,
               state = %(state)s,
               country = %(country)s,
               if_others_specify = %(if_others_specify)s,
               modified = %(modified)s,
               modified_by = %(modified_by)s
         WHERE name = %(name)s
    """

    insert_cols = (
        "name, owner, creation, modified, modified_by, docstatus, idx, "
        "response_id, name_of_household_head, gender_of_household_head, "
        "date_of_birth_of_household_head, phone_number, educational_level_of_household_head, "
        "is_the_household_head_employed, industry_of_employment, average_monthly_income, "
        "is_the_household_residing_in_a_rented_apartment, are_there_any_pregnant_women_in_the_household, "
        "how_many_pregnant_women_are_there, how_many_household_members_are_above_18, "
        "how_many_household_members_are_below_5, how_many_people_live_in_the_household, "
        "how_many_household_members_are_between_9_and_14_years, "
        "most_common_illness_within_the_last_year, "
        "do_you_take_your_childchildren_to_the_facility_for_ri_services, "
        "building, project, status, comment_to_supervisor, "
        "settlement, ward, local_government_area, state, country, if_others_specify"
    )
    insert_sql = f"""
        INSERT INTO `tabHousehold` ({insert_cols})
        VALUES (
            %(name)s, %(owner)s, %(creation)s, %(modified)s, %(modified_by)s, %(docstatus)s, %(idx)s,
            %(response_id)s, %(name_of_household_head)s, %(gender_of_household_head)s,
            %(date_of_birth_of_household_head)s, %(phone_number)s, %(educational_level_of_household_head)s,
            %(is_the_household_head_employed)s, %(industry_of_employment)s, %(average_monthly_income)s,
            %(is_the_household_residing_in_a_rented_apartment)s, %(are_there_any_pregnant_women_in_the_household)s,
            %(how_many_pregnant_women_are_there)s, %(how_many_household_members_are_above_18)s,
            %(how_many_household_members_are_below_5)s, %(how_many_people_live_in_the_household)s,
            %(how_many_household_members_are_between_9_and_14_years)s,
            %(most_common_illness_within_the_last_year)s,
            %(do_you_take_your_childchildren_to_the_facility_for_ri_services)s,
            %(building)s, %(project)s, %(status)s, %(comment_to_supervisor)s,
            %(settlement)s, %(ward)s, %(local_government_area)s, %(state)s, %(country)s, %(if_others_specify)s
        )
    """

    updates_batch, inserts_batch = [], []
    written = 0

    for raw in buffered_rows:
        try:
            rid = _cell(raw, idx.response_id)
            if not rid:
                _append_failure(failures, _row_to_dict(header, raw), "Missing required: response_id")
                continue

            cts = _cell(raw, idx.comment_to_supervisor)
            binfo = building_map.get(cts) if cts else None
            building_name = binfo["name"] if binfo else None

            # Pull settlement lineage from Building (if available)
            sett   = binfo["settlement"] if binfo else None
            ward   = binfo["ward"] if binfo else None
            lga    = binfo["local_government_area"] if binfo else None
            state  = binfo["state"] if binfo else None
            country= binfo["country"] if binfo else None

            params = {
                "response_id": rid,
                "name_of_household_head": _cell(raw, idx.name_of_household_head),
                "gender_of_household_head": _cell(raw, idx.gender_of_household_head),
                "date_of_birth_of_household_head": _to_date_str(_cell(raw, idx.date_of_birth_of_household_head)),
                "phone_number": _cell(raw, idx.phone_number),
                "educational_level_of_household_head": _cell(raw, idx.educational_level_of_household_head),
                "is_the_household_head_employed": _cell(raw, idx.is_the_household_head_employed),
                "industry_of_employment": _cell(raw, idx.industry_of_employment),
                "average_monthly_income": _normalize_income_select(_cell(raw, idx.average_monthly_income)),
                "is_the_household_residing_in_a_rented_apartment": _cell(raw, idx.is_the_household_residing_in_a_rented_apartment),
                "are_there_any_pregnant_women_in_the_household": _cell(raw, idx.are_there_any_pregnant_women_in_the_household),
                "how_many_pregnant_women_are_there": _to_int_or_none(_cell(raw, idx.how_many_pregnant_women_are_there)),
                "how_many_household_members_are_above_18": _to_int_or_none(_cell(raw, idx.how_many_household_members_are_above_18)),
                "how_many_household_members_are_below_5": _to_int_or_none(_cell(raw, idx.how_many_household_members_are_below_5)),
                "how_many_people_live_in_the_household": _to_int_or_none(_cell(raw, idx.how_many_people_live_in_the_household)),
                "how_many_household_members_are_between_9_and_14_years": _to_int_or_none(_cell(raw, idx.how_many_household_members_are_between_9_and_14_years)),
                "most_common_illness_within_the_last_year": _cell(raw, idx.most_common_illness_within_the_last_year),
                # constants / derived
                "do_you_take_your_childchildren_to_the_facility_for_ri_services": "Yes",
                "if_others_specify": "Others",
                "building": building_name,
                "project": "STRICAN - Phase 2",
                "status": "Approved",
                "comment_to_supervisor": cts,
                "settlement": sett,
                "ward": ward,
                "local_government_area": lga,
                "state": state,
                "country": country,
                "modified": now_ts,
                "modified_by": user,
            }

            existing_name = existing_map.get(rid)
            if existing_name:
                p = dict(params); p["name"] = existing_name
                updates_batch.append(p)
            else:
                p = dict(params)
                p.update({
                    "name": str(uuid.uuid4()),
                    "owner": user,
                    "creation": now_ts,
                    "docstatus": 0,
                    "idx": 0,
                })
                inserts_batch.append(p)

            # Flush in batches
            if len(updates_batch) >= BATCH_SIZE:
                _executemany(update_sql, updates_batch); written += len(updates_batch); updates_batch.clear()
            if len(inserts_batch) >= BATCH_SIZE:
                _executemany(insert_sql, inserts_batch); written += len(inserts_batch); inserts_batch.clear()

        except Exception as e:
            _append_failure(failures, _row_to_dict(header, raw), frappe.utils.cstr(e))

    # Final flush
    if updates_batch:
        _executemany(update_sql, updates_batch); written += len(updates_batch)
    if inserts_batch:
        _executemany(insert_sql, inserts_batch); written += len(inserts_batch)

    frappe.db.commit()

    out = {"written_rows": written, "failed": len(failures)}
    if failures:
        out["failed_file_url"] = _export_failures_csv(failures, FAILURES_FILE_PREFIX)
    return out

# ---------------- Header index helper ----------------
class _Index:
    def __init__(self, header: list):
        def find(col):
            try: return header.index(col)
            except ValueError: return -1
        self.response_id = find("response_id")
        self.name_of_household_head = find("name_of_household_head")
        self.gender_of_household_head = find("gender_of_household_head")
        self.date_of_birth_of_household_head = find("date_of_birth_of_household_head")
        self.phone_number = find("phone_number")
        self.educational_level_of_household_head = find("educational_level_of_household_head")
        self.is_the_household_head_employed = find("is_the_household_head_employed")
        self.industry_of_employment = find("industry_of_employment")
        self.average_monthly_income = find("average_monthly_income")
        self.is_the_household_residing_in_a_rented_apartment = find("is_the_household_residing_in_a_rented_apartment")
        self.are_there_any_pregnant_women_in_the_household = find("are_there_any_pregnant_women_in_the_household")
        self.how_many_pregnant_women_are_there = find("how_many_pregnant_women_are_there")
        self.how_many_household_members_are_above_18 = find("how_many_household_members_are_above_18")
        self.how_many_household_members_are_below_5 = find("how_many_household_members_are_below_5")
        self.how_many_people_live_in_the_household = find("how_many_people_live_in_the_household")
        self.how_many_household_members_are_between_9_and_14_years = find("how_many_household_members_are_between_9_and_14_years")
        self.most_common_illness_within_the_last_year = find("most_common_illness_within_the_last_year")
        self.comment_to_supervisor = find("comment_to_supervisor")

# ---------------- DB helper ----------------
def _executemany(sql: str, params_seq):
    conn = frappe.db.get_connection()
    cur = conn.cursor()
    try:
        cur.executemany(sql, params_seq)
        conn.commit()
    finally:
        cur.close()

# ---------------- File / parsing helpers ----------------
def _iter_rows(file_url: str) -> Tuple[Iterable, bool]:
    path = get_file_path(file_url)
    ext = (file_url or "").lower().rsplit(".", 1)[-1]
    if ext in ("csv", "txt"):
        def gen():
            with open(path, "rb") as fh:
                raw = fh.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            sio = io.StringIO(text)
            rdr = csv.reader(sio)
            for row in rdr:
                yield row
        return gen(), False
    if ext in ("xlsx", "xlsm", "xls"):
        with open(path, "rb") as fh:
            fbytes = fh.read()
        table = read_xlsx_file_from_attached_file(file_content=fbytes)
        sheet = table[0] if table else []
        def gen():
            for row in sheet:
                yield row
        return gen(), True
    frappe.throw(f"Unsupported file type: .{ext}")

def _split_header(row_iter: Iterable) -> Tuple[list, Iterable]:
    it = iter(row_iter)
    try:
        header = next(it)
    except StopIteration:
        frappe.throw("File is empty.")
    header = [str(h).strip() for h in header]
    return header, it

def _row_to_dict(header: list, row) -> Dict[str, Optional[str]]:
    out = {}
    for i, h in enumerate(header):
        val = row[i] if i < len(row) else None
        if isinstance(val, str): val = val.strip()
        out[h] = val
    return out

def _assert_required_headers(header: list, expected_cols: list):
    missing = [c for c in expected_cols if c not in header]
    if missing:
        frappe.throw("Missing columns in header: " + ", ".join(missing))

# ---------------- Value helpers ----------------
def _cell(row, idx) -> Optional[str]:
    if idx < 0 or idx >= len(row): return None
    v = row[idx]
    if v is None: return None
    s = str(v).strip()
    return s if s else None

def _to_int_or_none(v):
    try:
        if v is None: return None
        s = str(v).strip()
        if s == "": return None
        return int(float(s))
    except Exception:
        return None

def _to_date_str(v: Optional[str]) -> Optional[str]:
    if not v: return None
    s = str(v).strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    for sep in ("/", "-"):
        parts = s.split(sep)
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            a, b, y = parts
            if len(y) == 4:
                try:
                    da = int(a); db = int(b); yy = int(y)
                    if da > 12:  # dd/mm/yyyy
                        return f"{yy:04d}-{db:02d}-{da:02d}"
                    return f"{yy:04d}-{da:02d}-{db:02d}"  # mm/dd/yyyy
                except Exception:
                    break
            if len(a) == 4:
                try:
                    yy = int(a); mm = int(b); dd = int(y)
                    return f"{yy:04d}-{mm:02d}-{dd:02d}"
                except Exception:
                    break
    return None

# ---------------- Failures export (CSV, public) ----------------
def _append_failure(failures: list, row: Dict, msg: str):
    bad = dict(row) if isinstance(row, dict) else {"row": row}
    bad["error"] = msg
    failures.append(bad)

def _export_failures_csv(failed_rows: list, prefix: str) -> str:
    cols, seen = [], set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k); cols.append(k)
    if "error" in cols:
        cols.remove("error")
    cols.append("error")

    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in failed_rows:
        writer.writerow({c: r.get(c, "") for c in cols})
    content = sio.getvalue()

    fname = f"{prefix}_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url

# ---------------- Income select helpers ----------------
def _fix_naira(s: str) -> str:
    if s is None: return ""
    s = str(s)
    s = s.replace("â‚¦", "₦").replace("NGN", "₦").replace("ngn", "₦")
    s = re.sub(r"\s+", " ", s.strip())
    return s

def _get_income_options() -> list:
    df = frappe.get_meta("Household").get_field("average_monthly_income")
    if not df or not getattr(df, "options", ""):
        return []
    return [opt.strip() for opt in df.options.split("\n") if opt.strip()]

def _normalize_income_select(raw_val: str) -> str:
    if raw_val is None: return ""
    s = _fix_naira(raw_val)
    options = _get_income_options()
    if not options:
        return s
    if s in options:
        return s

    def canon(x: str) -> str:
        x = _fix_naira(x)
        x = x.replace("₦", "")
        x = re.sub(r"\s+", "", x)
        return x

    cs = canon(s)
    for opt in options:
        if canon(opt) == cs:
            return opt

    s_num = re.sub(r"[^\d<>-]+", "", s)
    for opt in options:
        if re.sub(r"[^\d<>-]+", "", opt) == s_num:
            return opt
    return ""




# import io
# import os
# import csv
# import re
# import frappe
# from typing import Iterable, Dict, Tuple, Optional
# from frappe.utils import now_datetime
# from frappe.utils.file_manager import get_file_path
# from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

# # --------------- Tunables ---------------
# BATCH_COMMIT = 100
# CHILD_DOCTYPE = "Children"
# HOUSEHOLD_DOCTYPE = "Household"
# FAILURES_FILE_PREFIX = "children_import_failures"

# # --------------- Entry Point ---------------
# @frappe.whitelist()
# def import_children_via_orm(
#     file_url: str = "/files/Children Upload.csv",
#     total_limit: int =  0 # 0 = no limit; set small number to test
# ):
#     """
#     Import/Upsert Children via ORM so that hooks run.

#     Sheet columns used (case-sensitive):
#       - first_name
#       - last_name
#       - full_name
#       - gender
#       - date_of_birth
#       - does_the_child_have_a_vaccination_card
#       - response_id (REQUIRED; used to find existing Children)
#       - comment_to_supervisor (used to locate Household by response_id)
#       - last_vaccine_administered (text; if present add one row to child table with field 'vaccine')

#     Derived/Constants:
#       - project = "STRICAN - Phase 2"
#       - status  = "Approved"
#       - household := Household.name where Household.response_id == comment_to_supervisor

#     Behavior:
#       - If Children with same response_id exists -> update via ORM.
#       - Else -> insert via ORM.
#       - Commit every BATCH_COMMIT records.
#     """
#     if not file_url:
#         frappe.throw("Provide 'file_url' (e.g., /files/Children Upload.csv).")

#     # Load & prepare iteration
#     row_iter, _ = _iter_rows(file_url)
#     header, rows = _split_header(row_iter)
#     _assert_required_headers(header, ["response_id"])
#     idx = _Index(header)

#     failures = []
#     written = 0
#     committed_since = 0

#     # Buffer rows for pre-queries and optional limit
#     buffered_rows = list(rows)
#     if total_limit and total_limit > 0:
#         buffered_rows = buffered_rows[:total_limit]

#     # ---- Preload Household map (comment_to_supervisor -> Household.name) ----
#     # Collect unique comment_to_supervisor values (these are Household.response_id)
#     cts_values = { _cell(r, idx.comment_to_supervisor) for r in buffered_rows if _cell(r, idx.comment_to_supervisor) }
#     household_map: Dict[str, Optional[str]] = {}
#     if cts_values:
#         cts_list = list(cts_values)
#         for i in range(0, len(cts_list), 1000):
#             chunk = cts_list[i:i+1000]
#             placeholders = ", ".join(["%s"] * len(chunk))
#             res = frappe.db.sql(
#                 f"""
#                 SELECT name, response_id
#                   FROM `tab{HOUSEHOLD_DOCTYPE}`
#                  WHERE response_id IN ({placeholders})
#                 """,
#                 tuple(chunk),
#                 as_dict=True
#             )
#             for r in res:
#                 household_map[r["response_id"]] = r["name"]

#     # ---- Preload existing Children by response_id -> name ----
#     sheet_rids = [ _cell(r, idx.response_id) for r in buffered_rows if _cell(r, idx.response_id) ]
#     existing_by_rid: Dict[str, str] = {}
#     if sheet_rids:
#         for i in range(0, len(sheet_rids), 1000):
#             chunk = sheet_rids[i:i+1000]
#             placeholders = ", ".join(["%s"] * len(chunk))
#             res = frappe.db.sql(
#                 f"""
#                 SELECT name, response_id
#                   FROM `tab{CHILD_DOCTYPE}`
#                  WHERE response_id IN ({placeholders})
#                 """,
#                 tuple(chunk),
#                 as_dict=True
#             )
#             for r in res:
#                 existing_by_rid[r["response_id"]] = r["name"]

#     # -------- Process rows via ORM (hooks run) --------
#     for raw in buffered_rows:
#         try:
#             rid = _cell(raw, idx.response_id)
#             if not rid:
#                 _append_failure(failures, _row_to_dict(header, raw), "Missing required: response_id")
#                 continue

#             first_name  = _cell(raw, idx.first_name)
#             last_name   = _cell(raw, idx.last_name)
#             full_name   = _cell(raw, idx.full_name) or _build_full_name(first_name, last_name)
#             gender      = _cell(raw, idx.gender)
#             dob         = _to_date_str(_cell(raw, idx.date_of_birth))
#             has_card    = _cell(raw, idx.does_the_child_have_a_vaccination_card)
#             cts         = _cell(raw, idx.comment_to_supervisor)
#             household   = household_map.get(cts) if cts else None

#             # NEW: read the sheet value for child table
#             last_vax_txt = _cell(raw, idx.last_vaccine_administered)

#             existing_name = existing_by_rid.get(rid)

#             if existing_name:
#                 # Update existing via ORM
#                 doc = frappe.get_doc(CHILD_DOCTYPE, existing_name)
#                 doc.update({
#                     "first_name": first_name,
#                     "last_name": last_name,
#                     "full_name": full_name,
#                     "gender": gender,
#                     "date_of_birth": dob,
#                     "does_the_child_have_a_vaccination_card": has_card,
#                     "comment_to_supervisor": cts,
#                     "household": household,
#                     "project": "STRICAN - Phase 2",
#                     "status": "Approved",
#                 })

#                 # Append one child row if text provided AND not already present (avoid duplicates)
#                 if last_vax_txt:
#                     exists_same = any(
#                         (getattr(rw, "vaccine", "") or "").strip().lower() == last_vax_txt.strip().lower()
#                         for rw in (doc.last_vaccine_administered or [])
#                     )
#                     if not exists_same:
#                         doc.append("last_vaccine_administered", {"vaccine": last_vax_txt})

#                 doc.save(ignore_permissions=True)
#                 written += 1

#             else:
#                 # Insert new via ORM
#                 doc = frappe.new_doc(CHILD_DOCTYPE)
#                 doc.update({
#                     "response_id": rid,
#                     "first_name": first_name,
#                     "last_name": last_name,
#                     "full_name": full_name,
#                     "gender": gender,
#                     "date_of_birth": dob,
#                     "does_the_child_have_a_vaccination_card": has_card,
#                     "comment_to_supervisor": cts,
#                     "household": household,
#                     "project": "STRICAN - Phase 2",
#                     "status": "Approved",
#                 })

#                 if last_vax_txt:
#                     doc.append("last_vaccine_administered", {"vaccine": last_vax_txt})

#                 doc.insert(ignore_permissions=True)
#                 written += 1
#                 existing_by_rid[rid] = doc.name

#             committed_since += 1
#             if committed_since >= BATCH_COMMIT:
#                 frappe.db.commit()
#                 committed_since = 0

#         except Exception as e:
#             _append_failure(failures, _row_to_dict(header, raw), frappe.utils.cstr(e))

#     frappe.db.commit()

#     out = {"written_rows": written, "failed": len(failures)}
#     if failures:
#         out["failed_file_url"] = _export_failures_csv(failures, FAILURES_FILE_PREFIX)
#     return out

# # --------------- Header index helper ---------------
# class _Index:
#     def __init__(self, header: list):
#         def find(col):
#             try: return header.index(col)
#             except ValueError: return -1

#         self.first_name = find("first_name")
#         self.last_name  = find("last_name")
#         self.full_name  = find("full_name")
#         self.gender     = find("gender")
#         self.date_of_birth = find("date_of_birth")
#         self.does_the_child_have_a_vaccination_card = find("does_the_child_have_a_vaccination_card")
#         self.response_id = find("response_id")
#         self.comment_to_supervisor = find("comment_to_supervisor")
#         # NEW:
#         self.last_vaccine_administered = find("last_vaccine_administered")

# # --------------- File / parsing helpers ---------------
# def _iter_rows(file_url: str) -> Tuple[Iterable, bool]:
#     path = get_file_path(file_url)
#     ext = (file_url or "").lower().rsplit(".", 1)[-1]

#     if ext in ("csv", "txt"):
#         def gen():
#             with open(path, "rb") as fh:
#                 raw = fh.read()
#             try:
#                 text = raw.decode("utf-8-sig")
#             except UnicodeDecodeError:
#                 text = raw.decode("latin-1")
#             sio = io.StringIO(text)
#             rdr = csv.reader(sio)
#             for row in rdr:
#                 yield row
#         return gen(), False

#     if ext in ("xlsx", "xlsm", "xls"):
#         with open(path, "rb") as fh:
#             fbytes = fh.read()
#         table = read_xlsx_file_from_attached_file(file_content=fbytes)
#         sheet = table[0] if table else []
#         def gen():
#             for row in sheet:
#                 yield row
#         return gen(), True

#     frappe.throw(f"Unsupported file type: .{ext}")

# def _split_header(row_iter: Iterable) -> Tuple[list, Iterable]:
#     it = iter(row_iter)
#     try:
#         header = next(it)
#     except StopIteration:
#         frappe.throw("File is empty.")
#     header = [str(h).strip() for h in header]
#     return header, it

# def _row_to_dict(header: list, row) -> Dict[str, Optional[str]]:
#     out = {}
#     for i, h in enumerate(header):
#         val = row[i] if i < len(row) else None
#         if isinstance(val, str): val = val.strip()
#         out[h] = val
#     return out

# def _assert_required_headers(header: list, expected_cols: list):
#     missing = [c for c in expected_cols if c not in header]
#     if missing:
#         frappe.throw("Missing columns in header: " + ", ".join(missing))

# # --------------- Value helpers ---------------
# def _cell(row, idx) -> Optional[str]:
#     if idx < 0 or idx >= len(row):
#         return None
#     v = row[idx]
#     if v is None:
#         return None
#     s = str(v).strip()
#     return s if s else None

# def _build_full_name(first_name: Optional[str], last_name: Optional[str]) -> Optional[str]:
#     f = (first_name or "").strip()
#     l = (last_name or "").strip()
#     if f and l:
#         return f"{f} {l}"
#     return f or l or None

# def _to_date_str(v: Optional[str]) -> Optional[str]:
#     """
#     Normalizes to YYYY-MM-DD when possible. Accepts:
#       - already ISO yyyy-mm-dd
#       - dd/mm/yyyy, mm/dd/yyyy, dd-mm-yyyy, mm-dd-yyyy, yyyy-mm-dd, yyyy/mm/dd
#     If year is 2-digit (e.g. '01-05-91'), this helper will NOT guess the century.
#     Provide '1991-05-01' in your sheet if you need it imported.
#     """
#     if not v:
#         return None
#     s = str(v).strip()
#     # already ISO yyyy-mm-dd
#     if len(s) == 10 and s[4] == "-" and s[7] == "-":
#         return s
#     # dd/mm/yyyy or mm/dd/yyyy or dd-mm-yyyy or mm-dd-yyyy
#     for sep in ("/", "-"):
#         parts = s.split(sep)
#         if len(parts) == 3 and all(p.isdigit() for p in parts):
#             a, b, y = parts
#             # yyyy-mm-dd or yyyy/mm/dd
#             if len(a) == 4:
#                 try:
#                     yy = int(a); mm = int(b); dd = int(y)
#                     return f"{yy:04d}-{mm:02d}-{dd:02d}"
#                 except Exception:
#                     break
#             # dd/mm/yyyy or mm/dd/yyyy
#             if len(y) == 4:
#                 try:
#                     da = int(a); db = int(b); yy = int(y)
#                     if da > 12:
#                         return f"{yy:04d}-{db:02d}-{da:02d}"  # dd/mm/yyyy
#                     return f"{yy:04d}-{da:02d}-{db:02d}"     # mm/dd/yyyy
#                 except Exception:
#                     break
#     return None

# # --------------- Failures export (CSV, public) ---------------
# def _append_failure(failures: list, row: Dict, msg: str):
#     bad = dict(row) if isinstance(row, dict) else {"row": row}
#     bad["error"] = msg
#     failures.append(bad)

# def _export_failures_csv(failed_rows: list, prefix: str) -> str:
#     # collect union of columns (keep first-seen order)
#     cols, seen = [], set()
#     for r in failed_rows:
#         for k in r.keys():
#             if k not in seen:
#                 seen.add(k); cols.append(k)
#     if "error" in cols:
#         cols.remove("error")
#     cols.append("error")

#     sio = io.StringIO()
#     writer = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
#     writer.writeheader()
#     for r in failed_rows:
#         writer.writerow({c: r.get(c, "") for c in cols})
#     content = sio.getvalue()

#     fname = f"{prefix}_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
#     fdoc = frappe.get_doc({
#         "doctype": "File",
#         "file_name": fname,
#         "content": content,
#         "is_private": 0,
#         "folder": "Home/Attachments",
#     }).insert(ignore_permissions=True)
#     return fdoc.file_url


import io
import os
import csv
import re
import frappe
from typing import Iterable, Dict, Tuple, Optional
from frappe.utils import now_datetime
from frappe.utils.file_manager import get_file_path
from frappe.utils.xlsxutils import read_xlsx_file_from_attached_file

# --------------- Tunables ---------------
BATCH_COMMIT = 100
CHILD_DOCTYPE = "Children"
HOUSEHOLD_DOCTYPE = "Household"
FAILURES_FILE_PREFIX = "children_import_failures"

# --------------- Entry Point ---------------
@frappe.whitelist()
def import_children_via_orm(
    file_url: str = "/files/Children Upload.csv",
    total_limit: int = 0  # 0 = no limit; set small number to test
):
    """
    Import/Upsert Children via ORM so that hooks run.

    Sheet columns used (case-sensitive):
      - first_name
      - last_name
      - full_name (ignored for value; we compute from sanitized first/last)
      - gender
      - date_of_birth
      - does_the_child_have_a_vaccination_card
      - response_id (REQUIRED; used to find existing Children)
      - comment_to_supervisor (used to locate Household by response_id)
      - last_vaccine_administered (text; if present add one row to child table with field 'vaccine')

    Derived/Constants:
      - project = "STRICAN - Phase 2"
      - status  = "Approved"
      - household := Household.name where Household.response_id == comment_to_supervisor

    Behavior:
      - If Children with same response_id exists -> update via ORM.
      - Else -> insert via ORM.
      - Commit every BATCH_COMMIT records.
    """
    if not file_url:
        frappe.throw("Provide 'file_url' (e.g., /files/Children Upload.csv).")

    # Load & prepare iteration
    row_iter, _ = _iter_rows(file_url)
    header, rows = _split_header(row_iter)
    _assert_required_headers(header, ["response_id"])
    idx = _Index(header)

    failures = []
    written = 0
    committed_since = 0

    # Buffer rows for pre-queries and optional limit
    buffered_rows = list(rows)
    if total_limit and total_limit > 0:
        buffered_rows = buffered_rows[:total_limit]

    # ---- Preload Household map (comment_to_supervisor -> Household.name) ----
    cts_values = { _cell(r, idx.comment_to_supervisor) for r in buffered_rows if _cell(r, idx.comment_to_supervisor) }
    household_map: Dict[str, Optional[str]] = {}
    if cts_values:
        cts_list = list(cts_values)
        for i in range(0, len(cts_list), 1000):
            chunk = cts_list[i:i+1000]
            placeholders = ", ".join(["%s"] * len(chunk))
            res = frappe.db.sql(
                f"""
                SELECT name, response_id
                  FROM `tab{HOUSEHOLD_DOCTYPE}`
                 WHERE response_id IN ({placeholders})
                """,
                tuple(chunk),
                as_dict=True
            )
            for r in res:
                household_map[r["response_id"]] = r["name"]

    # ---- Preload existing Children by response_id -> name ----
    sheet_rids = [ _cell(r, idx.response_id) for r in buffered_rows if _cell(r, idx.response_id) ]
    existing_by_rid: Dict[str, str] = {}
    if sheet_rids:
        for i in range(0, len(sheet_rids), 1000):
            chunk = sheet_rids[i:i+1000]
            placeholders = ", ".join(["%s"] * len(chunk))
            res = frappe.db.sql(
                f"""
                SELECT name, response_id
                  FROM `tab{CHILD_DOCTYPE}`
                 WHERE response_id IN ({placeholders})
                """,
                tuple(chunk),
                as_dict=True
            )
            for r in res:
                existing_by_rid[r["response_id"]] = r["name"]

    # -------- Process rows via ORM (hooks run) --------
    for raw in buffered_rows:
        try:
            rid = _cell(raw, idx.response_id)
            if not rid:
                _append_failure(failures, _row_to_dict(header, raw), "Missing required: response_id")
                continue

            # Read from sheet
            first_name_raw = _cell(raw, idx.first_name)
            last_name_raw  = _cell(raw, idx.last_name)
            gender         = _cell(raw, idx.gender)
            dob            = _to_date_str(_cell(raw, idx.date_of_birth))
            has_card       = _cell(raw, idx.does_the_child_have_a_vaccination_card)
            cts            = _cell(raw, idx.comment_to_supervisor)
            household      = household_map.get(cts) if cts else None
            last_vax_txt   = _cell(raw, idx.last_vaccine_administered)

            # --- SANITIZE NAMES ---
            s_first = _sanitize_name(first_name_raw)
            s_last  = _sanitize_name(last_name_raw)
            s_full  = _build_full_name_sanitized(s_first, s_last)  # "first last", trimmed, single spaces

            existing_name = existing_by_rid.get(rid)

            if existing_name:
                # Update existing via ORM
                doc = frappe.get_doc(CHILD_DOCTYPE, existing_name)
                doc.update({
                    "first_name": s_first,
                    "last_name": s_last,
                    "full_name": s_full,
                    "gender": gender,
                    "date_of_birth": dob,
                    "does_the_child_have_a_vaccination_card": has_card,
                    "comment_to_supervisor": cts,
                    "household": household,
                    "project": "STRICAN - Phase 2",
                    "status": "Approved",
                })

                # Append one child row if text provided AND not already present (avoid duplicates)
                if last_vax_txt:
                    exists_same = any(
                        (getattr(rw, "vaccine", "") or "").strip().lower() == last_vax_txt.strip().lower()
                        for rw in (doc.last_vaccine_administered or [])
                    )
                    if not exists_same:
                        doc.append("last_vaccine_administered", {"vaccine": last_vax_txt})

                doc.save(ignore_permissions=True)
                written += 1

            else:
                # Insert new via ORM
                doc = frappe.new_doc(CHILD_DOCTYPE)
                doc.update({
                    "response_id": rid,
                    "first_name": s_first,
                    "last_name": s_last,
                    "full_name": s_full,
                    "gender": gender,
                    "date_of_birth": dob,
                    "does_the_child_have_a_vaccination_card": has_card,
                    "comment_to_supervisor": cts,
                    "household": household,
                    "project": "STRICAN - Phase 2",
                    "status": "Approved",
                })
                if last_vax_txt:
                    doc.append("last_vaccine_administered", {"vaccine": last_vax_txt})

                doc.insert(ignore_permissions=True)
                written += 1
                existing_by_rid[rid] = doc.name

            committed_since += 1
            if committed_since >= BATCH_COMMIT:
                frappe.db.commit()
                committed_since = 0

        except Exception as e:
            _append_failure(failures, _row_to_dict(header, raw), frappe.utils.cstr(e))

    frappe.db.commit()

    out = {"written_rows": written, "failed": len(failures)}
    if failures:
        out["failed_file_url"] = _export_failures_csv(failures, FAILURES_FILE_PREFIX)
    return out

# --------------- Header index helper ---------------
class _Index:
    def __init__(self, header: list):
        def find(col):
            try: return header.index(col)
            except ValueError: return -1

        self.first_name = find("first_name")
        self.last_name  = find("last_name")
        self.full_name  = find("full_name")  # present on sheet but ignored for value
        self.gender     = find("gender")
        self.date_of_birth = find("date_of_birth")
        self.does_the_child_have_a_vaccination_card = find("does_the_child_have_a_vaccination_card")
        self.response_id = find("response_id")
        self.comment_to_supervisor = find("comment_to_supervisor")
        self.last_vaccine_administered = find("last_vaccine_administered")

# --------------- File / parsing helpers ---------------
def _iter_rows(file_url: str) -> Tuple[Iterable, bool]:
    path = get_file_path(file_url)
    ext = (file_url or "").lower().rsplit(".", 1)[-1]

    if ext in ("csv", "txt"):
        def gen():
            with open(path, "rb") as fh:
                raw = fh.read()
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1")
            sio = io.StringIO(text)
            rdr = csv.reader(sio)
            for row in rdr:
                yield row
        return gen(), False

    if ext in ("xlsx", "xlsm", "xls"):
        with open(path, "rb") as fh:
            fbytes = fh.read()
        table = read_xlsx_file_from_attached_file(file_content=fbytes)
        sheet = table[0] if table else []
        def gen():
            for row in sheet:
                yield row
        return gen(), True

    frappe.throw(f"Unsupported file type: .{ext}")

def _split_header(row_iter: Iterable) -> Tuple[list, Iterable]:
    it = iter(row_iter)
    try:
        header = next(it)
    except StopIteration:
        frappe.throw("File is empty.")
    header = [str(h).strip() for h in header]
    return header, it

def _row_to_dict(header: list, row) -> Dict[str, Optional[str]]:
    out = {}
    for i, h in enumerate(header):
        val = row[i] if i < len(row) else None
        if isinstance(val, str): val = val.strip()
        out[h] = val
    return out

def _assert_required_headers(header: list, expected_cols: list):
    missing = [c for c in expected_cols if c not in header]
    if missing:
        frappe.throw("Missing columns in header: " + ", ".join(missing))

# --------------- Value helpers ---------------
def _cell(row, idx) -> Optional[str]:
    if idx < 0 or idx >= len(row):
        return None
    v = row[idx]
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None

def _sanitize_name(v: Optional[str]) -> Optional[str]:
    """
    Keep only letters and spaces. Collapse multiple spaces, trim ends.
    Returns None if nothing remains after cleaning.
    """
    if not v:
        return None
    s = re.sub(r"[^A-Za-z\s]", "", str(v))
    s = re.sub(r"\s+", " ", s).strip()
    return s or None

def _build_full_name_sanitized(first_name: Optional[str], last_name: Optional[str]) -> Optional[str]:
    """
    full_name = "first_name last_name" from already-sanitized parts.
    Ensures single spaces and no leading/trailing spaces.
    """
    f = first_name or ""
    l = last_name or ""
    s = f"{f} {l}".strip()
    s = re.sub(r"\s+", " ", s)
    return s or None

def _to_date_str(v: Optional[str]) -> Optional[str]:
    """
    Normalizes to YYYY-MM-DD when possible. Accepts:
      - already ISO yyyy-mm-dd
      - dd/mm/yyyy, mm/dd/yyyy, dd-mm-yyyy, mm-dd-yyyy, yyyy-mm-dd, yyyy/mm/dd
    If year is 2-digit (e.g. '01-05-91'), this helper will NOT guess the century.
    Provide '1991-05-01' in your sheet if you need it imported.
    """
    if not v:
        return None
    s = str(v).strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    for sep in ("/", "-"):
        parts = s.split(sep)
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            a, b, y = parts
            if len(a) == 4:
                try:
                    yy = int(a); mm = int(b); dd = int(y)
                    return f"{yy:04d}-{mm:02d}-{dd:02d}"
                except Exception:
                    break
            if len(y) == 4:
                try:
                    da = int(a); db = int(b); yy = int(y)
                    if da > 12:
                        return f"{yy:04d}-{db:02d}-{da:02d}"  # dd/mm/yyyy
                    return f"{yy:04d}-{da:02d}-{db:02d}"     # mm/dd/yyyy
                except Exception:
                    break
    return None

# --------------- Failures export (CSV, public) ---------------
def _append_failure(failures: list, row: Dict, msg: str):
    bad = dict(row) if isinstance(row, dict) else {"row": row}
    bad["error"] = msg
    failures.append(bad)

def _export_failures_csv(failed_rows: list, prefix: str) -> str:
    cols, seen = [], set()
    for r in failed_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k); cols.append(k)
    if "error" in cols:
        cols.remove("error")
    cols.append("error")

    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    for r in failed_rows:
        writer.writerow({c: r.get(c, "") for c in cols})
    content = sio.getvalue()

    fname = f"{prefix}_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url



import io, csv
import frappe
from typing import List, Dict, Optional
from frappe.utils import now_datetime

BATCH_COMMIT = 200  # how many successful saves before a DB commit

@frappe.whitelist()
def link_households_to_buildings_by_response_id(limit:int = 0):
    """
    Find Household records where `building` is NULL/empty and `comment_to_supervisor`
    is present. For each, look up Building by `response_id == comment_to_supervisor`
    and set `household.building = building.name`, saving the doc (ORM) to trigger hooks.

    Args:
        limit (int): Process at most this many households (0 = no limit).

    Returns:
        dict: { scanned, linked, skipped_no_match, skipped_no_key, failed, failed_file_url? }
    """

    # 1) Pull candidate households (missing building, but with a response-id key in comment_to_supervisor)
    where_limit = "" if not limit or int(limit) <= 0 else f"LIMIT {int(limit)}"
    households = frappe.db.sql(f"""
        SELECT name, comment_to_supervisor
        FROM `tabHousehold`
        WHERE (building IS NULL OR building = '')
          AND COALESCE(comment_to_supervisor, '') <> ''
        {where_limit}
    """, as_dict=True)

    if not households:
        return {"scanned": 0, "linked": 0, "skipped_no_match": 0, "skipped_no_key": 0, "failed": 0}

    scanned = len(households)
    # 2) Build a unique set of response_ids to resolve in bulk from Building
    resp_ids = list({h["comment_to_supervisor"].strip() for h in households if h.get("comment_to_supervisor")})
    building_map: Dict[str, str] = {}

    # 3) Fetch matching buildings in chunks: response_id -> name
    for i in range(0, len(resp_ids), 1000):
        chunk = resp_ids[i:i+1000]
        placeholders = ", ".join(["%s"] * len(chunk))
        rows = frappe.db.sql(f"""
            SELECT response_id, name
            FROM `tabBuilding`
            WHERE response_id IN ({placeholders})
        """, tuple(chunk), as_dict=True)
        for r in rows:
            if r.get("response_id"):
                building_map[r["response_id"]] = r["name"]

    linked = skipped_no_match = skipped_no_key = failed = 0
    failures = []
    to_commit = 0

    # 4) Link and save via ORM (so validations/after_save fire)
    for h in households:
        try:
            key = (h.get("comment_to_supervisor") or "").strip()
            if not key:
                skipped_no_key += 1
                continue

            bname = building_map.get(key)
            if not bname:
                skipped_no_match += 1
                continue

            doc = frappe.get_doc("Household", h["name"])
            # skip if someone else already filled it between query and now
            if getattr(doc, "building", None):
                continue

            doc.building = bname
            doc.save(ignore_permissions=True)  # trigger validations/after_save
            linked += 1
            to_commit += 1

            if to_commit >= BATCH_COMMIT:
                frappe.db.commit()
                to_commit = 0

        except Exception as e:
            failed += 1
            failures.append({
                "household": h.get("name"),
                "comment_to_supervisor": h.get("comment_to_supervisor"),
                "error": frappe.utils.cstr(e),
            })

    # final commit
    frappe.db.commit()

    out = {
        "scanned": scanned,
        "linked": linked,
        "skipped_no_match": skipped_no_match,
        "skipped_no_key": skipped_no_key,
        "failed": failed,
    }
    if failures:
        out["failed_file_url"] = _export_failures_csv(failures, "household_building_link_failures")
    return out


# --------- helper: export failures as a public CSV attachment ---------
def _export_failures_csv(rows: List[Dict], prefix: str) -> str:
    cols = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k); cols.append(k)

    sio = io.StringIO()
    w = csv.DictWriter(sio, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})
    content = sio.getvalue()

    fname = f"{prefix}_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"
    fdoc = frappe.get_doc({
        "doctype": "File",
        "file_name": fname,
        "content": content,
        "is_private": 0,  # public
        "folder": "Home/Attachments",
    }).insert(ignore_permissions=True)
    return fdoc.file_url
