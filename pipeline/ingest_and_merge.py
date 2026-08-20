# Master ETL ingestion and deduplication script
# Loads 3 dirty CSV sources, cleans data, performs multi-pass entity resolution, and saves to MySQL

import os
import csv
import re
from typing import List, Dict, Any
from .db_connection import get_db_connection
from .data_cleaner import (
    clean_phone_number,
    clean_email,
    clean_name,
    clean_city,
    clean_ctc_lpa,
    clean_rate,
    clean_status,
    clean_verified,
    clean_date,
    clean_skills
)
from .entity_matcher import EntityMatcher

# Paths to the 3 source CSV files
SOURCE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC1_PATH = os.path.join(SOURCE_DIR, "source1_naukri_applicants.csv")
SRC2_PATH = os.path.join(SOURCE_DIR, "source2_gig_workers.csv")
SRC3_PATH = os.path.join(SOURCE_DIR, "source3_cbnexus_contacts.csv")

# Global audit list to record every detected data issue and action taken
audit_logs: List[Dict[str, Any]] = []

# Records an identified data issue into the audit tracking collection
def log_audit(source: str, row_idx: int, issue_type: str, raw_data: str, action_taken: str):
    audit_logs.append({
        "source_file": source,
        "row_index": row_idx,
        "issue_type": issue_type,
        "raw_data": str(raw_data),
        "action_taken": action_taken
    })

# Ingests and cleans applicants from Source 1 (Naukri CSV)
def process_source1(matcher: EntityMatcher):
    print("🔹 Processing Source 1: Naukri Applicants...")
    with open(SRC1_PATH, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            raw_phone = row.get("Phone")
            raw_email = row.get("Email")
            raw_name = row.get("Full Name")
            raw_city = row.get("City")
            raw_ctc = row.get("Current CTC")
            raw_exp = row.get("Experience (Years)")
            raw_date = row.get("Applied Date")
            raw_skills = row.get("Skills")

            # Check for phone formatting anomalies (e.g. leading zeros, country codes)
            clean_p = clean_phone_number(raw_phone)
            if raw_phone and clean_p and clean_p != raw_phone:
                log_audit("source1_naukri_applicants.csv", idx, "Phone Format Normalized", raw_phone, f"Normalized to 10-digit '{clean_p}'")

            # Check for email normalization
            clean_e = clean_email(raw_email)
            if raw_email and clean_e and clean_e != raw_email:
                log_audit("source1_naukri_applicants.csv", idx, "Email Lowercased", raw_email, f"Converted to '{clean_e}'")

            # Check for abbreviated names like 'R. Verma'
            clean_n = clean_name(raw_name)
            if "." in raw_name:
                log_audit("source1_naukri_applicants.csv", idx, "Abbreviated Name Detected", raw_name, "Marked for full name merge resolution")

            # Check and convert CTC format
            clean_ctc = clean_ctc_lpa(raw_ctc)
            if raw_ctc and clean_ctc:
                try:
                    if float(raw_ctc) > 1000:
                        log_audit("source1_naukri_applicants.csv", idx, "CTC Unit Converted", raw_ctc, f"Converted raw annual INR to {clean_ctc} LPA")
                except ValueError:
                    pass

            # Standardize date format
            clean_d = clean_date(raw_date)
            if raw_date and clean_d and clean_d != raw_date:
                log_audit("source1_naukri_applicants.csv", idx, "Date Format Normalized", raw_date, f"Converted to ISO '{clean_d}'")

            # Standardize city names
            clean_c = clean_city(raw_city)
            if raw_city and clean_c != raw_city.strip():
                log_audit("source1_naukri_applicants.csv", idx, "City Canonicalized", raw_city, f"Standardized to '{clean_c}'")

            exp_val = float(raw_exp) if raw_exp and raw_exp.strip() else None

            record = {
                "full_name": clean_n,
                "email": clean_e,
                "phone": clean_p,
                "city": clean_c,
                "experience_years": exp_val,
                "current_ctc_lpa": clean_ctc,
                "applied_date": clean_d,
                "skills": raw_skills
            }
            matcher.process_record(record, "S1_Naukri", audit_callback=log_audit)
        
# Ingests and cleans gig workers from Source 2, fixing swapped columns and rate formats
def process_source2(matcher: EntityMatcher):
    print("🔹 Processing Source 2: Gig Workers...")
    with open(SRC2_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines[1:], start=2):
        raw_line = line.strip()
        # Detect and skip completely empty rows (such as line 12)
        if not raw_line or raw_line == ",,,,,":
            log_audit("source2_gig_workers.csv", idx, "Empty Row Filtered", raw_line, "Skipped completely blank row")
            continue

        # Parse CSV line respecting quotes
        parts = [p.strip(' \t\r\n"') for p in re.split(r',(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', raw_line)]
        if len(parts) < 6:
            continue

        # Detect swapped columns where skill tags appear in column 1 instead of email
        if "@" in parts[1]:
            log_audit("source2_gig_workers.csv", idx, "Swapped Columns Detected", raw_line, "Realigned: [skills, email, name, rate, location, status]")
            raw_email = parts[1]
            raw_name = parts[2]
            raw_rate = parts[3]
            raw_location = parts[4]
            raw_status = parts[5]
            raw_skills = parts[0]
        else:
            raw_email = parts[0]
            raw_name = parts[1]
            raw_rate = parts[2]
            raw_location = parts[3]
            raw_status = parts[4]
            raw_skills = parts[5]

        clean_e = clean_email(raw_email)
        clean_n = clean_name(raw_name)
        clean_c = clean_city(raw_location)
        rate_hr, rate_mo = clean_rate(raw_rate)
        clean_st = clean_status(raw_status)

        # Log rate conversion
        if raw_rate:
            log_audit("source2_gig_workers.csv", idx, "Rate Format Standardized", raw_rate, f"Hourly: {rate_hr}, Monthly: {rate_mo}")

        record = {
            "full_name": clean_n,
            "email": clean_e,
            "phone": None,
            "city": clean_c,
            "rate_hourly_inr": rate_hr,
            "rate_monthly_inr": rate_mo,
            "status": clean_st,
            "skills": raw_skills
        }
        matcher.process_record(record, "S2_GigWorkers", audit_callback=log_audit)

# Ingests and cleans contacts from Source 3 (CBNexus), handling duplicate headers and verification flags
def process_source3(matcher: EntityMatcher):
    print("🔹 Processing Source 3: CBNexus Contacts...")
    with open(SRC3_PATH, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()

    for idx, line in enumerate(lines[1:], start=2):
        raw_line = line.strip()
        if not raw_line:
            continue

        parts = [p.strip(' \t\r\n"') for p in re.split(r',(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)', raw_line)]
        # Detect repeated header line inside data body (line 16)
        if parts[0] == "Name" and parts[1] == "Phone Number":
            log_audit("source3_cbnexus_contacts.csv", idx, "Duplicate Header Row", raw_line, "Skipped repeated CSV header line")
            continue

        raw_name = parts[0]
        raw_phone = parts[1]
        raw_city = parts[2]
        raw_verified = parts[3] if len(parts) > 3 else "N"
        raw_projects = parts[4] if len(parts) > 4 else "0"

        clean_p = clean_phone_number(raw_phone)
        clean_n = clean_name(raw_name)
        clean_c = clean_city(raw_city)
        clean_v = clean_verified(raw_verified)
        try:
            projects_cnt = int(raw_projects)
        except ValueError:
            projects_cnt = 0

        # Log uppercase name normalization
        if raw_name.isupper():
            log_audit("source3_cbnexus_contacts.csv", idx, "Uppercase Name Normalized", raw_name, f"Converted to Title Case '{clean_n}'")

        # Log verified string normalization
        log_audit("source3_cbnexus_contacts.csv", idx, "Verification Flag Normalized", raw_verified, f"Normalized to '{clean_v}' (was: '{raw_verified}')")

        record = {
            "full_name": clean_n,
            "email": None,
            "phone": clean_p,
            "city": clean_c,
            "is_verified": clean_v,
            "projects_completed": projects_cnt
        }
        matcher.process_record(record, "S3_CBNexus", audit_callback=log_audit)

# Persists all deduplicated candidates and audit records into MySQL
def save_to_mysql(matcher: EntityMatcher):
    print("💾 Persisting unified records into MySQL database...")
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # Clear existing data to allow idempotent re-runs
            cursor.execute("DELETE FROM audio_submissions;")
            cursor.execute("DELETE FROM data_cleaning_audit;")
            cursor.execute("DELETE FROM candidates;")

            # Insert consolidated candidate records
            candidate_sql = """
                INSERT INTO candidates (
                    full_name, email, phone, city, experience_years, current_ctc_lpa,
                    applied_date, rate_hourly_inr, rate_monthly_inr, status,
                    skills, skill_category, is_verified, projects_completed, data_sources
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            for c in matcher.candidates:
                sources_str = ", ".join(sorted(list(c.data_sources)))
                cursor.execute(candidate_sql, (
                    c.full_name,
                    c.email,
                    c.phone,
                    c.city,
                    c.experience_years,
                    c.current_ctc_lpa,
                    c.applied_date,
                    c.rate_hourly_inr,
                    c.rate_monthly_inr,
                    c.status,
                    c.skills,
                    c.skill_category,
                    c.is_verified if isinstance(c.is_verified, str) else ("Yes" if c.is_verified else "No"),
                    c.projects_completed,
                    sources_str
                ))

            # Insert audit trail logs
            audit_sql = """
                INSERT INTO data_cleaning_audit (source_file, row_index, issue_type, raw_data, action_taken)
                VALUES (%s, %s, %s, %s, %s)
            """
            for a in audit_logs:
                cursor.execute(audit_sql, (
                    a["source_file"],
                    a["row_index"],
                    a["issue_type"],
                    a["raw_data"],
                    a["action_taken"]
                ))

    print(f"✅ Successfully inserted {len(matcher.candidates)} unified candidates and {len(audit_logs)} audit records!")

# Main execution entrypoint orchestrating data ingestion and database synchronization
def run_pipeline():
    print("=" * 60)
    print("🚀 Starting ConsultBae Multi-Source Merge ETL Pipeline")
    print("=" * 60)

    matcher = EntityMatcher()
    process_source1(matcher)
    process_source2(matcher)
    process_source3(matcher)
    save_to_mysql(matcher)

    print("\n📊 Ingestion & Merge Summary Statistics:")
    print(f" • Total Unique Candidates Created: {len(matcher.candidates)}")
    print(f" • Total Data Quality Issues Logged: {len(audit_logs)}")
    
    # Categorization breakdown
    categories: Dict[str, int] = {}
    for c in matcher.candidates:
        categories[c.skill_category] = categories.get(c.skill_category, 0) + 1
    print("\n🎯 Skill Category Breakdown:")
    for cat, count in categories.items():
        print(f"   - {cat}: {count}")

    print("\n✅ Task 1 Database Merge Pipeline Completed Successfully!\n")

if __name__ == "__main__":
    run_pipeline()
