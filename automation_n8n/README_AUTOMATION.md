# Task 2: No-Code / Low-Code Automation Workflow (n8n)

## Overview
This directory contains the production-ready **n8n Automation Workflow** designed for ConsultBae's talent ingestion pipeline.

The automation provides:
1. **Webhook Ingestion**: Real-time webhook trigger receiving applicant details or CSV uploads.
2. **Data Sanitization**: Automatic parsing and normalization of phone numbers, emails, names, and skill lists.
3. **Database Deduplication**: Direct MySQL query against `consultbae_db.candidates` indexed on phone and email.
4. **Conditional Routing**:
   - **Duplicate Branch**: Triggers an immediate Slack/Email alert highlighting the conflict, existing candidate ID, and matched source systems.
   - **New Candidate Branch**: Passes unformatted skills to an **LLM Auto-Tagging Node** to classify into official domains (`Automation & AI Heavy`, `Web & Fullstack`, `Data & Analytics`, `QA & Web Scraping`), then inserts the enriched record into MySQL.

---

## Workflow Diagram

```text
       ┌──────────────────────────────────────────────────────────┐
       │     Webhook Trigger: New Applicant / CSV Upload          │
       └─────────────────────────────┬────────────────────────────┘
                                     │
                                     ▼
       ┌──────────────────────────────────────────────────────────┐
       │     Code Node: Normalize Phone, Email, City & Skills     │
       └─────────────────────────────┬────────────────────────────┘
                                     │
                                     ▼
       ┌──────────────────────────────────────────────────────────┐
       │     MySQL Node: Query `candidates` by Phone & Email      │
       └─────────────────────────────┬────────────────────────────┘
                                     │
                                     ▼
                       ┌───────────────────────────┐
                       │   Router: Is Duplicate?   │
                       └───┬───────────────────┬───┘
               [YES]       │                   │       [NO]
                           ▼                   ▼
     ┌────────────────────────────┐    ┌────────────────────────────────────┐
     │ Format Duplicate Alert     │    │ LLM: Auto-Tag Skill Category       │
     └─────────────┬──────────────┘    └─────────────────┬──────────────────┘
                   │                                     │
                   ▼                                     ▼
     ┌────────────────────────────┐    ┌────────────────────────────────────┐
     │ Send Slack / Webhook Alert │    │ MySQL: Insert Enriched Candidate   │
     └────────────────────────────┘    └─────────────────┬──────────────────┘
                                                         │
                                                         ▼
                                       ┌────────────────────────────────────┐
                                       │ Format Success JSON Response       │
                                       └────────────────────────────────────┘
```

---

## How to Import and Run in n8n

1. **Start n8n**:
   - Self-hosted: `npx n8n start` or `docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n`
   - Or open your existing n8n instance at `http://localhost:5678`.

2. **Import Workflow**:
   - In n8n, click **Workflows** -> **Import from File...**
   - Select `automation_n8n/workflow_consultbae_automation.json`.

3. **Configure Credentials**:
   - Under **Credentials**, add/update your **MySQL** credentials:
     - Host: `localhost` / `127.0.0.1`
     - Database: `consultbae_db`
     - User: `root`
     - Port: `3306`
   - Under **LLM Node**, select your OpenAI, Anthropic, or HuggingFace API key (or use local Ollama).

4. **Test the Webhook**:
   - Send a `POST` request to `http://localhost:5678/webhook/candidate-ingest` with JSON body:
     ```json
     {
       "full_name": "Tanvi Gupta",
       "phone": "+91-9000000254",
       "email": "tanvi.gupta31@example.com",
       "skills": "n8n, LangChain, REST APIs, MongoDB, SQL",
       "city": "Bengaluru"
     }
     ```
   - Duplicate flow will instantly execute and return a Duplicate Alert response.

---

## Local Verification Simulation
You can verify the entire workflow logic locally against MySQL at any time using:
```bash
python3 -m automation_n8n.n8n_runner_simulation
```
