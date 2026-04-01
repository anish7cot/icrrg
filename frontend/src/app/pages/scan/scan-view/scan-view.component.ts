import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ScanService, ScanResponse } from '../../../services/scan.service';
import { ScanDetailComponent } from '../scan-detail/scan-detail.component';

@Component({
  selector: 'app-scan-view',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatIconModule,
    ScanDetailComponent,
  ],
  templateUrl: './scan-view.component.html',
  styleUrls: ['./scan-view.component.scss'],
})
export class ScanViewComponent implements OnInit, OnDestroy {
  scan: ScanResponse | null = null;
  loading = false;
  error = '';
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private scanId = '';
  private pollCount = 0;
  private readonly MAX_POLLS = 24; // 24 * 5s = 2 minutes

  constructor(
    private route: ActivatedRoute,
    private scanService: ScanService,
  ) {}

  ngOnInit(): void {
    this.scanId = this.route.snapshot.paramMap.get('id') || '';
    if (!this.scanId) {
      this.error = 'No scan ID provided';
      return;
    }
    this.loading = true;
    this.loadScan();
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  refresh(): void {
    this.loadScan();
  }

  private loadScan(): void {
    this.scanService.getScan(this.scanId).subscribe({
      next: (result) => {
        this.scan = result;
        this.loading = false;
        if (result.status === 'reviewing') {
          this.startPolling();
        } else {
          this.stopPolling();
        }
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail || 'Failed to load scan';
      },
    });
  }

  private startPolling(): void {
    if (this.pollTimer) return;
    this.pollCount = 0;
    this.pollTimer = setInterval(() => {
      this.pollCount++;
      if (this.pollCount > this.MAX_POLLS) {
        this.stopPolling();
        if (this.scan) {
          this.scan = { ...this.scan, status: 'completed' };
        }
        return;
      }
      this.loadScan();
    }, 5000);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }
}
