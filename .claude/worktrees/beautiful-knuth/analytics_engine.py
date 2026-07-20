"""
MARTA Analytics Engine
Calculates performance metrics, identifies patterns, and generates insights
"""
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
from scipy import stats
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MARTAAnalyticsEngine:
    """Advanced analytics engine for MARTA transit data"""
    
    def __init__(self):
        """Initialize analytics engine with Supabase connection"""
        load_dotenv('.env.supabase')
        
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')
        
        if not url or not key:
            raise ValueError("Missing Supabase credentials")
        
        self.supabase: Client = create_client(url, key)
        logger.info("Analytics Engine initialized")
    
    def calculate_performance_metrics(self, hours_back: int = 24) -> Dict:
        """
        Calculate comprehensive performance metrics for all stations
        
        Args:
            hours_back: Number of hours to analyze
        
        Returns:
            Dictionary of performance metrics by station and line
        """
        logger.info(f"Calculating performance metrics for last {hours_back} hours")
        
        # Fetch recent arrival data
        since = (datetime.now() - timedelta(hours=hours_back)).isoformat()
        
        try:
            result = self.supabase.table('arrivals')\
                .select('*')\
                .gte('collected_at', since)\
                .execute()
            
            if not result.data:
                logger.warning("No arrival data found")
                return {}
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(result.data)
            
            # Calculate metrics by station and line
            metrics = {}
            
            for (station, line), group in df.groupby(['station_id', 'line']):
                station_metrics = self._calculate_station_metrics(group)
                metrics[f"{station}_{line}"] = station_metrics
            
            # Store metrics in database
            self._store_performance_metrics(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return {}
    
    def _calculate_station_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate detailed metrics for a specific station/line combination"""
        
        # Basic counts
        total_arrivals = len(df)
        
        # Delay analysis
        delays = df['delay_seconds'].fillna(0).astype(float)
        on_time = (delays <= 60).sum()  # Within 1 minute is on-time
        delayed = (delays > 60).sum()
        
        # Statistical metrics
        metrics = {
            'total_arrivals': total_arrivals,
            'on_time_arrivals': int(on_time),
            'delayed_arrivals': int(delayed),
            'on_time_percentage': round((on_time / total_arrivals * 100) if total_arrivals > 0 else 0, 2),
            'avg_delay_seconds': round(float(delays.mean()), 2),
            'max_delay_seconds': int(delays.max()) if not delays.empty else 0,
            'min_delay_seconds': int(delays.min()) if not delays.empty else 0,
            'median_delay_seconds': round(float(delays.median()), 2),
            'std_dev_delay': round(float(delays.std()), 2),
        }
        
        # Calculate reliability score (custom metric)
        reliability_factors = [
            metrics['on_time_percentage'] / 100,  # On-time weight: 40%
            min(1.0, 60 / (metrics['avg_delay_seconds'] + 1)),  # Delay weight: 30%
            min(1.0, total_arrivals / 20),  # Frequency weight: 20%
            1.0 - (metrics['std_dev_delay'] / 300)  # Consistency weight: 10%
        ]
        weights = [0.4, 0.3, 0.2, 0.1]
        reliability_score = sum(f * w for f, w in zip(reliability_factors, weights)) * 100
        metrics['reliability_score'] = round(min(100, max(0, reliability_score)), 2)
        
        # Calculate headway (time between trains)
        if 'collected_at' in df.columns and len(df) > 1:
            df_sorted = df.sort_values('collected_at')
            timestamps = pd.to_datetime(df_sorted['collected_at'])
            headways = timestamps.diff().dt.total_seconds().dropna()
            metrics['avg_headway_seconds'] = round(float(headways.mean()), 2) if not headways.empty else 0
        else:
            metrics['avg_headway_seconds'] = 0
        
        return metrics
    
    def _store_performance_metrics(self, metrics: Dict):
        """Store calculated metrics in the database"""
        
        records = []
        current_hour = datetime.now().hour
        current_date = datetime.now().date()
        
        for key, metric_data in metrics.items():
            station_id, line = key.rsplit('_', 1)
            
            record = {
                'station_id': station_id,
                'line': line,
                'hour': current_hour,
                'date': current_date.isoformat(),
                **metric_data
            }
            records.append(record)
        
        if records:
            try:
                # Upsert metrics (update if exists, insert if not)
                for record in records:
                    self.supabase.table('performance_metrics').upsert(
                        record,
                        on_conflict='station_id,line,hour,date'
                    ).execute()
                
                logger.info(f"Stored {len(records)} performance metric records")
            except Exception as e:
                logger.error(f"Error storing metrics: {e}")
    
    def identify_delay_patterns(self, days_back: int = 7) -> List[Dict]:
        """
        Identify recurring delay patterns using pattern recognition
        
        Args:
            days_back: Number of days to analyze
        
        Returns:
            List of identified delay patterns
        """
        logger.info(f"Identifying delay patterns for last {days_back} days")
        
        since = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        try:
            # Fetch arrival data with delays
            result = self.supabase.table('arrivals')\
                .select('*')\
                .gte('collected_at', since)\
                .gt('delay_seconds', 300)\
                .execute()  # Focus on delays > 5 minutes
            
            if not result.data:
                logger.info("No significant delays found")
                return []
            
            df = pd.DataFrame(result.data)
            df['collected_at'] = pd.to_datetime(df['collected_at'])
            df['hour'] = df['collected_at'].dt.hour
            df['day_of_week'] = df['collected_at'].dt.dayofweek
            
            patterns = []
            
            # Analyze patterns by line
            for line in df['line'].unique():
                line_df = df[df['line'] == line]
                
                # Cascade pattern detection
                cascade_pattern = self._detect_cascade_pattern(line_df)
                if cascade_pattern:
                    patterns.append(cascade_pattern)
                
                # Time-based pattern detection
                time_patterns = self._detect_time_patterns(line_df)
                patterns.extend(time_patterns)
            
            # Store identified patterns
            self._store_delay_patterns(patterns)
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying patterns: {e}")
            return []
    
    def _detect_cascade_pattern(self, df: pd.DataFrame) -> Optional[Dict]:
        """Detect cascading delay patterns where delays propagate along a line"""
        
        if len(df) < 10:
            return None
        
        # Sort by time and look for sequential delays
        df_sorted = df.sort_values('collected_at')
        
        # Group delays that occur within 30 minutes of each other
        cascade_groups = []
        current_group = []
        
        for idx, row in df_sorted.iterrows():
            if not current_group:
                current_group.append(row)
            else:
                time_diff = (row['collected_at'] - current_group[-1]['collected_at']).total_seconds()
                if time_diff <= 1800:  # Within 30 minutes
                    current_group.append(row)
                else:
                    if len(current_group) >= 3:  # At least 3 stations affected
                        cascade_groups.append(current_group)
                    current_group = [row]
        
        if len(current_group) >= 3:
            cascade_groups.append(current_group)
        
        if not cascade_groups:
            return None
        
        # Analyze the most significant cascade
        largest_cascade = max(cascade_groups, key=len)
        
        affected_stations = [row['station_id'] for row in largest_cascade]
        avg_delay = np.mean([row['delay_seconds'] for row in largest_cascade])
        
        pattern = {
            'pattern_type': 'cascade',
            'line': df['line'].iloc[0],
            'origin_station': affected_stations[0],
            'pattern_signature': {
                'cascade_length': len(affected_stations),
                'propagation_time': (largest_cascade[-1]['collected_at'] - 
                                    largest_cascade[0]['collected_at']).total_seconds()
            },
            'frequency': len(cascade_groups),
            'avg_impact_minutes': round(avg_delay / 60, 2),
            'affected_stations': affected_stations,
            'common_hours': [largest_cascade[0]['collected_at'].hour],
            'common_days': [largest_cascade[0]['collected_at'].dayofweek]
        }
        
        return pattern
    
    def _detect_time_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """Detect patterns that occur at specific times"""
        
        patterns = []
        
        # Group by hour and day of week
        time_groups = df.groupby(['hour', 'day_of_week'])
        
        for (hour, dow), group in time_groups:
            if len(group) >= 3:  # Pattern occurs at least 3 times
                pattern = {
                    'pattern_type': 'temporal',
                    'line': df['line'].iloc[0],
                    'origin_station': None,
                    'pattern_signature': {
                        'hour': int(hour),
                        'day_of_week': int(dow),
                        'occurrence_count': len(group)
                    },
                    'frequency': len(group),
                    'avg_impact_minutes': round(group['delay_seconds'].mean() / 60, 2),
                    'affected_stations': group['station_id'].unique().tolist(),
                    'common_hours': [int(hour)],
                    'common_days': [int(dow)]
                }
                patterns.append(pattern)
        
        return patterns
    
    def _store_delay_patterns(self, patterns: List[Dict]):
        """Store identified delay patterns in the database"""
        
        for pattern in patterns:
            try:
                # Convert pattern signature to JSON string
                pattern['pattern_signature'] = json.dumps(pattern['pattern_signature'])
                pattern['first_observed'] = datetime.now().isoformat()
                pattern['last_observed'] = datetime.now().isoformat()
                
                self.supabase.table('delay_patterns').upsert(
                    pattern,
                    on_conflict='pattern_type,line,pattern_signature'
                ).execute()
                
            except Exception as e:
                logger.error(f"Error storing pattern: {e}")
    
    def calculate_system_health(self) -> Dict:
        """
        Calculate overall system health metrics
        
        Returns:
            Dictionary of system health indicators
        """
        logger.info("Calculating system health metrics")
        
        try:
            # Get current system status
            result = self.supabase.from_('current_system_status_enhanced')\
                .select('*')\
                .execute()
            
            if not result.data or not result.data[0]:
                return {}
            
            status = result.data[0]
            
            # Calculate line-specific health scores
            line_health = {}
            for line in ['RED', 'GOLD', 'BLUE', 'GREEN']:
                line_result = self.supabase.table('arrivals')\
                    .select('delay_seconds')\
                    .eq('line', line)\
                    .gte('collected_at', (datetime.now() - timedelta(hours=1)).isoformat())\
                    .execute()
                
                if line_result.data:
                    delays = [r['delay_seconds'] for r in line_result.data if r['delay_seconds']]
                    if delays:
                        avg_delay = np.mean(delays)
                        # Health score: 100 = no delays, 0 = avg delay > 15 min
                        health = max(0, min(100, 100 - (avg_delay / 900 * 100)))
                    else:
                        health = 100
                else:
                    health = 50  # No data = assume medium health
                
                line_health[f"{line.lower()}_line_health"] = int(health)
            
            # Calculate delay risk score
            recent_delays = status.get('major_delays', 0)
            delay_risk = min(100, recent_delays * 10)  # Each major delay adds 10 to risk
            
            # Calculate congestion forecast (simplified - would use ML in production)
            hour = datetime.now().hour
            if 7 <= hour <= 9 or 17 <= hour <= 19:  # Rush hours
                congestion_forecast = 75
            elif 10 <= hour <= 16:  # Mid-day
                congestion_forecast = 40
            else:  # Off-peak
                congestion_forecast = 20
            
            health_metrics = {
                'metric_time': datetime.now().isoformat(),
                'active_trains': status.get('active_trains', 0),
                'active_stations': status.get('active_stations', 0),
                'total_delays': status.get('recent_arrivals', 0),
                'major_delays': status.get('major_delays', 0),
                'system_on_time_pct': status.get('on_time_pct', 0),
                'avg_delay_seconds': status.get('avg_delay', 0),
                'max_delay_seconds': status.get('max_current_delay', 0),
                **line_health,
                'delay_risk_score': delay_risk,
                'congestion_forecast': congestion_forecast,
                'active_alerts': 0,  # Would be populated from alerts system
                'active_warnings': recent_delays
            }
            
            # Store health metrics
            self.supabase.table('system_health_metrics').insert(health_metrics).execute()
            
            return health_metrics
            
        except Exception as e:
            logger.error(f"Error calculating system health: {e}")
            return {}
    
    def generate_insights(self) -> List[str]:
        """
        Generate actionable insights from analytics
        
        Returns:
            List of insight strings
        """
        insights = []
        
        try:
            # Get recent performance metrics
            result = self.supabase.table('performance_metrics')\
                .select('*')\
                .gte('date', (datetime.now().date() - timedelta(days=1)).isoformat())\
                .execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                
                # Insight 1: Worst performing stations
                worst_stations = df.nsmallest(3, 'on_time_percentage')
                if not worst_stations.empty:
                    worst = worst_stations.iloc[0]
                    insights.append(
                        f"⚠️ {worst['station_id']} on {worst['line']} line has only "
                        f"{worst['on_time_percentage']:.1f}% on-time performance"
                    )
                
                # Insight 2: Best performing stations
                best_stations = df.nlargest(3, 'on_time_percentage')
                if not best_stations.empty:
                    best = best_stations.iloc[0]
                    insights.append(
                        f"✅ {best['station_id']} on {best['line']} line is performing well with "
                        f"{best['on_time_percentage']:.1f}% on-time arrivals"
                    )
                
                # Insight 3: System-wide trends
                avg_on_time = df['on_time_percentage'].mean()
                insights.append(
                    f"📊 System-wide on-time performance: {avg_on_time:.1f}%"
                )
                
                # Insight 4: Peak delay times
                delay_by_hour = df.groupby('hour')['avg_delay_seconds'].mean()
                if not delay_by_hour.empty:
                    worst_hour = delay_by_hour.idxmax()
                    insights.append(
                        f"🕐 Highest delays typically occur at {worst_hour:02d}:00 "
                        f"(avg {delay_by_hour[worst_hour]:.0f} seconds)"
                    )
            
            # Get delay patterns
            pattern_result = self.supabase.table('delay_patterns')\
                .select('*')\
                .gte('last_observed', (datetime.now() - timedelta(days=1)).isoformat())\
                .execute()
            
            if pattern_result.data:
                insights.append(
                    f"🔍 Identified {len(pattern_result.data)} recurring delay patterns in the last 24 hours"
                )
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            insights.append("Unable to generate insights at this time")
        
        return insights


# CLI for testing
if __name__ == "__main__":
    engine = MARTAAnalyticsEngine()
    
    print("🚇 MARTA Analytics Engine")
    print("=" * 50)
    
    # Calculate performance metrics
    print("\n📊 Calculating Performance Metrics...")
    metrics = engine.calculate_performance_metrics(hours_back=24)
    print(f"Calculated metrics for {len(metrics)} station/line combinations")
    
    # Identify delay patterns
    print("\n🔍 Identifying Delay Patterns...")
    patterns = engine.identify_delay_patterns(days_back=7)
    print(f"Found {len(patterns)} delay patterns")
    
    # Calculate system health
    print("\n💚 Calculating System Health...")
    health = engine.calculate_system_health()
    if health:
        print(f"System on-time: {health.get('system_on_time_pct', 0):.1f}%")
        print(f"Delay risk: {health.get('delay_risk_score', 0):.0f}/100")
    
    # Generate insights
    print("\n💡 Insights:")
    insights = engine.generate_insights()
    for insight in insights:
        print(f"  {insight}")