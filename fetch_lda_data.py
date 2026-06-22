import urllib.request
import urllib.parse
import json
import pandas as pd
import time
import os

os.chdir(r"C:\Users\lchau\OneDrive\Desktop\influence-intelligence")

# Exact LDA name variants mapped to clean company labels
COMPANY_NAMES = {
    "Google": [
        "GOOGLE", "GOOGLE INC", "PUBLIC POLICY PARTNERS (GOOGLE INC)"
    ],
    "Microsoft": [
        "MICROSOFT", "MICROSOFT CORP", "MICROSOFT CORPORATION"
    ],
    "NVIDIA": [
        "NVIDIA", "NVIDIA CORPORATION"
    ],
    "Apple": [
        "APPLE INC", "APPLE, INC", "APPLE COMPUTERS INC", "APPLE COMPUTER INC"
    ],
    "Qualcomm": [
        "QUALCOMM", "QUALCOMM INC", "QUALCOMM INCORPORATED"
    ],
    "JPMorgan Chase": [
    "JPMORGAN CHASE & CO",
    "JPMORGAN CHASE CO",
    "JP MORGAN CHASE",
    "JP MORGAN CHASE & CO",
    "JP MORGAN & CO",
    "JP MORGAN"
    ],
    "Goldman Sachs": [
        "GOLDMAN SACHS", "GOLDMAN SACHS & CO",
        "GOLDMAN SACHS & CO LLC", "GOLDMAN SACHS GROUP INC"
    ],
    "GE Aerospace": [
        "GENERAL ELECTRIC CO", "GENERAL ELECTRIC COMPANY",
        "GENERAL ELECTRIC CORP", "GENERAL ELECTRIC (GE)",
        "GENERAL ELECTRIC CO (GE)",
        "GENERAL ELECTRIC COMPANY (INCLUDING SUBSIDIARIES)",
        "NEW NAME: GE AVIATION (FORMERLY KNOWN AS GENERAL ELECTRIC CO )"
    ],
    "Boeing": [
        "BOEING", "BOEING CO", "BOEING CORP", "BOEING CORPORATION",
        "BOEING COMPANY", "BOEING COMPANY THE", "BOEING AIRCRAFT CO"
    ],
    "Lockheed Martin": [
        "LOCKHEED MARTIN", "LOCKHEED MARTIN CORP",
        "LOCKHEED MARTIN CORPORATION"
    ]
}

YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

def fetch_page(url):
    req = urllib.request.Request(
        url, headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode())

def fetch_by_exact_name(exact_name, year, clean_label):
    base = "https://lda.senate.gov/api/v1/filings/"
    params = urllib.parse.urlencode({
        "client_name": exact_name,
        "filing_year": year,
        "format": "json",
        "limit": 25
    })
    url = f"{base}?{params}"
    records = []

    while url:
        try:
            data = fetch_page(url)
            for f in data.get("results", []):

                income   = float(f.get("income")   or 0)
                expenses = float(f.get("expenses")  or 0)
                spend    = income if income > 0 else expenses

                if spend == 0:
                    continue

                issue_codes = f.get("lobbying_activities") or []
                codes = list({
                    a.get("general_issue_code", "")
                    for a in issue_codes
                    if a.get("general_issue_code")
                })
                issues_text = " | ".join(
                    a.get("specific_issues", "")
                    for a in issue_codes
                    if a.get("specific_issues")
                )
                agencies = list({
                    g if isinstance(g, str) else g.get("name", "")
                    for a in issue_codes
                    for g in (a.get("government_entities") or [])
                })

                records.append({
                    "filing_uuid":     f.get("filing_uuid"),
                    "filing_year":     f.get("filing_year"),
                    "filing_period":   f.get("filing_period"),
                    "company":         clean_label,
                    "client_name_raw": f.get("client", {}).get("name", ""),
                    "registrant_name": f.get("registrant", {}).get("name", ""),
                    "lobbying_spend":  spend,
                    "issue_codes":     "|".join(codes),
                    "specific_issues": issues_text[:600],
                    "agencies":        "|".join(agencies[:6]),
                })

            url = data.get("next")
            if url:
                time.sleep(1.2)
 
        except urllib.error.HTTPError as e:
            if e.code == 429:
                print("  ⏳ Rate limited — waiting 15s...")
                time.sleep(15)
                continue  # retry same url
            else:
                print(f"  ✗ Error: {exact_name} {year} — {e}")
                break
        except Exception as e:
            print(f"  ✗ Error: {exact_name} {year} — {e}")
            break

    return records

# ── Main loop ─────────────────────────────────────────────────────
all_records = []
total = sum(len(v) for v in COMPANY_NAMES.values()) * len(YEARS)
count = 0

for clean_label, name_variants in COMPANY_NAMES.items():
    company_records = []
    for exact_name in name_variants:
        for year in YEARS:
            count += 1
            recs = fetch_by_exact_name(exact_name, year, clean_label)
            company_records.extend(recs)
            if recs:
                print(f"  ✓ {clean_label} ({exact_name}) {year} — {len(recs)} filings")
            time.sleep(1.2)

    all_records.extend(company_records)
    subtotal = sum(r["lobbying_spend"] for r in company_records) / 1e6
    print(f"→ {clean_label}: {len(company_records)} filings | ${subtotal:.1f}M\n")

# ── Deduplicate and save ──────────────────────────────────────────
df = pd.DataFrame(all_records)
df.drop_duplicates(subset="filing_uuid", inplace=True)
df.to_csv("data/raw/lda_raw_pull.csv", index=False)

print(f"\n{'='*50}")
print(f"✓ {len(df)} total filings → data/raw/lda_raw_pull.csv")
print(f"  Companies: {df['company'].nunique()}")
print(f"  Year range: {df['filing_year'].min()}–{df['filing_year'].max()}")
print(f"  Total spend: ${df['lobbying_spend'].sum()/1e6:.1f}M")
print(f"\nSpend by company ($M):")
print((df.groupby('company')['lobbying_spend'].sum()/1e6).round(1)
        .sort_values(ascending=False).to_string())