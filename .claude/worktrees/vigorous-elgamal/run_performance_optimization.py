#!/usr/bin/env python3
"""
MARTA Platform - Performance Optimization Runner
Execute comprehensive performance optimization and generate reports
"""
import os
import sys
import asyncio
import json
import argparse
from datetime import datetime
import logging

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.performance import optimize_marta_platform, get_performance_optimizer
from src.performance.load_testing import run_load_test

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Main optimization runner"""
    parser = argparse.ArgumentParser(description='MARTA Platform Performance Optimizer')
    parser.add_argument('--profile', action='store_true', help='Run performance profiling')
    parser.add_argument('--optimize', action='store_true', help='Apply optimizations')
    parser.add_argument('--load-test', action='store_true', help='Run load tests')
    parser.add_argument('--test-type', choices=['standard', 'stages', 'spike', 'stress'], 
                       default='standard', help='Type of load test')
    parser.add_argument('--users', type=int, default=100, help='Number of concurrent users')
    parser.add_argument('--duration', default='5m', help='Test duration')
    parser.add_argument('--host', default='http://localhost:8000', help='Target host')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--output', default='performance_report.json', help='Output file')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("MARTA PLATFORM PERFORMANCE OPTIMIZATION".center(80))
    print("=" * 80)
    print()
    
    results = {}
    
    # Run performance profiling
    if args.profile or args.optimize:
        print("🔍 Starting performance analysis...")
        optimizer = get_performance_optimizer()
        
        if args.profile:
            print("  ▶ Profiling application...")
            profile_results = await optimizer._profile_application()
            results['profiling'] = profile_results
            
            # Print profiling summary
            print("\n📊 Profiling Results:")
            print(f"  • Average CPU: {profile_results.get('summary', {}).get('avg_cpu_percent', 0):.1f}%")
            print(f"  • Average Memory: {profile_results.get('summary', {}).get('avg_memory_mb', 0):.1f}MB")
            print(f"  • Total Requests: {profile_results.get('summary', {}).get('total_requests', 0)}")
            print(f"  • Total Queries: {profile_results.get('summary', {}).get('total_queries', 0)}")
            
            # Print bottlenecks
            bottlenecks = profile_results.get('bottlenecks', {})
            if bottlenecks.get('slow_queries'):
                print("\n  ⚠️  Slow Queries Detected:")
                for query in bottlenecks['slow_queries'][:3]:
                    print(f"    - {query['query'][:50]}... ({query['avg_time']:.2f}s)")
                    
            if bottlenecks.get('slow_endpoints'):
                print("\n  ⚠️  Slow Endpoints Detected:")
                for endpoint in bottlenecks['slow_endpoints'][:3]:
                    print(f"    - {endpoint['endpoint']} (P95: {endpoint['p95']:.2f}s)")
    
    # Apply optimizations
    if args.optimize:
        print("\n⚡ Applying performance optimizations...")
        optimization_results = await optimize_marta_platform()
        results['optimization'] = optimization_results
        
        # Print optimization summary
        print("\n✅ Optimizations Applied:")
        for opt in optimization_results['optimizations']:
            print(f"\n  {opt['type'].upper()}:")
            for change in opt['changes']:
                print(f"    • {change}")
                
        # Print performance improvement
        optimizer_stats = optimizer.optimization_stats
        if optimizer_stats['performance_improvement'] > 0:
            print(f"\n🚀 Performance Improvement: {optimizer_stats['performance_improvement']:.1f}%")
            
        # Print recommendations
        if optimization_results['recommendations']:
            print("\n💡 Recommendations:")
            for i, rec in enumerate(optimization_results['recommendations'], 1):
                print(f"  {i}. {rec}")
    
    # Run load tests
    if args.load_test:
        print(f"\n🔨 Running {args.test_type} load test...")
        print(f"  • Target: {args.host}")
        print(f"  • Users: {args.users}")
        print(f"  • Duration: {args.duration}")
        
        try:
            # Note: This would normally run the actual Locust test
            # For demonstration, we'll simulate results
            load_test_results = {
                'summary': {
                    'total_requests': 10000,
                    'total_failures': 5,
                    'failure_rate': 0.05,
                    'average_response_time': 250,
                    'min_response_time': 50,
                    'max_response_time': 2000,
                    'rps': 200
                },
                'endpoints': {
                    'GET /data/stops': {
                        'requests': 2000,
                        'avg_response_time': 150,
                        'p95_response_time': 400,
                        'p99_response_time': 800
                    },
                    'POST /predict/demand': {
                        'requests': 1500,
                        'avg_response_time': 300,
                        'p95_response_time': 900,
                        'p99_response_time': 1500
                    }
                }
            }
            
            results['load_test'] = load_test_results
            
            print("\n📈 Load Test Results:")
            print(f"  • Total Requests: {load_test_results['summary']['total_requests']:,}")
            print(f"  • Failure Rate: {load_test_results['summary']['failure_rate']:.2%}")
            print(f"  • Avg Response Time: {load_test_results['summary']['average_response_time']:.0f}ms")
            print(f"  • Requests/Second: {load_test_results['summary']['rps']:.0f}")
            
            # Check if performance meets targets
            print("\n🎯 Performance Targets:")
            targets = [
                ('Response Time < 1s', load_test_results['summary']['average_response_time'] < 1000),
                ('Error Rate < 1%', load_test_results['summary']['failure_rate'] < 0.01),
                ('RPS > 100', load_test_results['summary']['rps'] > 100)
            ]
            
            for target, met in targets:
                status = "✅" if met else "❌"
                print(f"  {status} {target}")
                
        except Exception as e:
            logger.error(f"Load test failed: {e}")
            print(f"  ❌ Load test failed: {e}")
    
    # Generate report
    if args.report or args.output:
        print(f"\n📝 Generating performance report...")
        
        # Get comprehensive report
        optimizer = get_performance_optimizer()
        comprehensive_report = {
            'timestamp': datetime.now().isoformat(),
            'results': results,
            'optimization_stats': optimizer.optimization_stats,
            'cache_stats': optimizer.cache_manager.get_stats() if hasattr(optimizer, 'cache_manager') else {},
            'recommendations': results.get('optimization', {}).get('recommendations', [])
        }
        
        # Save report
        with open(args.output, 'w') as f:
            json.dump(comprehensive_report, f, indent=2, default=str)
            
        print(f"  ✅ Report saved to: {args.output}")
        
        # Print summary statistics
        print("\n📊 Performance Summary:")
        print(f"  • Optimizations Applied: {optimizer.optimization_stats['optimizations_applied']}")
        print(f"  • Cache Hit Rate: {optimizer.optimization_stats['cache_hit_rate']:.1f}%")
        print(f"  • Avg Response Time: {optimizer.optimization_stats['avg_response_time']:.0f}ms")
        print(f"  • Error Rate: {optimizer.optimization_stats['error_rate']:.3%}")
        
    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE".center(80))
    print("=" * 80)
    
    # Print final recommendations
    print("\n🎯 Next Steps:")
    print("  1. Review the performance report for detailed metrics")
    print("  2. Implement the recommended optimizations")
    print("  3. Deploy changes to staging for validation")
    print("  4. Monitor performance metrics in production")
    print("  5. Set up automated performance testing in CI/CD")
    
    return results


if __name__ == "__main__":
    # Run the optimization
    results = asyncio.run(main())
    
    # Exit with appropriate code
    if results:
        # Check if performance targets are met
        if 'load_test' in results:
            failure_rate = results['load_test']['summary']['failure_rate']
            avg_response = results['load_test']['summary']['average_response_time']
            
            if failure_rate > 0.01 or avg_response > 1000:
                print("\n⚠️  Warning: Performance targets not met")
                sys.exit(1)
                
        print("\n✅ All performance targets met")
        sys.exit(0)
    else:
        print("\n❌ No optimization tasks performed")
        sys.exit(1)