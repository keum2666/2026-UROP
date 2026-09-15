# -*- coding: utf-8 -*-
"""국토교통부 버스정류장 위치정보를 이용한 승차·하차 좌표 매핑."""

from pathlib import Path
import re
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "gtx_a_seoul_bus_outputs" / "transport_card"

# 국토부 위치정보 CSV 경로를 실제 파일 위치로 수정하세요.
STOPS_FP = Path(
    r"C:\Users\금경훈\Desktop\Gachon\2-2\새 폴더\도시 빅데이터 분석\찐 잠실\국토교통부_전국 버스정류장 위치정보_20241028.csv"
)
DATES = ["20241017", "20251016"]


def normalize_name(value):
    """정류장명 비교용 정규화: 결측·공백·괄호 안 공백 차이를 완화한다."""
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", "", str(value).strip())


def find_column(df, candidates):
    for column in candidates:
        if column in df.columns:
            return column
    raise ValueError(f"컬럼을 찾을 수 없습니다. 후보: {candidates}")


def build_location_lookup(location_df):
    name_col = find_column(location_df, ["정류장명", "정류장 명칭", "버스정류장명"])
    lat_col = find_column(location_df, ["위도", "정류장Y위치값", "Y좌표"])
    lon_col = find_column(location_df, ["경도", "정류장X위치값", "X좌표"])

    locations = location_df[[name_col, lat_col, lon_col]].copy()
    locations["_name_key"] = locations[name_col].map(normalize_name)
    locations[lat_col] = pd.to_numeric(locations[lat_col], errors="coerce")
    locations[lon_col] = pd.to_numeric(locations[lon_col], errors="coerce")
    locations = locations.dropna(subset=["_name_key", lat_col, lon_col])

    # 같은 이름이 여러 위치에 있으면 이름만으로 확정할 수 없으므로 제외한다.
    unique = locations.groupby("_name_key")[[lat_col, lon_col]].nunique()
    unique_names = unique[(unique[lat_col] == 1) & (unique[lon_col] == 1)].index
    locations = locations[locations["_name_key"].isin(unique_names)]
    return locations.drop_duplicates("_name_key").set_index("_name_key"), lat_col, lon_col


def enrich(date, lookup, lat_col, lon_col):
    input_path = DATA_DIR / f"gtx_a_transport_card_{date}_raw_with_stop_names.csv"
    output_path = DATA_DIR / f"gtx_a_transport_card_{date}_raw_with_coords.csv"
    df = pd.read_csv(input_path, dtype=str, encoding="utf-8-sig").fillna("")

    ride_key = df["승차정류장명"].map(normalize_name)
    goff_key = df["하차정류장명"].map(normalize_name)
    ride_coords = lookup.reindex(ride_key)
    goff_coords = lookup.reindex(goff_key)

    df["승차위도"] = ride_coords[lat_col].to_numpy()
    df["승차경도"] = ride_coords[lon_col].to_numpy()
    df["하차위도"] = goff_coords[lat_col].to_numpy()
    df["하차경도"] = goff_coords[lon_col].to_numpy()

    front = [
        "query_date", "query_route_no", "승차정류장ID", "승차정류장명",
        "승차위도", "승차경도", "하차정류장ID", "하차정류장명",
        "하차위도", "하차경도",
    ]
    df = df[[c for c in front if c in df.columns] + [c for c in df.columns if c not in front]]
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(
        f"{date}: {output_path.name} 저장 ({len(df)}건), "
        f"승차 {df['승차위도'].notna().mean():.1%}, "
        f"하차 {df['하차위도'].notna().mean():.1%}"
    )


def main():
    if not STOPS_FP.exists():
        raise FileNotFoundError(f"국토부 정류장 위치정보 파일이 없습니다: {STOPS_FP}")
    location_df = pd.read_csv(STOPS_FP, encoding="cp949")
    lookup, lat_col, lon_col = build_location_lookup(location_df)
    print(f"위치정보 {len(location_df)}건, 이름 기준 매칭 후보 {len(lookup)}개")
    for date in DATES:
        enrich(date, lookup, lat_col, lon_col)


if __name__ == "__main__":
    main()
