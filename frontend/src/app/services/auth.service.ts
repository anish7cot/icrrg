import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap, catchError, throwError, switchMap } from 'rxjs';

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  username: string;
  role: string;
}

export interface UserInfo {
  username: string;
  is_active: boolean;
  role: string;
}

const TOKEN_KEY = 'icrrg_token';
const REFRESH_TOKEN_KEY = 'icrrg_refresh_token';
const USER_KEY = 'icrrg_user';
const ROLE_KEY = 'icrrg_role';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = '/api/v1/auth';

  private loggedIn$ = new BehaviorSubject<boolean>(this.hasToken());
  private username$ = new BehaviorSubject<string>(this.storedUsername());
  private role$ = new BehaviorSubject<string>(this.storedRole());
  private refreshing = false;

  isLoggedIn$ = this.loggedIn$.asObservable();
  currentUsername$ = this.username$.asObservable();
  currentRole$ = this.role$.asObservable();

  constructor(private http: HttpClient) {}

  register(username: string, password: string): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.baseUrl}/register`, { username, password })
      .pipe(tap(res => this.saveSession(res)));
  }

  login(username: string, password: string): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${this.baseUrl}/login`, { username, password })
      .pipe(tap(res => this.saveSession(res)));
  }

  refreshToken(): Observable<AuthResponse> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) {
      this.logout();
      return throwError(() => new Error('No refresh token'));
    }
    this.refreshing = true;
    return this.http
      .post<AuthResponse>(`${this.baseUrl}/refresh`, { refresh_token: refreshToken })
      .pipe(
        tap(res => {
          this.saveSession(res);
          this.refreshing = false;
        }),
        catchError(err => {
          this.refreshing = false;
          this.logout();
          return throwError(() => err);
        })
      );
  }

  logout(): void {
    const refreshToken = this.getRefreshToken();
    if (refreshToken) {
      this.http
        .post(`${this.baseUrl}/logout`, { refresh_token: refreshToken })
        .subscribe({ error: () => {} });
    }
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(ROLE_KEY);
    this.loggedIn$.next(false);
    this.username$.next('');
    this.role$.next('');
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  isRefreshing(): boolean {
    return this.refreshing;
  }

  getRole(): string {
    return localStorage.getItem(ROLE_KEY) || 'developer';
  }

  isAdmin(): boolean {
    return this.getRole() === 'admin';
  }

  isManagerOrAdmin(): boolean {
    return ['admin', 'manager'].includes(this.getRole());
  }

  isLoggedIn(): boolean {
    return this.hasToken();
  }

  private hasToken(): boolean {
    return !!localStorage.getItem(TOKEN_KEY);
  }

  private storedUsername(): string {
    return localStorage.getItem(USER_KEY) || '';
  }

  private storedRole(): string {
    return localStorage.getItem(ROLE_KEY) || '';
  }

  private saveSession(res: AuthResponse): void {
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, res.refresh_token);
    localStorage.setItem(USER_KEY, res.username);
    localStorage.setItem(ROLE_KEY, res.role || 'developer');
    this.loggedIn$.next(true);
    this.username$.next(res.username);
    this.role$.next(res.role || 'developer');
  }
}
