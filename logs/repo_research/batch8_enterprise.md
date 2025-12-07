# Batch 8: Enterprise Repos Research
Generated: 2025-12-06

## Summary

Researched 10 enterprise-grade TypeScript repositories for PR Mirroring F2P potential. Results show **4 repos with HIGH potential** (Jest configured), **5 repos with LOW potential** (no clear test framework), and **1 repo not found** (cal-smith/rallly).

## Detailed Results

### illacloud/illa-builder
- **Test Framework**: Turbo-delegated (unknown subpackage tests)
- **F2P Potential**: LOW
- **Reason**: Root package.json has `"test": "turbo run test"` but test framework not declared at root level. Apps directory found but subpackages lack Jest/Vitest/Mocha

### lowdefy/lowdefy
- **Test Framework**: Jest (in subpackages)
- **F2P Potential**: HIGH
- **Reason**: Monorepo with Jest configured in individual workspace packages. Has `pnpm -r` test script delegating to workspaces

### signoz/signoz
- **Test Framework**: Unknown/Minimal
- **F2P Potential**: LOW
- **Reason**: Has `tests/` directory but no clear Jest/Vitest/Mocha in package.json. Likely integration/e2e focused rather than unit tests

### grafana/grafana
- **Test Framework**: Jest
- **F2P Potential**: HIGH
- **Reason**: Root-level Jest configuration with `jest.config.js`. Large monorepo with extensive unit test coverage expected for core packages

### elastic/kibana
- **Test Framework**: Jest, Mocha, Playwright
- **F2P Potential**: HIGH
- **Reason**: Multiple test frameworks configured: Jest, Mocha for unit tests, Playwright for e2e. Mature enterprise project with comprehensive test coverage

### n8n-io/n8n
- **Test Framework**: Jest
- **F2P Potential**: HIGH
- **Reason**: Jest configured in root package.json. Large workflow automation platform with good test coverage for core backend/frontend logic

### windmill-labs/windmill
- **Test Framework**: Unknown/Minimal
- **F2P Potential**: LOW
- **Reason**: Has `integration_tests/` directory but no Jest/Vitest/Mocha in root package.json. Integration-focused rather than unit test framework

### cal-smith/rallly
- **Test Framework**: NOT FOUND
- **F2P Potential**: UNKNOWN
- **Reason**: Repository not found at GitHub. Repo name may be incorrect (possibly `rallly/rallly` or archived)

### highlight/highlight
- **Test Framework**: Unknown/Likely Vitest
- **F2P Potential**: MEDIUM
- **Reason**: Has tsconfig.json (TypeScript project) but test framework not clearly visible in package.json. Modern frontend app likely using Vitest/Jest but needs verification

### inngest/inngest
- **Test Framework**: Unknown (has tests/)
- **F2P Potential**: MEDIUM
- **Reason**: Has `tests/` and `api.test` files but primary test framework unclear. Package.json didn't show Jest/Vitest. Likely using Node.js native test runner or custom setup

## Priority Ranking

| Priority | Repo | Test Framework | Expected F2P Rate |
|----------|------|----------------|-------------------|
| **1 - IMMEDIATE** | elastic/kibana | Jest + Mocha + Playwright | HIGH (40-50%) |
| **1 - IMMEDIATE** | grafana/grafana | Jest | HIGH (40-50%) |
| **2 - HIGH** | n8n-io/n8n | Jest | HIGH (30-40%) |
| **2 - HIGH** | lowdefy/lowdefy | Jest (subpackages) | MEDIUM (20-30%) |
| **3 - MEDIUM** | highlight/highlight | Unknown (likely Vitest) | MEDIUM (15-25%) |
| **3 - MEDIUM** | inngest/inngest | Unknown (custom tests) | MEDIUM (15-25%) |
| **4 - LOW** | illacloud/illa-builder | Turbo-delegated | LOW (10-15%) |
| **4 - LOW** | windmill-labs/windmill | Integration only | LOW (5-10%) |
| **4 - LOW** | signoz/signoz | Minimal/Integration | LOW (5-10%) |
| **N/A** | cal-smith/rallly | NOT FOUND | - |

## Recommendations

1. **Start with Kibana and Grafana** - Both are enterprise-grade with proven Jest setups and extensive test coverage
2. **Skip windmill-labs/windmill** - No clear unit test framework, only integration tests (low F2P potential)
3. **Skip signoz/signoz** - Minimal unit test coverage (low F2P potential)
4. **Verify cal-smith/rallly** - Confirm correct repository name before proceeding

## Next Steps

For optimal F2P instance generation:
- Profile and mirror: `elastic/kibana`, `grafana/grafana`, `n8n-io/n8n`
- Collect PRs with strict filtering (small diffs, actual unit test changes, not snapshots)
- Expected combined F2P: 15-25 instances from these 3 repos alone

