# Data cleaning and normalization utility module
# Standardizes dirty, inconsistent fields across phone, email, dates, rates, and skills

import re
from datetime import datetime
from typing import Optional, Tuple, List, Set

# Normalizes phone numbers by stripping country codes, prefixes, spaces, and formatting to standard 10 digits
def clean_phone_number(raw_phone: Optional[str]) -> Optional[str]:
    if not raw_phone:
        return None
    # Remove all non-numeric characters such as plus signs, dashes, and spaces
    digits = re.sub(r"[^0-9]", "", str(raw_phone).strip())
    # Handle Indian country code prefix 91 when total length is 12 digits
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    # Handle leading zero prefix when total length is 11 digits
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    # Return valid 10-digit mobile number or None if length is invalid
    return digits if len(digits) == 10 else None

# Converts email addresses to lowercase and removes leading or trailing whitespace
def clean_email(raw_email: Optional[str]) -> Optional[str]:
    if not raw_email:
        return None
    cleaned = str(raw_email).strip().lower()
    # Validate basic email structure containing an '@' and a domain dot
    if "@" in cleaned and "." in cleaned.split("@")[-1]:
        return cleaned
    return None

# Standardizes person names into Title Case while removing extraneous whitespace
def clean_name(raw_name: Optional[str]) -> str:
    if not raw_name:
        return ""
    # Split by whitespace and rejoin with single spaces in Title Case format
    tokens = str(raw_name).strip().split()
    return " ".join(t.capitalize() for t in tokens)

# Canonicalizes city names to unify variations, spelling differences, and abbreviations
def clean_city(raw_city: Optional[str]) -> str:
    if not raw_city:
        return "Unknown"
    city_lower = str(raw_city).strip().lower()
    # Normalize variants of Gurugram and Gurgaon
    if "gurgaon" in city_lower or "gurugram" in city_lower:
        return "Gurugram"
    # Normalize variants of Bangalore and Bengaluru
    elif "bangalore" in city_lower or "bengaluru" in city_lower:
        return "Bengaluru"
    # Normalize variants of Delhi, New Delhi, and Delhi NCR
    elif "delhi" in city_lower:
        if "ncr" in city_lower:
            return "Delhi NCR"
        return "New Delhi"
    # Normalize variants of Pune
    elif "pune" in city_lower:
        return "Pune"
    # Normalize variants of Noida
    elif "noida" in city_lower:
        return "Noida"
    # Fallback to Title Case for other locations
    return str(raw_city).strip().title()

# Normalizes Current CTC values into standard Lakhs Per Annum (LPA) float format
def clean_ctc_lpa(raw_ctc: Optional[any]) -> Optional[float]:
    if raw_ctc is None or str(raw_ctc).strip() == "" or str(raw_ctc).lower() == "nan":
        return None
    try:
        val = float(str(raw_ctc).strip())
        # If value is greater than 1000, it represents raw annual INR, convert by dividing by 100,000
        if val > 1000:
            return round(val / 100000.0, 2)
        # Otherwise it is already in LPA format (e.g. 4.2 LPA)
        return round(val, 2)
    except (ValueError, TypeError):
        return None

# Parses rate strings into structured hourly and monthly rate values in INR
def clean_rate(raw_rate: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    if not raw_rate or str(raw_rate).strip() == "":
        return None, None
    text = str(raw_rate).strip().lower()
    # Parse hourly rates formatted like '1415/hr'
    if "/hr" in text or "hr" in text:
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            return float(match.group(1)), None
    # Parse monthly rates formatted like '15k/month' or '72k/month'
    if "month" in text or "/month" in text or "k/" in text or text.endswith("k"):
        match = re.search(r"(\d+(?:\.\d+)?)\s*k", text)
        if match:
            return None, float(match.group(1)) * 1000.0
        match_num = re.search(r"(\d+(?:\.\d+)?)", text)
        if match_num:
            return None, float(match_num.group(1))
    return None, None

# Standardizes worker status values into Active, Inactive, or Paused
def clean_status(raw_status: Optional[str]) -> str:
    if not raw_status:
        return "Active"
    s = str(raw_status).strip().lower()
    if s == "active":
        return "Active"
    elif s == "inactive":
        return "Inactive"
    elif s == "paused":
        return "Paused"
    return str(raw_status).strip().capitalize()

# Normalizes verification flags to consistent "Yes" or "No" string values
# Accepts: Y, y, Yes, yes, YES, true, 1 → "Yes" | N, n, No, no, NO, false, 0, blank → "No"
def clean_verified(raw_verified: Optional[str]) -> str:
    if not raw_verified:
        return "No"
    val = str(raw_verified).strip().lower()
    return "Yes" if val in ["y", "yes", "true", "1"] else "No"

# Parses varied date strings into standard ISO YYYY-MM-DD format for SQL storage
def clean_date(raw_date: Optional[str]) -> Optional[str]:
    if not raw_date or str(raw_date).strip() == "" or str(raw_date).lower() == "nan":
        return None
    d_str = str(raw_date).strip()
    # List of expected date pattern formats found across source systems
    formats = [
        "%d-%m-%Y",     # e.g. 24-07-2026
        "%Y-%m-%d",     # e.g. 2026-08-08
        "%d %b %Y",     # e.g. 7 Jul 2026, 24 Jun 2026
        "%m/%d/%Y",     # e.g. 07/13/2026, 08/13/2026
        "%d/%m/%Y"      # e.g. 13/07/2026 fallback
    ]
    for fmt in formats:
        try:
            parsed = datetime.strptime(d_str, fmt)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None

# Cleans and standardizes skills into a comma-separated list of Title Case skills
def clean_skills(raw_skills: Optional[str]) -> Tuple[str, List[str]]:
    if not raw_skills or str(raw_skills).strip() in ["", "-", "--", "n/a", "N/A", "nan", "NaN", "None", "null"]:
        return "--", []
    # Split skills by commas and remove surrounding quotes and extra whitespace
    raw_list = [s.strip(" \"'\t\r\n") for s in str(raw_skills).split(",")]
    canonical_skills = []
    seen = set()
    for s in raw_list:
        if not s or s.strip() in ["-", "--", "n/a", "N/A", "nan", "NaN", "None", "null"]:
            continue
        # Map specific tech names to their official standard casing
        s_lower = s.lower()
        if s_lower == "fastapi":
            std = "FastAPI"
        elif s_lower == "mysql":
            std = "MySQL"
        elif s_lower == "mongodb":
            std = "MongoDB"
        elif s_lower == "javascript":
            std = "JavaScript"
        elif s_lower == "n8n":
            std = "n8n"
        elif s_lower == "rest apis" or s_lower == "rest api":
            std = "REST APIs"
        elif s_lower == "sql":
            std = "SQL"
        elif s_lower == "langchain":
            std = "LangChain"
        else:
            std = s.title()
        if std.lower() not in seen:
            seen.add(std.lower())
            canonical_skills.append(std)
    if not canonical_skills:
        return "--", []
    return ", ".join(canonical_skills), canonical_skills

# Automatically tags each candidate into a high-level domain category based on their skill set across technical and non-technical industries
def categorize_skills(skills_list: List[str]) -> str:
    if not skills_list:
        return "--"
    s_set = {s.lower().strip() for s in skills_list}
    s_text = " ".join(s_set)

    # 1. Automation & AI Heavy
    if any(k in s_text for k in ["n8n", "zapier", "langchain", "llm", "ai automation", "prompt engineering", "openai", "machine learning"]):
        return "Automation & AI Heavy"

    # 2. Sales & Business Development
    if any(k in s_text for k in ["sales", "business development", "b2b", "b2c", "lead generation", "cold calling", "crm", "account management", "inside sales", "client acquisition"]):
        return "Sales & Business Development"

    # 3. Marketing & Growth
    if any(k in s_text for k in ["marketing", "digital marketing", "seo", "sem", "social media", "content writing", "copywriting", "performance marketing", "google ads", "facebook ads", "branding"]):
        return "Marketing & Growth"

    # 4. Human Resources & Talent Acquisition
    if any(k in s_text for k in ["hr", "human resources", "recruitment", "talent acquisition", "payroll", "employee engagement", "onboarding", "hris", "sourcing", "hiring"]):
        return "HR & Talent Acquisition"

    # 5. Finance & Accounting
    if any(k in s_text for k in ["finance", "accounting", "tally", "gst", "taxation", "financial analysis", "bookkeeping", "auditing", "invoicing", "tally prime"]):
        return "Finance & Accounting"

    # 6. Design & Creative
    if any(k in s_text for k in ["ui/ux", "figma", "graphic design", "photoshop", "illustrator", "video editing", "premiere pro", "after effects", "canva", "wireframing"]):
        return "Design & Creative"

    # 7. Operations & Support
    if any(k in s_text for k in ["operations", "supply chain", "project management", "customer support", "customer service", "logistics", "team management", "administration"]):
        return "Operations & Support"

    # 8. Web & Fullstack Development
    if any(k in s_text for k in ["react", "javascript", "typescript", "angular", "vue", "fastapi", "node", "django", "flask", "fullstack", "frontend", "backend", "web development", "rest apis", "php", "laravel", "java", "c++", "c#", ".net"]):
        return "Web & Fullstack"

    # 9. Data & Analytics
    if any(k in s_text for k in ["pandas", "mysql", "mongodb", "sql", "power bi", "tableau", "data analysis", "data science", "etl", "excel", "big data"]):
        return "Data & Analytics"

    # 10. QA & Web Scraping
    if any(k in s_text for k in ["selenium", "web scraping", "playwright", "puppeteer", "testing", "qa", "manual testing", "cypress", "postman"]):
        return "QA & Web Scraping"

    return "General / Other Role"
