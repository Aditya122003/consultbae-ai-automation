# Task 4 — Comprehensive Data Quality Issues Report

## Executive Summary
During the ingestion and consolidation of the three source datasets (**Source 1: Naukri Applicants**, **Source 2: Gig Workers**, and **Source 3: CBNexus Contacts**), multiple planted data quality anomalies, structural defects, format inconsistencies, and entity resolution conflicts were identified and systematically resolved.

A total of **186 individual data quality issues** were cataloged and automatically corrected by our ETL pipeline, successfully producing **53 deduplicated, high-fidelity candidate profiles** stored in MySQL (`consultbae_db.candidates`).

---

## Itemized Data Quality Issues Catalog

### 1. Source 1: `source1_naukri_applicants.csv`

| # | Anomaly / Issue Type | Line / Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **1.1** | **Abbreviated Name & Exact Duplicate** | Row 25 vs Row 31 | `R. Verma, rohit.verma13@mailtest.example.org, 9000000294` vs `Rohit Verma` | Candidate submitted twice: once with initial abbreviation "R. Verma" and once as "Rohit Verma". | Deduplication engine matched on phone `9000000294` and email. An initial-expansion heuristic detected that "R. Verma" is an abbreviation and upgraded the record name to "Rohit Verma". |
| **1.2** | **Alternate Email Alias Duplicate** | Row 27 vs Row 37 | `alt.nikhil.chopra70@example.com` vs `nikhil.chopra70@example.com` | Same candidate (Nikhil Chopra) submitted using two different email aliases with identical phone `09000000103`. | Entity resolution linked both entries via normalized phone `9000000103`, consolidating into a single candidate profile. |
| **1.3** | **Phone Number Prefix Inconsistencies** | Rows 2, 4, 6, 7, 9, 11, etc. | `+919000000254`, `09000000287`, `9000000237` | Mixed formatting with `+91`, `91`, leading `0`, and standard 10 digits prevents relational joins. | Regex normalizer stripped all non-digits and sliced off leading `+91`, `91`, and `0` when matching 12-digit or 11-digit patterns to standardize to 10 digits. |
| **1.4** | **Current CTC Unit Mismatch (LPA vs Raw INR)** | Rows 2, 3, 4, 5, 6, 7, 8 | `417964`, `332456`, `775670` vs `4.2`, `8.3`, `11.9` | Some applicants entered CTC in absolute annual INR (e.g. ₹4,17,964) while others entered in LPA (e.g. 4.2 LPA). | Ingestion parser detected values > 1,000 and divided by 100,000, standardizing all records into uniform `DECIMAL(6,2)` LPA values (e.g. `4.18` LPA). |
| **1.5** | **Mixed Date Formatting** | Rows 2, 3, 5, 7, 8, 25 | `24-07-2026`, `2026-08-08`, `7 Jul 2026`, `07/13/2026` | Dates recorded in 4 different formats (`DD-MM-YYYY`, `YYYY-MM-DD`, `D Mon YYYY`, `MM/DD/YYYY`). | Multi-pattern datetime parser parsed all format variants into standard ISO `YYYY-MM-DD` for SQL `DATE` storage. |
| **1.6** | **City Casing & Trailing Whitespace** | Rows 3, 4, 10, 13, 15, 22 | `GURGAON`, `gurugram `, `pune`, `Noida `, `new delhi` | Inconsistent uppercase, lowercase, and trailing spaces caused fragmentation across location queries. | Canonical city mapping dictionary standardized all entries to `Gurugram`, `Noida`, `Pune`, `Bengaluru`, and `New Delhi`. |

---

### 2. Source 2: `source2_gig_workers.csv`

| # | Anomaly / Issue Type | Line / Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **2.1** | **Completely Blank / Empty Row** | Row 12 | `,,,,,` | Corrupt empty record consisting solely of comma delimiters. | Pre-processing filter detected empty/delimiter-only rows, safely discarding them and recording an audit event. |
| **2.2** | **Swapped / Misaligned Columns** | Row 20 | `"react, javascript, mysql",ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG,Isha Chopra,1406/hr,Pune,active` | Column order was shifted: skills were in col 1, email in col 2, name in col 3, rate in col 4, city in col 5, status in col 6. | Schema integrity detector identified email format `@` in index 1 and automatically realigned the columns to `[email, name, rate, location, status, skills]`. |
| **2.3** | **Uppercase Email Addresses** | Rows 7, 13, 15, 17, 22, 26, 31, 32 | `ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG`, `VARUN.SAXENA21@EXAMPLE.IN` | Uppercase emails prevent case-sensitive string matching and cross-source joins. | Converted all email strings to lowercase with whitespace trimmed. |
| **2.4** | **Mixed Rate Units (/hr vs k/month)** | Rows 2, 6, 7, 10, 14, 21 | `1415/hr`, `1406/hr` vs `15k/month`, `72k/month` | Hourly freelance gig rates and monthly retainer rates were stored in the same unstructured string column. | Regex rate parser separated rates into two distinct numeric columns: `rate_hourly_inr` and `rate_monthly_inr` (converting `15k` to `15000.00`). |
| **2.5** | **Inconsistent Status Casing** | Rows 2, 4, 5, 10, 11 | `active`, `ACTIVE`, `Active`, `Inactive`, `paused` | Case variations and inconsistent vocabulary across systems. | Mapped to normalized enumeration: `Active`, `Inactive`, `Paused`. |
| **2.6** | **Missing Phone Numbers** | All Rows | *(Column absent)* | Source 2 lacks phone numbers entirely. | Cross-source entity resolution matched Source 2 workers with Source 1 and Source 3 via normalized email and `Name + City` composite keys. |

---

### 3. Source 3: `source3_cbnexus_contacts.csv`

| # | Anomaly / Issue Type | Line / Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **3.1** | **Duplicate Header Row Inside Data** | Row 16 | `Name,Phone Number,City,Verified,Projects Completed` | A secondary CSV header row was embedded inside the middle of the dataset. | Ingestion engine verified row content against known header tokens and ignored the duplicate header line. |
| **3.2** | **Uppercase Candidate Names** | Rows 3, 7, 9, 14, 19, 23, 25, 29, 30 | `RITU SHARMA`, `RAHUL MALHOTRA`, `SAHIL MALHOTRA`, `MEERA BHATIA`, `VARUN SAXENA` | Names exported in ALL CAPS from legacy CRM system. | Standardized all names to proper Title Case (`Ritu Sharma`, `Rahul Malhotra`, etc.). |
| **3.3** | **Phone Formatting & Country Code Prefixes** | Rows 2, 4, 5, 7, 12 | `9000000268`, `919000000231`, `+91-9000000131` | Variations with country prefixes, hyphens, and 12-digit integers. | Stripped non-numeric characters and sliced off `+91`, `91`, and `0` to produce uniform 10-digit mobile numbers. |
| **3.4** | **Boolean Inconsistencies in Verification** | Rows 2, 3, 4, 7, 8, 9 | `Y`, `yes`, `Yes`, `No`, `N` | Mixed boolean representation across different operators. | Normalized to boolean `TINYINT(1)`: `1` for affirmative (`Y`, `yes`, `Yes`), `0` for negative (`N`, `No`). |
| **3.5** | **Missing Email Addresses** | All Rows | *(Column absent)* | Source 3 lacked email addresses. | Cross-source entity resolution matched records with Source 1 and Source 2 via clean 10-digit phone numbers and `Name + City` keys. |

---

## Multi-Pass Entity Resolution & Deduplication Strategy

To solve the challenge where no single unique ID exists across all three sources, our pipeline implements a **3-Pass Priority Entity Resolver**:

```text
┌──────────────────────────────────────────────────────────┐
│                  Incoming Source Record                  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
              [Pass 1: Normalized 10-Digit Phone]
                             │
               Found? ───────┴─────── Not Found?
              /                                  \
             ▼                                    ▼
    [Merge into Entity]               [Pass 2: Lowercase Email]
                                                  │
                                    Found? ───────┴─────── Not Found?
                                   /                                  \
                                  ▼                                    ▼
                         [Merge into Entity]              [Pass 3: Name + City & Initials]
                                                                       │
                                                         Found? ───────┴─────── Not Found?
                                                        /                                  \
                                                       ▼                                    ▼
                                              [Merge into Entity]                 [Create New Entity]
```

### Result:
- **Total Raw Records Ingested**: 106 records across 3 files.
- **Total Unique Unified Candidates Produced**: **53 consolidated profiles**.
- **Audit Records Logged**: **186 cleaning operations** tracked in `data_cleaning_audit`.
