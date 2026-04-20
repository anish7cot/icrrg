import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ScanRequest {
  diff_text: string;
  repository?: string;
  commit_hash?: string;
}

export interface Finding {
  id: string;
  finding_type: string;
  severity: string;
  message: string;
  file_path: string | null;
  line_number: number | null;
  confidence: number | null;
}

export interface ScanResponse {
  id: string;
  repository: string;
  commit_hash: string | null;
  status: string;
  risk_score: number | null;
  findings: Finding[];
  created_at: string;
}

export interface ScanSummary {
  id: string;
  repository: string;
  status: string;
  risk_score: number | null;
  finding_count: number;
  created_at: string;
}

export interface ScanNotification {
  scan_id: string;
  status: string;
  finding_count: number;
  risk_score: number | null;
  timestamp: string;
}

export interface ScanAccuracy {
  scan_id: string;
  total_findings: number;
  reviewed_findings: number;
  true_positive: number;
  false_positive: number;
  disputed: number;
  precision: number;
  review_coverage: number;
}

export interface FeedbackRequest {
  verdict: 'true_positive' | 'false_positive' | 'disputed';
  comment?: string;
}

export interface FeedbackResponse {
  id: string;
  scan_finding_id: string;
  user_id: string;
  verdict: string;
  comment: string | null;
}

@Injectable({ providedIn: 'root' })
export class ScanService {
  private readonly baseUrl = '/api/v1/scans';
  private readonly findingsUrl = '/api/v1/findings';

  constructor(private http: HttpClient) {}

  submitScan(request: ScanRequest): Observable<ScanResponse> {
    return this.http.post<ScanResponse>(this.baseUrl, request);
  }

  getScan(id: string): Observable<ScanResponse> {
    return this.http.get<ScanResponse>(`${this.baseUrl}/${id}`);
  }

  listScans(limit = 20, repository?: string): Observable<ScanSummary[]> {
    let params = new HttpParams().set('limit', limit.toString());
    if (repository) params = params.set('repository', repository);
    return this.http.get<ScanSummary[]>(this.baseUrl, { params });
  }

  listRepositories(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/repositories`);
  }

  pollScans(since?: string, repository?: string): Observable<ScanNotification[]> {
    let params = new HttpParams();
    if (since) params = params.set('since', since);
    if (repository) params = params.set('repository', repository);
    return this.http.get<ScanNotification[]>(`${this.baseUrl}/poll`, { params });
  }

  getScanAccuracy(scanId: string): Observable<ScanAccuracy> {
    return this.http.get<ScanAccuracy>(`${this.findingsUrl}/scan/${scanId}/accuracy`);
  }

  submitFeedback(findingId: string, request: FeedbackRequest): Observable<FeedbackResponse> {
    return this.http.post<FeedbackResponse>(
      `${this.findingsUrl}/${findingId}/feedback`,
      request,
    );
  }

  getFeedback(findingId: string): Observable<FeedbackResponse[]> {
    return this.http.get<FeedbackResponse[]>(`${this.findingsUrl}/${findingId}/feedback`);
  }
}
