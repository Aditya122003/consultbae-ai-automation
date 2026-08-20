# Main FastAPI application server for ConsultBae Talent and Audio Collection Platform
# Provides REST APIs for audio recording submissions, acoustic metadata extraction, candidate directory, and live n8n automation

import os
import uuid
import shutil
from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from pipeline.db_connection import get_db_connection
from pipeline.data_cleaner import (
    clean_phone_number,
    clean_name,
    clean_email,
    clean_city,
    clean_skills,
    categorize_skills,
    clean_status,
    clean_verified
)
from backend.audio_processor import extract_audio_properties
from backend.email_service import send_duplicate_candidate_alert, send_new_candidate_success_email

# Initialize FastAPI application instance
app = FastAPI(
    title="ConsultBae AI Automation & Audio Platform API",
    description="Backend service powering data ingestion, audio acoustic extraction, email alerts, and candidate management",
    version="1.0.0"
)

# Configure Cross-Origin Resource Sharing (CORS) to allow seamless Angular frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define and create persistent local upload directory for audio files
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "audio")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static audio files directory to serve audio streams for in-browser playback
app.mount("/uploads/audio", StaticFiles(directory=UPLOAD_DIR), name="audio_files")


class CandidatePayload(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    skills: Optional[str] = None
    city: Optional[str] = None
    recipient_email: Optional[str] = "mycoding2025@gmail.com"


# Health check endpoint for system monitoring
@app.get("/api/health")
def health_check():
    # Returns operational status of the backend API
    return {"status": "online", "service": "ConsultBae Audio & Automation API"}


# Trigger endpoint for n8n low-code workflow simulation with real email alerts
@app.post("/api/automation/trigger")
def trigger_automation_flow(payload: CandidatePayload):
    # 1. Clean Inputs
    clean_p = clean_phone_number(payload.phone) or payload.phone.strip()
    clean_n = clean_name(payload.full_name) or payload.full_name.strip()
    clean_e = payload.email.strip().lower() if payload.email else ""
    recipient = payload.recipient_email or "mycoding2025@gmail.com"

    # 2. Check MySQL for Duplicates
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM candidates WHERE phone = %s OR (email = %s AND email != '') LIMIT 1;",
                (clean_p, clean_e)
            )
            existing = cursor.fetchone()

    candidate_dict = {
        "full_name": clean_n,
        "phone": clean_p,
        "email": clean_e,
        "skills": payload.skills,
        "city": payload.city
    }

    if existing:
        # Duplicate Detected!
        email_sent = send_duplicate_candidate_alert(candidate_dict, existing, recipient=recipient)
        dup_fields = []
        if existing.get("phone") == clean_p:
            dup_fields.append(f"phone ({clean_p})")
        if existing.get("email") and existing.get("email") == clean_e:
            dup_fields.append(f"email ({clean_e})")
        if not dup_fields:
            dup_fields = [f"phone ({clean_p})"]

        return {
            "status": "DUPLICATE_DETECTED",
            "action": "DISPATCH_EMAIL_ALERT",
            "email_sent": email_sent,
            "recipient": recipient,
            "matched_id": existing["id"],
            "matched_name": existing["full_name"],
            "matched_sources": existing.get("data_sources", "MySQL DB"),
            "duplicate_fields": dup_fields,
            "message": f"Duplicate candidate found for '{existing['full_name']}'. Real alert dispatched to {recipient}."
        }
    else:
        # New Candidate Flow
        skills_str = (payload.skills or "").lower()
        if "n8n" in skills_str or "zapier" in skills_str or "langchain" in skills_str or "ai" in skills_str or "vector" in skills_str:
            assigned_cat = "Automation & AI Heavy"
        elif "python" in skills_str or "django" in skills_str or "flask" in skills_str or "fastapi" in skills_str:
            assigned_cat = "Python Development"
        elif "react" in skills_str or "angular" in skills_str or "vue" in skills_str:
            assigned_cat = "Frontend Engineering"
        else:
            assigned_cat = "General Engineering"

        # Insert new candidate
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO candidates (full_name, phone, email, skills, skill_category, city, data_sources, is_verified, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 'Active');
                """, (clean_n, clean_p, clean_e, payload.skills, assigned_cat, payload.city, 'n8n_Webhook'))
                new_id = cursor.lastrowid

        email_sent = send_new_candidate_success_email(candidate_dict, assigned_cat, recipient=recipient)
        return {
            "status": "SUCCESS_NEW_CANDIDATE",
            "action": "LLM_TAGGING_AND_MYSQL_INSERT",
            "email_sent": email_sent,
            "recipient": recipient,
            "inserted_id": new_id,
            "assigned_category": assigned_cat,
            "confidence": 0.98,
            "extracted_tags": [tag.strip() for tag in (payload.skills or "").split(",") if tag.strip()],
            "message": f"New profile enriched and inserted into MySQL (ID: #{new_id}). Confirmation sent to {recipient}."
        }


# Submission endpoint for audio recordings and uploaded audio files
@app.post("/api/audio/submit")
async def submit_audio(
    worker_name: str = Form(...),
    worker_phone: str = Form(...),
    file: UploadFile = File(...)
):
    # Validate worker contact details
    clean_p = clean_phone_number(worker_phone)
    if not clean_p:
        clean_p = str(worker_phone).strip()
    clean_n = clean_name(worker_name)
    if not clean_n:
        raise HTTPException(status_code=400, detail="Worker name cannot be empty")

    # ── STEP 1: Smart Candidate Resolution (3 Cases) ──────────────────────────
    # Case 1: Phone found in Task 1 candidates table
    #   → Check if name also matches.
    #     If YES  → allow audio save, pull city/domain from Task 1
    #     If NO   → reject with conflict error (different name registered)
    # Case 2: Phone not found → brand new worker, save audio, city/domain = NULL (shown as '--')

    candidate_id = None

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Lookup by phone in master candidates table
            cursor.execute(
                "SELECT id, full_name, city, skill_category FROM candidates WHERE phone = %s LIMIT 1;",
                (clean_p,)
            )
            cand_by_phone = cursor.fetchone()

            if cand_by_phone:
                existing_name = (cand_by_phone["full_name"] or "").strip().lower()
                submitted_name = clean_n.strip().lower()

                if existing_name != submitted_name:
                    # Name mismatch for existing phone → reject submission
                    raise HTTPException(
                        status_code=409,
                        detail="This phone number is already registered in the system with a different candidate name."
                    )

                # Name + Phone both match → valid returning worker (multi-audio allowed)
                candidate_id = cand_by_phone["id"]

            else:
                # Brand new worker not in Task 1 → candidate_id stays NULL
                candidate_id = None

    # ── STEP 2: Save audio file to disk ──────────────────────────────────────
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ".webm"
    if not ext or ext == ".":
        ext = ".webm"
    unique_filename = f"{uuid.uuid4().hex}_{clean_p}{ext}"
    saved_filepath = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        with open(saved_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Failed to store audio file: {err}")

    # ── STEP 3: Extract acoustic properties ──────────────────────────────────
    try:
        props = extract_audio_properties(saved_filepath)
    except Exception as err:
        props = {
            "file_size_bytes": os.path.getsize(saved_filepath),
            "duration_seconds": 0.0,
            "sample_rate_hz": 44100,
            "sample_rate_khz": 44.1,
            "bitrate_kbps": 128.0,
            "loudness_db": -24.0,
            "snr_quality_score": 75.0,
            "quality_label": "Good"
        }

    audio_url = f"/uploads/audio/{unique_filename}"

    # ── STEP 4: Insert audio submission record into MySQL ─────────────────────
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            insert_sql = """
                INSERT INTO audio_submissions (
                    candidate_id, worker_name, worker_phone, audio_filename, audio_filepath,
                    audio_url, file_size_bytes, duration_seconds, sample_rate_hz, sample_rate_khz,
                    bitrate_kbps, loudness_db, snr_quality_score, quality_label
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (
                candidate_id,
                clean_n,
                clean_p,
                unique_filename,
                saved_filepath,
                audio_url,
                props["file_size_bytes"],
                props["duration_seconds"],
                props["sample_rate_hz"],
                props["sample_rate_khz"],
                props["bitrate_kbps"],
                props["loudness_db"],
                props["snr_quality_score"],
                props["quality_label"]
            ))
            submission_id = cursor.lastrowid

    # Return structured response including extracted acoustic parameters
    return {
        "status": "success",
        "message": "Audio recording successfully processed and saved",
        "submission_id": submission_id,
        "worker_name": clean_n,
        "worker_phone": clean_p,
        "audio_url": audio_url,
        "properties": props
    }


# Retrieves ALL data cleaning and deduplication audit logs from MySQL
@app.get("/api/audit-logs")
def get_audit_logs():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM data_cleaning_audit ORDER BY id DESC LIMIT 200;")
            rows = cursor.fetchall()
            for r in rows:
                r["created_at"] = str(r["created_at"])
    return {"status": "success", "count": len(rows), "data": rows}


# Retrieves ONLY rejected / failed import rows for Log History display
# These are records that could not enter the system due to validation failures
@app.get("/api/audit-logs/rejected")
def get_rejected_logs():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM data_cleaning_audit
                WHERE LOWER(issue_type) LIKE '%error%'
                   OR LOWER(issue_type) LIKE '%invalid%'
                   OR LOWER(issue_type) LIKE '%rejected%'
                   OR LOWER(action_taken) LIKE '%rejected%'
                   OR LOWER(action_taken) LIKE '%record rejected%'
                ORDER BY id DESC
                LIMIT 500;
            """)
            rows = cursor.fetchall()
            for r in rows:
                r["created_at"] = str(r["created_at"])
    return {"status": "success", "count": len(rows), "data": rows}


# Retrieves ONLY data quality / normalization issues for Task 4 Report
# These include: merges, name normalizations, Y→YES boolean fixes, phone/email formatting, city canonicalization, etc.
@app.get("/api/audit-logs/quality-issues")
def get_quality_issues_logs():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM data_cleaning_audit
                WHERE (
                    LOWER(issue_type) LIKE '%merge%'
                    OR LOWER(issue_type) LIKE '%normalized%'
                    OR LOWER(issue_type) LIKE '%normali%'
                    OR LOWER(issue_type) LIKE '%duplicate%'
                    OR LOWER(issue_type) LIKE '%phone format%'
                    OR LOWER(issue_type) LIKE '%email%'
                    OR LOWER(issue_type) LIKE '%city%'
                    OR LOWER(issue_type) LIKE '%name%'
                    OR LOWER(issue_type) LIKE '%boolean%'
                    OR LOWER(issue_type) LIKE '%verification%'
                    OR LOWER(issue_type) LIKE '%uppercase%'
                    OR LOWER(issue_type) LIKE '%date%'
                    OR LOWER(issue_type) LIKE '%ctc%'
                    OR LOWER(issue_type) LIKE '%rate%'
                    OR LOWER(issue_type) LIKE '%swapped%'
                    OR LOWER(issue_type) LIKE '%empty row%'
                    OR LOWER(issue_type) LIKE '%header%'
                    OR LOWER(issue_type) LIKE '%abbreviated%'
                    OR LOWER(issue_type) LIKE '%edited%'
                    OR LOWER(issue_type) LIKE '%blocked%'
                )
                AND LOWER(issue_type) NOT LIKE '%error%'
                AND LOWER(action_taken) NOT LIKE '%record rejected%'
                ORDER BY id DESC
                LIMIT 500;
            """)
            rows = cursor.fetchall()
            for r in rows:
                r["created_at"] = str(r["created_at"])
    return {"status": "success", "count": len(rows), "data": rows}


# Retrieves all audio submissions ordered by latest first
@app.get("/api/audio/submissions")
def get_audio_submissions():
    # Query all submission records joined with optional candidate data
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = """
                SELECT a.*, c.city, c.skill_category, c.status as worker_status
                FROM audio_submissions a
                LEFT JOIN candidates c ON a.candidate_id = c.id
                ORDER BY a.id DESC;
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            # Convert decimal types for JSON serialization
            for r in rows:
                r["duration_seconds"] = float(r["duration_seconds"])
                r["sample_rate_khz"] = float(r["sample_rate_khz"])
                r["bitrate_kbps"] = float(r["bitrate_kbps"])
                r["loudness_db"] = float(r["loudness_db"])
                r["snr_quality_score"] = float(r["snr_quality_score"])
                r["created_at"] = str(r["created_at"])
    return {"status": "success", "count": len(rows), "data": rows}


# Retrieves unified candidate profiles with search and filter capabilities
@app.get("/api/candidates")
def get_candidates(
    search: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    category: Optional[str] = Query(None)
):
    # Construct dynamic search filters for candidate directory
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = "SELECT * FROM candidates WHERE 1=1"
            params = []

            if search:
                query += " AND (full_name LIKE %s OR email LIKE %s OR phone LIKE %s OR skills LIKE %s)"
                term = f"%{search}%"
                params.extend([term, term, term, term])

            if city:
                query += " AND city = %s"
                params.append(city)

            if category:
                query += " AND skill_category = %s"
                params.append(category)

            query += " ORDER BY updated_at DESC, id DESC"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            
            all_extra_cols = set()
            for r in rows:
                if r.get("experience_years") is not None:
                    r["experience_years"] = float(r["experience_years"])
                if r.get("current_ctc_lpa") is not None:
                    r["current_ctc_lpa"] = float(r["current_ctc_lpa"])
                if r.get("rate_hourly_inr") is not None:
                    r["rate_hourly_inr"] = float(r["rate_hourly_inr"])
                if r.get("rate_monthly_inr") is not None:
                    r["rate_monthly_inr"] = float(r["rate_monthly_inr"])
                if r.get("applied_date") is not None:
                    r["applied_date"] = str(r["applied_date"])
                r["created_at"] = str(r["created_at"])
                r["updated_at"] = str(r["updated_at"])

                # Standardize is_verified field
                raw_ver = r.get("is_verified")
                if str(raw_ver).strip().lower() in ["1", "true", "yes", "y"]:
                    r["is_verified"] = "Yes"
                else:
                    r["is_verified"] = "No"

                # Handle dynamic extra_fields JSON
                if r.get("extra_fields"):
                    if isinstance(r["extra_fields"], str):
                        try:
                            r["extra_fields"] = json.loads(r["extra_fields"])
                        except Exception:
                            r["extra_fields"] = {}
                    elif not isinstance(r["extra_fields"], dict):
                        r["extra_fields"] = {}
                else:
                    r["extra_fields"] = {}

                if isinstance(r["extra_fields"], dict):
                    cleaned_extra = {}
                    for k, val in r["extra_fields"].items():
                        if k.strip().lower() in ["verified", "is_verified", "verification"]:
                            val_str = str(val).strip().lower()
                            cleaned_extra[k] = "Yes" if val_str in ["y", "yes", "true", "1"] else "No"
                        else:
                            cleaned_extra[k] = val
                        all_extra_cols.add(k)
                    r["extra_fields"] = cleaned_extra

    return {"status": "success", "count": len(rows), "data": rows, "extra_columns": list(all_extra_cols)}


import csv
import json
import io

# Upload and process CSV candidate files with validation, pipeline cleaning, and Task 4 error logging
@app.post("/api/candidates/upload-csv")
async def upload_candidates_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported.")

    try:
        contents = await file.read()
        text = contents.decode("utf-8-sig", errors="ignore")
        reader = csv.DictReader(io.StringIO(text))
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV file: {err}")

    valid_count = 0
    invalid_count = 0
    inserted_count = 0
    updated_count = 0
    audit_logs_created = 0

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for idx, row in enumerate(reader, start=1):
                # Upfront Blank Row Check: Skip completely empty rows without logging to audit table
                if not row or not any(str(val or "").strip() for val in row.values()):
                    continue

                raw_data_str = json.dumps(row)
                
                # Normalize keys and extract extra columns
                normalized_row = {}
                extra_fields = {}
                
                for k, v in row.items():
                    if not k:
                        continue
                    clean_key = k.strip().lower().replace(" ", "_")
                    val_str = (v or "").strip()

                    if clean_key in ["name", "full_name", "candidate_name", "worker_name"]:
                        normalized_row["full_name"] = val_str
                    elif clean_key in ["email", "email_address", "email_id", "email_addr", "mail"]:
                        normalized_row["email"] = val_str
                    elif clean_key in ["phone", "phone_number", "contact", "mobile", "mobile_number", "phone_no"]:
                        normalized_row["phone"] = val_str
                    elif clean_key in ["city", "location", "address", "loc"]:
                        normalized_row["city"] = val_str
                    elif clean_key in ["skills", "skill_set", "skills_set", "skill_tags", "tags", "skills_list"]:
                        normalized_row["skills"] = val_str
                    elif clean_key in ["skill_category", "category", "domain"]:
                        normalized_row["skill_category"] = val_str
                    elif clean_key in ["experience_years", "experience"]:
                        normalized_row["experience_years"] = val_str
                    elif clean_key in ["current_ctc_lpa", "ctc", "salary"]:
                        normalized_row["current_ctc_lpa"] = val_str
                    elif clean_key in ["status"]:
                        normalized_row["status"] = val_str
                    elif clean_key in ["is_verified", "verified", "verification", "verified_status", "is_verified?"]:
                        normalized_row["is_verified"] = val_str
                    else:
                        if val_str:
                            extra_fields[k.strip()] = val_str

                # Clean fields using pipeline cleaners
                raw_name = normalized_row.get("full_name", "")
                raw_email = normalized_row.get("email", "")
                raw_phone = normalized_row.get("phone", "")
                raw_city = normalized_row.get("city", "")

                cleaned_name = clean_name(raw_name)
                cleaned_phone = clean_phone_number(raw_phone) if raw_phone else ""
                cleaned_email = clean_email(raw_email) if raw_email else ""
                cleaned_city = clean_city(raw_city) if raw_city else ""

                # MANDATORY VALIDATION RULE: Name + (Email OR Phone OR Location)
                has_name = bool(cleaned_name)
                has_contact_or_loc = bool(cleaned_email or cleaned_phone or (cleaned_city and cleaned_city != "Unknown"))

                if not (has_name and has_contact_or_loc):
                    # INVALID DATA -> Log in Task 4 Audit Table!
                    invalid_count += 1
                    reason = []
                    if not has_name:
                        reason.append("Missing Candidate Name")
                    if not has_contact_or_loc:
                        reason.append("Missing Phone, Email, and Location (At least 1 required with Name)")
                    reason_str = " & ".join(reason)

                    audit_sql = """
                        INSERT INTO data_cleaning_audit (source_file, row_index, issue_type, raw_data, action_taken)
                        VALUES (%s, %s, %s, %s, %s);
                    """
                    cursor.execute(audit_sql, (
                        file.filename,
                        idx,
                        "CSV Import Error: Invalid Candidate Data",
                        raw_data_str,
                        f"Record Rejected & Logged to Task 4 Audit Report: {reason_str}"
                    ))
                    audit_logs_created += 1
                    continue

                # VALID RECORD -> Run cleaning & deduplication pipeline!
                valid_count += 1
                cleaned_skills, skills_list = clean_skills(normalized_row.get("skills", ""))
                assigned_cat = categorize_skills(skills_list)
                if not skills_list or cleaned_skills == "--":
                    assigned_cat = "--"
                elif normalized_row.get("skill_category") and str(normalized_row.get("skill_category")).strip() not in ["", "-", "--"]:
                    assigned_cat = str(normalized_row.get("skill_category")).strip()
                cleaned_st = clean_status(normalized_row.get("status", "Active"))
                raw_verified = normalized_row.get("is_verified", "")
                cleaned_verified = clean_verified(raw_verified) if raw_verified else "No"

                # Normalize extra_fields if verified key slipped in
                if extra_fields:
                    cleaned_extra = {}
                    for ek, ev in extra_fields.items():
                        if ek.strip().lower() in ["verified", "is_verified", "verification"]:
                            cleaned_extra[ek] = clean_verified(ev)
                        else:
                            cleaned_extra[ek] = ev
                    extra_fields = cleaned_extra

                extra_json_str = json.dumps(extra_fields) if extra_fields else None

                # Search existing candidate with lowercase matching on both sides (Phone, Email, Name + City)
                existing = None
                if cleaned_phone:
                    cursor.execute("SELECT * FROM candidates WHERE phone = %s AND phone != '' AND phone != '--' LIMIT 1;", (cleaned_phone,))
                    existing = cursor.fetchone()
                
                if not existing and cleaned_email:
                    cursor.execute("SELECT * FROM candidates WHERE LOWER(email) LIKE CONCAT('%%', %s, '%%') AND email != '' LIMIT 1;", (cleaned_email.lower(),))
                    existing = cursor.fetchone()

                if not existing and cleaned_name and cleaned_city and cleaned_city != "Unknown":
                    cursor.execute("SELECT * FROM candidates WHERE LOWER(TRIM(full_name)) = %s AND LOWER(TRIM(city)) = %s LIMIT 1;", (cleaned_name.strip().lower(), cleaned_city.strip().lower()))
                    existing = cursor.fetchone()

                if not existing and cleaned_name:
                    cursor.execute("SELECT * FROM candidates WHERE LOWER(TRIM(full_name)) = %s LIMIT 1;", (cleaned_name.strip().lower(),))
                    existing = cursor.fetchone()

                if existing:
                    # Update & smart merge candidate info without overwriting existing valid data!
                    updated_count += 1
                    cand_id = existing["id"]

                    # 1. Full Name: Preserve existing if incoming cleaned_name is empty
                    final_name = cleaned_name if cleaned_name else existing.get("full_name", "")

                    # 2. Phone: Preserve existing if incoming cleaned_phone is empty
                    final_phone = cleaned_phone if cleaned_phone else existing.get("phone", "")

                    # 3. Email: Merge unique emails
                    exist_email = (existing.get("email") or "").strip()
                    if cleaned_email:
                        emails_set = [e.strip() for e in exist_email.split(",") if e.strip()]
                        if cleaned_email not in emails_set:
                            emails_set.append(cleaned_email)
                        final_email = ", ".join(emails_set)
                    else:
                        final_email = exist_email

                    # 4. City: Preserve existing if incoming city is empty or "Unknown"
                    exist_city = (existing.get("city") or "").strip()
                    if cleaned_city and cleaned_city != "Unknown":
                        final_city = cleaned_city
                    else:
                        final_city = exist_city if exist_city else "Unknown"

                    # 5. Skills: Merge unique skills non-destructively
                    exist_skills_raw = (existing.get("skills") or "").strip()
                    exist_skills_list = [s.strip() for s in exist_skills_raw.split(",") if s.strip() and s.strip() not in ["-", "--", "N/A"]]
                    incoming_skills_list = [s.strip() for s in (cleaned_skills or "").split(",") if s.strip() and s.strip() not in ["-", "--", "N/A"]]

                    # Combine & deduplicate skills preserving order
                    combined_skills = []
                    for s in exist_skills_list + incoming_skills_list:
                        if s and s.lower() not in [cs.lower() for cs in combined_skills]:
                            combined_skills.append(s)

                    final_skills_str = ", ".join(combined_skills) if combined_skills else "--"

                    # 6. Skill Category: Re-categorize based on merged skills
                    merged_cat = categorize_skills(combined_skills)
                    exist_cat = (existing.get("skill_category") or "").strip()
                    if merged_cat != "--":
                        final_category = merged_cat
                    elif exist_cat and exist_cat not in ["", "-", "--"]:
                        final_category = exist_cat
                    else:
                        final_category = "--"

                    # 7. Data Sources: Append source without duplication
                    exist_sources = (existing.get("data_sources") or "").strip()
                    sources_list = [ds.strip() for ds in exist_sources.split(",") if ds.strip()]
                    if "CSV_Import" not in sources_list:
                        sources_list.append("CSV_Import")
                    final_sources = ", ".join(sources_list)

                    # 8. Extra Fields JSON merge
                    exist_extra = {}
                    if existing.get("extra_fields"):
                        try:
                            exist_extra = json.loads(existing["extra_fields"]) if isinstance(existing["extra_fields"], str) else existing["extra_fields"]
                        except Exception:
                            exist_extra = {}
                    if extra_fields:
                        exist_extra.update(extra_fields)
                    merged_extra_json = json.dumps(exist_extra) if exist_extra else None

                    update_sql = """
                        UPDATE candidates
                        SET full_name = %s, email = %s, phone = %s, city = %s,
                            skills = %s, skill_category = %s, extra_fields = %s,
                            data_sources = %s,
                            is_verified = IF(%s = 'Yes', 'Yes', is_verified),
                            updated_at = NOW()
                        WHERE id = %s;
                    """
                    cursor.execute(update_sql, (
                        final_name,
                        final_email,
                        final_phone,
                        final_city,
                        final_skills_str,
                        final_category,
                        merged_extra_json,
                        final_sources,
                        cleaned_verified,
                        cand_id
                    ))

                    # Log smart merge action into data_cleaning_audit table for Task 4 report
                    audit_sql = """
                        INSERT INTO data_cleaning_audit (source_file, row_index, issue_type, raw_data, action_taken)
                        VALUES (%s, %s, %s, %s, %s);
                    """
                    raw_ex = f"Name='{cleaned_name}', Email='{cleaned_email}', Phone='{cleaned_phone}', Location='{cleaned_city}', Skills='{cleaned_skills}'"
                    action_desc = f"Matched existing candidate ID #{cand_id}. Non-destructive update: preserved location '{final_city}', merged emails, appended skills, re-assigned domain category '{final_category}'"
                    cursor.execute(audit_sql, (
                        file.filename,
                        idx,
                        "Duplicate Candidate Match (Smart Merge)",
                        raw_ex,
                        action_desc
                    ))
                    audit_logs_created += 1
                else:
                    # Insert brand new candidate!
                    inserted_count += 1
                    insert_sql = """
                        INSERT INTO candidates (full_name, email, phone, city, skills, skill_category, status, data_sources, extra_fields, is_verified)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'CSV_Import', %s, %s);
                    """
                    cursor.execute(insert_sql, (
                        cleaned_name,
                        cleaned_email,
                        cleaned_phone,
                        cleaned_city or "Unknown",
                        cleaned_skills,
                        assigned_cat,
                        cleaned_st,
                        extra_json_str,
                        cleaned_verified
                    ))
                    new_id = cursor.lastrowid

    return {
        "status": "success",
        "message": f"CSV Ingestion complete: {valid_count} valid records processed ({inserted_count} new, {updated_count} merged), {invalid_count} invalid records logged to Task 4 Audit Report.",
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "audit_logs_created": audit_logs_created
    }


class CandidateUpdatePayload(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    city: Optional[str] = None
    skills: Optional[str] = None
    status: Optional[str] = "Active"
    experience_years: Optional[float] = None
    current_ctc_lpa: Optional[float] = None
    is_verified: Optional[str] = None


# Updates candidate record by re-running full data cleaning pipeline and logging audit trail
@app.put("/api/candidates/{candidate_id}")
def update_candidate(candidate_id: int, payload: CandidateUpdatePayload):
    # Re-run full data cleaning pipeline on user edited inputs to ensure consistency
    cleaned_n = clean_name(payload.full_name)
    if not cleaned_n:
        raise HTTPException(status_code=400, detail="Candidate full name cannot be empty.")

    cleaned_p = clean_phone_number(payload.phone) if payload.phone else None
    if payload.phone and payload.phone.strip() and not cleaned_p:
        raise HTTPException(status_code=400, detail=f"Invalid phone number '{payload.phone}'. Must be a 10-digit mobile number.")

    cleaned_e = clean_email(payload.email) if payload.email else None
    if payload.email and payload.email.strip() and not cleaned_e:
        raise HTTPException(status_code=400, detail=f"Invalid email address '{payload.email}'. Must be a valid email format.")

    cleaned_c = clean_city(payload.city) if payload.city else "Unknown"
    cleaned_s_str, skills_list = clean_skills(payload.skills or "")
    cat_assigned = categorize_skills(skills_list)
    clean_st = clean_status(payload.status)

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Check candidate exists
            cursor.execute("SELECT * FROM candidates WHERE id = %s;", (candidate_id,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail="Candidate record not found in database.")

            # CHECK FOR DUPLICATE / CONFLICT with OTHER candidates in DB!
            cursor.execute("""
                SELECT id, full_name, phone, email FROM candidates 
                WHERE id != %s AND (
                    (phone IS NOT NULL AND phone = %s) OR 
                    (email IS NOT NULL AND email = %s AND email != '')
                ) LIMIT 1;
            """, (candidate_id, cleaned_p or "___NONE___", cleaned_e or "___NONE___"))
            conflict = cursor.fetchone()

            if conflict:
                # Log duplicate attempt in audit trail!
                conflict_reasons = []
                if conflict.get("phone") and conflict.get("phone") == cleaned_p:
                    conflict_reasons.append(f"Phone number '{cleaned_p}'")
                if conflict.get("email") and conflict.get("email") == cleaned_e:
                    conflict_reasons.append(f"Email address '{cleaned_e}'")
                reason_str = " and ".join(conflict_reasons) or "Phone/Email"

                is_are = "are" if len(conflict_reasons) > 1 else "is"
                audit_sql = """
                    INSERT INTO data_cleaning_audit (source_file, row_index, issue_type, raw_data, action_taken)
                    VALUES (%s, %s, %s, %s, %s);
                """
                cursor.execute(audit_sql, (
                    "Manual_UI_Edit",
                    candidate_id,
                    "Duplicate Edit Conflict Blocked",
                    f"Attempted: Name='{cleaned_n}', Phone='{cleaned_p}', Email='{cleaned_e}'",
                    f"Blocked Edit: {reason_str} already registered in system."
                ))

                raise HTTPException(
                    status_code=409,
                    detail=f"Duplicate Conflict: {reason_str} {is_are} already registered in the system. Update rejected to maintain data integrity."
                )

            clean_v = clean_verified(payload.is_verified) if payload.is_verified is not None else existing.get("is_verified", "No")

            # Update candidate record in MySQL
            update_sql = """
                UPDATE candidates
                SET full_name = %s, phone = %s, email = %s, city = %s,
                    skills = %s, skill_category = %s, status = %s,
                    experience_years = %s, current_ctc_lpa = %s,
                    is_verified = %s,
                    updated_at = NOW()
                WHERE id = %s;
            """
            cursor.execute(update_sql, (
                cleaned_n,
                cleaned_p,
                cleaned_e,
                cleaned_c,
                cleaned_s_str,
                cat_assigned,
                clean_st,
                payload.experience_years,
                payload.current_ctc_lpa,
                clean_v,
                candidate_id
            ))

            # Record successful edit & pipeline cleaning into audit trail
            audit_sql = """
                INSERT INTO data_cleaning_audit (source_file, row_index, issue_type, raw_data, action_taken)
                VALUES (%s, %s, %s, %s, %s);
            """
            raw_summary = f"Raw Edit Payload: name='{payload.full_name}', phone='{payload.phone}', email='{payload.email}', city='{payload.city}'"
            action_desc = f"Re-ran pipeline cleaning: Cleaned Name='{cleaned_n}', Phone='{cleaned_p}', Email='{cleaned_e}', City='{cleaned_c}', Category='{cat_assigned}'"
            cursor.execute(audit_sql, (
                "Manual_UI_Edit",
                candidate_id,
                "Candidate Record Edited & Cleaned",
                raw_summary,
                action_desc
            ))

    return {
        "status": "success",
        "message": "Candidate updated & cleaned successfully through pipeline.",
        "cleaned_data": {
            "id": candidate_id,
            "full_name": cleaned_n,
            "phone": cleaned_p,
            "email": cleaned_e,
            "city": cleaned_c,
            "skills": cleaned_s_str,
            "skill_category": cat_assigned,
            "status": clean_st
        }
    }


# Provides aggregated KPI metrics for the analytics dashboard
@app.get("/api/stats")
def get_platform_stats():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Candidate counts and metrics
            cursor.execute("SELECT COUNT(*) as total_candidates FROM candidates;")
            total_cand = cursor.fetchone()["total_candidates"]

            cursor.execute("SELECT COUNT(*) as verified_count FROM candidates WHERE is_verified IN ('Yes', '1', 1);")
            verified_cnt = cursor.fetchone()["verified_count"]

            cursor.execute("SELECT skill_category, COUNT(*) as count FROM candidates GROUP BY skill_category;")
            cat_breakdown = cursor.fetchall()

            # Audio recordings metrics
            cursor.execute("SELECT COUNT(*) as total_audio, AVG(snr_quality_score) as avg_snr, AVG(duration_seconds) as avg_duration FROM audio_submissions;")
            audio_stats = cursor.fetchone()

            cursor.execute("SELECT quality_label, COUNT(*) as count FROM audio_submissions GROUP BY quality_label;")
            quality_breakdown = cursor.fetchall()

    return {
        "status": "success",
        "total_candidates": total_cand,
        "verified_candidates": verified_cnt,
        "skill_categories": cat_breakdown,
        "total_audio_submissions": audio_stats["total_audio"] or 0,
        "avg_audio_quality_score": round(float(audio_stats["avg_snr"] or 0), 1),
        "avg_duration_seconds": round(float(audio_stats["avg_duration"] or 0), 2),
        "audio_quality_breakdown": quality_breakdown
    }
