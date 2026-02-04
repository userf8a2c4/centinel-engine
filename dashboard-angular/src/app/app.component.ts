import { Component } from '@angular/core';
import { DashboardComponent } from './components/dashboard.component';

/**
 * Componente raíz de la aplicación Angular para el dashboard de auditoría.
 * Root Angular component for the audit dashboard application.
 */
@Component({
  selector: 'app-root',
  standalone: true,
  imports: [DashboardComponent],
  template: '<app-dashboard />',
})
export class AppComponent {}
