import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface AuthResponse {
  access_token: string;
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
const USER_KEY = 'icrrg_user';
const ROLE_KEY = 'icrrg_role';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = '/api/v1/auth';

  private loggedIn$ = new BehaviorSubject<boolean>(this.hasToken());
  private username$ = new BehaviorSubject<string>(this.storedUsername());
  private role$ = new BehaviorSubject<string>(this.storedRole());

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

  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(ROLE_KEY);
    this.loggedIn$.next(false);
    this.username$.next('');
    this.role$.next('');
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
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
    localStorage.setItem(USER_KEY, res.username);
    localStorage.setItem(ROLE_KEY, res.role || 'developer');
    this.loggedIn$.next(true);
    this.username$.next(res.username);
    this.role$.next(res.role || 'developer');
  }
}
