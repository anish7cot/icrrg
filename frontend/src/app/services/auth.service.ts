import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface AuthResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export interface UserInfo {
  username: string;
  is_active: boolean;
}

const TOKEN_KEY = 'icrrg_token';
const USER_KEY = 'icrrg_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly baseUrl = '/api/v1/auth';

  private loggedIn$ = new BehaviorSubject<boolean>(this.hasToken());
  private username$ = new BehaviorSubject<string>(this.storedUsername());

  isLoggedIn$ = this.loggedIn$.asObservable();
  currentUsername$ = this.username$.asObservable();

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
    this.loggedIn$.next(false);
    this.username$.next('');
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
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

  private saveSession(res: AuthResponse): void {
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(USER_KEY, res.username);
    this.loggedIn$.next(true);
    this.username$.next(res.username);
  }
}
