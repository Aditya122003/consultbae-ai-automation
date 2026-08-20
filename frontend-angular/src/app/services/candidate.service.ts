// Candidate directory service managing search, filtering, and database synchronization
// Retrieves merged worker records and provides lookup helpers for the recording studio

import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Candidate } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class CandidateService {
  // Base backend API server URL
  private readonly baseUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) { }

  // Retrieves filtered list of unified candidate profiles from MySQL database
  getCandidates(search?: string, city?: string, category?: string): Observable<{ status: string; count: number; data: Candidate[] }> {
    let params = new HttpParams();
    if (search && search.trim()) {
      params = params.set('search', search.trim());
    }
    if (city && city !== 'ALL') {
      params = params.set('city', city);
    }
    if (category && category !== 'ALL') {
      params = params.set('category', category);
    }

    return this.http.get<{ status: string; count: number; data: Candidate[] }>(`${this.baseUrl}/candidates`, { params });
  }

  // Triggers the real n8n automation pipeline on backend (MySQL duplicate lookup, AI classification, Real Email dispatch)
  triggerAutomation(payload: { full_name: string; phone: string; email?: string; skills?: string; city?: string; recipient_email?: string }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/automation/trigger`, payload);
  }

  // Updates candidate profile by triggering backend pipeline re-run cleaning
  updateCandidate(id: number, payload: Partial<Candidate>): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/candidates/${id}`, payload);
  }

  // Uploads CSV file to backend for pipeline processing and Task 4 error logging
  uploadCandidatesCsv(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<any>(`${this.baseUrl}/candidates/upload-csv`, formData);
  }

  // Retrieves real-time audit logs from MySQL data_cleaning_audit table (all entries)
  getAuditLogs(): Observable<{ status: string; count: number; data: any[] }> {
    return this.http.get<{ status: string; count: number; data: any[] }>(`${this.baseUrl}/audit-logs`);
  }

  // Retrieves ONLY rejected/failed import rows — used by Log History modal
  // Shows records that could NOT enter the system along with rejection reasons
  getRejectedLogs(): Observable<{ status: string; count: number; data: any[] }> {
    return this.http.get<{ status: string; count: number; data: any[] }>(`${this.baseUrl}/audit-logs/rejected`);
  }

  // Retrieves ONLY data quality / normalization events — used by Task 4 Report
  // Includes: merges, name changes, Y→YES boolean fixes, phone/email/city normalizations
  getQualityIssuesLogs(): Observable<{ status: string; count: number; data: any[] }> {
    return this.http.get<{ status: string; count: number; data: any[] }>(`${this.baseUrl}/audit-logs/quality-issues`);
  }
}
