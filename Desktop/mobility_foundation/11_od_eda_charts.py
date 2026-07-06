from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import pandas as pd
import seaborn as sns


BASE_DIR = Path("output") / "od_compare_2023"
FIG_DIR = BASE_DIR / "figures"

CITY_LABELS = {
    "bundang": "분당",
    "ilsan": "일산",
    "dongtan": "동탄",
    "wirye": "위례",
}

CITY_ORDER = ["bundang", "ilsan", "dongtan", "wirye"]
CITY_COLORS = {
    "bundang": "#2563eb",
    "ilsan": "#16a34a",
    "dongtan": "#dc2626",
    "wirye": "#9333ea",
}


def setup_style() -> None:
    sns.set_theme(style="whitegrid")
    sns.set_context("talk", font_scale=0.85)
    font_path = Path("C:/Windows/Fonts/malgun.ttf")
    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        font_name = font_manager.FontProperties(fname=str(font_path)).get_name()
    else:
        font_name = "Malgun Gothic"
    plt.rcParams["font.family"] = font_name
    plt.rcParams["axes.unicode_minus"] = False


def save_fig(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary = pd.read_csv(BASE_DIR / "city_od_summary_2023.csv")
    external = pd.read_csv(BASE_DIR / "city_external_top_destinations_2023.csv")
    internal = pd.read_csv(BASE_DIR / "city_internal_top_od_pairs_2023.csv")

    for frame in [summary, external, internal]:
        frame["city_label"] = frame["city"].map(CITY_LABELS)
        frame["city_label"] = pd.Categorical(frame["city_label"], [CITY_LABELS[c] for c in CITY_ORDER], ordered=True)
    return summary, external, internal


def plot_internal_external_ratio(summary: pd.DataFrame) -> Path:
    data = summary.set_index("city").loc[CITY_ORDER].reset_index()
    labels = data["city"].map(CITY_LABELS)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(labels, data["internal_ratio"] * 100, label="내부 이동", color="#3b82f6")
    ax.bar(
        labels,
        data["external_ratio"] * 100,
        bottom=data["internal_ratio"] * 100,
        label="외부 이동",
        color="#f97316",
    )

    for i, row in data.iterrows():
        ax.text(i, row["internal_ratio"] * 50, f"{row['internal_ratio'] * 100:.1f}%", ha="center", va="center", color="white", weight="bold")
        ax.text(i, row["internal_ratio"] * 100 + row["external_ratio"] * 50, f"{row['external_ratio'] * 100:.1f}%", ha="center", va="center", color="white", weight="bold")

    ax.set_title("도시별 내부/외부 이동 비율")
    ax.set_ylabel("비율(%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="upper center", ncol=2, frameon=False)
    return FIG_DIR / "01_city_internal_external_ratio.png"


def plot_total_volume(summary: pd.DataFrame) -> Path:
    data = summary.set_index("city").loc[CITY_ORDER].reset_index()
    data["city_label"] = data["city"].map(CITY_LABELS)
    data["outbound_total_10k"] = data["outbound_total"] / 10000

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [CITY_COLORS[c] for c in data["city"]]
    bars = ax.bar(data["city_label"], data["outbound_total_10k"], color=colors)
    ax.set_title("도시별 총 발생 통행량")
    ax.set_ylabel("통행량(만 통행/일)")
    for bar, value in zip(bars, data["outbound_total_10k"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{value:.1f}", ha="center", va="bottom")
    return FIG_DIR / "02_city_total_outbound_volume.png"


def plot_top_destinations(external: pd.DataFrame) -> list[Path]:
    paths = []
    for city in CITY_ORDER:
        data = external[external["city"] == city].sort_values("total", ascending=True).tail(10)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(data["dest_label"], data["total"] / 1000, color=CITY_COLORS[city])
        ax.set_title(f"{CITY_LABELS[city]} 외부 도착지 Top 10")
        ax.set_xlabel("통행량(천 통행/일)")
        ax.set_ylabel("")
        for y, value in enumerate(data["total"] / 1000):
            ax.text(value, y, f" {value:.1f}", va="center")
        path = FIG_DIR / f"03_{city}_external_top10.png"
        paths.append(path)
        save_fig(path)
    return paths


def plot_top_internal_pairs(internal: pd.DataFrame) -> list[Path]:
    paths = []
    for city in CITY_ORDER:
        data = internal[internal["city"] == city].sort_values("total", ascending=True).tail(10).copy()
        data["pair"] = data["origin_dong"] + " -> " + data["dest_dong"]
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(data["pair"], data["total"] / 1000, color=CITY_COLORS[city])
        ax.set_title(f"{CITY_LABELS[city]} 내부 OD Pair Top 10")
        ax.set_xlabel("통행량(천 통행/일)")
        ax.set_ylabel("")
        for y, value in enumerate(data["total"] / 1000):
            ax.text(value, y, f" {value:.1f}", va="center")
        path = FIG_DIR / f"04_{city}_internal_top10.png"
        paths.append(path)
        save_fig(path)
    return paths


def main() -> None:
    setup_style()
    summary, external, internal = load_data()
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    chart_paths = []

    path = plot_internal_external_ratio(summary)
    save_fig(path)
    chart_paths.append(path)

    path = plot_total_volume(summary)
    save_fig(path)
    chart_paths.append(path)

    chart_paths.extend(plot_top_destinations(external))
    chart_paths.extend(plot_top_internal_pairs(internal))

    print("Saved charts:")
    for path in chart_paths:
        print(path)


if __name__ == "__main__":
    main()
