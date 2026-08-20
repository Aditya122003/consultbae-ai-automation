// Application configuration provider registering client hydration and HTTP client services
// Configures modern standalone Angular dependency injection and router providers

import { ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    // Optimizes Angular change detection cycle timing
    provideZoneChangeDetection({ eventCoalescing: true }),
    // Configures application client-side routing table
    provideRouter(routes),
    // Provides global HttpClient for backend REST API communication
    provideHttpClient()
  ]
};
