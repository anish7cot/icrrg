import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface MetricsSummary {
  total_scans: number;
  total_llm_calls: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_llm_cost_usd: number;
  total_estimated_savings_usd: number;
  avg_scan_time_ms: number;
  avg_llm_time_ms: number;
  cache_hit_rate: number;
  total_findings_before_dedup: number;
  total_findings_after_dedup: number;
  dedup_savings_count: number;
  roi_multiplier: number;
}

export interface ScanMetrics {
  scan_id: string;
  total_time_ms: number;
  regex_time_ms: number;
  entropy_time_ms: number;
  ner_time_ms: number;
  llm_time_ms: number;
  llm_input_tokens: number;
  llm_output_tokens: number;
  llm_cost_usd: number;
  llm_calls_count: number;
  reasoning_level: number;
  cache_hit: boolean;
  findings_before_dedup: number;
  findings_after_dedup: number;
  estimated_savings_usd: number;
}

export interface DailyMetricsTrend {
  date: string;
  scans: number;
  llm_cost_usd: number;
  estimated_savings_usd: number;
  avg_time_ms: number;
  total_tokens: number;
}

@Injectable({ providedIn: 'root' })
export class MetricsService {
  private readonly baseUrl = '/api/v1/metrics';

  constructor(private http: HttpClient) {}

  getSummary(repository?: string, days?: number): Observable<MetricsSummary> {
    let params = new HttpParams();
    if (repository) params = params.set('repository', repository);
    if (days) params = params.set('days', days.toString());
    return this.http.get<MetricsSummary>(`${this.baseUrl}/summary`, { params });
  }

  getScanMetrics(scanId: string): Observable<ScanMetrics> {
    return this.http.get<ScanMetrics>(`${this.baseUrl}/scan/${scanId}`);
  }

  getTrends(days?: number, repository?: string): Observable<DailyMetricsTrend[]> {
    let params = new HttpParams();
    if (days) params = params.set('days', days.toString());
    if (repository) params = params.set('repository', repository);
    return this.http.get<DailyMetricsTrend[]>(`${this.baseUrl}/trends`, { params });
  }
}
