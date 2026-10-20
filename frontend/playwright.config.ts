import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./e2e',timeout:60000,workers:1,
 use:{baseURL:'http://127.0.0.1:8026',headless:true,
  launchOptions:{executablePath:process.env['PLAYWRIGHT_CHROMIUM_EXECUTABLE'],args:['--no-sandbox']}},
 reporter:'list'});
