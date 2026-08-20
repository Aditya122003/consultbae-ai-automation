# Entity resolution and deduplication engine
# Unifies records across disparate sources using multi-pass matching on phone, email, and name+city

from typing import Dict, List, Optional, Any
from .data_cleaner import clean_skills, categorize_skills, clean_name

# Unified candidate entity representing a single consolidated person profile
class UnifiedCandidate:
    def __init__(self, full_name: str, email: Optional[str] = None, phone: Optional[str] = None, city: Optional[str] = None):
        # Initialize primary identification attributes
        self.full_name = clean_name(full_name)
        self.email = email
        self.phone = phone
        self.city = city
        # Multi-attribute tracking sets for anomaly detection (3+ location / phone limits)
        self.phone_numbers: set = set([phone]) if phone else set()
        self.locations: set = set([city]) if city and city != "Unknown" else set()
        # Experience and financial metrics
        self.experience_years: Optional[float] = None
        self.current_ctc_lpa: Optional[float] = None
        self.applied_date: Optional[str] = None
        self.rate_hourly_inr: Optional[float] = None
        self.rate_monthly_inr: Optional[float] = None
        # Status and project verification metrics
        self.status: str = "Active"
        self.skills_set: set = set()
        self.skill_category: str = "General"
        self.is_verified: str = "No"
        self.projects_completed: int = 0
        self.data_sources: set = set()

    # Returns comma-separated canonical string of merged skills
    @property
    def skills(self) -> str:
        return ", ".join(sorted(list(self.skills_set)))

    # Merges incoming source attributes into this candidate record while preserving highest quality data
    def merge(self, incoming: Dict[str, Any], source_label: str, audit_callback: Optional[Any] = None):
        # Record source system contributing to this profile
        self.data_sources.add(source_label)
        
        # Upgrade abbreviated or short name to full name if available (e.g. 'R. Verma' -> 'Rohit Verma')
        incoming_name = clean_name(incoming.get("full_name") or incoming.get("worker_name") or incoming.get("Name"))
        if incoming_name:
            if len(incoming_name) > len(self.full_name) and not ("." in incoming_name and "." not in self.full_name):
                self.full_name = incoming_name

        # Update contact and location fields if currently missing
        if not self.email and incoming.get("email"):
            self.email = incoming.get("email")
        if not self.phone and incoming.get("phone"):
            self.phone = incoming.get("phone")
        if (not self.city or self.city == "Unknown") and incoming.get("city"):
            self.city = incoming.get("city")

        # Track distinct phones and cities to audit 3+ anomaly limits
        inc_phone = incoming.get("phone")
        if inc_phone:
            self.phone_numbers.add(inc_phone)
            if len(self.phone_numbers) >= 3 and audit_callback:
                audit_callback(
                    source_label,
                    0,
                    "Excessive Phone Numbers Anomaly",
                    f"Candidate '{self.full_name}' linked with {len(self.phone_numbers)} phones: {list(self.phone_numbers)}",
                    f"Flagged for audit: Worker exceeds 3 phone limit. Kept primary '{self.phone}'."
                )

        inc_city = incoming.get("city")
        if inc_city and inc_city != "Unknown":
            self.locations.add(inc_city)
            if len(self.locations) >= 3 and audit_callback:
                audit_callback(
                    source_label,
                    0,
                    "Excessive Locations Anomaly",
                    f"Candidate '{self.full_name}' linked with {len(self.locations)} cities: {list(self.locations)}",
                    f"Flagged for audit: Worker exceeds 3 location limit. Kept primary '{self.city}'."
                )

        # Merge recruitment metrics from Source 1
        if incoming.get("experience_years") is not None:
            self.experience_years = incoming["experience_years"]
        if incoming.get("current_ctc_lpa") is not None:
            self.current_ctc_lpa = incoming["current_ctc_lpa"]
        if incoming.get("applied_date") is not None:
            self.applied_date = incoming["applied_date"]

        # Merge gig rate and status metrics from Source 2
        if incoming.get("rate_hourly_inr") is not None:
            self.rate_hourly_inr = incoming["rate_hourly_inr"]
        if incoming.get("rate_monthly_inr") is not None:
            self.rate_monthly_inr = incoming["rate_monthly_inr"]
        if incoming.get("status"):
            self.status = incoming["status"]

        # Merge verification and projects metrics from Source 3
        if incoming.get("is_verified") is not None:
            inc_v = incoming["is_verified"]
            if isinstance(inc_v, str):
                if inc_v.strip().lower() in ["yes", "y", "true", "1"]:
                    self.is_verified = "Yes"
                elif self.is_verified != "Yes":
                    self.is_verified = "No"
            elif inc_v:
                self.is_verified = "Yes"
        if incoming.get("projects_completed") is not None:
            self.projects_completed = max(self.projects_completed, incoming["projects_completed"])

        # Accumulate and union unique skills across all participating sources
        incoming_skills_str = incoming.get("skills") or incoming.get("skill_tags") or ""
        _, skills_list = clean_skills(incoming_skills_str)
        for s in skills_list:
            self.skills_set.add(s)

        # Re-compute skill category using the complete union of verified skills
        self.skill_category = categorize_skills(list(self.skills_set))


# Multi-pass entity matcher maintaining lookup indices for fast deduplication
class EntityMatcher:
    def __init__(self):
        # Master repository of deduplicated candidate instances
        self.candidates: List[UnifiedCandidate] = []
        # Multi-key index maps for rapid O(1) matching lookups
        self.phone_index: Dict[str, UnifiedCandidate] = {}
        self.email_index: Dict[str, UnifiedCandidate] = {}
        self.name_city_index: Dict[str, UnifiedCandidate] = {}

    # Matches an incoming record against existing candidates or instantiates a new entity
    def process_record(self, record: Dict[str, Any], source_label: str, audit_callback: Optional[Any] = None) -> UnifiedCandidate:
        phone = record.get("phone")
        email = record.get("email")
        name = clean_name(record.get("full_name") or record.get("worker_name") or record.get("Name"))
        city = record.get("city") or "Unknown"

        matched_candidate: Optional[UnifiedCandidate] = None

        # Pass 1: Attempt matching via unique 10-digit phone number
        if phone and phone in self.phone_index:
            matched_candidate = self.phone_index[phone]

        # Pass 2: Attempt matching via unique lowercase email address
        elif email and email in self.email_index:
            matched_candidate = self.email_index[email]

        # Pass 3: Attempt matching via Name + City combination for records lacking cross-system IDs
        elif name and city and city != "Unknown":
            # Generate primary key and fuzzy initial key (e.g. 'r verma|bengaluru')
            key = f"{name.lower()}|{city.lower()}"
            if key in self.name_city_index:
                matched_candidate = self.name_city_index[key]
            else:
                # Check for initial abbreviation match like 'r. verma' vs 'rohit verma'
                parts = name.split()
                if len(parts) >= 2:
                    initial_key = f"{parts[0][0].lower()} {parts[-1].lower()}|{city.lower()}"
                    if initial_key in self.name_city_index:
                        matched_candidate = self.name_city_index[initial_key]

        # If entity does not exist yet, create a new master record
        if not matched_candidate:
            matched_candidate = UnifiedCandidate(full_name=name, email=email, phone=phone, city=city)
            self.candidates.append(matched_candidate)

        # Merge incoming data into the matched entity
        matched_candidate.merge(record, source_label, audit_callback=audit_callback)

        # Re-index matched entity under all available keys to link future records
        if matched_candidate.phone:
            self.phone_index[matched_candidate.phone] = matched_candidate
        if matched_candidate.email:
            self.email_index[matched_candidate.email] = matched_candidate
        if matched_candidate.full_name and matched_candidate.city:
            self.name_city_index[f"{matched_candidate.full_name.lower()}|{matched_candidate.city.lower()}"] = matched_candidate
            parts = matched_candidate.full_name.split()
            if len(parts) >= 2:
                initial_key = f"{parts[0][0].lower()} {parts[-1].lower()}|{matched_candidate.city.lower()}"
                self.name_city_index[initial_key] = matched_candidate

        return matched_candidate
