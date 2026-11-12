import { defineConfig, devices } from '@playwright/test'

// End-to-end tests run the built app against the real API with mock providers, on a mobile
// viewport. Two API instances: one on the repository content, one on the synthetic fixture
// content (the only content with a LOW rule, needed to show all five results).
// Ports differ from `make dev` (8000/5173) so both can run at once. Build first (`npm run e2e`).
const api = (port: number, db: string, content = '') =>
  `cd ../backend && rm -f ${db} && export DATABASE_URL=sqlite:///./${db} ${content} && uv run alembic upgrade head && uv run python -m app.seed && uv run uvicorn app.main:app --port ${port}`

export default defineConfig({
  testDir: 'tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    ...devices['Pixel 5'],
    browserName: 'chromium',
    trace: 'retain-on-failure',
    // A fake microphone (a tone) so recording runs end to end without hardware.
    permissions: ['microphone'],
    launchOptions: { args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'] },
  },
  projects: [
    { name: 'real', testMatch: /real\/.*\.spec\.ts/, use: { baseURL: 'http://127.0.0.1:4174' } },
    { name: 'fixture', testMatch: /fixture\/.*\.spec\.ts/, use: { baseURL: 'http://127.0.0.1:4175' } },
  ],
  webServer: [
    { command: api(8011, 'e2e.db'), url: 'http://127.0.0.1:8011/healthz', reuseExistingServer: false, timeout: 60_000 },
    {
      command: api(8012, 'e2e_fixture.db', 'CONTENT_ROOT=tests/fixtures/content'),
      url: 'http://127.0.0.1:8012/healthz',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    { command: 'API_URL=http://127.0.0.1:8011 npx vite preview --port 4174', url: 'http://127.0.0.1:4174', reuseExistingServer: false },
    { command: 'API_URL=http://127.0.0.1:8012 npx vite preview --port 4175', url: 'http://127.0.0.1:4175', reuseExistingServer: false },
  ],
})
