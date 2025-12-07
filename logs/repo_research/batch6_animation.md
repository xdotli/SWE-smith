# Batch 6: Animation/ORM Repos Research
Generated: 2025-12-06


### nivo
- **Test Framework**: Cypress (E2E) + Jest (likely)
- **Test Files**: Monorepo with multiple packages, likely 100+
- **F2P Potential**: MEDIUM
- **Reason**: Large React charting library with Cypress E2E tests; may have unit tests in packages but E2E tests could timeout


### framer/motion
- **Test Framework**: Playwright (E2E)
- **Test Files**: tests/ directory, likely 30+
- **F2P Potential**: MEDIUM
- **Reason**: Animation library with Playwright E2E tests; E2E tests tend to be slow and may timeout; needs unit tests for F2P generation


### pmndrs/react-three-fiber
- **Test Framework**: Jest
- **Test Files**: In packages/ subdirectories, likely 20+
- **F2P Potential**: MEDIUM-HIGH
- **Reason**: React Three Fiber is a monorepo with Jest unit tests; better for F2P than E2E-only repos

