import os
import re
import pandas as pd
from pathlib import Path

def extract_incident_data_from_txt(txt_path: str) -> pd.DataFrame:
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    # If the file contains a header before the first incident report, remove it.
    header_split = re.split(r"(Incident Report \d+:)", text, flags=re.IGNORECASE)
    if len(header_split) > 1:
        # Rebuild the text so it starts with "Incident Report ..."
        text = "".join(header_split[1:])

    # Split the text into chunks where each incident begins with "Incident Report <number>:"
    incident_chunks = re.split(r"(?=Incident Report \d+:)", text.strip(), flags=re.IGNORECASE)
    incident_data = []

    for i, chunk in enumerate(incident_chunks):
        # Only process chunks that clearly start with an incident report header.
        if not re.search(r"^Incident Report \d+:", chunk, re.IGNORECASE):
            continue

        entry = {"Incident Number": i + 1}

        # Extract severity from header (e.g., [Severity: 🟡 Minor])
        severity_match = re.search(r"\[severity:\s*([^\]]+)\]", chunk, re.IGNORECASE)
        severity_raw = severity_match.group(1).strip() if severity_match else ""
        entry["Severity"] = severity_raw

        # Extract normalized severity label (e.g., "Minor" from "🟡 Minor")
        severity_level_match = re.search(r"(minor|low|moderate|high|critical)", severity_raw, re.IGNORECASE)
        entry["Severity Level"] = severity_level_match.group(1).capitalize() if severity_level_match else ""

        # Extract Date
        date_match = re.search(r"date:\s*(.+)", chunk, re.IGNORECASE)
        entry["Date"] = date_match.group(1).strip() if date_match else ""

        # Extract Location
        location_match = re.search(r"location:\s*(.+)", chunk, re.IGNORECASE)
        entry["Location"] = location_match.group(1).strip() if location_match else ""

        # Extract Pipeline Operator
        operator_match = re.search(r"pipeline operator:\s*(.+)", chunk, re.IGNORECASE)
        entry["Pipeline Operator"] = operator_match.group(1).strip() if operator_match else ""

        # Extract Material Released
        material_match = re.search(r"material released:\s*(.+)", chunk, re.IGNORECASE)
        entry["Material Released"] = material_match.group(1).strip() if material_match else ""

        # Extract PHMSA Guide Reference
        guide_match = re.search(r"phmsa guide reference:\s*(.+)", chunk, re.IGNORECASE)
        entry["PHMSA Guide Reference"] = guide_match.group(1).strip() if guide_match else ""

        # Extract Incident Description (up to the start of Response Actions or Casualties & Injuries)
        description_match = re.search(r"incident description:\s*(.+?)(response actions:|casualties & injuries:)", 
                                      chunk, re.IGNORECASE | re.DOTALL)
        entry["Incident Description"] = description_match.group(1).strip() if description_match else ""

        # Extract Response Actions (up to Casualties & Injuries or end of chunk)
        response_match = re.search(r"response actions:\s*(.+?)(casualties & injuries:|$)", 
                                   chunk, re.IGNORECASE | re.DOTALL)
        entry["Response Actions"] = response_match.group(1).strip() if response_match else ""

        # Extract Casualties & Injuries
        injuries_match = re.search(r"casualties & injuries:\s*(.+)", chunk, re.IGNORECASE | re.DOTALL)
        entry["Casualties & Injuries"] = injuries_match.group(1).strip() if injuries_match else ""

        incident_data.append(entry)

    return pd.DataFrame(incident_data)

def save_incident_data(df: pd.DataFrame, output_folder="data/processed"):
    os.makedirs(output_folder, exist_ok=True)
    csv_path = os.path.join(output_folder, "incident_reports.csv")
    json_path = os.path.join(output_folder, "incident_reports.json")
    
    df.to_csv(csv_path, index=False)
    df.to_json(json_path, orient="records", indent=2)
    
    print(f"Data saved to CSV: {csv_path}")
    print(f"Data saved to JSON: {json_path}")

if __name__ == "__main__":
    txt_path = "processed_docs/Incident_report_modified_without regulatory clause_200 cases.docx.txt"
    output_folder = "data/processed"

    if os.path.exists(txt_path):
        df = extract_incident_data_from_txt(txt_path)
        save_incident_data(df, output_folder)
        print(f"✅ Extracted and saved {len(df)} incidents.")
    else:
        print(f"❌ TXT file not found: {txt_path}")
