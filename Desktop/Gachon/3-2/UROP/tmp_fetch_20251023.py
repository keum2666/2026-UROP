import os
from pathlib import Path
import requests
import pandas as pd

BASE_URL = "https://apis.data.go.kr/1613000/RegionalTransportationCardUsageSyntheticData/getGyeonggiTransportationCardUsageSyntheticData"
KEY = os.environ.get("SYNTHETIC_CARD_API_KEY", "").strip()
DATE = os.environ.get("QUERY_DATE", "20251023")
ROUTE_NO = "M7731"
ROUTE_ID = "41016902"
OUT = Path("gtx_a_seoul_bus_outputs") / "transport_card"
OUT.mkdir(parents=True, exist_ok=True)

if not KEY:
    raise RuntimeError("SYNTHETIC_CARD_API_KEY 환경변수가 없습니다.")

rows = []
page = 1
while True:
    params = {
        "serviceKey": KEY,
        "pageNo": page,
        "numOfRows": 1000,
        "dataType": "JSON",
        "opr_ymd": DATE,
        "rte_id": ROUTE_ID,
        "users_type_cd": "01",
        "ride_ctpv_cd": "41",
    }
    response = requests.get(BASE_URL, params=params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    root = payload.get("response", payload.get("Response", payload))
    header = root.get("header", {}) or {}
    body = root.get("body", {}) or {}
    code = str(header.get("resultCode", header.get("resultcode", "")))
    if code not in ("", "00", "0", "200"):
        raise RuntimeError(f"resultCode={code}: {header}")
    items = (body.get("items", {}) or {})
    items = items.get("item", []) if isinstance(items, dict) else items
    if isinstance(items, dict):
        items = [items]
    items = items or []
    rows.extend(items)
    total = int(body.get("totalCount", body.get("totalcount", 0)) or 0)
    if not items or (total and len(rows) >= total) or len(items) < 1000:
        break
    page += 1

df = pd.DataFrame(rows)
df.insert(0, "query_date", DATE)
df.insert(1, "query_route_no", ROUTE_NO)
df.insert(2, "query_route_id", ROUTE_ID)
print(f"api_rows_before_goff_filter={len(df)}")
df.to_csv(OUT / f"gtx_a_transport_card_{DATE}_M7731_raw_all.csv", index=False, encoding="utf-8-sig")
goff = next((c for c in ["goff_ctpv_cd", "alight_ctpv_cd", "arr_ctpv_cd", "arrive_ctpv_cd"] if c in df.columns), None)
if goff:
    df[goff] = df[goff].astype(str).str.strip().str.zfill(2)
    print("goff_counts=", df[goff].value_counts(dropna=False).to_dict())
    df = df[df[goff].eq("11")].copy()
path = OUT / f"gtx_a_transport_card_{DATE}_M7731_raw.csv"
df.to_csv(path, index=False, encoding="utf-8-sig")
print(f"saved={path}")
print(f"rows={len(df)}")
if not df.empty:
    df["utztn_nope"] = pd.to_numeric(df["utztn_nope"], errors="coerce").fillna(0)
    print(f"users={int(df['utztn_nope'].sum())}")
    print("columns=", df.columns.tolist())
