import { ApplicationConfig, provideAppInitializer, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import {loadRuntimeConfig,apiOriginInterceptor} from './core/runtime-config';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withInterceptors([apiOriginInterceptor])),
    provideAppInitializer(loadRuntimeConfig),
    
  ]
};
