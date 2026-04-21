import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule, DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatBadgeModule } from '@angular/material/badge';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { ScanService, ScanSummary } from '../../services/scan.service';
import { StatsService, DashboardStats, DailyTrend } from '../../services/stats.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    DatePipe,
    DecimalPipe,
    MatCardModule,
    MatListModule,
    MatIconModule,
    MatChipsModule,
    MatBadgeModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDividerModule,
    MatSelectModule,
    MatFormFieldModule,
    BaseChartDirective,
  ],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent implements OnInit, OnDestroy {
  scans: ScanSummary[] = [];
  stats: DashboardStats | null = null;
  loading = true;
  statsLoading = true;
  trendsReady = false;
  error: string | null = null;

  // Project filter
  repositories: string[] = [];
  selectedRepo = '';  // empty string = all projects

  // ── Line chart: Issues Over Time ──
  lineChartData: ChartConfiguration<'line'>['data'] = { labels: [], datasets: [] };
  lineChartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
    },
    scales: {
      x: { grid: { display: false } },
      y: { beginAtZero: true, ticks: { precision: 0 } },
    },
  };

  // ── Donut chart: Severity Distribution ──
  donutChartData: ChartConfiguration<'doughnut'>['data'] = { labels: [], datasets: [] };
  donutChartOptions: ChartConfiguration<'doughnut'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { position: 'bottom', labels: { usePointStyle: true, padding: 16 } },
    },
    cutout: '60%',
  };

  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private readonly POLL_INTERVAL = 5000;

  constructor(
    private scanService: ScanService,
    private statsService: StatsService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.scanService.listRepositories().subscribe({
      next: (repos) => {
        this.repositories = repos;
        // Auto-select when there's only one project
        if (repos.length === 1) {
          this.selectedRepo = repos[0];
          this.onRepoChange();
        }
      },
      error: () => {},
    });
    this.loadStats();
    this.loadScans();
    this.loadTrends();
    this.pollTimer = setInterval(() => {
      this.loadScans();
      this.loadStats();
    }, this.POLL_INTERVAL);
  }

  onRepoChange(): void {
    this.statsLoading = true;
    this.loading = true;
    this.trendsReady = false;
    this.loadStats();
    this.loadScans();
    this.loadTrends();
    // Refresh repo list in case new repos appeared
    this.scanService.listRepositories().subscribe({
      next: (repos) => this.repositories = repos,
      error: () => {},
    });
  }

  ngOnDestroy(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  openScan(id: string): void {
    this.router.navigate(['/scan', id]);
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'completed': return 'check_circle';
      case 'reviewing': return 'hourglass_top';
      default: return 'pending';
    }
  }

  riskClass(score: number | null): string {
    if (score === null || score === 0) return 'risk-clean';
    if (score >= 7) return 'risk-critical';
    if (score >= 4) return 'risk-medium';
    return 'risk-low';
  }

  riskLabel(score: number | null): string {
    if (score === null || score === 0) return 'Clean';
    if (score >= 7) return 'Critical';
    if (score >= 4) return 'Medium';
    return 'Low';
  }

  get severityTotal(): number {
    if (!this.stats) return 0;
    const s = this.stats.severity;
    return s.critical + s.high + s.medium + s.low;
  }

  severityPercent(count: number): number {
    const total = this.severityTotal;
    return total > 0 ? (count / total) * 100 : 0;
  }

  friendlyType(raw: string): string {
    const label = raw.includes(':') ? raw.split(':')[1] : raw;
    return label.replace(/[_-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  trackByScanId(_index: number, scan: ScanSummary): string {
    return scan.id;
  }

  private loadStats(): void {
    const repo = this.selectedRepo || undefined;
    this.statsService.getStats(repo).subscribe({
      next: (stats) => {
        this.stats = stats;
        this.statsLoading = false;
        this.buildDonutChart(stats);
      },
      error: () => {
        this.statsLoading = false;
      },
    });
  }

  private loadScans(): void {
    const repo = this.selectedRepo || undefined;
    this.scanService.listScans(10, repo).subscribe({
      next: (scans) => {
        this.scans = scans;
        this.loading = false;
        this.error = null;
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load scans';
      },
    });
  }

  private loadTrends(): void {
    const repo = this.selectedRepo || undefined;
    this.statsService.getTrends(30, repo).subscribe({
      next: (trends) => this.buildLineChart(trends),
      error: () => {},
    });
  }

  private buildLineChart(trends: DailyTrend[]): void {
    const labels = trends.map(t => {
      const d = new Date(t.date);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    this.lineChartData = {
      labels,
      datasets: [
        {
          label: 'Critical',
          data: trends.map(t => t.critical),
          borderColor: '#c62828',
          backgroundColor: 'rgba(198,40,40,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 2,
        },
        {
          label: 'High',
          data: trends.map(t => t.high),
          borderColor: '#d84315',
          backgroundColor: 'rgba(216,67,21,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 2,
        },
        {
          label: 'Medium',
          data: trends.map(t => t.medium),
          borderColor: '#ef6c00',
          backgroundColor: 'rgba(239,108,0,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 2,
        },
        {
          label: 'Low',
          data: trends.map(t => t.low),
          borderColor: '#2e7d32',
          backgroundColor: 'rgba(46,125,50,0.08)',
          fill: true,
          tension: 0.35,
          pointRadius: 2,
        },
      ],
    };
    this.trendsReady = true;
  }

  private buildDonutChart(stats: DashboardStats): void {
    const s = stats.severity;
    this.donutChartData = {
      labels: ['Critical', 'High', 'Medium', 'Low'],
      datasets: [{
        data: [s.critical, s.high, s.medium, s.low],
        backgroundColor: ['#c62828', '#d84315', '#ef6c00', '#4caf50'],
        hoverBackgroundColor: ['#e53935', '#ff5722', '#ff9800', '#66bb6a'],
        borderWidth: 2,
        borderColor: '#fff',
      }],
    };
  }
}
