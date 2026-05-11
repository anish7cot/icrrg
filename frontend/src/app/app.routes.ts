import { Routes } from '@angular/router';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { ScanComponent } from './pages/scan/scan.component';
import { ScanViewComponent } from './pages/scan/scan-view/scan-view.component';
import { ReportsComponent } from './pages/reports/reports.component';
import { ReportViewComponent } from './pages/reports/report-view/report-view.component';
import { LoginComponent } from './pages/login/login.component';
import { ScoreboardComponent } from './pages/scoreboard/scoreboard.component';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  { path: 'login', component: LoginComponent },
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] },
  { path: 'scan', component: ScanComponent, canActivate: [authGuard] },
  { path: 'scan/:id', component: ScanViewComponent, canActivate: [authGuard] },
  { path: 'reports', component: ReportsComponent, canActivate: [authGuard] },
  { path: 'reports/:id', component: ReportViewComponent, canActivate: [authGuard] },
  { path: 'scoreboard', component: ScoreboardComponent, canActivate: [authGuard] },
];
