# MARTA Platform Test Suite

This directory contains the comprehensive test suite for the MARTA platform, designed to ensure system reliability, performance, and correctness across all components.

## Test Structure

```
tests/
├── conftest.py                 # Global test configuration and fixtures
├── __init__.py                # Test package initialization
├── README.md                  # This file
│
├── fixtures/                  # Test data generators and factories
│   ├── __init__.py
│   └── data_factories.py      # Realistic test data generation
│
├── unit/                      # Unit tests for individual modules
│   ├── __init__.py
│   ├── test_models.py         # ML models and algorithms
│   ├── test_data_ingestion.py # Data ingestion pipelines
│   └── test_optimization.py   # Route optimization algorithms
│
├── integration/               # Integration tests for cross-module functionality
│   ├── __init__.py
│   ├── test_api_endpoints.py  # API endpoint integration
│   └── test_database_operations.py  # Database integration
│
├── e2e/                       # End-to-end tests for complete workflows
│   ├── __init__.py
│   ├── test_optimization_workflow.py  # Complete optimization pipeline
│   └── test_user_journeys.py          # User experience workflows
│
├── performance/               # Performance and load testing
│   ├── __init__.py
│   ├── test_optimization_performance.py  # Algorithm performance
│   └── test_load_testing.py              # API load testing
│
└── utils/                     # Test utilities and helpers
    ├── __init__.py
    └── test_helpers.py        # Common testing utilities
```

## Test Categories

### 🧪 Unit Tests
- **Purpose**: Test individual functions and classes in isolation
- **Location**: `tests/unit/`
- **Coverage Target**: 85%+
- **Features**:
  - Fast execution (< 1 second per test)
  - Mock external dependencies
  - Test edge cases and error conditions
  - Parametric testing for multiple scenarios

### 🔧 Integration Tests
- **Purpose**: Test component interactions and external services
- **Location**: `tests/integration/`
- **Coverage Target**: 80%+
- **Features**:
  - Database integration testing
  - API endpoint testing
  - External service mocking
  - Error propagation testing

### 🎯 End-to-End Tests
- **Purpose**: Test complete user workflows and system behavior
- **Location**: `tests/e2e/`
- **Coverage Target**: Critical paths only
- **Features**:
  - Full optimization workflows
  - User journey simulation
  - Browser automation (Selenium)
  - Multi-service coordination

### ⚡ Performance Tests
- **Purpose**: Validate system performance and scalability
- **Location**: `tests/performance/`
- **Features**:
  - Load testing with realistic traffic
  - Memory and CPU profiling
  - Algorithm benchmarking
  - Scalability validation

## Running Tests

### Quick Start

```bash
# Run all unit tests
python run_tests.py --unit

# Run with coverage
python run_tests.py --unit --coverage

# Run all test suites
python run_tests.py --all

# Run integration tests (requires services)
python run_tests.py --integration

# Run performance tests
python run_tests.py --performance
```

### Detailed Commands

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests with services
pytest tests/integration/ -v --tb=short

# End-to-end tests
pytest tests/e2e/ -v -m "not slow"

# Performance tests
pytest tests/performance/ -v -m "performance"

# Coverage analysis
pytest tests/unit/ tests/integration/ --cov=src --cov-report=html

# Parallel execution
pytest tests/unit/ -n auto

# Stop on first failure
pytest tests/ --maxfail=1

# Run specific test patterns
pytest -k "test_optimization" -v

# Run tests with specific markers
pytest -m "unit and not slow" -v
```

## Test Configuration

### Pytest Configuration (`pytest.ini`)
- Test discovery patterns
- Coverage settings
- Markers for test categorization
- Output formatting
- Performance thresholds

### Coverage Configuration (`.coveragerc`)
- Source code directories
- Files to exclude from coverage
- Coverage thresholds by module
- Report formats and locations

## Test Fixtures and Data

### Global Fixtures (`conftest.py`)
- **Database**: Test database setup with cleanup
- **Redis**: Mock Redis client for caching
- **External APIs**: Mock external service responses
- **Test Data**: Sample GTFS, ridership, and weather data
- **Performance Config**: Benchmarking configurations

### Data Factories (`fixtures/data_factories.py`)
- **GTFSDataFactory**: Generate realistic GTFS transit data
- **RidershipDataFactory**: Create ridership patterns with seasonality
- **WeatherDataFactory**: Generate weather data with Atlanta patterns
- **RealtimeDataFactory**: Mock real-time transit updates

### Example Usage
```python
def test_optimization_with_realistic_data(sample_gtfs_data, sample_ridership_data):
    """Test optimization with realistic data."""
    optimizer = RouteOptimizer()
    result = optimizer.optimize_routes(sample_gtfs_data)
    assert result['best_fitness'] > 0.8
```

## Test Helpers and Utilities

### TestDataBuilder
```python
# Build complex test scenarios
test_data = (TestDataBuilder()
    .with_gtfs_data(num_routes=10, num_stops=50)
    .with_ridership_data(num_days=30)
    .with_weather_data(num_days=30)
    .build())
```

### MockServiceManager
```python
# Mock external services
mock_manager = MockServiceManager()
mock_db = mock_manager.mock_database_service()
mock_redis = mock_manager.mock_redis_service()
```

### PerformanceProfiler
```python
# Profile function performance
profiler = PerformanceProfiler()
result, timing = profiler.time_function(optimization_function, data)
memory_result, memory_usage = profiler.memory_usage(memory_intensive_function)
```

## Coverage Requirements

### Overall Coverage Targets
- **Overall**: 80% minimum
- **Unit Tests**: 85% minimum
- **Integration Tests**: 75% minimum

### Module-Specific Targets
- **Models (ML)**: 85%
- **Optimization**: 80%
- **Data Ingestion**: 75%
- **API**: 70%
- **Database**: 80%
- **Visualization**: 65%

### Coverage Reports
- **HTML**: `htmlcov/index.html`
- **XML**: `coverage.xml` (for CI/CD)
- **JSON**: `coverage.json` (for analysis)
- **Terminal**: Real-time coverage output

## Continuous Integration

### GitHub Actions Integration
- Automated test execution on push/PR
- Multi-Python version testing
- Database service containers
- Coverage reporting to Codecov
- Performance regression detection

### Test Stages
1. **Code Quality**: Linting, formatting, type checking
2. **Unit Tests**: Fast, isolated component testing
3. **Integration Tests**: Cross-component functionality
4. **End-to-End Tests**: Complete workflow validation
5. **Performance Tests**: Load and benchmark testing
6. **Security Scanning**: Vulnerability detection

## Best Practices

### Test Writing Guidelines
1. **AAA Pattern**: Arrange, Act, Assert
2. **Descriptive Names**: Clear test purpose in name
3. **Single Responsibility**: One concept per test
4. **Data Independence**: Tests don't share state
5. **Fast Execution**: Unit tests < 1s, integration < 10s

### Mock and Fixture Guidelines
1. **Realistic Data**: Use data factories for realistic scenarios
2. **Isolation**: Mock external dependencies
3. **Cleanup**: Proper teardown in fixtures
4. **Reusability**: Common fixtures in conftest.py
5. **Performance**: Efficient fixture creation and cleanup

### Performance Testing Guidelines
1. **Baseline Metrics**: Establish performance baselines
2. **Regression Detection**: Alert on performance degradation
3. **Realistic Load**: Use production-like traffic patterns
4. **Resource Monitoring**: Track memory, CPU, and I/O usage
5. **Scalability Testing**: Validate system scaling characteristics

## Debugging Tests

### Common Issues and Solutions

#### Test Discovery Issues
```bash
# Verify test discovery
pytest --collect-only

# Check Python path
export PYTHONPATH=$PWD:$PYTHONPATH
```

#### Database Connection Issues
```bash
# Check database services
docker ps
pg_isready -h localhost -p 5432

# Run database setup
python -c "from tests.conftest import setup_test_database; setup_test_database()"
```

#### Import Errors
```bash
# Install dependencies
pip install -r requirements.txt

# Check module imports
python -c "import src.models.demand_forecaster"
```

### Test Debugging Tools
```bash
# Run with debugging
pytest -v --pdb --pdbcls=IPython.terminal.debugger:Pdb

# Capture output
pytest -v -s

# Show local variables on failure
pytest -v --tb=long

# Run single test with debugging
pytest tests/unit/test_models.py::TestDemandForecaster::test_training -v -s --pdb
```

## Contributing to Tests

### Adding New Tests
1. **Identify Test Category**: Unit, integration, or E2E
2. **Follow Naming Conventions**: `test_*.py` files, `test_*` functions
3. **Use Appropriate Fixtures**: Leverage existing fixtures
4. **Add Documentation**: Clear docstrings and comments
5. **Update Coverage**: Ensure new code is covered

### Test Review Checklist
- [ ] Tests follow AAA pattern
- [ ] Clear and descriptive test names
- [ ] Appropriate test category (unit/integration/e2e)
- [ ] Proper use of fixtures and mocks
- [ ] Edge cases and error conditions covered
- [ ] Performance considerations addressed
- [ ] Documentation updated

## Maintenance

### Regular Tasks
1. **Update Test Data**: Keep test datasets current
2. **Review Performance**: Monitor test execution times
3. **Update Dependencies**: Keep testing libraries current
4. **Clean Artifacts**: Remove old test outputs
5. **Analyze Coverage**: Identify coverage gaps

### Monitoring
- Test execution times trending up
- Flaky test identification and resolution
- Coverage percentage trends
- CI/CD pipeline performance
- Test failure patterns and root causes

## Support

### Getting Help
- Check this documentation first
- Review existing tests for patterns
- Consult team testing standards
- Create GitHub issue for test infrastructure problems

### Useful Resources
- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Testing Best Practices](https://docs.python.org/3/library/unittest.html)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)