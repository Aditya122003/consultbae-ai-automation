// Data contract interfaces representing candidate profiles, audio metadata, and analytics
// Ensures strict TypeScript type safety across all frontend components and API services

export interface AudioProperties {
  file_size_bytes: number;
  duration_seconds: number;
  sample_rate_hz: number;
  sample_rate_khz: number;
  bitrate_kbps: number;
  loudness_db: number;
  snr_quality_score: number;
  quality_label: string;
}

export interface AudioSubmission {
  id: number;
  candidate_id?: number | null;
  worker_name: string;
  worker_phone: string;
  audio_filename: string;
  audio_filepath: string;
  audio_url: string;
  file_size_bytes: number;
  duration_seconds: number;
  sample_rate_hz: number;
  sample_rate_khz: number;
  bitrate_kbps: number;
  loudness_db: number;
  snr_quality_score: number;
  quality_label: string;
  city?: string;
  skill_category?: string;
  worker_status?: string;
  created_at: string;
}

export interface Candidate {
  id: number;
  full_name: string;
  email?: string | null;
  phone?: string | null;
  city?: string | null;
  experience_years?: number | null;
  current_ctc_lpa?: number | null;
  applied_date?: string | null;
  rate_hourly_inr?: number | null;
  rate_monthly_inr?: number | null;
  status: string;
  skills?: string;
  skill_category: string;
  is_verified: boolean | number | string;
  projects_completed: number;
  data_sources: string;
  extra_fields?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface PlatformStats {
  status: string;
  total_candidates: number;
  verified_candidates: number;
  skill_categories: { skill_category: string; count: number }[];
  total_audio_submissions: number;
  avg_audio_quality_score: number;
  avg_duration_seconds: number;
  audio_quality_breakdown: { quality_label: string; count: number }[];
}
