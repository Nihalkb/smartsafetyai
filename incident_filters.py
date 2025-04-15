import pandas as pd
from datetime import datetime
import re


def normalize_column_names(df):
    return df.rename(columns=lambda col: col.strip().replace(":", "").strip())


def load_incident_data(path="data/processed/incident_reports.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
    return normalize_column_names(df)


def filter_incidents(
    df: pd.DataFrame,
    material: str = None,
    location_contains: str = None,
    from_year: int = None,
    to_year: int = None,
    has_injuries: bool = None,
    severity: str = None
) -> pd.DataFrame:
    filtered = df.copy()

    # Normalize column names to avoid key errors
    columns = [col.lower() for col in filtered.columns]

    # Filter by material
    if material and "Material Released" in filtered.columns:
        filtered = filtered[filtered["Material Released"].str.contains(material, case=False, na=False)]

    # Filter by location keyword
    if location_contains and "Location" in filtered.columns:
        filtered = filtered[filtered["Location"].str.contains(location_contains, case=False, na=False)]

    # Filter by date range
    if "Date" in filtered.columns:
        try:
            filtered["Parsed Date"] = pd.to_datetime(filtered["Date"], errors="coerce")
            if from_year:
                filtered = filtered[filtered["Parsed Date"].dt.year >= from_year]
            if to_year:
                filtered = filtered[filtered["Parsed Date"].dt.year <= to_year]
            # Convert datetime objects to ISO format strings and replace NaT with None
            filtered["Parsed Date"] = filtered["Parsed Date"].apply(
                lambda x: x.isoformat() if pd.notnull(x) else None
            )
        except Exception as e:
            print("Date filtering error:", e)

    # Filter by injury status
    if "Casualties & Injuries" in filtered.columns:
        col = filtered["Casualties & Injuries"].fillna("").str.lower()
        if has_injuries is True:
            filtered = filtered[
                col.str.contains("injur") &
                ~col.str.contains("no injur|no injuries|none reported")
            ]
        elif has_injuries is False:
            filtered = filtered[
                col.str.contains("no injur|no injuries|none reported")
            ]

    # Filter by severity
    if severity and "Severity" in filtered.columns:
        severity = severity.lower().strip()
        filtered = filtered[
            filtered["Severity"].fillna("").str.lower().str.contains(severity)
        ]

    return filtered


def construct_filter_summary(filters):
    parts = []
    if filters.get("material"):
        parts.append(f"material: {filters['material']}")
    if filters.get("location_contains"):
        parts.append(f"location includes: {filters['location_contains']}")
    if filters.get("from_year") or filters.get("to_year"):
        parts.append(f"from {filters.get('from_year') or 'any'} to {filters.get('to_year') or 'present'}")
    if filters.get("has_injuries") is not None:
        parts.append("with injuries" if filters["has_injuries"] else "without injuries")
    if filters.get("severity"):
        parts.append(f"severity: {filters['severity']}")
    return ", ".join(parts)
