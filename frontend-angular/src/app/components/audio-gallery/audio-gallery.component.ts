// Audio submissions gallery component
// Displays historical audio recordings, embedded interactive players, and acoustic metadata chips

import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AudioService } from '../../services/audio.service';
import { AudioSubmission } from '../../models/types';

@Component({
  selector: 'app-audio-gallery',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './audio-gallery.component.html',
  styleUrls: ['./audio-gallery.component.css']
})
export class AudioGalleryComponent implements OnInit {
  // Output event to trigger top bar KPI stats refresh in app.component
  @Output() statsUpdated = new EventEmitter<void>();

  // Master list of retrieved audio submissions
  submissions: AudioSubmission[] = [];
  filteredSubmissions: AudioSubmission[] = [];

  // Filter state
  searchTerm: string = '';
  selectedQuality: string = 'ALL';
  isLoading: boolean = false;

  // Active audio player state
  currentPlayingId: number | null = null;
  playbackSpeed: number = 1.0;

  // Manage Columns toggle state (default 6 columns enabled)
  isManageColsOpen: boolean = false;
  columnMap: { [key: string]: { label: string; visible: boolean } } = {
    seq: { label: '#', visible: true },
    name: { label: 'Candidate Name', visible: true },
    phone: { label: 'Phone Number', visible: true },
    city: { label: 'City', visible: false },
    player: { label: 'Audio Playback', visible: true },
    quality: { label: 'Quality & SNR', visible: true },
    acoustic: { label: 'Acoustic Parameters', visible: false },
    date: { label: 'Recorded Date & Time', visible: true }
  };

  constructor(private audioService: AudioService) { }

  toggleManageColsDropdown(): void {
    this.isManageColsOpen = !this.isManageColsOpen;
  }

  toggleColumnVisibility(key: string): void {
    if (this.columnMap[key]) {
      this.columnMap[key].visible = !this.columnMap[key].visible;
    }
  }

  ngOnInit(): void {
    // Initial fetch of historical recordings on component load
    this.loadSubmissions();
  }

  // Fetches latest audio submissions from the backend MySQL database
  loadSubmissions(): void {
    this.isLoading = true;
    this.audioService.getSubmissions().subscribe({
      next: (res) => {
        this.submissions = res.data;
        this.applyFilter();
        this.isLoading = false;
        this.statsUpdated.emit();
      },
      error: (err) => {
        console.error('Failed to load audio submissions:', err);
        this.isLoading = false;
      }
    });
  }

  // Filters audio submissions by worker name, phone number, and quality score tag
  applyFilter(): void {
    const term = this.searchTerm.trim().toLowerCase();
    this.filteredSubmissions = this.submissions.filter((sub) => {
      const matchSearch =
        !term ||
        sub.worker_name.toLowerCase().includes(term) ||
        sub.worker_phone.includes(term) ||
        (sub.city && sub.city.toLowerCase().includes(term));

      const matchQuality =
        this.selectedQuality === 'ALL' ||
        sub.quality_label.toLowerCase().includes(this.selectedQuality.toLowerCase());

      return matchSearch && matchQuality;
    });
  }

  // Resolves static audio streaming URL for in-browser playback
  getAudioUrl(path: string): string {
    if (path.startsWith('http')) return path;
    return `http://localhost:8000${path}`;
  }

  // Changes playback rate speed on the native audio element
  changeSpeed(audioElement: HTMLAudioElement, speed: number): void {
    this.playbackSpeed = speed;
    audioElement.playbackRate = speed;
  }

  // Formats MySQL timestamp into human-readable format (e.g. 21 Aug 2026, 1:00 PM)
  formatDate(dateStr: string | undefined): string {
    if (!dateStr) return '-';
    try {
      const d = new Date(dateStr.replace(' ', 'T'));
      if (isNaN(d.getTime())) return dateStr;

      const day = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
      return `${day}, ${time}`;
    } catch {
      return dateStr;
    }
  }
}
