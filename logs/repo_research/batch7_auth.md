# Batch 7: Auth/Starter Repos Research
Generated: Sat Dec 6 23:56:16 EST 2025


## Repos Analyzed

### supertokens/supertokens-auth-react
- **Test Framework**: Jest + Mocha
- **Test Files**: Multiple (test/ directory exists, 56% TypeScript)
- **F2P Potential**: HIGH
- **Reason**: Mature React auth library with comprehensive testing infrastructure (Jest primary, Mocha secondary). Mixed TS/JS codebase suggests solid test coverage for authentication logic.

### shadcn-ui/taxonomy
- **Test Framework**: None detected
- **Test Files**: 0
- **F2P Potential**: LOW
- **Reason**: No test configuration files found (no jest.config.js, vitest.config.ts, playwright.config.ts). Work-in-progress template repo without testing infrastructure.

### steven-tey/precedent
- **Test Framework**: None detected
- **Test Files**: 0
- **F2P Potential**: LOW
- **Reason**: No test framework configuration or test directories visible. Template/starter repo focused on config (ESLint, Prettier, Tailwind) without testing setup.

### timlrx/tailwind-nextjs-blog
- **Test Framework**: Unknown (404 - repo unavailable or private)
- **Test Files**: Unknown
- **F2P Potential**: UNKNOWN
- **Reason**: Could not access repository.

### ixartz/next-js-boilerplate
- **Test Framework**: Vitest + Playwright
- **Test Files**: Present (configured for .test.ts/tsx alongside source)
- **F2P Potential**: HIGH
- **Reason**: Well-structured testing setup with Vitest (unit), Playwright (e2e), and Storybook. Tests co-located with source code. Professional boilerplate with integrated testing pipeline.


### emilkowalski/vaul
- **Test Framework**: Playwright
- **Test Files**: Present (test/ directory exists)
- **F2P Potential**: MEDIUM
- **Reason**: Playwright configured but exact test count unclear. Component/dialog library (React Dialog open source). Playwright suggests e2e tests rather than unit tests - may have fewer test assertions to trigger F2P.

### pacocoursey/cmdk
- **Test Framework**: Playwright
- **Test Files**: Present (test/ directory exists)
- **F2P Potential**: MEDIUM
- **Reason**: Playwright configured for testing. Command palette component library. E2E focus may limit F2P potential compared to unit test-focused repos.

### leerob/leerob.io
- **Test Framework**: None detected
- **Test Files**: 0
- **F2P Potential**: LOW
- **Reason**: No test configuration files visible. Personal blog/portfolio site. No testing infrastructure - typical for content-focused projects.

### shadcn-ui/ui
- **Test Framework**: Vitest + Vitest Workspace
- **Test Files**: Present (vitest.config.ts and vitest.workspace.ts configured)
- **F2P Potential**: HIGH
- **Reason**: Monorepo with Vitest setup across multiple packages. Large collection of reusable UI components with unit testing infrastructure. Workspace setup suggests per-package test coverage.

### TryGhost/Ghost
- **Test Framework**: Unknown (nx.json monorepo, JS/TS mixed)
- **Test Files**: Likely present (monorepo pattern suggests testing)
- **F2P Potential**: MEDIUM
- **Reason**: Monorepo with nx.json (Nx framework). Mixed JS/TS. No specific test config visible from overview, but complex platform (blogging CMS) typically has testing. Would need deeper inspection.

---

## Summary

### HIGH F2P Potential (3 repos)
1. **supertokens/supertokens-auth-react** - Jest + Mocha, auth library with solid test infrastructure
2. **ixartz/next-js-boilerplate** - Vitest + Playwright, professional boilerplate with integrated testing
3. **shadcn-ui/ui** - Vitest monorepo, large component library with workspace testing

### MEDIUM F2P Potential (3 repos)
1. **emilkowalski/vaul** - Playwright e2e tests
2. **pacocoursey/cmdk** - Playwright e2e tests
3. **TryGhost/Ghost** - Monorepo (nx.json) with unknown test framework

### LOW F2P Potential (3 repos)
1. **shadcn-ui/taxonomy** - No testing infrastructure
2. **steven-tey/precedent** - Template repo, no tests
3. **leerob/leerob.io** - Personal site, no tests

### UNKNOWN (1 repo)
1. **timlrx/tailwind-nextjs-blog** - Could not access (404)

---

## Recommendation

**Priority 1: Create profiles for HIGH potential repos**
- supertokens-auth-react (authentication logic tests)
- next-js-boilerplate (comprehensive unit test suite)
- shadcn-ui/ui (monorepo with component tests)

**Priority 2: Investigate MEDIUM repos**
- Ghost (complex platform, likely hidden test infrastructure)
- vaul & cmdk (Playwright tests might have assertions-based tests beyond e2e)

