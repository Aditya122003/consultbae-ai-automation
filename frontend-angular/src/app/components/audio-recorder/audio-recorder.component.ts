// Audio recorder and upload studio component
// Manages real-time microphone recording, Web Audio API waveform visualization, file uploads, and acoustic metrics

import { Component, EventEmitter, Output, ViewChild, ElementRef, OnDestroy, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AudioService } from '../../services/audio.service';
import { CandidateService } from '../../services/candidate.service';
import { AudioProperties, Candidate } from '../../models/types';

@Component({
  selector: 'app-audio-recorder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audio-recorder.component.html',
  styleUrls: ['./audio-recorder.component.css']
})
export class AudioRecorderComponent implements OnInit, OnDestroy {
  // Event emitted whenever a new audio submission successfully completes
  @Output() submissionCreated = new EventEmitter<void>();

  // Canvas reference used for real-time audio frequency waveform visualization
  @ViewChild('waveformCanvas', { static: false }) canvasRef!: ElementRef<HTMLCanvasElement>;

  // Form input fields
  workerName: string = '';
  workerPhone: string = '';
  phoneTouched: boolean = false;
  nameTouched: boolean = false;

  // Recording lifecycle state
  isRecording: boolean = false;
  isPaused: boolean = false;
  recordingSeconds: number = 0;
  private timerInterval: any = null;

  // Web Audio and MediaRecorder instances
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  private animationFrameId: number | null = null;
  private currentStream: MediaStream | null = null;

  // Selected or recorded audio blob
  recordedAudioBlob: Blob | null = null;
  audioPreviewUrl: string | null = null;
  selectedFile: File | null = null;

  // UI state and results feedback
  isSubmitting: boolean = false;
  submissionSuccess: boolean = false;
  lastProperties: AudioProperties | null = null;
  lastWorkerName: string = '';
  lastWorkerPhone: string = '';
  errorMessage: string | null = null;

  // Quick candidate auto-complete suggestions
  candidateSuggestions: Candidate[] = [];

  constructor(
    private audioService: AudioService,
    private candidateService: CandidateService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    // Preload candidate directory for convenient autofill suggestions
    this.candidateService.getCandidates().subscribe({
      next: (res) => {
        this.candidateSuggestions = res.data.slice(0, 10);
      },
      error: (err) => console.error('Failed to load candidate suggestions:', err)
    });
  }

  ngOnDestroy(): void {
    // Ensure recording streams and audio contexts are cleaned up on component destroy
    this.stopRecordingStream();
  }

  // Checks if worker name meets minimum length requirements
  get isNameValid(): boolean {
    return this.workerName.trim().length >= 2;
  }

  // Checks if phone number is exactly 10 digits
  get isPhoneValid(): boolean {
    const digitsOnly = this.workerPhone.replace(/\D/g, '');
    return digitsOnly.length === 10;
  }

  // Returns true only when both name and valid 10-digit phone are provided
  get isFormValid(): boolean {
    return this.isNameValid && this.isPhoneValid;
  }

  // Populates form input fields when a user clicks on an autofill candidate pill
  selectCandidate(c: Candidate): void {
    this.workerName = c.full_name;
    this.workerPhone = c.phone || '';
    this.nameTouched = true;
    this.phoneTouched = true;
    this.errorMessage = null;
  }

  // Cleanses phone input to allow only numeric digits up to 10 chars
  onPhoneInput(): void {
    this.phoneTouched = true;
    this.errorMessage = null;
    const digits = this.workerPhone.replace(/\D/g, '');
    this.workerPhone = digits.slice(0, 10);
  }

  onNameInput(): void {
    this.nameTouched = true;
    this.errorMessage = null;
  }

  // Initiates browser microphone stream and configures live Web Audio API analyzer
  async startRecording(): Promise<void> {
    this.nameTouched = true;
    this.phoneTouched = true;

    if (!this.isFormValid) {
      if (!this.isNameValid) {
        this.errorMessage = 'Please enter worker name (at least 2 characters).';
      } else if (!this.isPhoneValid) {
        this.errorMessage = 'Please enter a valid 10-digit phone number (e.g. 9000000254).';
      }
      return;
    }

    this.errorMessage = null;
    this.audioChunks = [];
    this.submissionSuccess = false;
    this.lastProperties = null;
    this.recordedAudioBlob = null;
    this.audioPreviewUrl = null;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.currentStream = stream;
      this.isRecording = true;
      this.isPaused = false;
      this.recordingSeconds = 0;
      this.cdr.detectChanges();

      // Start elapsed recording duration timer
      this.timerInterval = setInterval(() => {
        if (!this.isPaused) {
          this.recordingSeconds++;
          this.cdr.detectChanges();
        }
      }, 1000);

      // Initialize Web Audio API Analyser for live oscilloscope visualization
      try {
        this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
        const source = this.audioContext.createMediaStreamSource(stream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);

        // Schedule canvas waveform rendering loop once canvas element is mounted
        setTimeout(() => {
          this.drawWaveform();
        }, 60);
      } catch (audioCtxErr) {
        console.warn('Web Audio Analyser initialization notice:', audioCtxErr);
      }

      // Determine best supported audio MIME container
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/ogg;codecs=opus')) {
        mimeType = 'audio/ogg;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      }

      // Configure MediaRecorder for audio capture
      this.mediaRecorder = new MediaRecorder(stream, { mimeType });
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const finalBlob = new Blob(this.audioChunks, { type: mimeType });
        this.recordedAudioBlob = finalBlob;
        this.audioPreviewUrl = URL.createObjectURL(finalBlob);

        // Clean up stream tracks and audio context
        if (this.currentStream) {
          this.currentStream.getTracks().forEach((track) => track.stop());
          this.currentStream = null;
        }
        this.stopAudioContext();
        this.cdr.detectChanges();

        // Auto-submit immediately after recording stops so user doesn't have to click twice
        this.submitAudio();
      };

      this.mediaRecorder.start(100);
    } catch (err: any) {
      this.isRecording = false;
      this.errorMessage = `Microphone access error: ${err.message || 'Permission denied. Please allow microphone in browser.'}`;
      this.cdr.detectChanges();
    }
  }

  // Pauses or resumes the ongoing audio recording
  togglePause(): void {
    if (!this.mediaRecorder) return;
    if (this.isPaused) {
      this.mediaRecorder.resume();
      this.isPaused = false;
    } else {
      this.mediaRecorder.pause();
      this.isPaused = true;
    }
    this.cdr.detectChanges();
  }

  // Stops audio recording and triggers auto-submission
  stopRecording(): void {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
    }

    this.isRecording = false;
    this.isPaused = false;
    this.cdr.detectChanges();
  }

  // Discards current recording and resets to fresh state
  resetRecording(): void {
    this.recordedAudioBlob = null;
    this.audioPreviewUrl = null;
    this.selectedFile = null;
    this.recordingSeconds = 0;
    this.submissionSuccess = false;
    this.lastProperties = null;
    this.errorMessage = null;
    this.isSubmitting = false;
    this.cdr.detectChanges();
  }

  // Handles manual audio file upload via file picker
  onFileSelected(event: any): void {
    if (!this.isFormValid) {
      this.nameTouched = true;
      this.phoneTouched = true;
      this.errorMessage = 'Please enter Worker Name and a valid 10-digit Phone Number before uploading audio.';
      return;
    }
    const file: File = event.target.files[0];
    if (file) {
      this.selectedFile = file;
      this.recordedAudioBlob = file;
      this.audioPreviewUrl = URL.createObjectURL(file);
      this.submissionSuccess = false;
      this.lastProperties = null;
      this.errorMessage = null;
      this.cdr.detectChanges();
      // Auto-submit uploaded file
      this.submitAudio();
    }
  }

  // Handles drag-and-drop audio file upload
  onFileDropped(event: DragEvent): void {
    event.preventDefault();
    if (!this.isFormValid) {
      this.nameTouched = true;
      this.phoneTouched = true;
      this.errorMessage = 'Please enter Worker Name and a valid 10-digit Phone Number before uploading audio.';
      return;
    }
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      const file = event.dataTransfer.files[0];
      this.selectedFile = file;
      this.recordedAudioBlob = file;
      this.audioPreviewUrl = URL.createObjectURL(file);
      this.submissionSuccess = false;
      this.lastProperties = null;
      this.errorMessage = null;
      this.cdr.detectChanges();
      // Auto-submit dropped file
      this.submitAudio();
    }
  }

  // Submits the recorded blob or audio file to the backend extraction endpoint
  submitAudio(): void {
    if (!this.isNameValid) {
      this.errorMessage = 'Please enter worker name';
      return;
    }
    if (!this.isPhoneValid) {
      this.errorMessage = 'Please enter a valid 10-digit phone number (e.g. 9000000254)';
      return;
    }
    if (!this.recordedAudioBlob) {
      this.errorMessage = 'Please record audio or upload an audio file before submitting';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = null;
    this.lastWorkerName = this.workerName.trim();
    this.lastWorkerPhone = this.workerPhone.trim();
    this.cdr.detectChanges();

    const fileName = this.selectedFile ? this.selectedFile.name : 'browser_recording.webm';

    this.audioService.submitAudio(this.lastWorkerName, this.lastWorkerPhone, this.recordedAudioBlob, fileName).subscribe({
      next: (res) => {
        this.isSubmitting = false;
        this.submissionSuccess = true;
        this.lastProperties = res.properties;
        this.submissionCreated.emit();
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.isSubmitting = false;
        this.errorMessage = err.error?.detail || 'Failed to process audio recording. Please try again.';
        this.cdr.detectChanges();
      }
    });
  }

  // Renders animated sine waveform on HTML5 canvas during live microphone recording
  private drawWaveform(): void {
    if (!this.analyser || !this.canvasRef) return;
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const bufferLength = this.analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const render = () => {
      if (!this.isRecording) return;
      this.animationFrameId = requestAnimationFrame(render);
      this.analyser!.getByteTimeDomainData(dataArray);

      ctx.fillStyle = '#0d1322';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.lineWidth = 2.5;
      ctx.strokeStyle = '#06b6d4';
      ctx.beginPath();

      const sliceWidth = (canvas.width * 1.0) / bufferLength;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = (v * canvas.height) / 2;
        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
        x += sliceWidth;
      }

      ctx.lineTo(canvas.width, canvas.height / 2);
      ctx.stroke();
    };

    render();
  }

  // Stops audio context and closes microphone stream tracks
  private stopAudioContext(): void {
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close();
      } catch (e) {}
      this.audioContext = null;
    }
  }

  // Utility to cleanly format recording seconds into MM:SS string
  formatTime(seconds: number): string {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  private stopRecordingStream(): void {
    this.stopRecording();
    this.stopAudioContext();
  }
}
