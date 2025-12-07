# Batch 9: Additional CMS Repos Research
Generated: 2025-12-06


### contentlayerdev/contentlayer
- **Test Framework**: Unknown (no test config visible, project unmaintained)
- **Test Files**: Unknown (monorepo structure)
- **F2P Potential**: LOW
- **Reason**: Project is no longer maintained (⚠️), monorepo structure makes testing unclear, fork exists at contentlayer2


### shuding/nextra
- **Test Framework**: Unknown (monorepo, no test config visible)
- **Test Files**: Unknown (PNPM + Turborepo structure)
- **F2P Potential**: LOW
- **Reason**: Monorepo with no exposed test configuration; would require diving into individual packages; documentation-focused tool rather than core logic


### BuilderIO/builder
- **Test Framework**: Unknown (monorepo, no test config visible in listing)
- **Test Files**: Unknown (visual platform with multiple SDKs)
- **F2P Potential**: MEDIUM
- **Reason**: Large active monorepo (8.5k stars, 932 releases) with multiple packages likely to have tests; visual/UI-heavy so tests may be integration-focused rather than unit tests


### BuilderIO/qwik
- **Test Framework**: Vitest (vitest.config.ts, vitest-setup.ts, vitest.workspace.js visible)
- **Test Files**: Multiple test suites across packages (vitest.workspace.js indicates comprehensive setup)
- **F2P Potential**: HIGH
- **Reason**: Framework with dedicated Vitest configuration, workspace testing setup, e2e testing directory; active monorepo with strong testing infrastructure


### solidjs/solid
- **Test Framework**: Likely Vitest/Jest (tsconfig.test.json visible, but specific config not detailed)
- **Test Files**: Multiple across monorepo (pnpm-workspace.yaml + turbo.json indicate coordinated testing)
- **F2P Potential**: HIGH
- **Reason**: Active UI framework with monorepo structure, dedicated test TypeScript config, CI/CD testing infrastructure; compiler-based logic likely has good unit test coverage


### preactjs/preact
- **Test Framework**: Vitest (vitest.config.mjs, vitest.setup.js present)
- **Test Files**: Multiple in `/test` directory (organized test structure)
- **F2P Potential**: HIGH
- **Reason**: Small, focused framework (like React alternative) with dedicated Vitest setup; library code tends to have good unit test coverage for core logic

