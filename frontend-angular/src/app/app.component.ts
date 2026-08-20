// Main root application component orchestrating the ConsultBae AI Automation Platform
// Manages task-wise navigation via 5 interactive KPI cards (Task 1, Task 2, Task 3.1, Task 3.2, Tasks 4 & 5)

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CandidateDirectoryComponent } from './components/candidate-directory/candidate-directory.component';
import { AutomationSimulatorComponent } from './components/automation-simulator/automation-simulator.component';
import { AudioRecorderComponent } from './components/audio-recorder/audio-recorder.component';
import { AudioGalleryComponent } from './components/audio-gallery/audio-gallery.component';
import { AudioService } from './services/audio.service';
import { PlatformStats } from './models/types';

import { CandidateService } from './services/candidate.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    CandidateDirectoryComponent,
    AutomationSimulatorComponent,
    AudioRecorderComponent,
    AudioGalleryComponent
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  // Application title
  title = 'ConsultBae AI Automation & Audio Platform';

  // Active navigation view tab identifier mapped to the 5 deliverables:
  // Task 1, Task 2, Task 3.1 (Audio Collection), Task 3.2 (Audio Catalog), Tasks 4 & 5 (Docs)
  activeTab: 'task1' | 'task2' | 'task3-1' | 'task3-2' | 'task4-5' = 'task1';

  // Live aggregated analytics stats
  stats: PlatformStats | null = null;
  isLoadingStats: boolean = false;

  // Dynamic live audit logs fetched from MySQL data_cleaning_audit table
  liveAuditLogs: any[] = [];
  isLoadingAuditLogs: boolean = false;

  constructor(
    private audioService: AudioService,
    private candidateService: CandidateService
  ) {}

  ngOnInit(): void {
    // Initial fetch of platform metrics and audit logs
    this.fetchStats();
    this.fetchAuditLogs();
  }

  // Retrieves platform telemetry stats from backend API
  fetchStats(): void {
    this.isLoadingStats = true;
    this.audioService.getStats().subscribe({
      next: (res: any) => {
        this.stats = res;
        this.isLoadingStats = false;
      },
      error: (err: any) => {
        console.error('Failed to load stats:', err);
        this.isLoadingStats = false;
      }
    });
    // Immediately fetch live audit logs so Tasks 4 & 5 update automatically on CSV upload
    this.fetchAuditLogs();
  }

  // Retrieves data QUALITY / NORMALIZATION events for Task 4 Report
  // Includes: merges, name changes, Y→YES boolean fixes, phone/city/email normalizations
  // Rejected rows are intentionally EXCLUDED — those go to Log History (Task 1) only
  fetchAuditLogs(): void {
    this.isLoadingAuditLogs = true;
    this.candidateService.getQualityIssuesLogs().subscribe({
      next: (res) => {
        this.liveAuditLogs = res.data || [];
        this.isLoadingAuditLogs = false;
      },
      error: (err) => {
        console.error('Failed to load quality issues audit logs:', err);
        this.liveAuditLogs = [];
        this.isLoadingAuditLogs = false;
      }
    });
  }

  // Switches active navigation view tab
  setTab(tab: 'task1' | 'task2' | 'task3-1' | 'task3-2' | 'task4-5'): void {
    this.activeTab = tab;
    if (tab === 'task4-5') {
      this.fetchAuditLogs();
    }
  }

  // Returns user-friendly badge title for currently selected task
  getActiveTaskLabel(): string {
    switch (this.activeTab) {
      case 'task1':
        return 'Viewing: Task 1 (Talent Directory)';
      case 'task2':
        return 'Viewing: Task 2 (n8n Automation)';
      case 'task3-1':
        return 'Viewing: Task 3.1 (Audio Collection)';
      case 'task3-2':
        return 'Viewing: Task 3.2 (Audio Catalog)';
      case 'task4-5':
        return 'Viewing: Tasks 4 & 5 (Audit & Scaling)';
      default:
        return 'Viewing: Task 1 (Talent Directory)';
    }
  }

  // Callback triggered when a new audio recording is submitted to refresh platform metrics
  onAudioSubmitted(): void {
    this.fetchStats();
  }

  // ── Data Quality Issues Table Data (Task 4) ────────────────────────────────
  dataIssues = [
    { id: '1.1', source: 'Source 1', sourceClass: 'src-1', type: 'Abbreviated Name & Duplicate', rows: 'Row 25 & 31', example: 'R. Verma vs Rohit Verma', cause: 'Candidate submitted twice with name abbreviation and full name', fix: 'Matched on phone 9000000294 & email; expanded "R. Verma" to "Rohit Verma"' },
    { id: '1.2', source: 'Source 1', sourceClass: 'src-1', type: 'Alternate Email Alias Duplicate', rows: 'Row 27 & 37', example: 'alt.nikhil.chopra70 vs nikhil.chopra70', cause: 'Same candidate used two different email aliases with identical phone', fix: 'Entity resolution via normalized phone 9000000103; merged into single profile' },
    { id: '1.3', source: 'Source 1', sourceClass: 'src-1', type: 'Phone Number Prefix Inconsistency', rows: '2,4,6,7,9,11+', example: '+919000000254, 09000000287', cause: 'Mixed +91, 91, leading 0 and raw 10-digit formats prevent relational joins', fix: 'Regex normalizer stripped non-digits; sliced country code to produce clean 10 digits' },
    { id: '1.4', source: 'Source 1', sourceClass: 'src-1', type: 'CTC Unit Mismatch (INR vs LPA)', rows: '2,3,4,5,6,7,8', example: '417964 vs 4.2 LPA', cause: 'CTC entered in absolute annual INR and LPA in same column', fix: 'Detected values >1000; divided by 100,000 to standardize all to DECIMAL(6,2) LPA' },
    { id: '1.5', source: 'Source 1', sourceClass: 'src-1', type: 'Mixed Date Formatting', rows: '2,3,5,7,8,25', example: '24-07-2026, 07/13/2026', cause: '4 distinct date formats (DD-MM-YYYY, YYYY-MM-DD, D Mon YYYY, MM/DD/YYYY)', fix: 'Multi-pattern datetime parser normalized all to ISO YYYY-MM-DD for SQL DATE storage' },
    { id: '1.6', source: 'Source 1', sourceClass: 'src-1', type: 'City Casing & Trailing Whitespace', rows: '3,4,10,13,15,22', example: 'GURGAON, gurugram , pune', cause: 'Inconsistent case and trailing spaces fragmented location filters', fix: 'Canonical city dictionary standardized to Gurugram, Bengaluru, Pune, Noida, New Delhi' },
    { id: '2.1', source: 'Source 2', sourceClass: 'src-2', type: 'Blank / Empty Row', rows: 'Row 12', example: ',,,,,', cause: 'Corrupt empty record consisting solely of comma delimiters', fix: 'Pre-processing filter detected and safely discarded delimiter-only rows' },
    { id: '2.2', source: 'Source 2', sourceClass: 'src-2', type: 'Swapped / Misaligned Columns', rows: 'Row 20', example: '"react, js, mysql",EMAIL@X.COM,Isha Chopra', cause: 'Column order shifted: skills in col 1, email in col 2, name in col 3', fix: 'Schema integrity detector identified @ in index 1 and realigned to correct column order' },
    { id: '2.3', source: 'Source 2', sourceClass: 'src-2', type: 'Uppercase Email Addresses', rows: '7,13,15,17,22,26,31,32', example: 'ISHA.CHOPRA95@MAILTEST.EXAMPLE.ORG', cause: 'Uppercase emails prevent case-sensitive joins across sources', fix: 'Converted all email strings to lowercase with whitespace trimmed' },
    { id: '2.4', source: 'Source 2', sourceClass: 'src-2', type: 'Mixed Rate Units (/hr vs k/month)', rows: '2,6,7,10,14,21', example: '1415/hr vs 15k/month', cause: 'Hourly and monthly rates stored in same unstructured string column', fix: 'Regex parser split into rate_hourly_inr and rate_monthly_inr (15k → 15000.00)' },
    { id: '2.5', source: 'Source 2', sourceClass: 'src-2', type: 'Inconsistent Status Casing', rows: '2,4,5,10,11', example: 'active, ACTIVE, Active, paused', cause: 'Case variations and inconsistent vocabulary across operators', fix: 'Normalized to canonical enumeration: Active, Inactive, Paused' },
    { id: '2.6', source: 'Source 2', sourceClass: 'src-2', type: 'Missing Phone Numbers', rows: 'All Rows', example: '(Column absent in Source 2)', cause: 'Source 2 lacks phone numbers entirely', fix: 'Cross-source entity resolution via normalized email and Name + City composite keys' },
    { id: '3.1', source: 'Source 3', sourceClass: 'src-3', type: 'Duplicate Header Row Inside Data', rows: 'Row 16', example: 'Name,Phone Number,City,Verified', cause: 'Secondary CSV header embedded mid-file from copy-paste error', fix: 'Ingestion engine matched row against known header tokens and discarded it' },
    { id: '3.2', source: 'Source 3', sourceClass: 'src-3', type: 'Uppercase Candidate Names', rows: '3,7,9,14,19,23,25,29,30', example: 'RITU SHARMA, RAHUL MALHOTRA', cause: 'Names exported in ALL CAPS from legacy CRM system', fix: 'Applied .title() normalization to all name fields (Ritu Sharma, Rahul Malhotra)' },
    { id: '3.3', source: 'Source 3', sourceClass: 'src-3', type: 'Phone Formatting & Country Codes', rows: '2,4,5,7,12', example: '+91-9000000131, 919000000231', cause: 'Variations with country prefixes, hyphens, and 12-digit integers', fix: 'Stripped non-numeric chars; sliced +91, 91, and 0 prefix to produce 10-digit numbers' },
    { id: '3.4', source: 'Source 3', sourceClass: 'src-3', type: 'Boolean Inconsistencies (Verification)', rows: '2,3,4,7,8,9', example: 'Y, yes, Yes, No, N', cause: 'Mixed boolean representation across different data entry operators', fix: 'Normalized to TINYINT(1): 1 for Y/yes/Yes, 0 for N/No' },
    { id: '3.5', source: 'Source 3', sourceClass: 'src-3', type: 'Missing Email Addresses', rows: 'All Rows', example: '(Column absent in Source 3)', cause: 'Source 3 lacked email addresses entirely', fix: 'Cross-source join via clean 10-digit phone number and Name + City keys' },
  ];

  // Exports live data quality and merge audit log records to a downloadable CSV report
  downloadIssuesCsv(): void {
    if (this.liveAuditLogs.length === 0) return;
    const headers = ['Source', 'CSV Rows Affected', 'Raw Example', 'Root Cause', 'Automated Fix'];
    const rows = this.liveAuditLogs.map((i) => {
      const cause = i.issue_type.includes('Merge')
        ? 'Duplicate Candidate Match (Phone / Email)'
        : (i.issue_type.includes('Rejected') || i.issue_type.includes('Validation') ? 'Validation Failure (Missing Required Fields)' : 'Pipeline Cleaning & Formatting');
      return [
        i.source_file,
        `Row ${i.row_index || '-'}`,
        i.raw_data,
        cause,
        i.action_taken
      ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(',');
    });
    const csvContent = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'data_quality_issues_report.csv';
    link.click();
    URL.revokeObjectURL(url);
  }
}
