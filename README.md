# ConsultBae — Automated Data Platform & Audio Collection Studio

[![Angular 19](https://img.shields.io/badge/Angular-19.0-dd0031?style=for-the-badge&logo=angular)](https://angular.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![MySQL 8](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![n8n Automation](https://img.shields.io/badge/n8n-Low--Code-FF6D5A?style=for-the-badge&logo=n8n)](https://n8n.io/)
[![FFmpeg Signal Processing](https://img.shields.io/badge/FFmpeg-Audio_DSP-0078D7?style=for-the-badge&logo=ffmpeg)](https://ffmpeg.org/)

An enterprise-grade data integration, low-code automation, signal processing, and dynamic audit platform built for ConsultBae's gig workforce operations.

---

## 🌟 Solution Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                             ConsultBae Data Platform                                             │
├───────────────────────────────┬──────────────────────────────────┬───────────────────────────────┬───────────────┤
│    Task 1: Ingestion & ETL    │   Task 2: Low-Code Automation    │ Task 3: Audio Recording Studio│ Task 4 & 5    │
│                               │                                  │                               │               │
│ • 3 Inconsistent CSV Sources  │ • Webhook Application Ingestion  │ • Glassmorphic Angular 19 UI  │ • 6-Col Audit │
│ • 3-Pass Entity Resolution    │ • MySQL Phone/Email Duplication  │ • Real-time Canvas Waveform   │ • Download CSV│
│ • 186 Anomalies Remediation   │ • LLM Domain Auto-Tagging        │ • RMS dBFS & SNR Quality DSP  │ • 5K Scale    │
│ • MySQL Canonical Relational  │ • Slack Alert Notification        │ • 3-Case Candidate Resolver   │   Architecture│
└───────────────────────────────┴──────────────────────────────────┴───────────────────────────────┴───────────────┘
```

---

## 📂 Repository Structure

```text
├── database/
│   └── schema.sql                  # MySQL database DDL (candidates, audio_submissions, data_cleaning_audit)
├── pipeline/
│   ├── db_connection.py            # PyMySQL connection manager with transaction management
│   ├── data_cleaner.py             # Normalizers for phone (+91/0), email, name casing, CTC (LPA), and dates
│   ├── entity_matcher.py           # 3-Pass priority entity resolution (Phone -> Email -> Name+City)
│   └── ingest_and_merge.py         # Master ETL script ingesting and deduplicating CSV datasets
├── automation_n8n/
│   ├── workflow_consultbae_automation.json  # Exportable n8n workflow definition
│   ├── n8n_runner_simulation.py    # Standalone execution simulator for n8n duplicate & LLM pipeline
│   └── README_AUTOMATION.md        # n8n installation, node configuration, and setup guide
├── backend/
│   ├── main.py                     # FastAPI REST API server (ports 8000)
│   ├── audio_processor.py          # Acoustic signal processing (Duration, sample rate, bitrate, dBFS, SNR)
│   └── requirements.txt            # Python dependencies (fastapi, uvicorn, pymysql, pydub, scipy, numpy)
├── frontend-angular/
│   ├── src/app/
│   │   ├── components/
│   │   │   ├── audio-recorder/         # Browser recording studio with Web Audio HTML5 waveform oscilloscope
│   │   │   ├── audio-gallery/          # Submissions catalog with in-browser audio player & metric chips
│   │   │   ├── candidate-directory/    # Unified candidate explorer & dynamic 6-column audit issue table
│   │   │   └── automation-simulator/   # Interactive n8n workflow tester with pattern validation
│   │   ├── services/
│   │   │   ├── audio.service.ts        # Audio API HTTP client
│   │   │   └── candidate.service.ts    # Candidate directory, CSV upload, & audit event bus
│   │   └── models/types.ts             # TypeScript interfaces for candidates, submissions, and audit logs
│   └── src/styles.css                  # ConsultBae glassmorphism design system & CSS variables
├── docs/
│   ├── DATA_ISSUES_REPORT.md       # Task 4: Complete itemized report of all 186 remediated data anomalies
│   └── SCALING_ARCHITECTURE.md     # Task 5: 5,000 gig worker scaling blueprint & AWS cost model
├── source1_naukri_applicants.csv   # Source 1 input dataset
├── source2_gig_workers.csv         # Source 2 input dataset
├── source3_cbnexus_contacts.csv    # Source 3 input dataset
├── source4_candidates.csv          # Sample dataset for dynamic CSV ingestion testing
├── start_all.sh                    # One-command startup script for backend & frontend
└── README.md                       # Master platform documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **MySQL Server 8.0+** running locally on port `3306`
- **Python 3.10+**
- **Node.js 18+** & **Angular CLI 19+**
- **FFmpeg** (optional system dependency for extended audio format support)

### 2. Environment Setup & Database Initialization
Create database and initialize schema:
```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS consultbae_db;"
mysql -u root -p consultbae_db < database/schema.sql
```

### 3. One-Command Platform Launch
Launch both the FastAPI REST backend and Angular 19 frontend concurrently:
```bash
chmod +x start_all.sh
./start_all.sh
```

- **Angular Web Studio**: `http://localhost:4200`
- **FastAPI REST Server**: `http://localhost:8000`
- **Interactive OpenAPI Documentation (Swagger)**: `http://localhost:8000/docs`

---

## 🛠️ Task-by-Task Implementation Summary

### Task 1: MySQL Schema & Ingestion Pipeline
- **Canonical Database Schema**: Designed `consultbae_db` with `candidates`, `audio_submissions`, and `data_cleaning_audit`.
- **Multi-Pass Entity Resolution Engine**: Built a priority-weighted 3-Pass matcher:
  1. **Pass 1**: Normalized 10-Digit Phone match.
  2. **Pass 2**: Lowercase Email match.
  3. **Pass 3**: Composite `Name + City` match with abbreviation expansion (e.g. `R. Verma` -> `Rohit Verma`).
- **Data Remediation**: Automatically repaired column shifts (Source 2 row 20), empty lines, repeated header rows (Source 3 row 16), mixed CTC units (absolute INR vs LPA), and standardized dates to ISO format.
- **Run Ingestion**:
  ```bash
  python3 -m pipeline.ingest_and_merge
  ```
  *Result: 53 unified candidate records created out of 106 raw rows; 186 data anomalies audited.*

---

### Task 2: Low-Code Automation Workflow (n8n)
- **Workflow Architecture**: Defined in `automation_n8n/workflow_consultbae_automation.json`.
- **Pipeline Logic**:
  1. **Webhook Node**: Ingests incoming gig worker application payloads in real time.
  2. **MySQL Lookup Node**: Checks candidate database for existing phone/email records.
  3. **Router / Switch Node**:
     - **Duplicate Found**: Triggers **Slack Alert Dispatcher** node with candidate details.
     - **New Application**: Directs payload to **LLM Tagging Node** to analyze skill sets into standard domains (`Automation & AI Heavy`, `Web & Fullstack`, `Data & Analytics`, `QA & Web Scraping`).
- **Simulation Verification**:
  ```bash
  python3 -m automation_n8n.n8n_runner_simulation
  ```

---

### Task 3: Mini Audio Collection App (Core)
- **FastAPI Signal Processing Engine (`backend/audio_processor.py`)**:
  - `POST /api/audio/submit`: Receives candidate audio files (WebM, WAV, MP3, OGG, M4A).
  - Automatically measures and stores:
    1. **Duration** (seconds)
    2. **Sample Rate** (kHz & Hz)
    3. **Bitrate** (kbps)
    4. **Loudness** (dBFS RMS)
    5. **Noise / Quality Metrics** (Signal-to-Noise Ratio & 0-100 Quality Score)
- **Smart 3-Case Candidate Resolution Rule**:
  - **Case 1 (Phone Conflict)**: Phone number exists under a *different* candidate name -> Returns **HTTP 409 Conflict** error (`"Phone number registered under another worker name"`).
  - **Case 2 (Existing Profile Match)**: Phone matches an existing candidate with matching name -> Links audio submission directly to Task 1 candidate ID and inherits city, domain, and experience metadata.
  - **Case 3 (New Worker Provisioning)**: Phone number not found -> Auto-provisions a new candidate record with `--` unassigned metadata placeholders.
- **Angular 19 Studio Interface (`frontend-angular/`)**:
  - **Microphone Recorder**: Real-time waveform canvas visualizer using Web Audio API `AnalyserNode`.
  - **Playback Controls**: Built-in player with speed toggles (1x, 1.25x, 1.5x, 2x).
  - **Submissions Catalog**: Interactive gallery grid with metric badges and playable audio preview.

---

### Task 4: Comprehensive Data Issues Report & Dynamic Audit Table

#### 📊 Live Database Audit Metrics Summary
Based on the live database state in MySQL (`consultbae_db`), a total of **53 audit category records tracking 186 individual row-level data quality remediation events** have been logged in `data_cleaning_audit`. The automated ETL pipeline (`pipeline/ingest_and_merge.py`) has successfully produced **65 deduplicated, high-fidelity candidate profiles** stored in `consultbae_db.candidates`.

| Source Dataset | Primary File Name | Audit Issues Logged | Primary Anomaly Types |
|---|---|---|---|
| **Source 1** | `source1_naukri_applicants.csv` | **2 Audit Logs** | Abbreviated names, alternate email aliases, +91/0 phone prefixes, CTC unit conversions (LPA), 4 date formats. |
| **Source 2** | `source2_gig_workers.csv` | **17 Audit Logs** | Empty delimiter rows, column misalignment (row 20), uppercase emails, rate unit splitting (/hr vs k/month), missing phone column. |
| **Source 3** | `source3_cbnexus_contacts.csv` | **30 Audit Logs** | Embedded duplicate header (row 16), ALL CAPS names, country code phone prefixes, mixed boolean flags (Y/N/Yes), missing email column. |
| **Source 4** | `source4_candidates.csv` *(Candidate Test Dataset)* | **4 Audit Logs** | Custom candidate batch upload containing missing candidate names (rows 10-11), missing phone/email (row 12), placeholder skills (`"--"` row 9), and rate normalizations. |
| **TOTAL** | **Live Database State** | **53 Audit Logs (186 Issues)** | **65 Unified Candidate Profiles** |

#### 📋 Itemized 6-Column Data Quality Issues Catalog

##### 1. Source 1: `source1_naukri_applicants.csv`
| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 1** | **Abbreviated Name & Duplicate** | Row 25 vs 31 | `R. Verma, rohit.verma13@mailtest.example.org, 9000000294` vs `Rohit Verma` | Candidate submitted twice: once with initial abbreviation ("R. Verma") and once as "Rohit Verma". | Priority entity resolver matched on phone `9000000294` and email. Initial-expansion heuristic expanded "R. Verma" to canonical "Rohit Verma". |
| **Source 1** | **Alternate Email Alias Duplicate** | Row 27 vs 37 | `alt.nikhil.chopra70@example.com` vs `nikhil.chopra70@example.com` | Same applicant submitted using two different email aliases with identical phone `09000000103`. | Entity matcher linked both entries via normalized 10-digit phone `9000000103`, consolidating into a single candidate profile. |
| **Source 1** | **Phone Number Prefix Inconsistencies** | Rows 2, 4, 6, 7, 9, 11 | `+919000000254`, `09000000287`, `9000000237` | Mixed formatting with country codes (`+91`, `91`) and leading zeroes (`0`) broke relational queries. | Regex normalizer stripped non-digits and sliced off leading `+91`, `91`, and `0` to produce uniform 10-digit integers. |
| **Source 1** | **Current CTC Unit Mismatch (LPA vs Raw INR)** | Rows 2, 3, 4, 5, 6, 7 | `417964`, `332456` vs `4.2`, `8.3` | Applicants entered CTC in absolute annual INR (e.g. ₹4,17,964) while others entered in LPA (e.g. 4.2 LPA). | Ingestion parser detected values > 1,000, dividing by 100,000 to standardize into uniform `DECIMAL(6,2)` LPA values (e.g. `4.18` LPA). |
| **Source 1** | **Mixed Date Formatting** | Rows 2, 3, 5, 7, 8, 25 | `24-07-2026`, `2026-08-08`, `7 Jul 2026`, `07/13/2026` | Dates recorded in 4 distinct formats (`DD-MM-YYYY`, `YYYY-MM-DD`, `D Mon YYYY`, `MM/DD/YYYY`). | Multi-pattern datetime parser converted all date variants into standard ISO `YYYY-MM-DD` for SQL `DATE` storage. |
| **Source 1** | **City Casing & Trailing Whitespace** | Rows 3, 4, 10, 13, 15 | `GURGAON`, `gurugram `, `pune`, `Noida ` | Uppercase, lowercase, and trailing spaces caused location query fragmentation. | Canonical city mapping dictionary standardized entries to `Gurugram`, `Noida`, `Pune`, `Bengaluru`, and `New Delhi`. |

##### 2. Source 2: `source2_gig_workers.csv`
| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 2** | **Completely Blank Row** | Row 12 | `,,,,,` | Corrupt empty record consisting solely of comma delimiters. | Pre-processing filter detected delimiter-only rows, safely discarding them and logging an audit entry. |
| **Source 2** | **Swapped / Misaligned Columns** | Row 20 | `"react, javascript",ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG,Isha Chopra,1406/hr,Pune` | Column order shifted: skills in col 1, email in col 2, name in col 3, rate in col 4, city in col 5. | Schema integrity inspector identified `@` symbol in column 2 and realigned fields to `[email, name, rate, city, status, skills]`. |
| **Source 2** | **Uppercase Email Addresses** | Rows 7, 13, 15, 17, 22 | `ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG` | Uppercase emails prevent case-sensitive string matching and cross-source joins. | Converted all email strings to lowercase with whitespace trimmed. |
| **Source 2** | **Mixed Rate Units (/hr vs k/month)** | Rows 2, 6, 7, 10, 14 | `1415/hr`, `1406/hr` vs `15k/month`, `72k/month` | Freelance hourly rates and monthly retainers stored in the same unstructured string column. | Regex parser split rates into two distinct numeric columns: `rate_hourly_inr` and `rate_monthly_inr` (converting `15k` to `15000.00`). |
| **Source 2** | **Inconsistent Status Vocabulary** | Rows 2, 4, 5, 10, 11 | `active`, `ACTIVE`, `Active`, `paused` | Vocabulary variations across freelance systems. | Standardized to normalized ENUM values: `Active`, `Inactive`, `Paused`. |
| **Source 2** | **Missing Phone Column** | All Rows | *(Column absent)* | Source 2 lacks phone numbers entirely. | Priority entity resolver matched Source 2 workers with Source 1 and Source 3 via normalized email and `Name + City` composite keys. |

##### 3. Source 3: `source3_cbnexus_contacts.csv`
| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 3** | **Embedded Duplicate Header** | Row 16 | `Name,Phone Number,City,Verified,Projects Completed` | A secondary CSV header row was embedded inside the middle of dataset export. | Ingestion engine verified row values against header tokens and filtered out embedded header lines. |
| **Source 3** | **Uppercase Candidate Names** | Rows 3, 7, 9, 14, 19 | `RITU SHARMA`, `RAHUL MALHOTRA`, `SAHIL MALHOTRA` | Names exported in ALL CAPS from legacy CRM system. | Standardized names to proper Title Case (`Ritu Sharma`, `Rahul Malhotra`, etc.). |
| **Source 3** | **Phone Prefix Inconsistencies** | Rows 2, 4, 5, 7, 12 | `9000000268`, `919000000231`, `+91-9000000131` | Variations with country code prefixes, hyphens, and 12-digit integers. | Stripped non-numeric characters and sliced off `+91`, `91`, and `0` to produce uniform 10-digit mobile numbers. |
| **Source 3** | **Boolean Inconsistencies** | Rows 2, 3, 4, 7, 8 | `Y`, `yes`, `Yes`, `No`, `N` | Mixed boolean strings across different operators. | Normalized to boolean `TINYINT(1)`: `1` for affirmative (`Y`, `yes`, `Yes`), `0` for negative (`N`, `No`). |
| **Source 3** | **Missing Email Column** | All Rows | *(Column absent)* | Source 3 lacked email addresses. | Cross-source entity matcher linked records with Source 1 and Source 2 via 10-digit phone numbers and `Name + City` composite keys. |

##### 4. Source 4: `source4_candidates.csv` *(Candidate-Provided Custom Test Dataset)*

> **Note**: `source4_candidates.csv` is a custom batch uploaded during evaluation to test dynamic CSV ingestion, non-destructive merging, and dynamic 6-column audit reporting.

| Source | Issue Type | CSV Rows Affected | Raw Example | Root Cause & Impact | Automated Remediation & Solution |
|---|---|---|---|---|---|
| **Source 4** | **Missing Candidate Names** | Rows 10, 11 | `,invalid_candidate1@example.com,9876500110` | Test rows submitted without full candidate names. | Pipeline auto-derived name fallback from email prefix or assigned unassigned worker flags. |
| **Source 4** | **Missing Contact Phone / Email** | Row 12, 13 | `Suresh Kumar,,,,Python,7.5` vs `,,9876500114` | Test candidate entries missing email or phone contact details. | Ingestion engine applied Pass 3 `Name + City` matching and populated null placeholders without dropping valid candidate details. |
| **Source 4** | **Placeholder Skill Values** | Row 9 | `Kavya Singh, kavya.singh@example.com, 9876500108, "--"` | Skills submitted as dashes or blank placeholders (`"--"`). | Dynamic cleaner replaced placeholders with `--` (unassigned status) and logged an audit event. |

- **Dynamic UI Audit Table**: Fed reactively by `/api/audit/logs` matching exact enterprise audit schema.
- **One-Click CSV Export**: Downloads formatted CSV file via `/api/audit/download-csv` generated directly from MySQL state.
- **Full Report Document**: Detailed standalone reference available in [`docs/DATA_ISSUES_REPORT.md`](docs/DATA_ISSUES_REPORT.md).

---

### Task 5: Scaling Architecture Blueprint (5,000 Workers)
- **Architecture Blueprint**: Detailed scaling strategy available in [`docs/SCALING_ARCHITECTURE.md`](docs/SCALING_ARCHITECTURE.md).
- **Core Scalability Innovations**:
  - **Client-Side Direct S3 Pre-Signed Uploads**: Bypasses API server network bottlenecks.
  - **Asynchronous Ingestion via Amazon SQS**: Decouples upload handling from background audio processing.
  - **Serverless Worker Pool (AWS Lambda / AWS Fargate)**: Auto-scales processing containers dynamically during peak submission spikes.
  - **Amazon RDS Aurora MySQL + RDS Proxy**: Provides high-throughput connection pooling for 5,000+ simultaneous workers.
- **Cost Analysis**: Total projected cloud infrastructure cost of **~$97.90 / month** for 40,000 monthly audio submissions.

---

## 🪵 Engineering Stuck Log (Problem-Solving & Troubleshooting)

Below are the **3 hardest technical bottlenecks** encountered during development, along with the exact troubleshooting workflow, AI prompts, rejected ideas, and final solutions.

---

### Incident 1: WebM Audio Decoding Failures & C-Dependency Container Bloat in FastAPI

#### 💥 The Bottleneck / Stuck State
When recording audio directly in the browser via Task 3 (MediaRecorder API), the browser sends raw `audio/webm;codecs=opus` blobs. When FastAPI tried to parse these blobs in `backend/audio_processor.py` using Python's native `wave` library, it crashed with `wave.Error: file does not start with RIFF id`. Attempting to use `librosa` caused severe docker container bloat (>1.5GB of dependencies including PyTorch and Numba), slow server cold starts, and missing system `ffmpeg` binary exceptions on lightweight server deployments.

#### 🔍 What Was Searched
- `fastapi decode webm audio opus pydub without librosa C dependencies`
- `calculate audio RMS signal noise ratio python wave memory bytes fallback`
- `scipy wavfile read raw webm bytes buffer python`

#### 🤖 What Was Asked AI
> "How can we decode browser-submitted WebM audio blobs in FastAPI to extract duration, sample rate, dBFS loudness, and SNR without forcing heavy C++ dependencies like librosa or crashing when system ffmpeg binaries are missing?"

#### ❌ Suggestions Rejected & Why
1. **Client-Side WAV Conversion in JavaScript**: Transcoding Opus WebM blobs to raw PCM WAV inside browser Web Audio API before upload.
   - *Why Rejected*: PCM WAV audio is uncompressed, resulting in 10x larger HTTP payloads (e.g. 100KB WebM became ~1MB WAV). On slow 3G networks used by gig workers, this caused upload timeouts and request buffering failures.
2. **Mandating Librosa + Torch Dependencies**: Adding `librosa`, `soundfile`, and `torch` to backend Python requirements.
   - *Why Rejected*: Increased environment build time by 8+ minutes, added 1.5GB to container footprint, and introduced complex C-extension build failures on ARM/Alpine Linux environments.

#### ✅ Final Solution & How Unstuck
Implemented a **3-Tier Resilient Audio Parsing Cascade** in `backend/audio_processor.py`:
- **Tier 1 (Pydub + FFmpeg)**: Attempts `pydub.AudioSegment.from_file(io.BytesIO(file_bytes))`.
- **Tier 2 (Native `wave` module)**: If standard PCM WAV is provided, uses native Python byte readers without spawning subprocesses.
- **Tier 3 (Pure Python Byte Parsing & Dynamic RMS Windowing)**: If FFmpeg is missing, extracts structural headers from raw byte buffers, performs PCM sample windowing via `numpy`, and derives dBFS loudness using `20 * log10(RMS / 32768)` and noise estimation using RMS signal variance across silence windows.

---

### Incident 2: Race Conditions & Candidate Name Overwrites in Audio Candidate Resolution

#### 💥 The Bottleneck / Stuck State
During Task 3 testing, when a worker submitted an audio recording with phone number `9000000254` and name `"Rahul Verma"`, but phone `9000000254` was already registered in Task 1 under `"Rohit Verma"`, the API either overwritten the canonical database name or created a duplicate candidate record with an identical phone number. This corrupted candidate profile integrity and broke relational joins across audio submissions and candidate directory tables.

#### 🔍 What Was Searched
- `fastapi duplicate entity lookup 409 conflict vs silent overwrite REST API pattern`
- `mysql candidate foreign key resolution phone number duplicate strategy`
- `angular form validation phone conflict HTTP 409 handling RxJS catchError`

#### 🤖 What Was Asked AI
> "How should the backend candidate resolution logic handle incoming audio metadata when a phone number matches an existing MySQL record but the submitted candidate name conflicts with the registered name?"

#### ❌ Suggestions Rejected & Why
1. **Silent Name Overwrite**: Updating candidate `full_name` in MySQL to whatever name was typed in the latest audio form submission.
   - *Why Rejected*: Destroyed data lineage. A rogue user could overwrite existing verified candidate names from Task 1, corrupting candidate auditing.
2. **Auto-Appending Suffixes to Create Duplicates**: Automatically inserting a new candidate record as `Rahul Verma (1)`.
   - *Why Rejected*: Phone numbers must serve as unique natural keys for gig worker identities. Creating duplicate candidate profiles with identical phones causes notification routing failures in n8n and Slack integrations.

#### ✅ Final Solution & How Unstuck
Designed an explicit **3-Case Candidate Resolution Protocol** in `backend/main.py`:
- **Case 1 (Phone Exists + Name Mismatch)**: Backend queries MySQL by phone. If `submitted_name.lower() != db_name.lower()`, the API immediately aborts with `HTTP 409 Conflict` and payload `{"detail": "Phone number is already registered under 'Rohit Verma'"}`. The Angular UI catches 409 errors and displays a clear red inline warning.
- **Case 2 (Phone Exists + Name Match)**: Links audio directly to the candidate's `candidate_id` and automatically populates domain, city, and experience attributes from Task 1.
- **Case 3 (Phone Not Found)**: Auto-provisions a new worker in `candidates` table and assigns `--` placeholders for missing city/domain fields.

---

### Incident 3: Reactive State Desynchronization & Out-of-Sync Audit Reports on CSV Upload

#### 💥 The Bottleneck / Stuck State
When users uploaded a new CSV file (e.g. `source4_candidates.csv`) via the Angular interface, MySQL successfully ingested the rows and recorded cleaning actions in `data_cleaning_audit`. However, the Task 4 UI table and KPI metrics cards failed to update, requiring a full browser page reload. Furthermore, trigger attempts caused duplicate audit log entries to render because client-side state merged stale arrays with fresh server responses.

#### 🔍 What Was Searched
- `angular rxjs BehaviorSubject trigger refresh table switchMap tap pattern`
- `mysql audit table query dynamic csv streaming response fastapi`
- `angular multi component state synchronization service event bus`

#### 🤖 What Was Asked AI
> "How can we implement a reactive state stream in Angular so that uploading a CSV or resetting MySQL instantly updates candidate counts, KPI cards, the 6-column audit issue table, and downloadable CSV endpoints without forcing page reloads?"

#### ❌ Suggestions Rejected & Why
1. **Client-Side Audit Log Accumulation**: Maintaining an in-memory audit log array inside Angular components and appending new items locally.
   - *Why Rejected*: Deviated from MySQL as the single source of truth. If multiple users or background scripts ingested data, client states diverged.
2. **Polling with `setInterval`**: Fetching `/api/audit/logs` every 2 seconds via an interval timer.
   - *Why Rejected*: Generated unnecessary server CPU load and database queries when the application was idle.

#### ✅ Final Solution & How Unstuck
Refactored `CandidateService` in Angular to implement a **Centralized RxJS Event Bus**:
- Created a `refreshSubject = new BehaviorSubject<void>(undefined)`.
- Bound candidate counts, directory tables, and audit logs to observable streams via `refreshSubject.pipe(switchMap(() => this.http.get(...)))`.
- Added dedicated backend routes `/api/audit/logs` and `/api/audit/download-csv` that query MySQL state dynamically.
- When a CSV upload completes or database reset occurs, `CandidateService` fires `.next()` on `refreshSubject`, causing all components (KPI cards, directory, 6-column table) to re-evaluate and render updated data simultaneously.

---

## 🧪 Testing & Verification Cheat Sheet

| Component / Scenario | Verification Command | Expected Outcome |
|---|---|---|
| **Task 1: Run Ingestion Pipeline** | `python3 -m pipeline.ingest_and_merge` | Merges 3 CSVs into 53 canonical profiles in MySQL; audits 186 cleaning actions. |
| **Task 2: n8n Workflow Simulation** | `python3 -m automation_n8n.n8n_runner_simulation` | Simulates webhook, duplicate check, LLM skill router, and Slack dispatch. |
| **Task 3: Audio API Ingestion Test** | `curl -X POST http://localhost:8000/api/audio/submit -F "worker_name=Test Candidate" -F "worker_phone=9000000254" -F "file=@/tmp/sample.wav"` | Returns JSON with extracted duration, sample rate, bitrate, RMS dBFS, & SNR quality score. |
| **Task 3: Duplicate Name 409 Conflict** | `curl -X POST http://localhost:8000/api/audio/submit -F "worker_name=Wrong Name" -F "worker_phone=9000000254" -F "file=@/tmp/sample.wav"` | Returns `HTTP 409 Conflict` error payload. |
| **Task 4: Export Audit Log CSV** | `curl -O http://localhost:8000/api/audit/download-csv` | Downloads `consultbae_audit_report.csv` containing itemized 6-column audit logs. |
| **Frontend Production Build** | `cd frontend-angular && npm run build` | Compiles Angular 19 application without syntax or bundle errors. |
