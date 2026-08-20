// Automation simulator component
// Executes low-code webhook triggering, MySQL duplicate detection, LLM skill auto-tagging, and REAL email dispatch

import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { CandidateService } from '../../services/candidate.service';

@Component({
  selector: 'app-automation-simulator',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './automation-simulator.component.html',
  styleUrls: ['./automation-simulator.component.css']
})
export class AutomationSimulatorComponent {
  // Output event to trigger top bar KPI stats refresh in app.component
  @Output() statsUpdated = new EventEmitter<void>();

  // Test simulation form inputs
  testName: string = '';
  testPhone: string = '';
  testEmail: string = '';
  testSkills: string = '';
  testCity: string = '';
  recipientEmail: string = 'mycoding2025@gmail.com';

  // Execution state & outputs
  isExecuting: boolean = false;
  flowResult: any = null;
  executedPayload: any = null;
  errorMessage: string | null = null;

  // Field-level validation touched state
  nameTouched: boolean = false;
  phoneTouched: boolean = false;
  emailTouched: boolean = false;

  // Audit Logs table & Manage Columns state (default 6 columns enabled)
  auditLogs: any[] = [];
  isLoadingAudit: boolean = false;
  isManageColsOpen: boolean = false;
  columnMap: { [key: string]: { label: string; visible: boolean } } = {
    seq: { label: '#', visible: true },
    source: { label: 'Source File', visible: true },
    issue: { label: 'Issue / Anomaly Type', visible: true },
    raw: { label: 'Raw Data', visible: true },
    action: { label: 'Action Taken', visible: true },
    row: { label: 'Row Index', visible: false },
    time: { label: 'Timestamp', visible: true }
  };

  constructor(private candidateService: CandidateService) {}

  ngOnInit(): void {
    this.loadAuditLogs();
  }

  loadAuditLogs(): void {
    this.isLoadingAudit = true;
    this.candidateService.getAuditLogs().subscribe({
      next: (res) => {
        this.auditLogs = res.data;
        this.isLoadingAudit = false;
      },
      error: (err) => {
        console.error('Audit log fetch error:', err);
        this.isLoadingAudit = false;
      }
    });
  }

  toggleManageColsDropdown(): void {
    this.isManageColsOpen = !this.isManageColsOpen;
  }

  toggleColumnVisibility(key: string): void {
    if (this.columnMap[key]) {
      this.columnMap[key].visible = !this.columnMap[key].visible;
    }
  }

  // ── Validation Getters ──────────────────────────────────────────────────────
  get isNameValid(): boolean {
    return this.testName.trim().length >= 2;
  }

  get isPhoneValid(): boolean {
    const digits = this.testPhone.replace(/\D/g, '');
    return digits.length === 10;
  }

  // Email: valid only if filled and format correct; empty is allowed
  get isEmailValid(): boolean {
    if (!this.testEmail.trim()) return true; // optional
    const emailRegex = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(this.testEmail.trim());
  }

  // Form valid when mandatory fields (name + phone) are filled and email format is correct if provided
  get isFormValid(): boolean {
    return this.isNameValid && this.isPhoneValid && this.isEmailValid;
  }

  // ── Validation: restrict phone input to digits only ─────────────────────────
  onNameInput(): void {
    this.nameTouched = true;
  }

  onPhoneInput(): void {
    this.phoneTouched = true;
    this.testPhone = this.testPhone.replace(/\D/g, '').slice(0, 10);
  }

  onEmailInput(): void {
    this.emailTouched = true;
  }

  // Pre-fills form with a known duplicate record for instant demonstration
  loadDuplicateSample(): void {
    this.testName = 'Tanvi Gupta';
    this.testPhone = '9000000254';
    this.testEmail = 'tanvi.gupta31@example.com';
    this.testSkills = 'n8n, LangChain, REST APIs, MongoDB, SQL';
    this.testCity = 'Bengaluru';
    this.flowResult = null;
    this.errorMessage = null;
    this.nameTouched = false;
    this.phoneTouched = false;
    this.emailTouched = false;
  }

  // Pre-fills form with a brand new candidate for instant demonstration
  loadNewSample(): void {
    const randomSuffix = Math.floor(1000 + Math.random() * 9000);
    this.testName = 'Aarav Singhal';
    this.testPhone = `987654${randomSuffix}`;
    this.testEmail = `aarav.singhal${randomSuffix}@example.com`;
    this.testSkills = 'n8n, Zapier, LangChain, Python, OpenAI, Vector DBs';
    this.testCity = 'Gurugram';
    this.flowResult = null;
    this.errorMessage = null;
    this.nameTouched = false;
    this.phoneTouched = false;
    this.emailTouched = false;
  }

  // Executes real backend pipeline and dispatches real Gmail alert
  triggerFlow(): void {
    // Mark all mandatory fields as touched to show validation errors
    this.nameTouched = true;
    this.phoneTouched = true;
    if (this.testEmail.trim()) this.emailTouched = true;

    if (!this.isFormValid) {
      if (!this.isNameValid) {
        this.errorMessage = 'Full Name is required (minimum 2 characters).';
      } else if (!this.isPhoneValid) {
        this.errorMessage = 'Please enter a valid 10-digit phone number.';
      } else if (!this.isEmailValid) {
        this.errorMessage = 'Email format is invalid (e.g. user@example.com).';
      }
      return;
    }

    this.isExecuting = true;
    this.flowResult = null;
    this.errorMessage = null;

    const payload = {
      full_name: this.testName,
      phone: this.testPhone,
      email: this.testEmail,
      skills: this.testSkills,
      city: this.testCity,
      recipient_email: this.recipientEmail
    };
    this.executedPayload = payload;

    this.candidateService.triggerAutomation(payload).subscribe({
      next: (res) => {
        this.flowResult = res;
        this.isExecuting = false;
        this.loadAuditLogs();
        this.statsUpdated.emit();
      },
      error: (err) => {
        console.error('Automation error:', err);
        this.errorMessage = err?.error?.detail || 'Failed to execute automation flow';
        this.isExecuting = false;
      }
    });
  }
}
