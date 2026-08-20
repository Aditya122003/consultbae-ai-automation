// Audio service communicating with backend API for recording submissions and telemetry
// Manages HTTP requests for audio acoustic extraction, submission listings, and platform metrics

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AudioSubmission, PlatformStats } from '../models/types';

@Injectable({
  providedIn: 'root'
})
export class AudioService {
  // Base backend API server URL
  private readonly baseUrl = 'http://localhost:8000/api';

  constructor(private http: HttpClient) { }

  // Submits a recorded audio blob or uploaded file along with worker identification to the server
  submitAudio(workerName: string, workerPhone: string, audioFile: Blob, fileName: string = 'recording.webm'): Observable<any> {
    const formData = new FormData();
    formData.append('worker_name', workerName);
    formData.append('worker_phone', workerPhone);
    formData.append('file', audioFile, fileName);

    return this.http.post<any>(`${this.baseUrl}/audio/submit`, formData);
  }

  // Fetches all historical audio submissions and their extracted acoustic properties
  getSubmissions(): Observable<{ status: string; count: number; data: AudioSubmission[] }> {
    return this.http.get<{ status: string; count: number; data: AudioSubmission[] }>(`${this.baseUrl}/audio/submissions`);
  }

  // Retrieves real-time platform metrics and analytics
  getStats(): Observable<PlatformStats> {
    return this.http.get<PlatformStats>(`${this.baseUrl}/stats`);
  }
}
