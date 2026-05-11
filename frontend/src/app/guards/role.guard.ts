import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const roleGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isLoggedIn() && auth.isManagerOrAdmin()) {
    return true;
  }
  if (!auth.isLoggedIn()) {
    router.navigate(['/login']);
  }
  // If logged in but not admin/manager, still allow access to the page
  // (scoreboard shows own score for regular users)
  return true;
};
