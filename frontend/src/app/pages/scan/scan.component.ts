import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { ScanService, ScanResponse } from '../../services/scan.service';
import { ScanDetailComponent } from './scan-detail/scan-detail.component';

@Component({
  selector: 'app-scan',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatCardModule,
    MatIconModule,
    ScanDetailComponent,
  ],
  templateUrl: './scan.component.html',
  styleUrls: ['./scan.component.scss'],
})
export class ScanComponent {
  diffText = '';
  repository = '';
  loading = false;
  scanResult: ScanResponse | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private pollCount = 0;
  private readonly MAX_POLLS = 24; // 24 * 5s = 2 minutes

  constructor(
    private scanService: ScanService,
    private snackBar: MatSnackBar,
    private router: Router,
  ) {}

  submitScan(): void {
    if (!this.diffText.trim()) return;

    this.loading = true;
    this.scanResult = null;
    this.stopPolling();

    this.scanService
      .submitScan({
        diff_text: this.diffText,
        repository: this.repository || 'manual-paste',
      })
      .subscribe({
        next: (result) => {
          this.scanResult = result;
          this.loading = false;
          const msg = result.status === 'reviewing'
            ? `Detection done — ${result.findings.length} finding(s). Code review in progress...`
            : `Scan complete — ${result.findings.length} finding(s)`;
          this.snackBar.open(msg, 'OK', { duration: 4000 });
          if (result.status === 'reviewing') {
            this.startPolling(result.id);
          }
        },
        error: (err) => {
          this.loading = false;
          const message = err.error?.detail || err.message || 'Scan failed';
          this.snackBar.open(`Error: ${message}`, 'Dismiss', {
            duration: 6000,
          });
        },
      });
  }

  private startPolling(scanId: string): void {
    this.pollCount = 0;
    this.pollTimer = setInterval(() => {
      this.pollCount++;
      if (this.pollCount > this.MAX_POLLS) {
        this.stopPolling();
        if (this.scanResult) {
          this.scanResult = { ...this.scanResult, status: 'completed' };
        }
        this.snackBar.open('Code review timed out — showing detection results', 'OK', { duration: 4000 });
        return;
      }
      this.scanService.getScan(scanId).subscribe({
        next: (result) => {
          this.scanResult = result;
          if (result.status === 'completed') {
            this.stopPolling();
            this.snackBar.open(
              `Code review complete — ${result.findings.length} total finding(s)`,
              'OK',
              { duration: 4000 },
            );
          }
        },
      });
    }, 5000);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }
}
