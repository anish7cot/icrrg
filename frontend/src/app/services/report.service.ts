import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ReportRequest {
  repository: string;
  date_range_start: string;
  date_range_end: string;
  audience_type: string;
}

export interface SeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface FileGroupSummary {
  file_path: string;
  finding_count: number;
  severity_breakdown: SeverityBreakdown;
}

export interface FindingTypeCount {
  finding_type: string;
  count: number;
}

export interface AggregationResult {
  repository: string;
  date_range_start: string;
  date_range_end: string;
  total_scans: number;
  total_findings: number;
  severity_breakdown: SeverityBreakdown;
  top_files: FileGroupSummary[];
  top_finding_types: FindingTypeCount[];
  average_risk_score: number;
  max_risk_score: number;
  scans_by_status: Record<string, number>;
}

export interface ReportResponse {
  id: string;
  repository: string;
  date_range_start: string;
  date_range_end: string;
  audience_type: string;
  status: string;
  content: string | null;
  aggregation: AggregationResult | null;
  created_at: string;
}

export interface ReportListItem {
  id: string;
  repository: string;
  date_range_start: string;
  date_range_end: string;
  audience_type: string;
  status: string;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ReportService {
  private readonly baseUrl = '/api/v1/reports';

  constructor(private http: HttpClient) {}

  createReport(request: ReportRequest): Observable<ReportResponse> {
    return this.http.post<ReportResponse>(this.baseUrl, request);
  }

  getReport(id: string): Observable<ReportResponse> {
    return this.http.get<ReportResponse>(`${this.baseUrl}/${id}`);
  }

  listReports(limit = 20): Observable<ReportListItem[]> {
    return this.http.get<ReportListItem[]>(this.baseUrl, {
      params: { limit: limit.toString() },
    });
  }

  exportPdf(id: string): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/${id}/export`, {
      params: { format: 'pdf' },
      responseType: 'blob',
    });
  }
}
