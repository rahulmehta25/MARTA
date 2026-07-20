# MARTA Frontend Testing Suite

This directory contains comprehensive test suites for the MARTA frontend application, covering unit tests, integration tests, and end-to-end tests.

## Test Structure

```
tests/
├── e2e/                    # End-to-end tests (Playwright)
├── integration/            # Integration tests
├── unit/                   # Unit tests
├── __mocks__/             # Mock implementations
├── setup.js               # Test setup and configuration
└── README.md              # This file
```

## Testing Stack

- **Unit Tests**: Jest + React Testing Library
- **Integration Tests**: Jest + React Testing Library
- **E2E Tests**: Playwright (for comprehensive browser testing)
- **Mocking**: Custom mocks for external dependencies

## Available Test Commands

```bash
# Run all unit and integration tests
npm test

# Run tests in watch mode during development
npm run test:watch

# Generate coverage report
npm run test:coverage

# Run E2E tests with Playwright
npm run test:e2e

# Run E2E tests with UI interface
npm run test:e2e:ui

# Test deployed application
npm run test:deployed

# Run all tests (unit, integration, and E2E)
npm run test:all
```

## Test Categories

### 1. Unit Tests (`/unit/`)

Test individual components in isolation:

- **SearchBar.test.jsx**: Search functionality, keyboard navigation, API integration
- **BottomDrawer.test.jsx**: Drawer behavior, tab navigation, demand data display
- **MainLayout.test.jsx**: Layout composition, state management, component integration

Key testing patterns:
- Component rendering and props
- User interactions (clicks, typing, keyboard events)
- State changes and side effects
- Error handling
- Accessibility features

### 2. Integration Tests (`/integration/`)

Test component interactions and data flow:

- **AppIntegration.test.jsx**: Full application workflow, component communication, error handling

Key integration scenarios:
- Search → Selection → Drawer workflow
- Map interaction → State updates
- Layer toggles → Visual feedback
- API failures → Graceful degradation

### 3. End-to-End Tests (`/e2e/`)

Test complete user workflows in real browser environments:

- **marta-app.spec.js**: Complete application testing across multiple browsers and devices

Key E2E scenarios:
- Page loading and rendering
- Cross-browser compatibility
- Mobile responsiveness  
- Performance benchmarks
- Accessibility compliance
- Error boundary testing

## Test Configuration Files

### Jest Configuration (`jest.config.js`)
- Test environment setup (jsdom)
- Module mapping and transforms
- Coverage thresholds and reporting
- Mock configurations

### Playwright Configuration (`playwright.config.js`)
- Multi-browser testing (Chrome, Firefox, Safari)
- Mobile device simulation
- Video recording and screenshots
- Parallel execution

### Test Setup (`setup.js`)
- Global test utilities
- DOM API mocks (IntersectionObserver, etc.)
- LocalStorage and fetch mocks
- Cleanup between tests

## Mock Strategy

### Component Mocks (`__mocks__/`)
- **mapbox-gl.js**: Mapbox GL library mock
- **framer-motion.js**: Animation library mock
- **fileMock.js**: Static asset mock

### API Mocks
All API calls are mocked in tests to ensure:
- Fast, reliable test execution
- Predictable test data
- Network-independent testing
- Error scenario simulation

## Coverage Targets

- **Lines**: 70%+
- **Functions**: 70%+
- **Branches**: 70%+
- **Statements**: 70%+

Coverage reports are generated in the `coverage/` directory with HTML, LCOV, and JSON formats.

## Best Practices

### Test Organization
- Group related tests with `describe` blocks
- Use descriptive test names that explain behavior
- Follow Arrange-Act-Assert pattern
- Test behavior, not implementation

### Component Testing
- Use `screen` queries from Testing Library
- Prefer user-centric queries (`getByRole`, `getByLabelText`)
- Mock external dependencies appropriately
- Test error states and edge cases

### Async Testing
- Use `waitFor` for async operations
- Mock API responses with realistic data
- Test loading states and error handling
- Avoid fixed delays in tests

### Accessibility Testing
- Test keyboard navigation
- Verify ARIA attributes
- Check focus management
- Test with screen reader expectations

## Running Specific Tests

```bash
# Run specific test file
npm test SearchBar.test.jsx

# Run tests matching pattern
npm test -- --testNamePattern="search"

# Run tests with verbose output
npm test -- --verbose

# Run tests and update snapshots
npm test -- --updateSnapshot

# Run only changed files
npm test -- --onlyChanged
```

## Continuous Integration

Tests are configured to run in CI environments with:
- Parallel execution for faster builds
- Retry logic for flaky tests
- Coverage reporting to external services
- Cross-browser testing matrix

## Debugging Tests

### Local Debugging
```bash
# Run tests with Node debugger
node --inspect-brk node_modules/.bin/jest --runInBand

# Debug specific test
npm test -- --testNamePattern="specific test" --runInBand
```

### E2E Debugging
```bash
# Run E2E tests with browser UI
npm run test:e2e:ui

# Run E2E tests in headed mode
npx playwright test --headed

# Debug specific E2E test
npx playwright test --debug
```

## Test Data Management

### Fixtures
Test data is managed through:
- Inline mock data for unit tests
- Factory functions for complex objects
- Realistic data that matches API responses
- Edge case data for error testing

### Test Database
For integration tests requiring persistent data:
- Use in-memory databases when possible
- Clean up data between tests
- Use database transactions for isolation

## Performance Testing

### Load Testing
- Component render performance
- Large dataset handling  
- Memory leak detection
- Bundle size impact

### Metrics Tracking
- Test execution time
- Coverage trends over time
- Flaky test identification
- Performance regression detection

## Contributing to Tests

When adding new features:

1. **Write tests first** (TDD approach recommended)
2. **Add unit tests** for new components
3. **Add integration tests** for component interactions  
4. **Update E2E tests** for new user workflows
5. **Maintain coverage** above threshold
6. **Update documentation** for new test patterns

### Test Review Checklist

- [ ] Tests cover happy path and edge cases
- [ ] Error handling is tested
- [ ] Async operations are properly awaited
- [ ] Mocks are appropriate and realistic
- [ ] Tests are deterministic (no random failures)
- [ ] Accessibility considerations are tested
- [ ] Performance impact is considered

## Troubleshooting

### Common Issues

**Tests timing out**
- Check for unresolved promises
- Verify API mocks are properly configured
- Increase timeout for slow operations

**Flaky tests**
- Remove fixed delays (`setTimeout`)
- Use `waitFor` with proper conditions
- Check for race conditions in async code

**Mock issues**
- Verify mock setup in `beforeEach`
- Clear mocks between tests
- Check mock implementation matches real API

**Coverage issues**
- Add tests for uncovered branches
- Remove dead code
- Check coverage exclusions

### Getting Help

- Review existing tests for patterns
- Check testing library documentation
- Use debugger to inspect test state
- Run tests with verbose output for details

## Future Enhancements

- Visual regression testing with screenshot comparisons
- Performance regression testing
- Automated accessibility auditing
- Cross-browser compatibility matrix expansion
- API contract testing with generated mocks