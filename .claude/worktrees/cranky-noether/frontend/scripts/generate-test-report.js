#!/usr/bin/env node

/**
 * Comprehensive Test Report Generator
 * Aggregates results from multiple test sources and generates detailed reports
 */

import fs from 'fs';
import path from 'path';

const RESULTS_DIR = '/Users/rahulmehta/Desktop/MARTA/frontend/test-results';
const REPORTS_DIR = '/Users/rahulmehta/Desktop/MARTA/frontend/reports';

class TestReportGenerator {
  constructor() {
    this.reports = {
      timestamp: new Date().toISOString(),
      summary: {
        totalTests: 0,
        passed: 0,
        failed: 0,
        skipped: 0,
        passRate: 0,
        coverage: null
      },
      categories: {
        unit: { tests: [], summary: { total: 0, passed: 0, failed: 0 } },
        integration: { tests: [], summary: { total: 0, passed: 0, failed: 0 } },
        e2e: { tests: [], summary: { total: 0, passed: 0, failed: 0 } },
        deployed: { tests: [], summary: { total: 0, passed: 0, failed: 0 } }
      },
      performance: {
        loadTime: null,
        renderTime: null,
        bundleSize: null
      },
      accessibility: {
        violations: [],
        warnings: [],
        score: null
      },
      recommendations: []
    };
  }

  async generateReport() {
    console.log('📊 Generating Comprehensive Test Report...');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');

    await this.ensureDirectories();
    await this.loadTestResults();
    await this.analyzeCoverage();
    await this.generateRecommendations();
    await this.createReports();

    this.printSummary();
  }

  async ensureDirectories() {
    try {
      await fs.promises.mkdir(RESULTS_DIR, { recursive: true });
      await fs.promises.mkdir(REPORTS_DIR, { recursive: true });
      console.log('📁 Report directories ready');
    } catch (error) {
      console.error('Failed to create directories:', error.message);
    }
  }

  async loadTestResults() {
    console.log('🔍 Loading test results...');

    // Load deployed app test results
    await this.loadDeployedResults();
    
    // Load Jest results (if available)
    await this.loadJestResults();
    
    // Load Playwright results (if available)  
    await this.loadPlaywrightResults();
    
    this.calculateSummary();
  }

  async loadDeployedResults() {
    const deployedResultsPath = path.join(RESULTS_DIR, 'simple-test-report.json');
    
    try {
      const data = await fs.promises.readFile(deployedResultsPath, 'utf8');
      const results = JSON.parse(data);
      
      this.reports.categories.deployed.tests = results.tests || [];
      this.reports.categories.deployed.summary = results.summary || { total: 0, passed: 0, failed: 0 };
      
      console.log(`  ✅ Loaded deployed app results: ${results.summary.total} tests`);
    } catch (error) {
      console.log('  ⚠️  No deployed app results found');
    }
  }

  async loadJestResults() {
    const jestResultsPath = path.join(RESULTS_DIR, 'jest-results.json');
    
    try {
      const data = await fs.promises.readFile(jestResultsPath, 'utf8');
      const results = JSON.parse(data);
      
      // Process Jest results
      if (results.testResults) {
        results.testResults.forEach(testFile => {
          const category = this.categorizeTest(testFile.name);
          
          testFile.assertionResults.forEach(test => {
            this.reports.categories[category].tests.push({
              name: test.fullName,
              passed: test.status === 'passed',
              duration: test.duration,
              file: testFile.name
            });
          });
        });
      }
      
      console.log(`  ✅ Loaded Jest results`);
    } catch (error) {
      console.log('  ⚠️  No Jest results found');
    }
  }

  async loadPlaywrightResults() {
    const playwrightResultsPath = path.join(RESULTS_DIR, 'results.json');
    
    try {
      const data = await fs.promises.readFile(playwrightResultsPath, 'utf8');
      const results = JSON.parse(data);
      
      if (results.suites) {
        results.suites.forEach(suite => {
          suite.specs.forEach(spec => {
            spec.tests.forEach(test => {
              this.reports.categories.e2e.tests.push({
                name: test.title,
                passed: test.results.every(r => r.status === 'passed'),
                duration: test.results.reduce((sum, r) => sum + (r.duration || 0), 0),
                browser: test.results[0]?.workerIndex || 'unknown'
              });
            });
          });
        });
      }
      
      console.log(`  ✅ Loaded Playwright results`);
    } catch (error) {
      console.log('  ⚠️  No Playwright results found');
    }
  }

  categorizeTest(testPath) {
    if (testPath.includes('/unit/')) return 'unit';
    if (testPath.includes('/integration/')) return 'integration';
    if (testPath.includes('/e2e/')) return 'e2e';
    return 'unit'; // default
  }

  calculateSummary() {
    let totalTests = 0;
    let totalPassed = 0;
    let totalFailed = 0;

    Object.keys(this.reports.categories).forEach(category => {
      const tests = this.reports.categories[category].tests;
      const summary = this.reports.categories[category].summary;
      
      if (tests.length > 0) {
        summary.total = tests.length;
        summary.passed = tests.filter(t => t.passed).length;
        summary.failed = tests.filter(t => !t.passed).length;
      }
      
      totalTests += summary.total;
      totalPassed += summary.passed;
      totalFailed += summary.failed;
    });

    this.reports.summary.totalTests = totalTests;
    this.reports.summary.passed = totalPassed;
    this.reports.summary.failed = totalFailed;
    this.reports.summary.passRate = totalTests > 0 ? (totalPassed / totalTests * 100) : 0;
  }

  async analyzeCoverage() {
    console.log('📈 Analyzing coverage data...');
    
    const coveragePath = path.join('/Users/rahulmehta/Desktop/MARTA/frontend', 'coverage', 'coverage-summary.json');
    
    try {
      const data = await fs.promises.readFile(coveragePath, 'utf8');
      const coverage = JSON.parse(data);
      
      this.reports.summary.coverage = {
        lines: coverage.total.lines.pct,
        functions: coverage.total.functions.pct,
        branches: coverage.total.branches.pct,
        statements: coverage.total.statements.pct
      };
      
      console.log(`  ✅ Coverage: ${coverage.total.lines.pct}% lines`);
    } catch (error) {
      console.log('  ⚠️  No coverage data found');
    }
  }

  generateRecommendations() {
    console.log('💡 Generating recommendations...');
    
    const recommendations = [];

    // Coverage recommendations
    if (this.reports.summary.coverage) {
      const coverage = this.reports.summary.coverage;
      if (coverage.lines < 70) {
        recommendations.push({
          type: 'coverage',
          priority: 'high',
          message: `Line coverage is ${coverage.lines}%. Recommend adding more unit tests to reach 70%+.`
        });
      }
      if (coverage.branches < 70) {
        recommendations.push({
          type: 'coverage',
          priority: 'medium',
          message: `Branch coverage is ${coverage.branches}%. Add tests for conditional logic and error paths.`
        });
      }
    }

    // Test quality recommendations
    const failureRate = (this.reports.summary.failed / this.reports.summary.totalTests) * 100;
    if (failureRate > 5) {
      recommendations.push({
        type: 'quality',
        priority: 'high',
        message: `${failureRate.toFixed(1)}% test failure rate. Investigate and fix failing tests.`
      });
    }

    // E2E test recommendations
    if (this.reports.categories.e2e.summary.total === 0) {
      recommendations.push({
        type: 'testing',
        priority: 'medium',
        message: 'No E2E tests found. Consider adding Playwright tests for critical user workflows.'
      });
    }

    // Performance recommendations
    const slowTests = [];
    Object.keys(this.reports.categories).forEach(category => {
      const tests = this.reports.categories[category].tests;
      tests.forEach(test => {
        if (test.duration && test.duration > 5000) { // 5 seconds
          slowTests.push(`${test.name}: ${test.duration}ms`);
        }
      });
    });

    if (slowTests.length > 0) {
      recommendations.push({
        type: 'performance',
        priority: 'low',
        message: `Found ${slowTests.length} slow tests. Consider optimizing: ${slowTests.slice(0, 3).join(', ')}`
      });
    }

    this.reports.recommendations = recommendations;
  }

  async createReports() {
    console.log('📝 Creating report files...');
    
    // JSON Report
    const jsonPath = path.join(REPORTS_DIR, 'test-report.json');
    await fs.promises.writeFile(jsonPath, JSON.stringify(this.reports, null, 2));
    
    // HTML Report
    const htmlPath = path.join(REPORTS_DIR, 'test-report.html');
    const htmlContent = this.generateHTMLReport();
    await fs.promises.writeFile(htmlPath, htmlContent);
    
    // Markdown Report
    const mdPath = path.join(REPORTS_DIR, 'test-report.md');
    const markdownContent = this.generateMarkdownReport();
    await fs.promises.writeFile(mdPath, markdownContent);
    
    console.log(`  📄 JSON Report: ${jsonPath}`);
    console.log(`  🌐 HTML Report: ${htmlPath}`);
    console.log(`  📋 Markdown Report: ${mdPath}`);
  }

  generateHTMLReport() {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MARTA Frontend Test Report</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui; margin: 0; padding: 20px; background: #f8f9fa; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 8px 8px 0 0; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; }
        .metric { background: #f8f9fa; border-radius: 8px; padding: 20px; text-align: center; border-left: 4px solid #007bff; }
        .metric.passed { border-left-color: #28a745; }
        .metric.failed { border-left-color: #dc3545; }
        .metric.coverage { border-left-color: #17a2b8; }
        .metric h3 { margin: 0; font-size: 2em; color: #333; }
        .metric p { margin: 10px 0 0 0; color: #666; font-weight: 500; }
        .section { padding: 30px; border-top: 1px solid #eee; }
        .section h2 { color: #333; margin: 0 0 20px 0; }
        .category { margin-bottom: 30px; }
        .category h3 { color: #555; margin: 0 0 15px 0; display: flex; align-items: center; gap: 10px; }
        .badge { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; }
        .badge.passed { background: #d4edda; color: #155724; }
        .badge.failed { background: #f8d7da; color: #721c24; }
        .test-list { background: #f8f9fa; border-radius: 6px; padding: 15px; }
        .test-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
        .test-item:last-child { border-bottom: none; }
        .recommendations { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 6px; padding: 20px; }
        .recommendation { margin: 10px 0; display: flex; align-items: start; gap: 10px; }
        .priority { padding: 2px 6px; border-radius: 4px; font-size: 0.7em; font-weight: bold; text-transform: uppercase; }
        .priority.high { background: #f8d7da; color: #721c24; }
        .priority.medium { background: #fff3cd; color: #856404; }
        .priority.low { background: #d1ecf1; color: #0c5460; }
        .coverage-bars { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }
        .coverage-bar { background: #f8f9fa; border-radius: 6px; padding: 15px; }
        .coverage-bar h4 { margin: 0 0 10px 0; color: #333; }
        .progress { background: #e9ecef; border-radius: 4px; overflow: hidden; height: 8px; }
        .progress-fill { height: 100%; transition: width 0.3s ease; }
        .progress-fill.good { background: #28a745; }
        .progress-fill.warning { background: #ffc107; }
        .progress-fill.danger { background: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚄 MARTA Frontend Test Report</h1>
            <p>Generated on ${new Date(this.reports.timestamp).toLocaleString()}</p>
        </div>

        <div class="summary">
            <div class="metric">
                <h3>${this.reports.summary.totalTests}</h3>
                <p>Total Tests</p>
            </div>
            <div class="metric passed">
                <h3>${this.reports.summary.passed}</h3>
                <p>Passed</p>
            </div>
            <div class="metric failed">
                <h3>${this.reports.summary.failed}</h3>
                <p>Failed</p>
            </div>
            <div class="metric coverage">
                <h3>${this.reports.summary.passRate.toFixed(1)}%</h3>
                <p>Pass Rate</p>
            </div>
        </div>

        ${this.reports.summary.coverage ? `
        <div class="section">
            <h2>📊 Code Coverage</h2>
            <div class="coverage-bars">
                <div class="coverage-bar">
                    <h4>Lines: ${this.reports.summary.coverage.lines}%</h4>
                    <div class="progress">
                        <div class="progress-fill ${this.getCoverageClass(this.reports.summary.coverage.lines)}" 
                             style="width: ${this.reports.summary.coverage.lines}%"></div>
                    </div>
                </div>
                <div class="coverage-bar">
                    <h4>Functions: ${this.reports.summary.coverage.functions}%</h4>
                    <div class="progress">
                        <div class="progress-fill ${this.getCoverageClass(this.reports.summary.coverage.functions)}" 
                             style="width: ${this.reports.summary.coverage.functions}%"></div>
                    </div>
                </div>
                <div class="coverage-bar">
                    <h4>Branches: ${this.reports.summary.coverage.branches}%</h4>
                    <div class="progress">
                        <div class="progress-fill ${this.getCoverageClass(this.reports.summary.coverage.branches)}" 
                             style="width: ${this.reports.summary.coverage.branches}%"></div>
                    </div>
                </div>
                <div class="coverage-bar">
                    <h4>Statements: ${this.reports.summary.coverage.statements}%</h4>
                    <div class="progress">
                        <div class="progress-fill ${this.getCoverageClass(this.reports.summary.coverage.statements)}" 
                             style="width: ${this.reports.summary.coverage.statements}%"></div>
                    </div>
                </div>
            </div>
        </div>
        ` : ''}

        <div class="section">
            <h2>🧪 Test Categories</h2>
            ${Object.entries(this.reports.categories).map(([category, data]) => `
                <div class="category">
                    <h3>
                        ${this.getCategoryIcon(category)} ${this.getCategoryName(category)}
                        <span class="badge ${data.summary.failed > 0 ? 'failed' : 'passed'}">
                            ${data.summary.passed}/${data.summary.total}
                        </span>
                    </h3>
                    ${data.tests.length > 0 ? `
                        <div class="test-list">
                            ${data.tests.slice(0, 10).map(test => `
                                <div class="test-item">
                                    <span>${test.name || test.test}</span>
                                    <span class="badge ${test.passed ? 'passed' : 'failed'}">
                                        ${test.passed ? '✓' : '✗'}
                                    </span>
                                </div>
                            `).join('')}
                            ${data.tests.length > 10 ? `<p>... and ${data.tests.length - 10} more tests</p>` : ''}
                        </div>
                    ` : '<p>No tests found in this category.</p>'}
                </div>
            `).join('')}
        </div>

        ${this.reports.recommendations.length > 0 ? `
        <div class="section">
            <h2>💡 Recommendations</h2>
            <div class="recommendations">
                ${this.reports.recommendations.map(rec => `
                    <div class="recommendation">
                        <span class="priority ${rec.priority}">${rec.priority}</span>
                        <span>${rec.message}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        ` : ''}

        <div class="section">
            <h2>🔧 Configuration</h2>
            <p><strong>Test Framework:</strong> Jest + React Testing Library + Playwright</p>
            <p><strong>Coverage Target:</strong> 70% lines, functions, branches, statements</p>
            <p><strong>Browser Support:</strong> Chrome, Firefox, Safari</p>
            <p><strong>Report Generated:</strong> ${new Date(this.reports.timestamp).toLocaleString()}</p>
        </div>
    </div>
</body>
</html>`;
  }

  generateMarkdownReport() {
    return `# MARTA Frontend Test Report

Generated: ${new Date(this.reports.timestamp).toLocaleString()}

## 📊 Summary

- **Total Tests:** ${this.reports.summary.totalTests}
- **Passed:** ${this.reports.summary.passed}
- **Failed:** ${this.reports.summary.failed}
- **Pass Rate:** ${this.reports.summary.passRate.toFixed(1)}%

${this.reports.summary.coverage ? `
## 📈 Code Coverage

| Metric | Coverage |
|--------|----------|
| Lines | ${this.reports.summary.coverage.lines}% |
| Functions | ${this.reports.summary.coverage.functions}% |
| Branches | ${this.reports.summary.coverage.branches}% |
| Statements | ${this.reports.summary.coverage.statements}% |
` : ''}

## 🧪 Test Categories

${Object.entries(this.reports.categories).map(([category, data]) => `
### ${this.getCategoryName(category)}

- **Total:** ${data.summary.total}
- **Passed:** ${data.summary.passed}
- **Failed:** ${data.summary.failed}
- **Pass Rate:** ${data.summary.total > 0 ? (data.summary.passed / data.summary.total * 100).toFixed(1) : 0}%

${data.tests.length > 0 ? `
#### Recent Test Results

${data.tests.slice(0, 5).map(test => `- ${test.passed ? '✅' : '❌'} ${test.name || test.test}`).join('\n')}
${data.tests.length > 5 ? `\n... and ${data.tests.length - 5} more tests` : ''}
` : 'No tests found in this category.'}
`).join('')}

${this.reports.recommendations.length > 0 ? `
## 💡 Recommendations

${this.reports.recommendations.map(rec => `
### ${rec.priority.toUpperCase()} Priority

${rec.message}
`).join('')}
` : ''}

## 🔧 Test Configuration

- **Framework:** Jest + React Testing Library + Playwright
- **Coverage Target:** 70% across all metrics
- **Browser Support:** Chrome, Firefox, Safari
- **Environment:** Node.js ${process.version}

## 📋 Next Steps

1. Address any failing tests
2. Improve coverage in areas below 70%
3. Add E2E tests for critical workflows
4. Monitor performance of slow tests
5. Implement recommended improvements

---
*Report generated automatically by MARTA test suite*`;
  }

  getCoverageClass(percentage) {
    if (percentage >= 80) return 'good';
    if (percentage >= 60) return 'warning';
    return 'danger';
  }

  getCategoryIcon(category) {
    const icons = {
      unit: '🔧',
      integration: '🔗',
      e2e: '🌐',
      deployed: '🚀'
    };
    return icons[category] || '🧪';
  }

  getCategoryName(category) {
    const names = {
      unit: 'Unit Tests',
      integration: 'Integration Tests',
      e2e: 'End-to-End Tests',
      deployed: 'Deployed App Tests'
    };
    return names[category] || category;
  }

  printSummary() {
    const passRate = this.reports.summary.passRate;
    
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 Test Report Summary:');
    console.log(`   Total Tests: ${this.reports.summary.totalTests}`);
    console.log(`   ✅ Passed: ${this.reports.summary.passed}`);
    console.log(`   ❌ Failed: ${this.reports.summary.failed}`);
    console.log(`   📈 Pass Rate: ${passRate.toFixed(1)}%`);
    
    if (this.reports.summary.coverage) {
      console.log(`   📊 Coverage: ${this.reports.summary.coverage.lines}% lines`);
    }
    
    console.log(`\n🎯 Overall Status: ${passRate >= 90 ? '🌟 EXCELLENT' : passRate >= 80 ? '✅ GOOD' : passRate >= 70 ? '⚠️  FAIR' : '❌ NEEDS WORK'}`);
    
    if (this.reports.recommendations.length > 0) {
      console.log(`💡 Recommendations: ${this.reports.recommendations.length}`);
    }
  }
}

// Main execution
async function main() {
  const generator = new TestReportGenerator();
  
  try {
    await generator.generateReport();
    console.log('\n✨ Report generation complete!');
  } catch (error) {
    console.error('❌ Report generation failed:', error);
    process.exit(1);
  }
}

main();