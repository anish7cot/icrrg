import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface LeaderboardEntry {
  rank: number;
  username: string;
  composite_score: number;
  security_score: number;
  responsiveness_score: number;
  improvement_score: number;
  total_scans: number;
  clean_scan_rate: number;
  findings_per_scan: number;
  period_start: string;
  period_end: string;
}

export interface MyScoreResponse {
  composite_score: number;
  security_score: number;
  responsiveness_score: number;
  improvement_score: number;
  total_scans: number;
  total_findings: number;
  clean_scan_rate: number;
  findings_per_scan: number;
  feedback_rate: number;
  improvement_rate: number;
  rank: number;
  percentile: number;
  period_start: string;
  period_end: string;
}

export interface ScoreHistoryEntry {
  period_start: string;
  composite_score: number;
  security_score: number;
  responsiveness_score: number;
  improvement_score: number;
}

export interface MethodologyResponse {
  version: string;
  description: string;
  weights: Record<string, number>;
  sub_scores: Array<{
    name: string;
    weight: string;
    formula: string;
    description: string;
    range: string;
  }>;
  scientific_basis: Array<{
    metric: string;
    standard: string;
    reference: string;
  }>;
}

@Injectable({ providedIn: 'root' })
export class ScoreboardService {
  private readonly baseUrl = '/api/v1/scoreboard';

  constructor(private http: HttpClient) {}

  getLeaderboard(periodStart?: string, limit?: number): Observable<LeaderboardEntry[]> {
    let params = new HttpParams();
    if (periodStart) params = params.set('period_start', periodStart);
    if (limit) params = params.set('limit', limit.toString());
    return this.http.get<LeaderboardEntry[]>(this.baseUrl, { params });
  }

  getMyScore(): Observable<MyScoreResponse | null> {
    return this.http.get<MyScoreResponse | null>(`${this.baseUrl}/me`);
  }

  getHistory(): Observable<ScoreHistoryEntry[]> {
    return this.http.get<ScoreHistoryEntry[]>(`${this.baseUrl}/history`);
  }

  triggerCalculation(): Observable<{ status: string; scores_computed: number }> {
    return this.http.post<{ status: string; scores_computed: number }>(
      `${this.baseUrl}/calculate`, {}
    );
  }

  getMethodology(): Observable<MethodologyResponse> {
    return this.http.get<MethodologyResponse>(`${this.baseUrl}/methodology`);
  }
}
