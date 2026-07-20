"""
Coverage helper utilities and analysis tools.
"""
import json
import os
from typing import Dict, List, Tuple
from pathlib import Path
import subprocess
import sys


class CoverageAnalyzer:
    """Analyze and report on test coverage metrics."""
    
    def __init__(self, coverage_file: str = "coverage.json"):
        self.coverage_file = coverage_file
        self.coverage_data = None
        self.load_coverage_data()
    
    def load_coverage_data(self):
        """Load coverage data from JSON file."""
        if os.path.exists(self.coverage_file):
            with open(self.coverage_file, 'r') as f:
                self.coverage_data = json.load(f)
        else:
            print(f"Coverage file {self.coverage_file} not found")
    
    def get_overall_coverage(self) -> float:
        """Get overall coverage percentage."""
        if not self.coverage_data:
            return 0.0
        
        return self.coverage_data.get('totals', {}).get('percent_covered', 0.0)
    
    def get_module_coverage(self) -> Dict[str, Dict]:
        """Get coverage breakdown by module."""
        if not self.coverage_data:
            return {}
        
        module_coverage = {}
        files = self.coverage_data.get('files', {})
        
        for file_path, file_data in files.items():
            if file_path.startswith('src/'):
                # Extract module name from path
                path_parts = file_path.split('/')
                if len(path_parts) >= 2:
                    module = path_parts[1]
                else:
                    module = 'root'
                
                if module not in module_coverage:
                    module_coverage[module] = {
                        'files': 0,
                        'total_lines': 0,
                        'covered_lines': 0,
                        'missing_lines': 0,
                        'percent_covered': 0.0
                    }
                
                summary = file_data.get('summary', {})
                module_coverage[module]['files'] += 1
                module_coverage[module]['total_lines'] += summary.get('num_statements', 0)
                module_coverage[module]['covered_lines'] += summary.get('covered_lines', 0)
                module_coverage[module]['missing_lines'] += summary.get('missing_lines', 0)
        
        # Calculate percentages
        for module, stats in module_coverage.items():
            if stats['total_lines'] > 0:
                stats['percent_covered'] = (stats['covered_lines'] / stats['total_lines']) * 100
        
        return module_coverage
    
    def get_low_coverage_files(self, threshold: float = 80.0) -> List[Tuple[str, float]]:
        """Get files with coverage below threshold."""
        if not self.coverage_data:
            return []
        
        low_coverage = []
        files = self.coverage_data.get('files', {})
        
        for file_path, file_data in files.items():
            if file_path.startswith('src/'):
                coverage = file_data.get('summary', {}).get('percent_covered', 0.0)
                if coverage < threshold:
                    low_coverage.append((file_path, coverage))
        
        return sorted(low_coverage, key=lambda x: x[1])
    
    def get_untested_files(self) -> List[str]:
        """Get files with 0% coverage."""
        if not self.coverage_data:
            return []
        
        untested = []
        files = self.coverage_data.get('files', {})
        
        for file_path, file_data in files.items():
            if file_path.startswith('src/'):
                coverage = file_data.get('summary', {}).get('percent_covered', 0.0)
                if coverage == 0.0:
                    untested.append(file_path)
        
        return sorted(untested)
    
    def generate_coverage_report(self) -> str:
        """Generate a comprehensive coverage report."""
        if not self.coverage_data:
            return "No coverage data available"
        
        report = []
        report.append("# Coverage Analysis Report")
        report.append("")
        
        # Overall coverage
        overall = self.get_overall_coverage()
        report.append(f"## Overall Coverage: {overall:.1f}%")
        report.append("")
        
        # Coverage status
        if overall >= 90:
            status = "🟢 Excellent"
        elif overall >= 80:
            status = "🟡 Good"
        elif overall >= 70:
            status = "🟠 Needs Improvement"
        else:
            status = "🔴 Critical"
        
        report.append(f"**Status:** {status}")
        report.append("")
        
        # Module breakdown
        module_coverage = self.get_module_coverage()
        report.append("## Coverage by Module")
        report.append("")
        report.append("| Module | Files | Coverage | Lines | Missing |")
        report.append("|--------|-------|----------|-------|---------|")
        
        for module, stats in sorted(module_coverage.items()):
            coverage_pct = stats['percent_covered']
            coverage_icon = self._get_coverage_icon(coverage_pct)
            report.append(f"| {module} | {stats['files']} | {coverage_icon} {coverage_pct:.1f}% | "
                         f"{stats['total_lines']} | {stats['missing_lines']} |")
        
        report.append("")
        
        # Low coverage files
        low_coverage = self.get_low_coverage_files()
        if low_coverage:
            report.append("## Files Needing Attention (< 80% coverage)")
            report.append("")
            report.append("| File | Coverage |")
            report.append("|------|----------|")
            
            for file_path, coverage in low_coverage[:10]:  # Top 10
                coverage_icon = self._get_coverage_icon(coverage)
                report.append(f"| {file_path} | {coverage_icon} {coverage:.1f}% |")
            
            if len(low_coverage) > 10:
                report.append(f"| ... and {len(low_coverage) - 10} more files | |")
            
            report.append("")
        
        # Untested files
        untested = self.get_untested_files()
        if untested:
            report.append("## Untested Files (0% coverage)")
            report.append("")
            for file_path in untested[:5]:  # Top 5
                report.append(f"- {file_path}")
            
            if len(untested) > 5:
                report.append(f"- ... and {len(untested) - 5} more files")
            
            report.append("")
        
        # Recommendations
        report.append("## Recommendations")
        report.append("")
        
        if overall < 80:
            report.append("- 🎯 **Priority:** Increase overall coverage to 80%")
        
        if low_coverage:
            report.append(f"- 📝 Focus on {len(low_coverage)} files with low coverage")
        
        if untested:
            report.append(f"- ⚠️ Add tests for {len(untested)} untested files")
        
        critical_modules = [m for m, s in module_coverage.items() if s['percent_covered'] < 70]
        if critical_modules:
            report.append(f"- 🚨 Critical: {', '.join(critical_modules)} modules need immediate attention")
        
        return "\n".join(report)
    
    def _get_coverage_icon(self, coverage: float) -> str:
        """Get emoji icon for coverage percentage."""
        if coverage >= 90:
            return "🟢"
        elif coverage >= 80:
            return "🟡"
        elif coverage >= 70:
            return "🟠"
        elif coverage > 0:
            return "🔴"
        else:
            return "⚫"
    
    def check_coverage_thresholds(self, thresholds: Dict[str, float] = None) -> bool:
        """Check if coverage meets specified thresholds."""
        if thresholds is None:
            thresholds = {
                'overall': 80.0,
                'models': 85.0,
                'optimization': 80.0,
                'data_ingestion': 75.0,
                'api': 70.0,
                'database': 80.0,
                'visualization': 65.0
            }
        
        # Check overall threshold
        overall = self.get_overall_coverage()
        if overall < thresholds.get('overall', 80.0):
            print(f"❌ Overall coverage {overall:.1f}% below {thresholds['overall']:.1f}% threshold")
            return False
        
        # Check module thresholds
        module_coverage = self.get_module_coverage()
        failed_modules = []
        
        for module, stats in module_coverage.items():
            threshold = thresholds.get(module, 70.0)  # Default 70%
            coverage = stats['percent_covered']
            
            if coverage < threshold:
                failed_modules.append(f"{module}: {coverage:.1f}% < {threshold:.1f}%")
                print(f"❌ Module {module} coverage {coverage:.1f}% below {threshold:.1f}% threshold")
        
        if failed_modules:
            return False
        
        print(f"✅ All coverage thresholds met! Overall: {overall:.1f}%")
        return True


def run_coverage_analysis():
    """Run comprehensive coverage analysis."""
    print("🔍 Running coverage analysis...")
    
    # Run tests with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/", "tests/integration/",
        "--cov=src",
        "--cov-report=json",
        "--cov-report=html",
        "--cov-report=term",
        "--cov-config=.coveragerc",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        print("📊 Test execution completed")
        
        if result.returncode != 0:
            print("⚠️ Some tests failed, but analyzing coverage anyway...")
            print(result.stderr)
        
    except subprocess.TimeoutExpired:
        print("⏰ Test execution timed out")
        return False
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False
    
    # Analyze coverage
    analyzer = CoverageAnalyzer()
    
    # Generate report
    report = analyzer.generate_coverage_report()
    print("\n" + report)
    
    # Save report to file
    with open('coverage-analysis-report.md', 'w') as f:
        f.write(report)
    
    # Check thresholds
    meets_thresholds = analyzer.check_coverage_thresholds()
    
    return meets_thresholds


def generate_coverage_badge(coverage_percentage: float) -> str:
    """Generate coverage badge URL."""
    if coverage_percentage >= 90:
        color = "brightgreen"
    elif coverage_percentage >= 80:
        color = "green"
    elif coverage_percentage >= 70:
        color = "yellow"
    elif coverage_percentage >= 60:
        color = "orange"
    else:
        color = "red"
    
    return f"https://img.shields.io/badge/coverage-{coverage_percentage:.1f}%25-{color}"


if __name__ == "__main__":
    success = run_coverage_analysis()
    sys.exit(0 if success else 1)