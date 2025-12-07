# Batch 2: AI/API Repos Research
Generated: 2025-12-06

## Repository Analysis


### FlowiseAI/Flowise
- **Test Framework**: Jest
- **Test Files**: 7 found (packages/server/test, packages/components)
- **F2P Potential**: HIGH
- **Reason**: Has jest.config.js in multiple packages, 7 test files covering API routes and utility functions, indicating unit test coverage.

### hoppscotch/hoppscotch
- **Test Framework**: Vitest
- **Test Files**: 148 found
- **F2P Potential**: VERY HIGH
- **Reason**: Extensive test coverage with 148 test files using Vitest, covering auth helpers, services, inspection logic - core functionality with strong unit test patterns.

### nocodb/nocodb
- **Test Framework**: Jest + Playwright
- **Test Files**: 264 found (mostly Playwright e2e)
- **F2P Potential**: MEDIUM
- **Reason**: Large test suite but mostly Playwright e2e tests (264 files). Has jest.config.js for unit tests in packages/nocodb, but Playwright tests may timeout during validation.

### umami-software/umami
- **Test Framework**: Jest
- **Test Files**: 3 found
- **F2P Potential**: LOW
- **Reason**: Very minimal unit test coverage with only 3 test files. Limited unit test patterns available for PR mirroring.

### unkeyed/unkey
- **Test Framework**: Vitest
- **Test Files**: 151 found
- **F2P Potential**: HIGH
- **Reason**: Strong unit test coverage across multiple internal packages (encryption, hash, keys, billing, rbac, clickhouse). Tests cover core business logic utilities, ideal for PR mirroring.

### papermark/papermark
- **Test Framework**: Not found
- **Test Files**: 0
- **F2P Potential**: N/A
- **Reason**: Repository not found or doesn't exist at https://github.com/papermark/papermark.

### openstatusHQ/openstatus
- **Test Framework**: Vitest (inferred)
- **Test Files**: 45 found
- **F2P Potential**: HIGH
- **Reason**: Good test coverage across API routes and server logic. Tests cover monitors, maintenances, incidents, notifications - core API endpoints with clear test patterns.

### PostHog/posthog
- **Test Framework**: Jest + Playwright
- **Test Files**: 568 found
- **F2P Potential**: MEDIUM
- **Reason**: Massive test suite (568 files) with Jest for frontend logic and Playwright for e2e. Mix of unit tests for utilities/logic and e2e tests, but e2e may timeout during validation.

### mckaywrigley/chatbot-ui
- **Test Framework**: Jest + Playwright
- **Test Files**: 2 found
- **F2P Potential**: LOW
- **Reason**: Minimal test coverage with only 2 test files (1 Playwright e2e, 1 Jest unit test). Not suitable for PR mirroring.

### vercel/ai-chatbot
- **Test Framework**: Playwright + Jest
- **Test Files**: 7 found
- **F2P Potential**: MEDIUM
- **Reason**: Mix of Playwright e2e tests (4 files) and API route tests (2 files) with 1 utility test. Limited unit test coverage but some API endpoint logic testing available.

---

## Summary

### High F2P Potential (3 repos)
1. **hoppscotch/hoppscotch** - 148 Vitest files, comprehensive service/auth logic tests
2. **unkeyed/unkey** - 151 Vitest files, strong internal package coverage (crypto, billing, rbac)
3. **FlowiseAI/Flowise** - 7 Jest files, API route and utility tests

### Medium F2P Potential (3 repos)
1. **openstatusHQ/openstatus** - 45 Vitest files, API endpoint tests (monitors, incidents)
2. **PostHog/posthog** - 568 mixed files (Jest + Playwright), heavy on e2e, some unit logic
3. **nocodb/nocodb** - 264 files (mostly Playwright), may timeout during validation

### Low F2P Potential (2 repos)
1. **umami-software/umami** - 3 Jest files, very minimal coverage
2. **mckaywrigley/chatbot-ui** - 2 test files (1 e2e, 1 unit), minimal test suite

### N/A (1 repo)
1. **papermark/papermark** - Repository not found

---

## Recommendation

**Priority 1: Hoppscotch & Unkey**
- Start with these 2 repos (299 total test files)
- Both use Vitest with focused unit tests on core logic
- Highest conversion probability for PR mirroring

**Priority 2: FlowiseAI & OpenStatus**
- Good test coverage of API/utility logic
- Smaller test suites (easier to validate faster)

**Priority 3: PostHog (if resources available)**
- Large test suite but many are e2e (timeout risk)
- Consider filtering to jest tests only (skip playwright)

