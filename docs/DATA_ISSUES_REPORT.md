# Task 4 — Comprehensive Data Quality Issues & Audit Report

## Executive Summary
During the ingestion, deduplication, and consolidation of ConsultBae's workforce datasets (**Source 1: Naukri Applicants**, **Source 2: Gig Workers**, **Source 3: CBNexus Contacts**, and **Source 4: Dynamic Candidate Batches**), multiple planted data quality anomalies, structural defects, format inconsistencies, and entity resolution conflicts were identified and systematically resolved.

A total of **186 individual data quality issues** were cataloged and automatically corrected by our Python ETL pipeline (`pipeline/ingest_and_merge.py`), producing **53 deduplicated, high-fidelity candidate profiles** stored in MySQL (`consultbae_db.candidates`). Every cleaning action is tracked in real-time in the `data_cleaning_audit` MySQL table and exposed via dynamic API endpoints for interactive UI rendering and CSV export.

---

## 📊 6-Column Data Quality Issues Catalog

### 1. Source 1: `source1_naukri_applicants.csv`

| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 1** | **Abbreviated Name & Duplicate** | Row 25 vs 31 | `R. Verma, rohit.verma13@mailtest.example.org, 9000000294` vs `Rohit Verma` | Candidate submitted twice: once with initial abbreviation ("R. Verma") and once as "Rohit Verma". | Priority entity resolver matched on phone `9000000294` and email. Initial-expansion heuristic expanded "R. Verma" to canonical "Rohit Verma". |
| **Source 1** | **Alternate Email Alias Duplicate** | Row 27 vs 37 | `alt.nikhil.chopra70@example.com` vs `nikhil.chopra70@example.com` | Same applicant submitted using two different email aliases with identical phone `09000000103`. | Entity matcher linked both entries via normalized 10-digit phone `9000000103`, consolidating into a single candidate profile. |
| **Source 1** | **Phone Number Prefix Inconsistencies** | Rows 2, 4, 6, 7, 9, 11 | `+919000000254`, `09000000287`, `9000000237` | Mixed formatting with country codes (`+91`, `91`) and leading zeroes (`0`) broke relational queries. | Regex normalizer stripped non-digits and sliced off leading `+91`, `91`, and `0` to produce uniform 10-digit integers. |
| **Source 1** | **Current CTC Unit Mismatch (LPA vs Raw INR)** | Rows 2, 3, 4, 5, 6, 7 | `417964`, `332456` vs `4.2`, `8.3` | Applicants entered CTC in absolute annual INR (e.g. ₹4,17,964) while others entered in LPA (e.g. 4.2 LPA). | Ingestion parser detected values > 1,000, dividing by 100,000 to standardize into uniform `DECIMAL(6,2)` LPA values (e.g. `4.18` LPA). |
| **Source 1** | **Mixed Date Formatting** | Rows 2, 3, 5, 7, 8, 25 | `24-07-2026`, `2026-08-08`, `7 Jul 2026`, `07/13/2026` | Dates recorded in 4 distinct formats (`DD-MM-YYYY`, `YYYY-MM-DD`, `D Mon YYYY`, `MM/DD/YYYY`). | Multi-pattern datetime parser converted all date variants into standard ISO `YYYY-MM-DD` for SQL `DATE` storage. |
| **Source 1** | **City Casing & Trailing Whitespace** | Rows 3, 4, 10, 13, 15 | `GURGAON`, `gurugram `, `pune`, `Noida ` | Uppercase, lowercase, and trailing spaces caused location query fragmentation. | Canonical city mapping dictionary standardized entries to `Gurugram`, `Noida`, `Pune`, `Bengaluru`, and `New Delhi`. |

---

### 2. Source 2: `source2_gig_workers.csv`

| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 2** | **Completely Blank Row** | Row 12 | `,,,,,` | Corrupt empty record consisting solely of comma delimiters. | Pre-processing filter detected delimiter-only rows, safely discarding them and logging an audit entry. |
| **Source 2** | **Swapped / Misaligned Columns** | Row 20 | `"react, javascript",ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG,Isha Chopra,1406/hr,Pune` | Column order shifted: skills in col 1, email in col 2, name in col 3, rate in col 4, city in col 5. | Schema integrity inspector identified `@` symbol in column 2 and realigned fields to `[email, name, rate, city, status, skills]`. |
| **Source 2** | **Uppercase Email Addresses** | Rows 7, 13, 15, 17, 22 | `ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG` | Uppercase emails prevent case-sensitive string matching and cross-source joins. | Converted all email strings to lowercase with whitespace trimmed. |
| **Source 2** | **Mixed Rate Units (/hr vs k/month)** | Rows 2, 6, 7, 10, 14 | `1415/hr`, `1406/hr` vs `15k/month`, `72k/month` | Freelance hourly rates and monthly retainers stored in the same unstructured string column. | Regex parser split rates into two distinct numeric columns: `rate_hourly_inr` and `rate_monthly_inr` (converting `15k` to `15000.00`). |
| **Source 2** | **Inconsistent Status Vocabulary** | Rows 2, 4, 5, 10, 11 | `active`, `ACTIVE`, `Active`, `paused` | Vocabulary variations across freelance systems. | Standardized to normalized ENUM values: `Active`, `Inactive`, `Paused`. |
| **Source 2** | **Missing Phone Column** | All Rows | *(Column absent)* | Source 2 lacks phone numbers entirely. | Priority entity resolver matched Source 2 workers with Source 1 and Source 3 via normalized email and `Name + City` composite keys. |

---

### 3. Source 3: `source3_cbnexus_contacts.csv`

| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 3** | **Embedded Duplicate Header** | Row 16 | `Name,Phone Number,City,Verified,Projects Completed` | A secondary CSV header row was embedded inside the middle of dataset export. | Ingestion engine verified row values against header tokens and filtered out embedded header lines. |
| **Source 3** | **Uppercase Candidate Names** | Rows 3, 7, 9, 14, 19 | `RITU SHARMA`, `RAHUL MALHOTRA`, `SAHIL MALHOTRA` | Names exported in ALL CAPS from legacy CRM system. | Standardized names to proper Title Case (`Ritu Sharma`, `Rahul Malhotra`, etc.). |
| **Source 3** | **Phone Prefix Inconsistencies** | Rows 2, 4, 5, 7, 12 | `9000000268`, `919000000231`, `+91-9000000131` | Variations with country code prefixes, hyphens, and 12-digit integers. | Stripped non-numeric characters and sliced off `+91`, `91`, and `0` to produce uniform 10-digit mobile numbers. |
| **Source 3** | **Boolean Inconsistencies** | Rows 2, 3, 4, 7, 8 | `Y`, `yes`, `Yes`, `No`, `N` | Mixed boolean strings across different operators. | Normalized to boolean `TINYINT(1)`: `1` for affirmative (`Y`, `yes`, `Yes`), `0` for negative (`N`, `No`). |
| **Source 3** | **Missing Email Column** | All Rows | *(Column absent)* | Source 3 lacked email addresses. | Cross-source entity matcher linked records with Source 1 and Source 2 via 10-digit phone numbers and `Name + City` composite keys. |

---

## 🔀 Multi-Pass Entity Resolution Engine Architecture

To solve cross-source fragmentation without a universal unique key, our pipeline (`pipeline/entity_matcher.py`) executes a **3-Pass Priority Entity Resolution Engine**:

```text
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Incoming Raw CSV Record                               │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │
                                         ▼
                     [Pass 1: Normalized 10-Digit Phone Match]
                                         │
                      Found? ────────────┴──────────── Not Found?
                     /                                           \
                    ▼                                             ▼
        [Merge into Existing Candidate]              [Pass 2: Lowercase Email Match]
                                                                  │
                                               Found? ────────────┴──────────── Not Found?
                                              /                                           \
                                             ▼                                             ▼
                                 [Merge into Existing Candidate]          [Pass 3: Name + City & Initial Match]
                                                                                           │
                                                                       Found? ─────────────┴───────────── Not Found?
                                                                      /                                             \
                                                                     ▼                                               ▼
                                                         [Merge into Existing Candidate]               [Provision New Candidate Profile]
```

### Ingestion Metrics Summary:
- **Total Raw CSV Rows Processed**: 106 records across 3 core source datasets.
- **Unified Canonical Candidates Produced**: **53 consolidated profiles**.
- **Audit Remediation Events Logged**: **186 automated cleaning actions** stored in `data_cleaning_audit`.

---

## 🔄 Dynamic Audit Pipeline & Real-Time Sync

### 1. Database Audit Table Schema (`data_cleaning_audit`)
```sql
CREATE TABLE IF NOT EXISTS data_cleaning_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_file VARCHAR(255) NOT NULL,
    issue_type VARCHAR(100) NOT NULL,
    csv_rows_affected VARCHAR(255) NOT NULL,
    raw_example TEXT,
    root_cause TEXT,
    automated_fix TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. REST API & Reactive Frontend Synchronization
- **`GET /api/audit/logs`**: Queries `data_cleaning_audit` dynamically from MySQL and returns structured JSON.
- **`GET /api/audit/download-csv`**: Generates a formatted CSV file on-the-fly directly from MySQL table state.
- **Angular RxJS Event Bus**: When users upload new CSV batches (e.g. `source4_candidates.csv`) or trigger database purges via the candidate directory UI, an RxJS `BehaviorSubject` automatically refetches audit logs and updates both KPI cards and the 6-column Angular table reactively without page reloads.
