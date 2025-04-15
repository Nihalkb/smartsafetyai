import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import io
import base64


def generate_material_bar_chart(df: pd.DataFrame) -> str:
    counts = df["Material Released"].value_counts().head(10)

    plt.figure(figsize=(10, 6))
    ax = counts.plot(kind="bar")
    plt.title("Top Materials Involved in Incidents")
    plt.xlabel("Material Released")
    plt.ylabel("Number of Incidents")
    plt.xticks(rotation=45, ha="right")
    for i, v in enumerate(counts):
        ax.text(i, v + 0.5, str(v), ha='center', va='bottom')
    plt.tight_layout()

    return _plot_to_base64()


def generate_operator_pie_chart(df: pd.DataFrame) -> str:
    counts = df["Pipeline Operator"].value_counts().head(6)

    plt.figure(figsize=(8, 8))
    counts.plot(kind="pie", autopct="%1.1f%%", startangle=140, colors=plt.cm.Paired.colors)
    plt.title("Incidents by Top Operators")
    plt.ylabel("")
    plt.tight_layout()

    return _plot_to_base64()


def generate_incidents_over_time(df: pd.DataFrame) -> str:
    try:
        df["Parsed Date"] = pd.to_datetime(df["Date"], errors="coerce")
        year_counts = df["Parsed Date"].dt.year.value_counts().sort_index()
    except Exception:
        return None

    plt.figure(figsize=(10, 5))
    ax = year_counts.plot(kind="line", marker="o", color="#e74c3c")
    plt.title("Incidents Over Time")
    plt.xlabel("Year")
    plt.ylabel("Number of Incidents")
    for x, y in zip(year_counts.index, year_counts.values):
        plt.text(x, y + 0.5, str(y), ha='center', va='bottom')
    plt.grid(True)
    plt.tight_layout()

    return _plot_to_base64()


def generate_severity_chart(df: pd.DataFrame) -> str:
    if "Severity" not in df.columns:
        return None

    severity_counts = df["Severity"].value_counts()

    plt.figure(figsize=(10, 6))
    ax = severity_counts.plot(kind="bar", color="#8e44ad")
    plt.title("Incidents by Severity")
    plt.xlabel("Severity Level")
    plt.ylabel("Number of Incidents")
    plt.xticks(rotation=45)
    for i, v in enumerate(severity_counts):
        ax.text(i, v + 0.5, str(v), ha='center', va='bottom')
    plt.tight_layout()

    return _plot_to_base64()


def generate_location_chart(df: pd.DataFrame) -> str:
    if "Location" not in df.columns:
        return None

    location_counts = df["Location"].value_counts().head(10)

    plt.figure(figsize=(10, 6))
    ax = location_counts.plot(kind="barh", color="#2ecc71")
    plt.title("Top Incident Locations")
    plt.xlabel("Number of Incidents")
    for i, v in enumerate(location_counts):
        ax.text(v + 0.5, i, str(v), va='center')
    plt.tight_layout()

    return _plot_to_base64()


def _plot_to_base64() -> str:
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"
