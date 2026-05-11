import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    MatProgressBarModule,
  ],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent implements OnInit {
  username = '';
  password = '';
  loading = false;
  error = '';
  isRegister = false;
  showPassword = false;

  // Password strength
  passwordErrors: string[] = [];
  passwordStrength = 0; // 0-4

  constructor(
    private auth: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    if (this.route.snapshot.queryParams['locked'] === 'true') {
      this.error = 'Account temporarily locked due to too many failed login attempts. Please try again later.';
    }
  }

  validatePassword(): void {
    this.passwordErrors = [];
    let strength = 0;
    const p = this.password;

    if (p.length >= 8) { strength++; } else { this.passwordErrors.push('At least 8 characters'); }
    if (/[A-Z]/.test(p)) { strength++; } else { this.passwordErrors.push('One uppercase letter'); }
    if (/[a-z]/.test(p)) { strength++; } else { this.passwordErrors.push('One lowercase letter'); }
    if (/[0-9]/.test(p)) { strength++; } else { this.passwordErrors.push('One digit'); }
    if (/[!@#$%^&*()_+\-=\[\]{}|;':",./<>?]/.test(p)) { strength++; } else { this.passwordErrors.push('One special character'); }

    this.passwordStrength = strength;
  }

  get strengthLabel(): string {
    if (this.passwordStrength <= 1) return 'Weak';
    if (this.passwordStrength <= 3) return 'Fair';
    if (this.passwordStrength === 4) return 'Good';
    return 'Strong';
  }

  get strengthColor(): string {
    if (this.passwordStrength <= 1) return 'warn';
    if (this.passwordStrength <= 3) return 'accent';
    return 'primary';
  }

  get canSubmit(): boolean {
    if (!this.username.trim() || !this.password.trim()) return false;
    if (this.isRegister && this.passwordStrength < 5) return false;
    return true;
  }

  submit(): void {
    if (!this.canSubmit) return;
    this.loading = true;
    this.error = '';

    const action$ = this.isRegister
      ? this.auth.register(this.username, this.password)
      : this.auth.login(this.username, this.password);

    action$.subscribe({
      next: () => {
        this.loading = false;
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading = false;
        if (err.status === 423) {
          this.error = 'Account temporarily locked due to too many failed login attempts. Please try again later.';
        } else {
          this.error = err.error?.detail || 'Authentication failed';
        }
      },
    });
  }

  toggleMode(): void {
    this.isRegister = !this.isRegister;
    this.error = '';
    this.passwordErrors = [];
    this.passwordStrength = 0;
  }

  togglePassword(): void {
    this.showPassword = !this.showPassword;
  }
}
