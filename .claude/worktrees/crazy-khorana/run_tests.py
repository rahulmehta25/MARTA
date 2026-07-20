#!/usr/bin/env python3
"""
MARTA Platform Test Runner
=========================

Comprehensive test runner for the MARTA platform with various test modes and configurations.

Usage:
    python run_tests.py [options]

Examples:
    python run_tests.py --unit                    # Run only unit tests
    python run_tests.py --integration            # Run only integration tests  
    python run_tests.py --e2e                    # Run only end-to-end tests
    python run_tests.py --performance            # Run performance tests
    python run_tests.py --coverage               # Run with coverage report
    python run_tests.py --all                    # Run all test suites
    python run_tests.py --fast                   # Skip slow tests
    python run_tests.py --verbose                # Verbose output
    python run_tests.py --parallel               # Run tests in parallel
"""

import argparse
import sys
import subprocess
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
import json

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.project_root = project_root
        self.test_dir = self.project_root / "tests"
        self.results = {}
        self.start_time = None
        self.total_time = None
    
    def run_unit_tests(self, args: argparse.Namespace) -> bool:
        """Run unit tests."""
        print("🧪 Running unit tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "unit"),
            "-v" if args.verbose else "--tb=short"
        ]
        
        if args.coverage:
            cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
        
        if args.parallel:
            cmd.extend(["-n", "auto"])
        
        if args.fast:
            cmd.extend(["-m", "not slow"])
        
        if args.maxfail:
            cmd.extend(["--maxfail", str(args.maxfail)])
        
        result = self._run_command(cmd, "unit_tests")
        return result.returncode == 0
    
    def run_integration_tests(self, args: argparse.Namespace) -> bool:
        """Run integration tests."""
        print("🔧 Running integration tests...")
        
        # Check for required services
        if not self._check_services():
            print("❌ Required services not available for integration tests")
            return False
        
        cmd = [
            sys.executable, "-m", "pytest", 
            str(self.test_dir / "integration"),
            "-v" if args.verbose else "--tb=short"
        ]
        
        if args.coverage:
            cmd.extend(["--cov=src", "--cov-append"])
        
        if args.fast:
            cmd.extend(["-m", "not slow"])
        
        if args.maxfail:
            cmd.extend(["--maxfail", str(args.maxfail)])
        
        result = self._run_command(cmd, "integration_tests")
        return result.returncode == 0
    
    def run_e2e_tests(self, args: argparse.Namespace) -> bool:
        """Run end-to-end tests."""
        print("🎯 Running end-to-end tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "e2e"),
            "-v" if args.verbose else "--tb=short"
        ]
        
        if args.fast:
            cmd.extend(["-m", "not slow"])
        
        if args.maxfail:
            cmd.extend(["--maxfail", str(args.maxfail)])
        
        result = self._run_command(cmd, "e2e_tests")
        return result.returncode == 0
    
    def run_performance_tests(self, args: argparse.Namespace) -> bool:
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "performance"),
            "--benchmark-json=benchmark-results.json",
            "-v" if args.verbose else "--tb=short"
        ]
        
        if args.fast:
            cmd.extend(["-m", "performance and not slow"])
        else:
            cmd.extend(["-m", "performance"])
        
        result = self._run_command(cmd, "performance_tests")
        
        # Process benchmark results
        if result.returncode == 0:
            self._process_benchmark_results()
        
        return result.returncode == 0
    
    def run_coverage_analysis(self, args: argparse.Namespace) -> bool:
        """Run comprehensive coverage analysis."""
        print("📊 Running coverage analysis...")
        
        cmd = [
            sys.executable, "-m", "pytest",
            str(self.test_dir / "unit"),
            str(self.test_dir / "integration"),
            "--cov=src",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=json:coverage.json",
            "--cov-report=term-missing",
            "--cov-config=.coveragerc",
            "--cov-fail-under=80",
            "-v" if args.verbose else "--tb=short"
        ]
        
        if args.parallel:
            cmd.extend(["-n", "auto"])
        
        result = self._run_command(cmd, "coverage_analysis")
        
        if result.returncode == 0:
            self._generate_coverage_report()
        
        return result.returncode == 0
    
    def run_all_tests(self, args: argparse.Namespace) -> bool:
        """Run all test suites."""
        print("🚀 Running complete test suite...")
        
        test_suites = [
            ("Unit Tests", self.run_unit_tests),
            ("Integration Tests", self.run_integration_tests),
            ("End-to-End Tests", self.run_e2e_tests)
        ]
        
        if not args.fast:
            test_suites.append(("Performance Tests", self.run_performance_tests))
        
        results = {}
        for suite_name, test_func in test_suites:
            print(f"\n{'='*50}")
            print(f"Running {suite_name}")
            print('='*50)
            
            success = test_func(args)
            results[suite_name] = success
            
            if not success and args.stop_on_failure:
                print(f"❌ Stopping due to {suite_name} failure")
                break
        
        # Summary
        print(f"\n{'='*50}")
        print("Test Suite Summary")
        print('='*50)
        
        all_passed = True
        for suite_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{suite_name:20} {status}")
            if not success:
                all_passed = False
        
        print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        
        return all_passed
    
    def _run_command(self, cmd: List[str], test_type: str) -> subprocess.CompletedProcess:
        """Run command and capture results."""
        print(f"Executing: {' '.join(cmd)}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
                env={**os.environ, "PYTHONPATH": str(self.project_root)}
            )
        except Exception as e:
            print(f"❌ Error executing command: {e}")
            result = subprocess.CompletedProcess(cmd, 1, "", str(e))
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        self.results[test_type] = {
            "success": result.returncode == 0,
            "execution_time": execution_time,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
        if result.returncode == 0:
            print(f"✅ {test_type} completed successfully ({execution_time:.2f}s)")
        else:
            print(f"❌ {test_type} failed ({execution_time:.2f}s)")
            if result.stderr:
                print(f"Error output:\n{result.stderr}")
        
        return result
    
    def _check_services(self) -> bool:
        """Check if required services are available for integration tests."""
        services = {
            "PostgreSQL": ("psql", "--version"),
            "Redis": ("redis-cli", "ping")
        }
        
        all_available = True
        for service_name, (cmd, arg) in services.items():
            try:
                result = subprocess.run(
                    [cmd, arg], 
                    capture_output=True, 
                    timeout=5
                )
                if result.returncode == 0:
                    print(f"✅ {service_name} available")
                else:
                    print(f"⚠️ {service_name} not responding")
                    all_available = False
            except (FileNotFoundError, subprocess.TimeoutExpired):
                print(f"❌ {service_name} not found")
                all_available = False
        
        return all_available
    
    def _process_benchmark_results(self):
        """Process benchmark results from performance tests."""
        benchmark_file = "benchmark-results.json"
        if os.path.exists(benchmark_file):
            try:
                with open(benchmark_file, 'r') as f:
                    data = json.load(f)
                
                print("\n📈 Performance Benchmark Results:")
                print("-" * 40)
                
                for benchmark in data.get('benchmarks', []):
                    name = benchmark['name']
                    stats = benchmark['stats']
                    
                    print(f"Test: {name}")
                    print(f"  Mean: {stats['mean']:.4f}s")
                    print(f"  Min:  {stats['min']:.4f}s")
                    print(f"  Max:  {stats['max']:.4f}s")
                    print(f"  Std:  {stats['stddev']:.4f}s")
                    print()
                
            except Exception as e:
                print(f"⚠️ Could not process benchmark results: {e}")
    
    def _generate_coverage_report(self):
        """Generate coverage report."""
        coverage_file = "coverage.json"
        if os.path.exists(coverage_file):
            try:
                with open(coverage_file, 'r') as f:
                    coverage_data = json.load(f)
                
                total_coverage = coverage_data.get('totals', {}).get('percent_covered', 0)
                
                print(f"\n📊 Coverage Report:")
                print("-" * 40)
                print(f"Overall Coverage: {total_coverage:.1f}%")
                
                if total_coverage >= 90:
                    print("🟢 Excellent coverage!")
                elif total_coverage >= 80:
                    print("🟡 Good coverage")
                elif total_coverage >= 70:
                    print("🟠 Coverage needs improvement")
                else:
                    print("🔴 Coverage critically low")
                
                print(f"HTML Report: {self.project_root}/htmlcov/index.html")
                
            except Exception as e:
                print(f"⚠️ Could not process coverage data: {e}")
    
    def generate_final_report(self):
        """Generate final test execution report."""
        if not self.results:
            return
        
        print(f"\n{'='*60}")
        print("FINAL TEST EXECUTION REPORT")
        print('='*60)
        print(f"Total execution time: {self.total_time:.2f}s")
        print()
        
        for test_type, result in self.results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            time_taken = result["execution_time"]
            print(f"{test_type:20} {status:10} ({time_taken:.2f}s)")
        
        # Overall success rate
        successful_tests = sum(1 for r in self.results.values() if r["success"])
        total_tests = len(self.results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\nSuccess Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
        
        # Save detailed results
        results_file = "test-results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "execution_time": self.total_time,
                "success_rate": success_rate,
                "results": self.results
            }, f, indent=2)
        
        print(f"Detailed results saved to: {results_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MARTA Platform Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --unit --coverage
  python run_tests.py --integration --verbose
  python run_tests.py --all --parallel
  python run_tests.py --performance --fast
        """
    )
    
    # Test selection
    test_group = parser.add_argument_group('Test Selection')
    test_group.add_argument('--unit', action='store_true', help='Run unit tests')
    test_group.add_argument('--integration', action='store_true', help='Run integration tests')
    test_group.add_argument('--e2e', action='store_true', help='Run end-to-end tests')
    test_group.add_argument('--performance', action='store_true', help='Run performance tests')
    test_group.add_argument('--coverage', action='store_true', help='Run coverage analysis')
    test_group.add_argument('--all', action='store_true', help='Run all test suites')
    
    # Test options
    options_group = parser.add_argument_group('Test Options')
    options_group.add_argument('--fast', action='store_true', help='Skip slow tests')
    options_group.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    options_group.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    options_group.add_argument('--maxfail', type=int, help='Stop after N failures')
    options_group.add_argument('--stop-on-failure', action='store_true', help='Stop test suite on first failure')
    
    args = parser.parse_args()
    
    # Default to unit tests if no specific test type selected
    if not any([args.unit, args.integration, args.e2e, args.performance, args.coverage, args.all]):
        args.unit = True
    
    # Initialize test runner
    runner = TestRunner()
    runner.start_time = time.time()
    
    try:
        success = False
        
        if args.all:
            success = runner.run_all_tests(args)
        else:
            # Run individual test suites
            results = []
            
            if args.unit:
                results.append(runner.run_unit_tests(args))
            
            if args.integration:
                results.append(runner.run_integration_tests(args))
            
            if args.e2e:
                results.append(runner.run_e2e_tests(args))
            
            if args.performance:
                results.append(runner.run_performance_tests(args))
            
            if args.coverage:
                results.append(runner.run_coverage_analysis(args))
            
            success = all(results) if results else False
        
        runner.total_time = time.time() - runner.start_time
        runner.generate_final_report()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️ Test execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()