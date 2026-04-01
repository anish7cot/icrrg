import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SeverityCounts {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface IssueTypeCount {
  finding_type: string;
  count: number;
}

export interface DashboardStats {
  total_scans: number;
  total_findings: number;
  scans_with_findings: number;
  clean_scans: number;
  average_risk_score: number;
  severity: SeverityCounts;
  top_issue_types: IssueTypeCount[];
}

export interface DailyTrend {
  date: string;
  scans: number;
  findings: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

@Injectable({ providedIn: 'root' })
export class StatsService {
  private readonly baseUrl = '/api/v1/stats';

  constructor(private http: HttpClient) {}

  getStats(repository?: string): Observable<DashboardStats> {
    let params: any = {};
    if (repository) params['repository'] = repository;
    return this.http.get<DashboardStats>(this.baseUrl, { params });
  }

  getTrends(days = 30, repository?: string): Observable<DailyTrend[]> {
    let params: any = { days: days.toString() };
    if (repository) params['repository'] = repository;
    return this.http.get<DailyTrend[]>(`${this.baseUrl}/trends`, { params });
  }
}
