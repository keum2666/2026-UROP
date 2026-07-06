from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
from branca.colormap import linear


DESCRIPTION = (
    "\ubd84\ub2f9/\uc77c\uc0b0/\ub3d9\ud0c4/\uc704\ub840 \uac01\uac01\uc758 "
    "\ub3c4\uc2dc \ub0b4\ubd80 OD Top 20\uacfc, \ud574\ub2f9 \ub3c4\uc2dc "
    "\ub0b4\ubd80 \uc774\ub3d9\ub9cc \uc81c\uc678\ud55c \ub3c4\uc2dc \ubc16 "
    "\ub3c4\ucc29\uc9c0 Top 20"
)

CITY_LABELS = {
    "bundang": "\ubd84\ub2f9",
    "ilsan": "\uc77c\uc0b0",
    "dongtan": "\ub3d9\ud0c4",
    "wirye": "\uc704\ub840",
}

CITY_COLORS = {
    "bundang": "#2563eb",
    "ilsan": "#16a34a",
    "dongtan": "#dc2626",
    "wirye": "#9333ea",
}

PURPOSE_COLUMNS = ["home", "work", "school", "business", "other"]
PURPOSE_LABELS = {
    "home": "\uadc0\uac00",
    "work": "\ucd9c\uadfc",
    "school": "\ub4f1\uad50",
    "business": "\uc5c5\ubb34",
    "other": "\uae30\ud0c0",
}


def format_number(value: float, digits: int = 1) -> str:
    if pd.isna(value):
        return "-"
    return f"{float(value):,.{digits}f}"


def load_boundaries(projected: bool = False) -> gpd.GeoDataFrame:
    shp_paths = [
        "bnd_dong_11_2021_4Q/bnd_dong_11_2021_4Q.shp",
        "bnd_dong_23_2021_4Q/bnd_dong_23_2021_4Q.shp",
        "bnd_dong_31_2021_4Q/bnd_dong_31_2021_4Q.shp",
    ]
    frames = [gpd.read_file(path)[["ADM_CD", "ADM_NM", "geometry"]] for path in shp_paths]
    boundaries = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), geometry="geometry", crs=frames[0].crs)
    boundaries["ADM_CD"] = boundaries["ADM_CD"].astype(str)
    boundaries["dest_dong"] = boundaries["ADM_NM"].astype(str)
    if projected:
        return boundaries
    return boundaries.to_crs(epsg=4326)


def representative_points() -> pd.DataFrame:
    projected = load_boundaries(projected=True)
    points = projected.copy()
    points["geometry"] = points.geometry.representative_point()
    points["x"] = points.geometry.x
    points["y"] = points.geometry.y

    wgs = points.to_crs(epsg=4326)
    return pd.DataFrame(
        {
            "boundary_code": points["ADM_CD"].astype(str),
            "lat": wgs.geometry.y,
            "lon": wgs.geometry.x,
            "x": points["x"],
            "y": points["y"],
        }
    )


def expected_region(row: pd.Series) -> str:
    sido = str(row["dest_sido"])
    sigungu = str(row["dest_sigungu"])
    if sido == "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc":
        return f"\uc11c\uc6b8_{sigungu}"
    if sido == "\uc778\ucc9c\uad11\uc5ed\uc2dc":
        return f"\uc778\ucc9c_{sigungu}"
    if sido == "\uacbd\uae30\ub3c4":
        city = sigungu.split()[0].replace("\uc2dc", "").replace("\uad70", "")
        return f"\uacbd\uae30_{city}"
    return f"{sido}_{sigungu}"


def load_boundary_code_crosswalk() -> pd.DataFrame:
    files = list(Path("output").glob("*.csv"))
    landuse_file = next(path for path in files if "2021" in path.name and "\uc0c1\uc5c5" in path.name)
    crosswalk = pd.read_csv(landuse_file)
    crosswalk = crosswalk.rename(
        columns={
            crosswalk.columns[0]: "expected_region",
            crosswalk.columns[2]: "boundary_code",
            crosswalk.columns[3]: "dest_dong",
        }
    )
    crosswalk["boundary_code"] = crosswalk["boundary_code"].astype(str)
    return crosswalk[["expected_region", "dest_dong", "boundary_code"]].drop_duplicates()


def load_external_top20() -> pd.DataFrame:
    path = Path("output") / "od_compare_2023" / "city_external_top_destinations_2023.csv"
    od = pd.read_csv(path)
    od["city_label"] = od["city"].map(CITY_LABELS)
    od["expected_region"] = od.apply(expected_region, axis=1)
    od["total_display"] = od["total"].map(format_number)
    for column in PURPOSE_COLUMNS:
        od[f"{column}_display"] = od[column].map(format_number)
    return od


def load_internal_top20() -> pd.DataFrame:
    path = Path("output") / "od_compare_2023" / "city_internal_top_od_pairs_2023.csv"
    od = pd.read_csv(path)
    od["city_label"] = od["city"].map(CITY_LABELS)
    od["total_display"] = od["total"].map(format_number)
    for column in PURPOSE_COLUMNS:
        od[f"{column}_display"] = od[column].map(format_number)
    return od


def map_external_to_boundaries(od: pd.DataFrame, boundaries: gpd.GeoDataFrame, crosswalk: pd.DataFrame) -> gpd.GeoDataFrame:
    od = od.merge(crosswalk, on=["expected_region", "dest_dong"], how="left")
    exact = od.dropna(subset=["boundary_code"]).merge(
        boundaries,
        left_on="boundary_code",
        right_on="ADM_CD",
        how="left",
        suffixes=("", "_boundary"),
    )

    duplicate_names = set(boundaries["dest_dong"][boundaries["dest_dong"].duplicated(keep=False)])
    unique_boundaries = boundaries[~boundaries["dest_dong"].isin(duplicate_names)]
    fallback = od[od["boundary_code"].isna()].merge(
        unique_boundaries,
        on="dest_dong",
        how="left",
        suffixes=("", "_boundary"),
    )

    mapped = pd.concat([exact, fallback], ignore_index=True)
    mapped["boundary_code"] = mapped["boundary_code"].fillna(mapped["ADM_CD"])
    mapped = gpd.GeoDataFrame(mapped, geometry="geometry", crs="EPSG:4326")
    return mapped.dropna(subset=["geometry"]).copy()


def expected_region_from_parts(sido: str, sigungu: str) -> str:
    if sido == "\uc11c\uc6b8\ud2b9\ubcc4\uc2dc":
        return f"\uc11c\uc6b8_{sigungu}"
    if sido == "\uc778\ucc9c\uad11\uc5ed\uc2dc":
        return f"\uc778\ucc9c_{sigungu}"
    if sido == "\uacbd\uae30\ub3c4":
        city = str(sigungu).split()[0].replace("\uc2dc", "").replace("\uad70", "")
        return f"\uacbd\uae30_{city}"
    return f"{sido}_{sigungu}"


def add_external_distance(
    external_mapped: gpd.GeoDataFrame,
    points: pd.DataFrame,
    city_zones: pd.DataFrame,
    crosswalk: pd.DataFrame,
) -> gpd.GeoDataFrame:
    data = external_mapped.copy()
    data = data.merge(
        points.rename(columns={"boundary_code": "dest_boundary_code", "lat": "dest_lat", "lon": "dest_lon", "x": "dest_x", "y": "dest_y"}),
        left_on="boundary_code",
        right_on="dest_boundary_code",
        how="left",
    )

    zone_points = city_zones.copy()
    zone_points["expected_region"] = zone_points.apply(
        lambda row: expected_region_from_parts(str(row["sido"]), str(row["sigungu"])),
        axis=1,
    )
    zone_points = zone_points.merge(
        crosswalk.rename(columns={"dest_dong": "dong", "boundary_code": "zone_boundary_code"}),
        on=["expected_region", "dong"],
        how="left",
    )
    zone_points = zone_points.merge(
        points.rename(columns={"boundary_code": "zone_boundary_code", "x": "zone_x", "y": "zone_y"}),
        on="zone_boundary_code",
        how="left",
    )
    city_centers = (
        zone_points.groupby("city", as_index=False)[["zone_x", "zone_y"]]
        .mean()
        .rename(columns={"zone_x": "city_x", "zone_y": "city_y"})
    )
    data = data.merge(city_centers, on="city", how="left")

    dx = data["city_x"] - data["dest_x"]
    dy = data["city_y"] - data["dest_y"]
    data["straight_distance_km"] = ((dx**2 + dy**2) ** 0.5) / 1000
    data["straight_distance_display"] = data["straight_distance_km"].map(format_number)
    data["straight_distance_popup"] = data["straight_distance_display"] + " km"
    return data


def add_internal_points_and_distance(internal_od: pd.DataFrame, points: pd.DataFrame) -> pd.DataFrame:
    data = internal_od.copy()
    data["origin_boundary_code"] = data["origin_admin_code_x"].astype(str)
    data["dest_boundary_code"] = data["dest_admin_code_x"].astype(str)
    data = data.merge(
        points.rename(
            columns={
                "boundary_code": "origin_boundary_code",
                "lat": "origin_lat",
                "lon": "origin_lon",
                "x": "origin_x",
                "y": "origin_y",
            }
        ),
        on="origin_boundary_code",
        how="left",
    ).merge(
        points.rename(
            columns={
                "boundary_code": "dest_boundary_code",
                "lat": "dest_lat",
                "lon": "dest_lon",
                "x": "dest_x",
                "y": "dest_y",
            }
        ),
        on="dest_boundary_code",
        how="left",
    )
    dx = data["origin_x"] - data["dest_x"]
    dy = data["origin_y"] - data["dest_y"]
    data["straight_distance_km"] = ((dx**2 + dy**2) ** 0.5) / 1000
    data["straight_distance_display"] = data["straight_distance_km"].map(format_number)
    return data


def save_internal_distance_csv(internal_with_points: pd.DataFrame) -> Path:
    output_path = Path("output") / "od_compare_2023" / "city_internal_top_od_pairs_2023_with_straight_distance.csv"
    internal_with_points.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def save_external_distance_csv(external_with_distance: pd.DataFrame) -> Path:
    output_path = Path("output") / "od_compare_2023" / "city_external_top_destinations_2023_with_straight_distance.csv"
    external_with_distance.to_csv(output_path, index=False, encoding="utf-8-sig")
    return output_path


def city_center_points(points: pd.DataFrame, city_zones: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    zones = city_zones.copy()
    zones["expected_region"] = zones.apply(
        lambda row: expected_region_from_parts(str(row["sido"]), str(row["sigungu"])),
        axis=1,
    )
    zones = zones.merge(
        crosswalk.rename(columns={"dest_dong": "dong", "boundary_code": "zone_boundary_code"}),
        on=["expected_region", "dong"],
        how="left",
    )
    zones = zones.merge(
        points.rename(columns={"boundary_code": "zone_boundary_code"}),
        on="zone_boundary_code",
        how="left",
    )
    centers = zones.groupby("city", as_index=False)[["lat", "lon"]].mean()
    centers["city_label"] = centers["city"].map(CITY_LABELS)
    return centers


def build_city_summary_popup(row: pd.Series) -> str:
    city = row["city"]
    city_label = CITY_LABELS.get(city, city)
    external_img = f"figures/03_{city}_external_top10.png"
    internal_img = f"figures/04_{city}_internal_top10.png"
    return f"""
    <div style="font-family:Arial,sans-serif; min-width:620px; max-width:760px;">
        <div style="font-weight:700; font-size:16px; margin-bottom:8px;">{city_label} OD EDA \uc694\uc57d</div>
        <div style="font-size:13px; line-height:1.5; margin-bottom:8px;">
            <b>\ucd1d \ubc1c\uc0dd \ud1b5\ud589\ub7c9</b>: {format_number(row['outbound_total'])} \ud1b5\ud589/\uc77c<br>
            <b>\ub0b4\ubd80 \uc774\ub3d9</b>: {row['internal_ratio'] * 100:.1f}% ·
            <b>\uc678\ubd80 \uc774\ub3d9</b>: {row['external_ratio'] * 100:.1f}%
        </div>
        <div style="font-size:12px; color:#52525b; margin-bottom:8px;">
            \ub3c4\uc2dc\ubcc4 \uc774\ub3d9 \uad6c\uc870\ub97c \ud655\uc778\ud558\uae30 \uc704\ud55c EDA \uacb0\uacfc\uc784.
            \uc678\ubd80 \ub3c4\ucc29\uc9c0 Top 10\uacfc \ub0b4\ubd80 OD Pair Top 10\uc744 \ud568\uaed8 \ud655\uc778\ud568.
        </div>
        <div style="display:grid; grid-template-columns:1fr; gap:10px;">
            <div>
                <div style="font-weight:700; margin-bottom:4px;">{city_label} \uc678\ubd80 \ub3c4\ucc29\uc9c0 Top 10</div>
                <img src="{external_img}" style="width:100%; border:1px solid #e5e7eb;">
            </div>
            <div>
                <div style="font-weight:700; margin-bottom:4px;">{city_label} \ub0b4\ubd80 OD Pair Top 10</div>
                <img src="{internal_img}" style="width:100%; border:1px solid #e5e7eb;">
            </div>
        </div>
    </div>
    """


def purpose_html(row: pd.Series) -> str:
    items = []
    for column in PURPOSE_COLUMNS:
        items.append(f"<div>{PURPOSE_LABELS[column]}: {row[f'{column}_display']}</div>")
    return "\n".join(items)


def build_internal_origin_popup(origin_label: str, city_label: str, group: pd.DataFrame) -> str:
    rows = []
    for _, row in group.sort_values("rank").iterrows():
        rows.append(
            f"""
            <tr>
                <td style="padding:5px 6px; border-top:1px solid #e5e7eb;">{int(row['rank'])}\uc704</td>
                <td style="padding:5px 6px; border-top:1px solid #e5e7eb;">
                    <b>\ucd9c\ubc1c \ud589\uc815\ub3d9</b>: {row['origin_label']}<br>
                    <b>\ub3c4\ucc29 \ud589\uc815\ub3d9</b>: {row['dest_label']}<br>
                    \ucd1d {row['total_display']} \ud1b5\ud589/\uc77c ·
                    \uc9c1\uc120\uac70\ub9ac {row['straight_distance_display']} km<br>
                    \uadc0\uac00 {row['home_display']} / \ucd9c\uadfc {row['work_display']} /
                    \ub4f1\uad50 {row['school_display']} / \uc5c5\ubb34 {row['business_display']} /
                    \uae30\ud0c0 {row['other_display']}
                </td>
            </tr>
            """
        )
    return f"""
    <div style="font-family:Arial,sans-serif; min-width:360px; max-width:520px;">
        <div style="font-weight:700; font-size:15px; margin-bottom:6px;">{city_label} \ub0b4\ubd80 \ucd9c\ubc1c\uc9c0</div>
        <div><b>{origin_label}</b></div>
        <table style="border-collapse:collapse; width:100%; margin-top:8px; font-size:12px;">
            {''.join(rows)}
        </table>
    </div>
    """


def build_map() -> folium.Map:
    external_od = load_external_top20()
    internal_od = load_internal_top20()
    summary = pd.read_csv(Path("output") / "od_compare_2023" / "city_od_summary_2023.csv")
    boundaries = load_boundaries(projected=False)
    crosswalk = load_boundary_code_crosswalk()
    points = representative_points()
    city_zones = pd.read_csv(Path("output") / "od_compare_2023" / "city_zones_2023.csv")

    external_mapped = map_external_to_boundaries(external_od, boundaries, crosswalk)
    external_mapped = add_external_distance(external_mapped, points, city_zones, crosswalk)
    internal_with_points = add_internal_points_and_distance(internal_od, points)
    save_external_distance_csv(external_mapped)
    save_internal_distance_csv(internal_with_points)

    center = external_mapped.geometry.unary_union.centroid
    fmap = folium.Map(location=[center.y, center.x], zoom_start=10, tiles="CartoDB positron")

    title_html = f"""
    <div style="
        position: fixed; top: 16px; left: 50px; z-index: 9999;
        background: white; border: 1px solid #d4d4d8; border-radius: 8px;
        padding: 12px 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.12);
        max-width: 560px; font-family: Arial, sans-serif;">
        <div style="font-weight: 700; font-size: 16px; margin-bottom: 6px;">2023 \uc2e0\ub3c4\uc2dc OD Top 20 \uc9c0\ub3c4</div>
        <div style="font-size: 13px; line-height: 1.45;">{DESCRIPTION}</div>
        <div style="font-size: 12px; color: #52525b; margin-top: 6px;">
            \ub0b4\ubd80 OD\ub294 \ucd9c\ubc1c \ud589\uc815\ub3d9 \ub9c8\ucee4\ub97c \ud074\ub9ad\ud558\uba74
            \ubaa9\uc801\uc9c0 \ubaa9\ub85d\uacfc \uc9c1\uc120\uac70\ub9ac\uac00 \ub098\uc635\ub2c8\ub2e4.
        </div>
    </div>
    """
    fmap.get_root().html.add_child(folium.Element(title_html))

    max_total = external_mapped["total"].max()
    colormap = linear.YlOrRd_09.scale(0, max_total)
    colormap.caption = "\ucd1d \ud1b5\ud589\ub7c9(\ud1b5\ud589/\uc77c)"
    colormap.add_to(fmap)

    centers = city_center_points(points, city_zones, crosswalk).merge(summary, on="city", how="left")
    city_summary_group = folium.FeatureGroup(name="\ub3c4\uc2dc\ubcc4 EDA \uc694\uc57d/\uadf8\ub798\ud504", show=True)
    for _, row in centers.iterrows():
        city = row["city"]
        city_label = CITY_LABELS.get(city, city)
        base_color = CITY_COLORS.get(city, "#334155")
        folium.CircleMarker(
            location=[row["lat"], row["lon"]],
            radius=11,
            color=base_color,
            fill=True,
            fill_color=base_color,
            fill_opacity=0.95,
            tooltip=f"{city_label} EDA \uc694\uc57d/\uadf8\ub798\ud504",
            popup=folium.Popup(build_city_summary_popup(row), max_width=800),
        ).add_to(city_summary_group)
    city_summary_group.add_to(fmap)

    for city, city_data in external_mapped.groupby("city", sort=False):
        city_label = CITY_LABELS.get(city, city)
        base_color = CITY_COLORS.get(city, "#334155")
        feature_group = folium.FeatureGroup(name=f"{city_label} \uc678\ubd80 \ub3c4\ucc29\uc9c0 Top 20", show=(city == "bundang"))

        def style_function(feature, base_color=base_color):
            total = feature["properties"]["total"]
            return {"fillColor": colormap(total), "color": base_color, "weight": 2, "fillOpacity": 0.68}

        folium.GeoJson(
            city_data,
            style_function=style_function,
            highlight_function=lambda _: {"weight": 4, "fillOpacity": 0.85},
            tooltip=folium.GeoJsonTooltip(
                fields=["rank", "dest_label", "total_display"],
                aliases=["\uc21c\uc704", "\ub3c4\ucc29\uc9c0", "\ucd1d \ud1b5\ud589\ub7c9"],
                sticky=True,
            ),
            popup=folium.GeoJsonPopup(
                fields=[
                    "city_label",
                    "rank",
                    "dest_label",
                    "total_display",
                    "home_display",
                    "work_display",
                    "school_display",
                    "business_display",
                    "other_display",
                    "straight_distance_popup",
                ],
                aliases=[
                    "\ucd9c\ubc1c \ub3c4\uc2dc",
                    "\uc21c\uc704",
                    "\ub3c4\ucc29 \ud589\uc815\ub3d9",
                    "\ucd1d \ud1b5\ud589\ub7c9",
                    "\uadc0\uac00",
                    "\ucd9c\uadfc",
                    "\ub4f1\uad50",
                    "\uc5c5\ubb34",
                    "\uae30\ud0c0",
                    "\uc9c1\uc120\uac70\ub9ac",
                ],
                localize=False,
                labels=True,
                max_width=360,
            ),
        ).add_to(feature_group)
        feature_group.add_to(fmap)

    for city, city_data in internal_with_points.groupby("city", sort=False):
        city_label = CITY_LABELS.get(city, city)
        base_color = CITY_COLORS.get(city, "#334155")

        marker_group = folium.FeatureGroup(name=f"{city_label} \ub0b4\ubd80 \ucd9c\ubc1c\uc9c0 \ub9c8\ucee4", show=True)
        line_group = folium.FeatureGroup(name=f"{city_label} \ub0b4\ubd80 OD \uc120", show=False)

        for (origin_label, origin_dong, origin_lat, origin_lon), origin_group in city_data.groupby(
            ["origin_label", "origin_dong", "origin_lat", "origin_lon"], sort=False
        ):
            folium.CircleMarker(
                location=[origin_lat, origin_lon],
                radius=7,
                color=base_color,
                fill=True,
                fill_color=base_color,
                fill_opacity=0.9,
                tooltip=f"{city_label} \ub0b4\ubd80 \ucd9c\ubc1c: {origin_dong}",
                popup=folium.Popup(build_internal_origin_popup(origin_label, city_label, origin_group), max_width=560),
            ).add_to(marker_group)

        max_city_total = city_data["total"].max()
        for _, row in city_data.iterrows():
            if pd.isna(row["origin_lat"]) or pd.isna(row["dest_lat"]):
                continue
            weight = 2 + 6 * (row["total"] / max_city_total if max_city_total else 0)
            popup_html = f"""
            <div style="font-family:Arial,sans-serif; min-width:280px;">
                <div style="font-weight:700; margin-bottom:6px;">{city_label} \ub0b4\ubd80 OD {int(row['rank'])}\uc704</div>
                <div><b>\ucd9c\ubc1c</b>: {row['origin_label']}</div>
                <div><b>\ub3c4\ucc29</b>: {row['dest_label']}</div>
                <div><b>\uc9c1\uc120\uac70\ub9ac</b>: {row['straight_distance_display']} km</div>
                <hr>
                <div><b>\ucd1d \ud1b5\ud589\ub7c9</b>: {row['total_display']} \ud1b5\ud589/\uc77c</div>
                {purpose_html(row)}
            </div>
            """
            folium.PolyLine(
                locations=[[row["origin_lat"], row["origin_lon"]], [row["dest_lat"], row["dest_lon"]]],
                color=base_color,
                weight=weight,
                opacity=0.65,
                tooltip=(
                    f"{city_label} \ub0b4\ubd80 {int(row['rank'])}\uc704: "
                    f"{row['origin_dong']} -> {row['dest_dong']} "
                    f"({row['total_display']} \ud1b5\ud589/\uc77c, {row['straight_distance_display']} km)"
                ),
                popup=folium.Popup(popup_html, max_width=420),
            ).add_to(line_group)

        marker_group.add_to(fmap)
        line_group.add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def main() -> None:
    output_dir = Path("output") / "od_compare_2023"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "city_od_top20_map_2023.html"
    fmap = build_map()
    fmap.save(output_path)
    print(output_path)


if __name__ == "__main__":
    main()
