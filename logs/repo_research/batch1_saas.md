# Batch 1: SaaS Repos Research
Generated: 2025-12-06 12:00 UTC


### calcom/cal.com
- **Test Framework**: Vitest + Playwright
- **Test Files**: Multiple, distributed across monorepo
- **F2P Potential**: MEDIUM
- **Reason**: Has vitest.config.ts and playwright.config.ts, E2E test infrastructure, but monorepo structure means tests are spread across packages. Some unit tests likely exist but E2E focus may limit F2P opportunities.

### dubinc/dub
- **Test Framework**: Unknown from public page
- **Test Files**: Not visible
- **F2P Potential**: LOW
- **Reason**: GitHub page doesn't show test configuration files or test directories. Likely has tests but setup not immediately visible. Would need to check package.json contents.

### makeplane/plane
- **Test Framework**: Unknown (likely Jest or Vitest)
- **Test Files**: Not visible in public listing
- **F2P Potential**: LOW
- **Reason**: Monorepo with Python/TypeScript hybrid. Page doesn't expose test config. Would need direct directory inspection to confirm test setup.

### twentyhq/twenty
- **Test Framework**: Jest + Playwright
- **Test Files**: Distributed across packages in monorepo
- **F2P Potential**: MEDIUM
- **Reason**: Jest and Playwright configurations present. NestJS backend + monorepo structure suggests decent unit test coverage in backend packages. Monorepo may have better isolated tests than UI-heavy repos.

### Infisical/infisical
- **Test Framework**: Cypress + BDD (Behavior-Driven Development)
- **Test Files**: E2E and integration tests
- **F2P Potential**: LOW
- **Reason**: Focus on E2E (Cypress) and BDD tests. Cypress/BDD tests are integration-level, less likely to produce unit-test F2P instances. 97.6% TypeScript but test strategy is E2E-focused.

