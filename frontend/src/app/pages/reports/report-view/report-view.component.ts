import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TitleCasePipe, DatePipe } from '@angular/common';
import { marked } from 'marked';
import { ReportService, ReportResponse } from '../../../services/report.service';

@Component({
  selector: 'app-report-view',
  standalone: true,
  imports: [
    RouterLink,
    TitleCasePipe,
    DatePipe,
    MatCardModule,
    MatProgressSpinnerModule,
    MatIconModule,
    MatChipsModule,
    MatButtonModule,
    MatDividerModule,
    MatTooltipModule,
  ],
  templateUrl: './report-view.component.html',
  styleUrl: './report-view.component.scss',
})
export class ReportViewComponent implements OnInit, OnDestroy {
  report: ReportResponse | null = null;
  renderedHtml: SafeHtml = '';
  loading = true;
  error = '';
  private pollTimer: ReturnType<typeof setInterval> | null = null;

  exportingPdf = false;
  exportError = '';

  constructor(
    private route: ActivatedRoute,
    private reportService: ReportService,
    private sanitizer: DomSanitizer,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.fetchReport(id);
  }

  ngOnDestroy(): void {
    this.stopPolling();
  }

  private fetchReport(id: string): void {
    this.reportService.getReport(id).subscribe({
      next: (report) => {
        this.report = report;
        this.loading = false;

        if (report.content) {
          const html = marked.parse(report.content) as string;
          this.renderedHtml = this.sanitizer.bypassSecurityTrustHtml(html);
        }

        if (report.status === 'generating') {
          this.startPolling(id);
        } else {
          this.stopPolling();
        }
      },
      error: () => {
        this.loading = false;
        this.error = 'Failed to load report.';
      },
    });
  }

  private startPolling(id: string): void {
    if (this.pollTimer) return;
    this.pollTimer = setInterval(() => this.fetchReport(id), 4000);
  }

  private stopPolling(): void {
    if (this.pollTimer) {
      clearInterval(this.pollTimer);
      this.pollTimer = null;
    }
  }

  exportMarkdown(): void {
    if (!this.report?.content) return;
    const blob = new Blob([this.report.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.report.repository}-${this.report.audience_type}-report.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  exportPdf(): void {
    if (!this.report || this.exportingPdf) return;
    this.exportingPdf = true;
    this.exportError = '';

    this.reportService.exportPdf(this.report.id).subscribe({
      next: (blob) => {
        this.exportingPdf = false;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.report!.repository}-${this.report!.audience_type}-report.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.exportingPdf = false;
        this.exportError = 'Failed to generate PDF. Try exporting as Markdown instead.';
      },
    });
  }
}
