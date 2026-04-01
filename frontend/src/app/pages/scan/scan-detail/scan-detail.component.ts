import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { Finding, ScanResponse } from '../../../services/scan.service';

interface SeverityCount {
  label: string;
  count: number;
  color: string;
  icon: string;
}

interface FileGroup {
  filePath: string;
  findings: Finding[];
  detectionCount: number;
  reviewCount: number;
}

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

@Component({
  selector: 'app-scan-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatChipsModule,
    MatIconModule,
    MatDividerModule,
    MatExpansionModule,
    MatProgressBarModule,
  ],
  templateUrl: './scan-detail.component.html',
  styleUrls: ['./scan-detail.component.scss'],
})
export class ScanDetailComponent implements OnChanges {
  @Input() scan: ScanResponse | null = null;

  sortedFindings: Finding[] = [];
  severityCounts: SeverityCount[] = [];
  fileGroups: FileGroup[] = [];
  detectionFindings: Finding[] = [];
  reviewFindings: Finding[] = [];
  expandedIds = new Set<string>();

  get riskLevel(): string {
    const score = this.scan?.risk_score ?? 0;
    if (score >= 7) return 'high';
    if (score >= 4) return 'medium';
    return 'low';
  }

  ngOnChanges(_changes: SimpleChanges): void {
    if (this.scan) {
      this.sortedFindings = [...this.scan.findings].sort(
        (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
      );
      this.detectionFindings = this.scan.findings.filter(f => !this.isReviewFinding(f));
      this.reviewFindings = this.scan.findings.filter(f => this.isReviewFinding(f));
      this.severityCounts = this.buildSeverityCounts();
      this.fileGroups = this.buildFileGroups();
    } else {
      this.sortedFindings = [];
      this.severityCounts = [];
      this.fileGroups = [];
      this.detectionFindings = [];
      this.reviewFindings = [];
    }
  }

  isReviewFinding(f: Finding): boolean {
    return f.finding_type.startsWith('llm:');
  }

  formatType(type: string): string {
    const [category, ...rest] = type.split(':');
    const label = category.charAt(0).toUpperCase() + category.slice(1);
    return rest.length ? `${label}: ${rest.join(':')}` : label;
  }

  toggleExpand(finding: Finding): void {
    if (this.expandedIds.has(finding.id)) {
      this.expandedIds.delete(finding.id);
    } else {
      this.expandedIds.add(finding.id);
    }
  }

  /** For LLM findings, message is "issue — suggestion". Split on " — ". */
  getSummary(f: Finding): string {
    return f.message.split(' — ')[0];
  }

  getExplanation(f: Finding): string {
    if (!this.isReviewFinding(f)) return '';
    const parts = f.message.split(' — ');
    return parts.length > 1 ? parts[1] : '';
  }

  getSuggestion(f: Finding): string {
    // Suggestions are stored in explanation for LLM findings
    return '';
  }

  private buildSeverityCounts(): SeverityCount[] {
    const counts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const f of this.scan?.findings ?? []) {
      counts[f.severity] = (counts[f.severity] ?? 0) + 1;
    }
    return [
      { label: 'critical', count: counts['critical'], color: '#d32f2f', icon: 'error' },
      { label: 'high',     count: counts['high'],     color: '#ef6c00', icon: 'warning' },
      { label: 'medium',   count: counts['medium'],   color: '#f9a825', icon: 'info' },
      { label: 'low',      count: counts['low'],      color: '#388e3c', icon: 'check_circle' },
    ];
  }

  private buildFileGroups(): FileGroup[] {
    const map = new Map<string, Finding[]>();
    for (const f of this.sortedFindings) {
      const key = f.file_path || '(unknown file)';
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(f);
    }
    return Array.from(map.entries()).map(([filePath, findings]) => ({
      filePath,
      findings,
      detectionCount: findings.filter(f => !this.isReviewFinding(f)).length,
      reviewCount: findings.filter(f => this.isReviewFinding(f)).length,
    }));
  }
}
