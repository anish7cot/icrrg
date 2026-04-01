import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TitleCasePipe } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatNativeDateModule } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatListModule } from '@angular/material/list';
import { MatChipsModule } from '@angular/material/chips';
import { ReportService, ReportListItem } from '../../services/report.service';
import { ScanService } from '../../services/scan.service';

@Component({
  selector: 'app-reports',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TitleCasePipe,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatDatepickerModule,
    MatNativeDateModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatListModule,
    MatChipsModule,
  ],
  templateUrl: './reports.component.html',
  styleUrl: './reports.component.scss',
})
export class ReportsComponent implements OnInit {
  repository = '';
  repositories: string[] = [];
  startDate: Date | null = null;
  endDate: Date | null = null;
  audienceType = 'developer';
  loading = false;
  error = '';
  recentReports: ReportListItem[] = [];
  reportsLoading = true;

  constructor(
    private reportService: ReportService,
    private scanService: ScanService,
    private router: Router,
  ) {
    const today = new Date();
    this.endDate = today;
    this.startDate = new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000);
  }

  ngOnInit(): void {
    this.loadRepositories();
    this.loadRecentReports();
  }

  loadRepositories(): void {
    this.scanService.listRepositories().subscribe({
      next: (repos) => {
        this.repositories = repos;
        if (repos.length === 1) this.repository = repos[0];
      },
      error: () => {},
    });
  }

  loadRecentReports(): void {
    this.reportsLoading = true;
    this.reportService.listReports(10).subscribe({
      next: (reports) => {
        this.recentReports = reports;
        this.reportsLoading = false;
      },
      error: () => {
        this.reportsLoading = false;
      },
    });
  }

  onSubmit(): void {
    if (!this.repository || !this.startDate || !this.endDate) return;

    this.loading = true;
    this.error = '';

    const formatDate = (d: Date): string => d.toISOString().split('T')[0];

    this.reportService
      .createReport({
        repository: this.repository,
        date_range_start: formatDate(this.startDate),
        date_range_end: formatDate(this.endDate),
        audience_type: this.audienceType,
      })
      .subscribe({
        next: (report) => {
          this.loading = false;
          this.router.navigate(['/reports', report.id]);
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.detail || 'Failed to create report. Please try again.';
        },
      });
  }

  viewReport(id: string): void {
    this.router.navigate(['/reports', id]);
  }
}
