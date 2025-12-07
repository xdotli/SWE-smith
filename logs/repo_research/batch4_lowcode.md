# Batch 4: Low-code/CMS Repos Research
Generated: 2025-12-06 (in progress)


## Repository Analysis

### budibase/budibase
- **Test Framework**: Jest (likely, monorepo structure)
- **Test Files**: Multiple packages with test configs
- **F2P Potential**: MEDIUM
- **Reason**: Monorepo with separate packages suggests segmented unit tests; need to verify package.json test scripts

### ToolJet/ToolJet
- **Test Framework**: Cypress (E2E), likely Jest for unit tests
- **Test Files**: cypress-tests directory visible
- **F2P Potential**: MEDIUM
- **Reason**: E2E tests typically harder to break; need unit test coverage verification

### supabase/supabase
- **Test Framework**: Unknown (monorepo, likely Jest/Vitest)
- **Test Files**: Structure unclear from repo page
- **F2P Potential**: MEDIUM
- **Reason**: Monorepo pattern suggests distributed test configs; needs package-level analysis

### payloadcms/payload
- **Test Framework**: Jest
- **Test Files**: jest.config.js present
- **F2P Potential**: HIGH
- **Reason**: Jest configured, TypeScript 96%, established CMS framework likely has good test coverage

### strapi/strapi
- **Test Framework**: Jest (multiple config files)
- **Test Files**: jest.config.api.js, jest.config.cli.js, jest.config.front.js, jest-preset.unit.js
- **F2P Potential**: HIGH
- **Reason**: Multiple Jest configs suggest segmented test suites (API, CLI, frontend, unit); good test isolation

