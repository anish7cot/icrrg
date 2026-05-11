import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { ScoreboardService, LeaderboardEntry, MyScoreResponse, ScoreHistoryEntry, MethodologyResponse } from '../../services/scoreboard.service';

@Component({
  selector: 'app-scoreboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './scoreboard.component.html',
  styleUrl: './scoreboard.component.scss',
})
export class ScoreboardComponent implements OnInit {
  isManagerOrAdmin = signal(false);
  leaderboard = signal<LeaderboardEntry[]>([]);
  myScore = signal<MyScoreResponse | null>(null);
  history = signal<ScoreHistoryEntry[]>([]);
  methodology = signal<MethodologyResponse | null>(null);
  loading = signal(true);
  calculating = signal(false);

  constructor(
    private auth: AuthService,
    private scoreboard: ScoreboardService
  ) {}

  ngOnInit(): void {
    this.isManagerOrAdmin.set(this.auth.isManagerOrAdmin());
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);

    // Load methodology
    this.scoreboard.getMethodology().subscribe(m => this.methodology.set(m));

    // Load user's own score
    this.scoreboard.getMyScore().subscribe(s => this.myScore.set(s));

    // Load history
    this.scoreboard.getHistory().subscribe(h => this.history.set(h));

    // Load leaderboard (admin/manager only)
    if (this.isManagerOrAdmin()) {
      this.scoreboard.getLeaderboard().subscribe({
        next: entries => {
          this.leaderboard.set(entries);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
    } else {
      this.loading.set(false);
    }
  }

  triggerCalculation(): void {
    this.calculating.set(true);
    this.scoreboard.triggerCalculation().subscribe({
      next: () => {
        this.calculating.set(false);
        this.loadData();
      },
      error: () => this.calculating.set(false),
    });
  }

  recalculateMyScore(): void {
    this.calculating.set(true);
    this.scoreboard.triggerMyCalculation().subscribe({
      next: () => {
        this.calculating.set(false);
        this.loadData();
      },
      error: () => this.calculating.set(false),
    });
  }

  getScoreColor(score: number): string {
    if (score >= 80) return '#4caf50';
    if (score >= 60) return '#ff9800';
    if (score >= 40) return '#f44336';
    return '#9e9e9e';
  }

  getRankBadge(rank: number): string {
    if (rank === 1) return '🥇';
    if (rank === 2) return '🥈';
    if (rank === 3) return '🥉';
    return `#${rank}`;
  }

  getTrendArrow(improvementRate: number): string {
    if (improvementRate > 5) return '↑';
    if (improvementRate < -5) return '↓';
    return '→';
  }

  getImprovementTip(): string {
    const score = this.myScore();
    if (!score) return '';
    const lowest = Math.min(score.security_score, score.responsiveness_score, score.improvement_score);
    if (lowest === score.security_score) {
      return 'Focus on reducing critical/high severity findings in your commits. Review OWASP Top 10 before coding.';
    }
    if (lowest === score.responsiveness_score) {
      return 'Increase your engagement by providing feedback (true positive/false positive) on all findings in your scans.';
    }
    return 'Your finding density is increasing. Review past findings to avoid repeating patterns.';
  }
}
