"""
============================================================
INFLUENCE INTELLIGENCE BRIEF — ANALYSIS PIPELINE
Lakshit Chaudhary | Portfolio Project | 2026

Research Question:
  Who is buying influence over AI regulation and US-India policy
  in Washington — and what does the pattern of spending reveal
  about their strategic intent?

Data:
  data/raw/lda_raw_pull.csv  (fetched via fetch_lda_data.py)
============================================================
"""

import pandas as pd
import numpy as np
import json
import os

os.chdir(r"C:\Users\lchau\OneDrive\Desktop\influence-intelligence")

pd.set_option('display.max_colwidth', 80)
pd.set_option('display.width', 120)


# ============================================================
# SECTION 1: LOAD & VALIDATE
# ============================================================

def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath, low_memory=False)

    # Enforce types
    df['filing_year'] = pd.to_numeric(df['filing_year'], errors='coerce')
    df['lobbying_spend'] = pd.to_numeric(df['lobbying_spend'], errors='coerce').fillna(0)

    # Add sector mapping
    sector_map = {
        "Google":         "Tech/AI",
        "Microsoft":      "Tech/AI",
        "NVIDIA":         "Tech/AI",
        "Apple":          "Tech/AI",
        "Qualcomm":       "Tech/AI",
        "JPMorgan Chase": "Finance",
        "Goldman Sachs":  "Finance",
        "GE Aerospace":   "Defense/Aerospace",
        "Boeing":         "Defense/Aerospace",
        "Lockheed Martin":"Defense/Aerospace",
    }
    df['sector'] = df['company'].map(sector_map)
    df['year']   = df['filing_year'].astype(int)

    print(f"✓ Loaded {len(df):,} filings | "
          f"{df['company'].nunique()} companies | "
          f"{df['year'].min()}–{df['year'].max()}")
    print(f"  Total spend: ${df['lobbying_spend'].sum()/1e6:.1f}M\n")
    return df


# ============================================================
# SECTION 2: ANALYSIS FUNCTIONS
# ============================================================

def build_annual_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate filings into annual spend per company."""
    annual = (
        df.groupby(['company', 'year', 'sector'])['lobbying_spend']
        .sum()
        .reset_index()
        .rename(columns={'lobbying_spend': 'annual_spend_usd'})
    )
    annual['annual_spend_m'] = (annual['annual_spend_usd'] / 1e6).round(2)
    return annual


def compute_growth_rates(annual: pd.DataFrame) -> pd.DataFrame:
    """
    Compare pre-2022 vs post-2022 average annual spend.

    2022 is the inflection point because:
    - CHIPS Act signed Aug 2022
    - ChatGPT launched Nov 2022 → AI regulation urgency surged
    - US-India iCET framework announced May 2022
    - Russia-Ukraine → defense procurement acceleration

    A company spending MORE post-2022 is directly responding to
    one of these structural policy shifts. That is your story.
    """
    pre  = (annual[annual['year'] <= 2021]
            .groupby('company')['annual_spend_usd'].mean()
            .rename('pre_2022_avg'))
    post = (annual[annual['year'] >= 2022]
            .groupby('company')['annual_spend_usd'].mean()
            .rename('post_2022_avg'))

    g = pd.concat([pre, post], axis=1)
    g['growth_pct'] = ((g['post_2022_avg'] - g['pre_2022_avg'])
                        / g['pre_2022_avg'] * 100).round(1)
    g['signal'] = g['growth_pct'].apply(
        lambda x: 'HIGH URGENCY' if x > 30
                  else ('ELEVATED' if x > 10
                  else 'STABLE/DECLINING')
    )
    return g.sort_values('growth_pct', ascending=False)


def india_exposure_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Flag and aggregate India-related lobbying from specific_issues text.
    Searches for keywords across the free-text field in each filing.
    """
    keywords = [
        'india', 'indian', 'icet', 'quad', 'dtti',
        'us-india', 'u.s.-india', 'major defense partner',
        'initiative on critical', 'hal ', 'bangalore',
        'mumbai', 'new delhi', 'rupee', 'indo-pacific'
    ]
    pattern = '|'.join(keywords)
    df['india_flag'] = (
        df['specific_issues'].fillna('').str.lower().str.contains(pattern)
    )

    india = (
        df[df['india_flag']]
        .groupby('company')
        .agg(
            india_filings=('india_flag', 'count'),
            india_spend_usd=('lobbying_spend', 'sum'),
            sample_issue=('specific_issues',
                          lambda x: x.dropna().iloc[0][:300] if len(x.dropna()) > 0 else '')
        )
        .sort_values('india_spend_usd', ascending=False)
    )
    india['india_spend_m'] = (india['india_spend_usd'] / 1e6).round(2)
    return india


def agency_targeting_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Explode the pipe-separated agencies field and aggregate by company.

    Agency targets reveal strategic intent:
    - U.S. House / U.S. Senate → legislation focus
    - DOD / DSCA              → defense sales, ITAR
    - Commerce / BIS          → export controls, CHIPS
    - USTR                    → trade policy
    - Treasury / SEC          → financial regulation
    - FTC / FCC               → tech/telecom regulation
    - NSC / State Dept        → foreign policy / India partnership
    """
    rows = []
    for _, row in df.iterrows():
        raw = str(row.get('agencies', '') or '')
        for agency in raw.split('|'):
            agency = agency.strip()
            if agency and agency != 'nan':
                rows.append({
                    'company': row['company'],
                    'sector':  row['sector'],
                    'agency':  agency,
                    'spend':   row['lobbying_spend']
                })
    agency_df = pd.DataFrame(rows)
    return agency_df


def compute_lobbying_intensity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Spend per filing = how much firepower per engagement.
    High intensity signals concentrated, high-value relationships.
    Low intensity signals volume strategy — many small firms.
    """
    intensity = (
        df.groupby('company')
        .agg(
            total_filings=('filing_uuid', 'count'),
            total_spend=('lobbying_spend', 'sum')
        )
    )
    intensity['spend_per_filing_k'] = (
        (intensity['total_spend'] / intensity['total_filings'] / 1000).round(1)
    )
    return intensity.sort_values('spend_per_filing_k', ascending=False)


# ============================================================
# SECTION 3: COMPANY PROFILE BUILDER (feeds Claude API)
# ============================================================

def build_company_profiles(df, annual, growth_df, india_df, agency_df):
    """
    Assemble one data package per company.
    This JSON feeds directly into the Claude API brief generator on Day 2.
    """
    profiles = {}

    for co in df['company'].dropna().unique():
        co_rows    = df[df['company'] == co]
        co_annual  = annual[annual['company'] == co]

        # Top 3 agencies by spend
        co_agencies = (
            agency_df[agency_df['company'] == co]
            .groupby('agency')['spend'].sum()
            .nlargest(3).index.tolist()
        )

        # Sample specific issue text
        sample_issues = (
            co_rows['specific_issues'].dropna().iloc[0][:250]
            if len(co_rows['specific_issues'].dropna()) > 0 else ''
        )

        # India stats
        india_row = india_df.loc[co] if co in india_df.index else None

        # Growth
        growth_row = growth_df.loc[co] if co in growth_df.index else None

        profiles[co] = {
            'sector':        co_rows['sector'].iloc[0],
            'total_spend_m': round(co_annual['annual_spend_usd'].sum() / 1e6, 1),
            'growth_pct':    float(growth_row['growth_pct']) if growth_row is not None else 0,
            'signal':        growth_row['signal'] if growth_row is not None else 'UNKNOWN',
            'top_agencies':  ', '.join(co_agencies) if co_agencies else 'N/A',
            'india_filings': int(india_row['india_filings']) if india_row is not None else 0,
            'india_spend_m': float(india_row['india_spend_m']) if india_row is not None else 0.0,
            'sample_issue':  sample_issues,
        }

    return profiles


def generate_brief_prompt(company: str, p: dict) -> str:
    """
    Prompt template for Claude API.
    Sent once per company on Day 2 to generate strategic briefs.
    """
    return f"""You are a senior government affairs analyst writing a strategic brief
for a BD director at a consulting firm. Based on the lobbying data below,
write a 3-sentence strategic summary answering:
1. What is this company's core government affairs priority?
2. What does their post-2022 spending trajectory signal about strategic intent?
3. What does this mean for companies trying to partner with or compete against them?

Company: {company}
Sector: {p['sector']}
Total 5-year lobbying spend: ${p['total_spend_m']}M
Post-2022 spending growth: {p['growth_pct']:+.1f}%
Urgency signal: {p['signal']}
Top agencies targeted: {p['top_agencies']}
India-related filings: {p['india_filings']} (${p['india_spend_m']}M)
Sample issue text: {p['sample_issue']}

Write in the voice of a McKinsey or Deloitte analyst briefing a C-suite client.
Be specific. Name the strategic implication. No hedging language."""


# ============================================================
# SECTION 4: EXPORT
# ============================================================

def export_all(annual, growth_df, india_df, agency_df, profiles):
    os.makedirs("outputs", exist_ok=True)

    annual.to_csv("outputs/dashboard_annual_spend.csv", index=False)
    growth_df.reset_index().to_csv("outputs/dashboard_growth.csv", index=False)
    india_df.reset_index().to_csv("outputs/dashboard_india.csv", index=False)

    # Top agencies per company
    top_agencies = (
        agency_df.groupby(['company', 'agency'])['spend']
        .sum().reset_index()
        .sort_values(['company', 'spend'], ascending=[True, False])
    )
    top_agencies.to_csv("outputs/dashboard_agencies.csv", index=False)

    with open("outputs/company_profiles.json", 'w') as f:
        json.dump(profiles, f, indent=2)

    print("✓ Exported to outputs/:")
    print("  dashboard_annual_spend.csv  → Tableau trend charts")
    print("  dashboard_growth.csv        → Growth heatmap")
    print("  dashboard_india.csv         → India spotlight")
    print("  dashboard_agencies.csv      → Agency targeting chart")
    print("  company_profiles.json       → Claude API brief generator")


# ============================================================
# SECTION 5: MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("INFLUENCE INTELLIGENCE BRIEF — ANALYSIS PIPELINE")
    print("=" * 60 + "\n")

    # Load
    df = load_data("data/raw/lda_raw_pull.csv")

    # Analyze
    annual    = build_annual_summary(df)
    growth_df = compute_growth_rates(annual)
    india_df  = india_exposure_analysis(df)
    agency_df = agency_targeting_analysis(df)
    intensity = compute_lobbying_intensity(df)

    # Print findings
    print("=" * 60)
    print("FINDING 1: POST-2022 SPENDING ACCELERATION")
    print("=" * 60)
    print(growth_df[['pre_2022_avg','post_2022_avg','growth_pct','signal']].to_string())

    print("\n" + "=" * 60)
    print("FINDING 2: INDIA-RELATED LOBBYING ACTIVITY")
    print("=" * 60)
    if len(india_df) > 0:
        print(india_df[['india_filings','india_spend_m']].to_string())
    else:
        print("No India-related filings detected.")
        print("Note: specific_issues field may be sparse in real LDA data.")
        print("This is expected — we will enrich this on Day 2.")

    print("\n" + "=" * 60)
    print("FINDING 3: LOBBYING INTENSITY (spend per filing $K)")
    print("=" * 60)
    print(intensity[['total_filings','spend_per_filing_k']].to_string())

    print("\n" + "=" * 60)
    print("FINDING 4: ANNUAL SPEND TREND")
    print("=" * 60)
    pivot = annual.pivot_table(
        index='company', columns='year',
        values='annual_spend_m', aggfunc='sum'
    ).round(1)
    print(pivot.to_string())

    # Build profiles and export
    profiles = build_company_profiles(df, annual, growth_df, india_df, agency_df)
    export_all(annual, growth_df, india_df, agency_df, profiles)

    # Show sample Claude prompt
    sample = list(profiles.keys())[0]
    print(f"\n{'='*60}")
    print(f"SAMPLE CLAUDE API PROMPT — {sample}")
    print("=" * 60)
    print(generate_brief_prompt(sample, profiles[sample]))

    print("\n✓ Day 1 analysis complete.")
    print("  Next: Day 2 — Claude API briefs + Tableau dashboard build.")