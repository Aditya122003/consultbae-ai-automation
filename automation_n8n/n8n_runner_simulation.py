# Low-code automation verification and simulation runner
# Demonstrates webhook ingestion, database duplicate detection, and LLM categorization mirroring n8n workflow

import json
from typing import Dict, Any
from pipeline.db_connection import get_db_connection
from pipeline.data_cleaner import (
    clean_phone_number,
    clean_email,
    clean_name,
    clean_city,
    clean_skills,
    categorize_skills
)

# Simulates n8n Webhook entrypoint with deduplication check and LLM categorization
def simulate_n8n_flow(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Extract and clean incoming fields
    raw_name = payload.get("full_name") or payload.get("Name") or payload.get("worker_name")
    raw_phone = payload.get("phone") or payload.get("Phone") or payload.get("Phone Number")
    raw_email = payload.get("email") or payload.get("Email") or payload.get("email_id")
    raw_skills = payload.get("skills") or payload.get("skill_tags") or ""
    raw_city = payload.get("city") or payload.get("City") or payload.get("location")

    phone = clean_phone_number(raw_phone)
    email = clean_email(raw_email)
    name = clean_name(raw_name)
    city = clean_city(raw_city)
    canonical_skills_str, skills_list = clean_skills(raw_skills)

    print("\n" + "="*50)
    print(f"📥 [n8n Webhook Trigger] Received candidate: '{name}' | Phone: {phone} | Email: {email}")

    # Check for existing duplicate in MySQL database
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            query = """
                SELECT id, full_name, email, phone, city, skill_category, data_sources
                FROM candidates
                WHERE (phone IS NOT NULL AND phone = %s) OR (email IS NOT NULL AND email = %s)
                LIMIT 1
            """
            cursor.execute(query, (phone, email))
            existing = cursor.fetchone()

    # If duplicate found, route to Duplicate Alert notification branch
    if existing:
        print("⚠️ [n8n Router Node: DUPLICATE FOUND]")
        print(f"   -> Matched Existing ID #{existing['id']} ({existing['full_name']})")
        print(f"   -> Dispatched Alert to Slack Webhook / Email Notification!")
        return {
            "status": "DUPLICATE_DETECTED",
            "message": f"Duplicate candidate record detected for '{name}'",
            "matched_existing_id": existing["id"],
            "matched_candidate_name": existing["full_name"],
            "matched_phone": existing["phone"],
            "matched_email": existing["email"],
            "data_sources": existing["data_sources"]
        }

    # If new candidate, route to LLM Skill Auto-Categorization node
    category = categorize_skills(skills_list)
    print(f"🤖 [n8n LLM Node] Auto-categorized skill set into: '{category}'")

    # Persist newly enriched candidate into MySQL database
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            insert_sql = """
                INSERT INTO candidates (full_name, email, phone, city, skills, skill_category, status, data_sources)
                VALUES (%s, %s, %s, %s, %s, %s, 'Active', 'n8n_Webhook_Automation')
            """
            cursor.execute(insert_sql, (name, email, phone, city, canonical_skills_str, category))
            new_id = cursor.lastrowid

    print(f"💾 [n8n MySQL Node] Successfully inserted new candidate with ID #{new_id}")
    return {
        "status": "SUCCESS",
        "message": "Candidate successfully ingested, auto-categorized by AI, and stored in MySQL",
        "id": new_id,
        "full_name": name,
        "email": email,
        "phone": phone,
        "category": category,
        "skills": canonical_skills_str
    }

# Executes test simulation cases covering both duplicate detection and new candidate onboarding
def main():
    print("🚀 Running ConsultBae n8n Workflow Simulation Test Suite")

    # Test Case 1: Ingesting an existing candidate (Duplicate Trigger)
    duplicate_payload = {
        "full_name": "Tanvi Gupta",
        "phone": "+91-9000000254",
        "email": "tanvi.gupta31@example.com",
        "skills": "n8n, LangChain, REST APIs, MongoDB, SQL",
        "city": "Bengaluru"
    }
    res1 = simulate_n8n_flow(duplicate_payload)
    print("Result 1:", json.dumps(res1, indent=2))

    # Test Case 2: Ingesting a brand new AI automation specialist
    new_candidate_payload = {
        "full_name": "Aarav Singhal",
        "phone": "9876543210",
        "email": "aarav.singhal@example.com",
        "skills": "n8n, Zapier, LangChain, Python, OpenAI, Vector DBs",
        "city": "Gurugram"
    }
    res2 = simulate_n8n_flow(new_candidate_payload)
    print("Result 2:", json.dumps(res2, indent=2))

if __name__ == "__main__":
    main()
