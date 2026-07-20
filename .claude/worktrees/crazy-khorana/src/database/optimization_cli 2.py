"""
MARTA Platform - Database Optimization CLI Tool
Command-line interface for database optimization, monitoring, and maintenance
"""
import os
import sys
import click
import json
import time
from typing import Dict, Any
from datetime import datetime
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.connection_pool import get_db_pool, optimize_queries, health_check
from src.database.redis_cache import get_cache_manager, flush_cache
from src.database.monitoring import (
    get_monitoring_manager, start_monitoring, stop_monitoring,
    get_monitoring_dashboard, generate_performance_report
)
from src.database.migration_manager import (
    migrate_database, rollback_database, generate_migration,
    get_migration_status, check_migration_safety
)
from src.database.spatial_queries import get_spatial_optimizer, SpatialPoint

@click.group()
@click.version_option(version='1.0.0')
def cli():
    """MARTA Database Optimization and Management CLI"""
    pass

@cli.group()
def monitoring():
    """Database monitoring commands"""
    pass

@cli.group()
def cache():
    """Cache management commands"""
    pass

@cli.group()
def migration():
    """Database migration commands"""
    pass

@cli.group()
def optimization():
    """Database optimization commands"""
    pass

@cli.group()
def spatial():
    """Spatial query commands"""
    pass

# =============================================
# MONITORING COMMANDS
# =============================================

@monitoring.command('start')
def start_monitoring_cmd():
    """Start database monitoring"""
    try:
        start_monitoring()
        click.echo("✅ Database monitoring started successfully")
    except Exception as e:
        click.echo(f"❌ Failed to start monitoring: {e}", err=True)

@monitoring.command('stop')
def stop_monitoring_cmd():
    """Stop database monitoring"""
    try:
        stop_monitoring()
        click.echo("✅ Database monitoring stopped successfully")
    except Exception as e:
        click.echo(f"❌ Failed to stop monitoring: {e}", err=True)

@monitoring.command('dashboard')
@click.option('--format', type=click.Choice(['table', 'json']), default='table',
              help='Output format')
@click.option('--output', type=click.File('w'), help='Output file')
def monitoring_dashboard(format, output):
    """Show monitoring dashboard"""
    try:
        dashboard_data = get_monitoring_dashboard()
        
        if format == 'json':
            output_text = json.dumps(dashboard_data, indent=2, default=str)
        else:
            output_text = format_dashboard_table(dashboard_data)
        
        if output:
            output.write(output_text)
        else:
            click.echo(output_text)
            
    except Exception as e:
        click.echo(f"❌ Failed to get dashboard: {e}", err=True)

@monitoring.command('report')
@click.option('--output', type=click.File('w'), help='Output file')
def monitoring_report(output):
    """Generate performance report"""
    try:
        report = generate_performance_report()
        
        if output:
            output.write(report)
        else:
            click.echo(report)
            
    except Exception as e:
        click.echo(f"❌ Failed to generate report: {e}", err=True)

@monitoring.command('health')
def health_check_cmd():
    """Perform database health check"""
    try:
        health = health_check()
        
        status_icon = "✅" if health['status'] == 'healthy' else "❌"
        click.echo(f"{status_icon} Database Status: {health['status']}")
        click.echo(f"Response Time: {health.get('response_time_ms', 0):.2f}ms")
        
        if 'connection_stats' in health:
            stats = health['connection_stats']
            click.echo(f"Active Connections: {stats.get('active_connections', 0)}")
            click.echo(f"Pool Size: {stats.get('pool_size', 0)}")
            click.echo(f"Query Count: {stats.get('query_count', 0)}")
            
    except Exception as e:
        click.echo(f"❌ Health check failed: {e}", err=True)

# =============================================
# CACHE COMMANDS
# =============================================

@cache.command('status')
def cache_status():
    """Show cache status"""
    try:
        cache_manager = get_cache_manager()
        cache_info = cache_manager.get_cache_info()
        
        click.echo("🔄 Redis Cache Status")
        click.echo(f"Status: {cache_info.get('status', 'unknown')}")
        
        if cache_info.get('status') == 'connected':
            click.echo(f"Redis Version: {cache_info.get('redis_version', 'unknown')}")
            click.echo(f"Used Memory: {cache_info.get('used_memory', 'unknown')}")
            click.echo(f"Connected Clients: {cache_info.get('connected_clients', 0)}")
            click.echo(f"Hit Rate: {cache_info.get('hit_rate', 0):.2f}%")
            
            if 'client_metrics' in cache_info:
                metrics = cache_info['client_metrics']
                click.echo(f"Client Hit Rate: {metrics.get('hit_rate', 0):.2f}%")
                click.echo(f"Total Operations: {metrics.get('total_operations', 0)}")
                
    except Exception as e:
        click.echo(f"❌ Failed to get cache status: {e}", err=True)

@cache.command('flush')
@click.option('--pattern', help='Pattern to match for selective flush')
@click.confirmation_option(prompt='Are you sure you want to flush cache?')
def cache_flush(pattern):
    """Flush cache data"""
    try:
        success = flush_cache(pattern)
        if success:
            pattern_msg = f" (pattern: {pattern})" if pattern else ""
            click.echo(f"✅ Cache flushed successfully{pattern_msg}")
        else:
            click.echo("❌ Failed to flush cache", err=True)
            
    except Exception as e:
        click.echo(f"❌ Cache flush failed: {e}", err=True)

@cache.command('metrics')
def cache_metrics():
    """Show cache performance metrics"""
    try:
        cache_manager = get_cache_manager()
        metrics = cache_manager.get_metrics()
        
        click.echo("📊 Cache Performance Metrics")
        click.echo(f"Hit Rate: {metrics.get('hit_rate', 0):.2f}%")
        click.echo(f"Hits: {metrics.get('hits', 0)}")
        click.echo(f"Misses: {metrics.get('misses', 0)}")
        click.echo(f"Operations/sec: {metrics.get('operations_per_second', 0):.2f}")
        click.echo(f"Avg Operation Time: {metrics.get('avg_operation_time', 0):.3f}s")
        click.echo(f"Uptime: {metrics.get('uptime_seconds', 0):.0f}s")
        
    except Exception as e:
        click.echo(f"❌ Failed to get cache metrics: {e}", err=True)

# =============================================
# MIGRATION COMMANDS
# =============================================

@migration.command('status')
def migration_status():
    """Show migration status"""
    try:
        status = get_migration_status()
        
        click.echo("🔄 Migration Status")
        click.echo(f"Current Revision: {status.get('current_revision', 'None')}")
        click.echo(f"Head Revision: {status.get('head_revision', 'None')}")
        click.echo(f"Up to Date: {'✅' if status.get('is_up_to_date') else '❌'}")
        click.echo(f"Pending Migrations: {status.get('pending_migrations_count', 0)}")
        
        if status.get('pending_migrations'):
            click.echo("\nPending Migrations:")
            for migration in status['pending_migrations']:
                click.echo(f"  - {migration['revision']}: {migration['description']}")
                
    except Exception as e:
        click.echo(f"❌ Failed to get migration status: {e}", err=True)

@migration.command('upgrade')
@click.option('--revision', help='Target revision (default: latest)')
@click.option('--no-backup', is_flag=True, help='Skip backup creation')
@click.option('--no-safety-check', is_flag=True, help='Skip safety checks')
def migration_upgrade(revision, no_backup, no_safety_check):
    """Run database migrations"""
    try:
        result = migrate_database(
            revision=revision,
            create_backup=not no_backup,
            safety_check=not no_safety_check
        )
        
        if result['success']:
            click.echo("✅ Migration completed successfully")
            if result.get('backup_file'):
                click.echo(f"Backup created: {result['backup_file']}")
            click.echo(f"Applied {len(result.get('applied_migrations', []))} migrations")
        else:
            click.echo("❌ Migration failed", err=True)
            for error in result.get('errors', []):
                click.echo(f"Error: {error}", err=True)
                
        for warning in result.get('warnings', []):
            click.echo(f"Warning: {warning}")
            
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}", err=True)

@migration.command('downgrade')
@click.argument('revision')
@click.option('--no-backup', is_flag=True, help='Skip backup creation')
@click.confirmation_option(prompt='Are you sure you want to downgrade?')
def migration_downgrade(revision, no_backup):
    """Downgrade to specific revision"""
    try:
        result = rollback_database(revision, create_backup=not no_backup)
        
        if result['success']:
            click.echo("✅ Downgrade completed successfully")
            if result.get('backup_file'):
                click.echo(f"Backup created: {result['backup_file']}")
        else:
            click.echo("❌ Downgrade failed", err=True)
            for error in result.get('errors', []):
                click.echo(f"Error: {error}", err=True)
                
    except Exception as e:
        click.echo(f"❌ Downgrade failed: {e}", err=True)

@migration.command('generate')
@click.argument('message')
@click.option('--no-autogenerate', is_flag=True, help='Disable autogenerate')
def migration_generate(message, no_autogenerate):
    """Generate new migration"""
    try:
        result = generate_migration(message, autogenerate=not no_autogenerate)
        
        if result['success']:
            click.echo("✅ Migration generated successfully")
            click.echo(f"Revision ID: {result['revision_id']}")
            click.echo(f"Migration File: {result['migration_file']}")
        else:
            click.echo("❌ Migration generation failed", err=True)
            for error in result.get('errors', []):
                click.echo(f"Error: {error}", err=True)
                
    except Exception as e:
        click.echo(f"❌ Migration generation failed: {e}", err=True)

@migration.command('safety-check')
@click.option('--revision', help='Target revision to check')
def migration_safety_check(revision):
    """Perform migration safety check"""
    try:
        safety_report = check_migration_safety(revision)
        
        status_icon = "✅" if safety_report['safe_to_migrate'] else "❌"
        click.echo(f"{status_icon} Safe to Migrate: {safety_report['safe_to_migrate']}")
        
        if safety_report.get('warnings'):
            click.echo("\n⚠️  Warnings:")
            for warning in safety_report['warnings']:
                click.echo(f"  - {warning}")
        
        if safety_report.get('errors'):
            click.echo("\n❌ Errors:")
            for error in safety_report['errors']:
                click.echo(f"  - {error}")
                
        if safety_report.get('recommendations'):
            click.echo("\n💡 Recommendations:")
            for rec in safety_report['recommendations']:
                click.echo(f"  - {rec}")
                
    except Exception as e:
        click.echo(f"❌ Safety check failed: {e}", err=True)

# =============================================
# OPTIMIZATION COMMANDS
# =============================================

@optimization.command('analyze-queries')
@click.option('--limit', default=20, help='Number of queries to show')
def analyze_queries(limit):
    """Analyze slow queries"""
    try:
        slow_queries = optimize_queries()
        
        if slow_queries.empty:
            click.echo("No query data available")
            return
        
        click.echo("📊 Query Performance Analysis")
        click.echo(f"Showing top {min(limit, len(slow_queries))} queries by total time:")
        
        for i, (_, row) in enumerate(slow_queries.head(limit).iterrows(), 1):
            click.echo(f"\n{i}. Query: {row.get('query', 'N/A')[:80]}...")
            click.echo(f"   Calls: {row.get('calls', 0)}")
            click.echo(f"   Total Time: {row.get('total_time', 0):.2f}ms")
            click.echo(f"   Mean Time: {row.get('mean_time', 0):.2f}ms")
            click.echo(f"   Hit Rate: {row.get('hit_percent', 0):.1f}%")
            
    except Exception as e:
        click.echo(f"❌ Query analysis failed: {e}", err=True)

@optimization.command('create-indexes')
@click.confirmation_option(prompt='Create optimization indexes?')
def create_indexes():
    """Create optimization indexes"""
    try:
        db_pool = get_db_pool()
        # This would call a stored procedure to create indexes
        result = db_pool.execute_query("SELECT create_optimization_indexes()")
        
        click.echo("✅ Optimization indexes created")
        if result:
            click.echo(f"Result: {result[0][0] if result else 'Success'}")
            
    except Exception as e:
        click.echo(f"❌ Index creation failed: {e}", err=True)

@optimization.command('vacuum-analyze')
@click.option('--full', is_flag=True, help='Perform VACUUM FULL')
@click.confirmation_option(prompt='Perform database vacuum and analyze?')
def vacuum_analyze(full):
    """Vacuum and analyze database"""
    try:
        db_pool = get_db_pool()
        
        if full:
            click.echo("Running VACUUM FULL ANALYZE (this may take a while)...")
            db_pool.execute_query("VACUUM FULL ANALYZE")
        else:
            click.echo("Running VACUUM ANALYZE...")
            db_pool.execute_query("VACUUM ANALYZE")
        
        click.echo("✅ Database vacuum and analyze completed")
        
    except Exception as e:
        click.echo(f"❌ Vacuum analyze failed: {e}", err=True)

# =============================================
# SPATIAL COMMANDS
# =============================================

@spatial.command('nearby-stops')
@click.argument('latitude', type=float)
@click.argument('longitude', type=float)
@click.option('--radius', default=800, help='Search radius in meters')
@click.option('--limit', default=10, help='Maximum results')
def nearby_stops(latitude, longitude, radius, limit):
    """Find nearby transit stops"""
    try:
        location = SpatialPoint(latitude=latitude, longitude=longitude)
        spatial_optimizer = get_spatial_optimizer()
        
        stops = spatial_optimizer.find_nearby_stops(
            location, radius_meters=radius, limit=limit
        )
        
        if not stops:
            click.echo("No stops found in the specified area")
            return
        
        click.echo(f"🚏 Found {len(stops)} stops near ({latitude}, {longitude}):")
        
        for i, stop in enumerate(stops, 1):
            click.echo(f"\n{i}. {stop.stop_name} ({stop.stop_id})")
            click.echo(f"   Distance: {stop.distance_meters:.0f}m")
            click.echo(f"   Walking Time: {stop.walking_time_minutes}min")
            if stop.routes_served:
                click.echo(f"   Routes: {', '.join(stop.routes_served)}")
            if stop.avg_daily_ridership:
                click.echo(f"   Avg Ridership: {stop.avg_daily_ridership:.1f}")
                
    except Exception as e:
        click.echo(f"❌ Nearby stops search failed: {e}", err=True)

@spatial.command('route-efficiency')
@click.argument('route_id')
def route_efficiency(route_id):
    """Analyze route efficiency"""
    try:
        spatial_optimizer = get_spatial_optimizer()
        analysis = spatial_optimizer.analyze_route_efficiency(route_id)
        
        if 'error' in analysis:
            click.echo(f"❌ {analysis['error']}", err=True)
            return
        
        click.echo(f"🚌 Route Efficiency Analysis: {analysis['route_name']} ({route_id})")
        click.echo(f"Length: {analysis['total_length_km']:.2f} km")
        click.echo(f"Stops: {analysis['total_stops']}")
        click.echo(f"Avg Stop Spacing: {analysis['avg_stop_spacing_m']:.0f}m")
        click.echo(f"Avg Ridership: {analysis['avg_ridership']:.1f}")
        click.echo(f"Ridership per km: {analysis['ridership_per_km']:.1f}")
        click.echo(f"Avg Delay: {analysis['avg_delay_seconds']:.0f}s")
        click.echo(f"Efficiency Score: {analysis['efficiency_score']:.1f}/100")
        
    except Exception as e:
        click.echo(f"❌ Route efficiency analysis failed: {e}", err=True)

# =============================================
# UTILITY FUNCTIONS
# =============================================

def format_dashboard_table(dashboard_data: Dict[str, Any]) -> str:
    """Format dashboard data as a readable table"""
    output = "🚇 MARTA Database Monitoring Dashboard\n"
    output += "=" * 50 + "\n\n"
    
    # Health Summary
    health = dashboard_data.get('health', {})
    output += f"📊 System Health: {health.get('status', 'unknown')}\n"
    output += f"Avg Buffer Hit Ratio: {health.get('avg_buffer_hit_ratio', 0):.2f}%\n"
    output += f"Avg Connections: {health.get('avg_connection_count', 0):.0f}\n"
    output += f"Max Active Queries: {health.get('max_active_queries', 0)}\n\n"
    
    # Top Queries
    output += "🔝 Top Queries by Total Time:\n"
    for i, query in enumerate(dashboard_data.get('top_queries', [])[:5], 1):
        output += f"{i}. {query.get('query_pattern', 'N/A')}\n"
        output += f"   Total: {query.get('total_time', 0):.2f}s, "
        output += f"Avg: {query.get('avg_time', 0):.3f}s, "
        output += f"Count: {query.get('execution_count', 0)}\n"
    
    # Connection Pool
    conn_stats = dashboard_data.get('connection_stats', {})
    output += f"\n🔗 Connection Pool:\n"
    output += f"Active: {conn_stats.get('active_connections', 0)}, "
    output += f"Pool Size: {conn_stats.get('pool_size', 0)}\n"
    
    # Cache Performance
    cache_stats = dashboard_data.get('cache_stats', {})
    output += f"\n💾 Cache Performance:\n"
    output += f"Hit Rate: {cache_stats.get('hit_rate', 0):.2f}%, "
    output += f"Operations/sec: {cache_stats.get('operations_per_second', 0):.2f}\n"
    
    return output

if __name__ == '__main__':
    cli()