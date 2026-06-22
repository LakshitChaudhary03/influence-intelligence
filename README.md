# Influence Intelligence Brief
### Federal Lobbying Intelligence Pipeline | 2020–2025

A data pipeline and analytics project mapping **$684.8M in federal 
lobbying spend** across 10 major US companies — built from 3,007 
verified filings pulled directly from the US Senate LDA API.

---

## Live Dashboard
[View on Tableau Public](https://public.tableau.com/app/profile/lakshit.chaudhary/viz/InfluenceIntelligenceBrief)

Two interactive dashboards:
- **Influence Intelligence Brief** — Spending trends, heatmap, 
  growth rankings, agency targeting
- **US–India Corridor** — $595.6M in India-relevant lobbying 
  across defense, tech, and finance sectors

---

## Companies Analyzed
| Sector | Companies |
|--------|-----------|
| Tech/AI | Google, Microsoft, NVIDIA, Apple, Qualcomm |
| Finance | JPMorgan Chase, Goldman Sachs |
| Defense/Aerospace | GE Aerospace, Boeing, Lockheed Martin |

---

## Key Findings

**1. NVIDIA: 1,359% Emergency**
NVIDIA spent $600K lobbying in all of 2024. In Q1–Q2 2025 alone 
they spent $9.3M — a direct response to Biden-era AI chip export 
controls threatening 75% of their international revenue.

**2. Tech outspends Defense on India**
Tech/AI companies ($315.6M) outspend Defense/Aerospace ($257.6M) 
on India-relevant lobbying — reframing the US-India relationship 
as a technology story, not just a defense story.

**3. The 2022 Inflection Point**
Every major spending acceleration traces to three simultaneous 
events: CHIPS Act (Aug 2022), US-India iCET framework (May 2022), 
and the emergence of federal AI regulation (late 2022).

**4. The Regulatory Moat**
JPMorgan Chase's distributed lobbying model — filing through 
dozens of outside firms — reveals how large institutions use 
complex compliance rules to structurally disadvantage smaller 
competitors.

---

## Pipeline Architecture
```
US Senate LDA API

↓

fetch_lda_data.py        # API acquisition + entity resolution

↓

influence_intelligence_analysis.py  # Cleaning + analysis

↓

outputs/                 # Dashboard-ready CSVs

↓

Tableau Public           # Interactive visualization

↓

Claude API               # AI-generated strategic briefs
```
## Data Source
- **Primary:** US Senate Lobbying Disclosure Act (LDA) Database
- **URL:** lda.senate.gov
- **Legal basis:** Lobbying Disclosure Act of 1995, 2 U.S.C. § 1601
- **Filings:** 3,007 unique filing UUIDs, zero duplicates
- **Years:** 2020–2025 (2025 = Q1–Q2 only, annualized)

**Methodology note:** India-relevant filings identified by issue 
code classification (DEF, TRD, TEC, AER, FOR, INT, COM). Filings 
may address multiple policy areas beyond US-India specifically.

---

## Tools
- **Python** — pandas, urllib (data acquisition + analysis)
- **Claude API** — claude-sonnet-4-6 (strategic brief generation)
- **Tableau Public** — interactive dashboard
- **ReportLab** — PDF report generation

---

*Prepared by Lakshit Chaudhary | 2026 | office.lcms1@gmail.com*
