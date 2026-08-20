// Master candidate directory component
// Displays deduplicated candidate profiles merged across all 3 source systems with interactive filtering

import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CandidateService } from '../../services/candidate.service';
import { Candidate } from '../../models/types';

@Component({
  selector: 'app-candidate-directory',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './candidate-directory.component.html',
  styleUrls: ['./candidate-directory.component.css']
})
export class CandidateDirectoryComponent implements OnInit {
  // Output event to trigger parent app stats refresh
  @Output() statsUpdated = new EventEmitter<void>();

  // Master list of all candidate records
  candidates: Candidate[] = [];
  filteredCandidates: Candidate[] = [];

  // Search and filter parameters
  searchTerm: string = '';
  selectedCity: string = 'ALL';
  selectedCategory: string = 'ALL';
  isLoading: boolean = false;

  // Filter options lists
  citiesList: string[] = ['ALL', 'Bengaluru', 'Gurugram', 'Noida', 'Pune', 'New Delhi', 'Delhi NCR'];
  categoriesList: string[] = ['ALL', 'Automation & AI Heavy', 'Web & Fullstack', 'Data & Analytics', 'QA & Web Scraping'];

  // Toast notification state — type drives colour (success=green, error=red, info=blue)
  toastMessage: string = '';
  toastType: 'success' | 'error' | 'info' = 'success';
  private toastTimer: any = null;


  // CSV Upload & History state
  isUploadingCsv: boolean = false;
  csvSuccessMessage: string = '';
  csvErrorMessage: string = '';
  isHistoryModalOpen: boolean = false;
  isLoadingHistory: boolean = false;
  csvAuditLogs: any[] = [];

  // Grouped import sessions for Log History modal
  // Each session = all rejected rows from one upload batch (within 2-min window)
  groupedRejectedLogs: {
    sessionLabel: string;
    sessionTime: Date;
    sourceFiles: string[];
    logs: any[];
    expanded: boolean;
  }[] = [];

  // Edit modal state
  editingCandidate: Candidate | null = null;
  editForm: Partial<Candidate> = {};
  isSaving: boolean = false;
  cardErrorMessage: string = '';


  // CSV Batch Ingestion Summary Modal state
  isCsvSummaryModalOpen: boolean = false;
  csvSummaryData: {
    totalFiles: number;
    totalRows: number;
    validCount: number;
    insertedCount: number;
    mergedCount: number;
    invalidCount: number;
    finalTotal: number;
  } | null = null;

  // Manage Columns toggle state (default 6 columns enabled)
  isManageColsOpen: boolean = false;
  columnMap: { [key: string]: { label: string; visible: boolean; isExtra?: boolean } } = {
    seq: { label: '#', visible: true },
    name: { label: 'Candidate Name', visible: true },
    email: { label: 'Email Address', visible: true },
    phone: { label: 'Phone Number', visible: true },
    location: { label: 'Location', visible: false },
    category: { label: 'Domain Category', visible: true },
    comp: { label: 'Compensation / Rate', visible: false },
    skills: { label: 'Skills Set', visible: false },
    verified: { label: 'Verification', visible: false },
    sources: { label: 'Data Sources', visible: false },
    actions: { label: 'Actions', visible: true }
  };

  // Standard column key set
  private standardKeys = new Set(['seq', 'name', 'email', 'phone', 'location', 'category', 'comp', 'skills', 'verified', 'sources', 'actions']);

  constructor(private candidateService: CandidateService) {}

  // ─── Toast helper ────────────────────────────────────────────────────────────
  // type: 'success' (green) | 'error' (red) | 'info' (blue)
  // duration: auto-dismiss delay in ms (default 4000, errors 6000)
  showToast(message: string, type: 'success' | 'error' | 'info' = 'success', duration = 4000): void {
    if (this.toastTimer) clearTimeout(this.toastTimer);
    this.toastMessage = message;
    this.toastType = type;
    this.toastTimer = setTimeout(() => {
      this.toastMessage = '';
      this.toastType = 'success';
    }, duration);
  }

  toggleManageColsDropdown(): void {
    this.isManageColsOpen = !this.isManageColsOpen;
  }

  toggleColumnVisibility(key: string): void {
    if (this.columnMap[key]) {
      this.columnMap[key].visible = !this.columnMap[key].visible;
    }
  }

  ngOnInit(): void {
    // Initial fetch of merged candidate database
    this.loadCandidates();
  }

  // Queries the backend API for candidate profiles and discovers extra dynamic columns
  loadCandidates(): void {
    this.isLoading = true;
    this.candidateService.getCandidates(this.searchTerm, this.selectedCity, this.selectedCategory).subscribe({
      next: (res: any) => {
        this.candidates = res.data || [];
        this.filteredCandidates = res.data || [];

        // Discover and register dynamic extra columns from backend
        const extraCols: string[] = res.extra_columns || [];
        
        // Also check in loaded candidate extra_fields
        this.candidates.forEach((cand) => {
          if (cand.extra_fields && typeof cand.extra_fields === 'object') {
            Object.keys(cand.extra_fields).forEach((k) => {
              if (!extraCols.includes(k)) {
                extraCols.push(k);
              }
            });
          }
        });

        // Add extra columns to columnMap if not already present
        extraCols.forEach((col) => {
          const key = 'extra_' + col.toLowerCase().replace(/\s+/g, '_');
          if (!this.columnMap[key]) {
            this.columnMap[key] = {
              label: col,
              visible: false, // Default hidden until checked in Manage Columns
              isExtra: true
            };
          }
        });

        this.isLoading = false;
        this.statsUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to load candidates:', err);
        this.isLoading = false;
      }
    });
  }

  // Trigger file input click for CSV upload
  triggerCsvFileSelect(fileInput: HTMLInputElement): void {
    fileInput.value = '';
    fileInput.click();
  }

  // Handle CSV file selection (supports single or multiple files)
  onCsvFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      const files = Array.from(target.files);
      this.uploadMultipleCsvFiles(files);
    }
  }

  // Uploads multiple CSV files sequentially to backend pipeline & displays summary modal card
  uploadMultipleCsvFiles(files: File[]): void {
    if (!files || files.length === 0) return;

    this.isUploadingCsv = true;
    this.csvSuccessMessage = '';
    this.csvErrorMessage = '';

    let totalValid = 0;
    let totalInvalid = 0;
    let totalInserted = 0;
    let totalMerged = 0;
    const totalFiles = files.length;

    const uploadNext = (index: number) => {
      if (index >= totalFiles) {
        this.isUploadingCsv = false;
        this.toastMessage = '';

        // Reload candidate list and emit stats update event so top cards refresh automatically
        this.loadCandidates();
        this.statsUpdated.emit();

        // Populate glassmorphism metrics summary modal card
        this.csvSummaryData = {
          totalFiles,
          totalRows: totalValid + totalInvalid,
          validCount: totalValid,
          insertedCount: totalInserted,
          mergedCount: totalMerged,
          invalidCount: totalInvalid,
          finalTotal: this.candidates.length
        };
        this.isCsvSummaryModalOpen = true;
        return;
      }

      const file = files[index];
      // Progress toast (blue / info)
      this.showToast(`⏳ Ingesting file ${index + 1} of ${totalFiles}: ${file.name}`, 'info', 60000);

      this.candidateService.uploadCandidatesCsv(file).subscribe({
        next: (res) => {
          totalValid += res.valid_count || 0;
          totalInvalid += res.invalid_count || 0;
          totalInserted += res.inserted_count || 0;
          totalMerged += res.updated_count || 0;
          uploadNext(index + 1);
        },
        error: (err) => {
          console.error(`CSV upload failed for ${file.name}:`, err);
          // Extract most helpful error detail from backend response
          const detail =
            err?.error?.detail ||
            err?.error?.message ||
            err?.message ||
            'Server error — check backend logs.';
          this.showToast(
            `❌ ${file.name}: ${detail}`,
            'error',
            8000
          );
          // Continue uploading remaining files even if this one failed
          uploadNext(index + 1);
        }
      });
    };

    uploadNext(0);
  }

  // Opens CSV Ingestion Summary modal card manually via Import Metrics button
  openCsvSummaryModal(): void {
    if (!this.csvSummaryData) {
      this.csvSummaryData = {
        totalFiles: 0,
        totalRows: this.candidates.length,
        validCount: this.candidates.length,
        insertedCount: this.candidates.length,
        mergedCount: 0,
        invalidCount: 0,
        finalTotal: this.candidates.length
      };
    }
    this.isCsvSummaryModalOpen = true;
  }

  // Closes CSV Ingestion Summary modal card
  closeCsvSummaryModal(): void {
    this.isCsvSummaryModalOpen = false;
  }

  // Downloads blank standard CSV template with candidate column headers
  downloadCsvTemplate(): void {
    const templateContent = 'Candidate Name,Email Address,Phone Number,Location,Skills Set,Current CTC (LPA)\n';

    const blob = new Blob([templateContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'Candidate_Import_Template.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    this.toastMessage = 'Blank CSV Template downloaded!';
    setTimeout(() => {
      this.toastMessage = '';
    }, 3000);
  }

  // Opens Log History modal — groups rejected rows by import session (2-min window)
  // Most recent session shown first
  openImportHistoryModal(): void {
    this.isHistoryModalOpen = true;
    this.isLoadingHistory = true;
    this.groupedRejectedLogs = [];
    this.candidateService.getRejectedLogs().subscribe({
      next: (res) => {
        this.csvAuditLogs = res.data || [];
        this.groupedRejectedLogs = this.groupRejectedLogs(this.csvAuditLogs);
        this.isLoadingHistory = false;
      },
      error: (err) => {
        console.error('Failed to load rejected import log history:', err);
        this.isLoadingHistory = false;
      }
    });
  }

  // Groups flat rejected log array into import sessions by time proximity (2-minute window)
  // Returns groups sorted most-recent-first
  groupRejectedLogs(logs: any[]): { sessionLabel: string; sessionTime: Date; sourceFiles: string[]; logs: any[]; expanded: boolean }[] {
    if (!logs || logs.length === 0) return [];

    // Sort DESC — most recent first
    const sorted = [...logs].sort((a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

    const groups: { sessionLabel: string; sessionTime: Date; sourceFiles: string[]; logs: any[]; expanded: boolean }[] = [];
    let currentLogs: any[] = [sorted[0]];
    let lastTime = new Date(sorted[0].created_at).getTime();

    for (let i = 1; i < sorted.length; i++) {
      const thisTime = new Date(sorted[i].created_at).getTime();
      // Within 2 minutes of the PREVIOUS log in this group = same session
      if (lastTime - thisTime <= 2 * 60 * 1000) {
        currentLogs.push(sorted[i]);
      } else {
        groups.push(this.buildSessionGroup(currentLogs, groups.length === 0));
        currentLogs = [sorted[i]];
      }
      lastTime = thisTime;
    }
    groups.push(this.buildSessionGroup(currentLogs, groups.length === 0));

    return groups;
  }

  // Builds a session group object from a flat array of logs belonging to the same upload batch
  buildSessionGroup(logs: any[], isFirst: boolean): { sessionLabel: string; sessionTime: Date; sourceFiles: string[]; logs: any[]; expanded: boolean } {
    const sessionTime = new Date(logs[0].created_at); // most recent in group
    const sourceFiles = [...new Set(logs.map(l => l.source_file))] as string[];
    const label = sessionTime.toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit', hour12: true
    });
    return { sessionLabel: label, sessionTime, sourceFiles, logs, expanded: isFirst };
  }

  // Toggle expand/collapse of a session group in Log History
  toggleGroupExpand(group: any): void {
    group.expanded = !group.expanded;
  }

  // Closes Log History modal
  closeImportHistoryModal(): void {
    this.isHistoryModalOpen = false;
  }

  // Downloads CSV file for a specific session group's rejected rows (with Rejection Reason column)
  downloadRejectedCsv(groupLogs?: any[]): void {
    const logsToProcess = groupLogs && groupLogs.length ? groupLogs : this.csvAuditLogs;

    if (!logsToProcess || logsToProcess.length === 0) {
      this.showToast('No rejected records to download.', 'error', 4000);
      return;
    }

    const headersSet = new Set<string>();
    const parsedRows: { data: Record<string, any>; reason: string; source: string; row: any }[] = [];

    logsToProcess.forEach((item) => {
      let rawObj: Record<string, any> = {};
      try {
        if (typeof item.raw_data === 'string') {
          rawObj = JSON.parse(item.raw_data);
        } else if (typeof item.raw_data === 'object' && item.raw_data !== null) {
          rawObj = item.raw_data;
        }
      } catch (e) {
        rawObj = { 'Raw Payload': String(item.raw_data) };
      }
      Object.keys(rawObj).forEach((k) => headersSet.add(k));
      let reasonStr = item.action_taken || 'Validation Failed';
      if (reasonStr.includes('Report:')) {
        reasonStr = reasonStr.split('Report:')[1].trim();
      }
      parsedRows.push({ data: rawObj, reason: reasonStr, source: item.source_file, row: item.row_index });
    });

    const headersList = ['Source File', 'Row #', ...Array.from(headersSet), 'Rejection Reason'];
    const csvLines: string[] = [headersList.map((h) => `"${h.replace(/"/g, '""')}"`).join(',')];

    parsedRows.forEach((rowObj) => {
      const lineVals = headersList.map((header) => {
        let val = '';
        if (header === 'Source File') val = rowObj.source;
        else if (header === 'Row #') val = String(rowObj.row || '');
        else if (header === 'Rejection Reason') val = rowObj.reason;
        else val = rowObj.data[header] !== undefined && rowObj.data[header] !== null ? String(rowObj.data[header]) : '';
        return `"${val.replace(/"/g, '""')}"`;
      });
      csvLines.push(lineVals.join(','));
    });

    // Use session timestamp in filename if downloading a specific group
    const tsLabel = logsToProcess[0]?.created_at
      ? new Date(logsToProcess[0].created_at).toISOString().slice(0, 16).replace('T', '_').replace(':', 'h')
      : new Date().toISOString().slice(0, 10);

    const blob = new Blob([csvLines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `Rejected_Rows_${tsLabel}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    this.showToast(`📥 Downloaded ${parsedRows.length} rejected row(s)!`, 'success', 4000);
  }

  // Returns list of extra column keys for table headers & cells
  getExtraColumnKeys(): { key: string; label: string }[] {
    const result: { key: string; label: string }[] = [];
    Object.keys(this.columnMap).forEach((k) => {
      if (!this.standardKeys.has(k) && this.columnMap[k]) {
        result.push({ key: k, label: this.columnMap[k].label });
      }
    });
    return result;
  }

  // Extract value of extra column from candidate record
  getExtraFieldValue(cand: Candidate, colLabel: string): string {
    if (!cand.extra_fields) return '--';
    const val = cand.extra_fields[colLabel];
    if (val !== undefined && val !== null && val !== '') {
      const lowerKey = colLabel.toLowerCase().trim();
      if (lowerKey === 'verified' || lowerKey === 'is_verified' || lowerKey === 'is_verified?' || lowerKey === 'verification') {
        const vStr = String(val).trim().toLowerCase();
        return ['y', 'yes', 'true', '1'].includes(vStr) ? 'Yes' : 'No';
      }
      return String(val);
    }
    return '--';
  }

  // Type-safe verification helper for template & export logic
  isCandidateVerified(cand: Candidate): boolean {
    if (!cand || cand.is_verified === undefined || cand.is_verified === null) return false;
    const val = String(cand.is_verified).trim().toLowerCase();
    return val === 'yes' || val === '1' || val === 'true' || val === 'y';
  }

  // Downloads CSV report of currently filtered candidates respecting Manage Columns visibility
  downloadReport(): void {
    if (!this.filteredCandidates || this.filteredCandidates.length === 0) {
      alert('No candidate data available to download.');
      return;
    }

    // Identify visible columns based on columnMap
    const visibleCols: { key: string; label: string; isExtra?: boolean }[] = [];
    
    // Check standard keys first in display order
    const orderedStandardKeys = [
      { key: 'seq', label: '#' },
      { key: 'name', label: 'Candidate Name' },
      { key: 'email', label: 'Email Address' },
      { key: 'phone', label: 'Phone Number' },
      { key: 'location', label: 'Location' },
      { key: 'category', label: 'Domain Category' },
      { key: 'comp', label: 'Compensation / Rate' },
      { key: 'skills', label: 'Skills Set' },
      { key: 'verified', label: 'Verification' },
      { key: 'sources', label: 'Data Sources' }
    ];

    orderedStandardKeys.forEach((item) => {
      if (this.columnMap[item.key] && this.columnMap[item.key].visible) {
        visibleCols.push(item);
      }
    });

    // Add visible extra columns
    this.getExtraColumnKeys().forEach((extra) => {
      if (this.columnMap[extra.key] && this.columnMap[extra.key].visible) {
        visibleCols.push({ key: extra.key, label: extra.label, isExtra: true });
      }
    });

    if (visibleCols.length === 0) {
      alert('Please select at least one visible column in Manage Columns to export.');
      return;
    }

    // Build CSV Headers
    const headers = visibleCols.map((c) => `"${c.label.replace(/"/g, '""')}"`);
    const csvRows: string[] = [headers.join(',')];

    // Build CSV Rows
    this.filteredCandidates.forEach((cand, idx) => {
      const rowValues = visibleCols.map((col) => {
        let val = '';
        if (col.key === 'seq') {
          val = `#${idx + 1}`;
        } else if (col.key === 'name') {
          val = cand.full_name || '';
        } else if (col.key === 'email') {
          val = cand.email || '--';
        } else if (col.key === 'phone') {
          val = cand.phone || '--';
        } else if (col.key === 'location') {
          val = cand.city || 'Unknown';
        } else if (col.key === 'category') {
          val = cand.skill_category || '';
        } else if (col.key === 'comp') {
          if (cand.current_ctc_lpa) val = `${cand.current_ctc_lpa} LPA`;
          else if (cand.rate_hourly_inr) val = `₹${cand.rate_hourly_inr}/hr`;
          else if (cand.rate_monthly_inr) val = `₹${cand.rate_monthly_inr}/mo`;
          else val = '-';
        } else if (col.key === 'skills') {
          val = cand.skills || '';
        } else if (col.key === 'verified') {
          val = this.isCandidateVerified(cand) ? `Verified (${cand.projects_completed || 0} projects)` : 'Unverified';
        } else if (col.key === 'sources') {
          val = cand.data_sources || '';
        } else if (col.isExtra) {
          val = this.getExtraFieldValue(cand, col.label);
        }

        // Escape double quotes and enclose in quotes
        return `"${val.toString().replace(/"/g, '""')}"`;
      });

      csvRows.push(rowValues.join(','));
    });

    // Create Blob and trigger browser download
    const csvString = csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `Candidate_Directory_Report_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    this.toastMessage = `📥 Report downloaded successfully (${this.filteredCandidates.length} rows, ${visibleCols.length} columns)!`;
    setTimeout(() => {
      this.toastMessage = '';
    }, 4000);
  }

  // Re-executes query on filter change
  onFilterChange(): void {
    this.loadCandidates();
  }

  // Opens edit candidate modal
  openEditModal(candidate: Candidate): void {
    this.editingCandidate = candidate;
    this.editForm = {
      full_name: candidate.full_name,
      email: candidate.email,
      phone: candidate.phone,
      city: candidate.city,
      skills: candidate.skills,
      status: 'Active',
      experience_years: candidate.experience_years,
      current_ctc_lpa: candidate.current_ctc_lpa
    };
    this.cardErrorMessage = '';
  }

  // Closes edit modal
  closeEditModal(): void {
    this.editingCandidate = null;
    this.editForm = {};
    this.cardErrorMessage = '';
  }

  // Saves edited candidate, triggers backend pipeline re-run cleaning
  saveCandidateEdit(): void {
    if (!this.editingCandidate) return;
    this.isSaving = true;
    this.cardErrorMessage = '';

    const candId = this.editingCandidate.id;

    this.candidateService.updateCandidate(candId, this.editForm).subscribe({
      next: (res) => {
        this.isSaving = false;
        this.closeEditModal();
        this.loadCandidates();
        this.statsUpdated.emit();
        // Show top-right corner success toast
        this.toastMessage = `✅ Profile updated & cleaned successfully through pipeline!`;
        setTimeout(() => {
          this.toastMessage = '';
        }, 4000);
      },
      error: (err) => {
        console.error('Failed to update candidate:', err);
        this.isSaving = false;
        // Display exact error/duplicate conflict inside the modal card
        this.cardErrorMessage = err.error?.detail || err.message || 'An error occurred while updating the candidate.';
      }
    });
  }

  // Splits comma-separated data sources string into distinct array of source tags
  getSourceTags(sourcesStr: string): string[] {
    if (!sourcesStr) return [];
    return sourcesStr.split(',').map((s) => s.trim()).filter((s) => s.length > 0);
  }

  // Splits comma-separated skills string into distinct array of skill pills
  getSkillsList(skillsStr?: string): string[] {
    if (!skillsStr) return [];
    return skillsStr.split(',').map((s) => s.trim()).filter((s) => s.length > 0);
  }
}
