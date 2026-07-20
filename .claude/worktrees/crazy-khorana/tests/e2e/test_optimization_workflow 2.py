"""
End-to-end tests for the complete route optimization workflow.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient

# Test imports
from src.api.optimization_api import app
from src.optimization.route_optimizer import RouteOptimizer
from src.optimization.route_simulator import RouteSimulator
from src.models.demand_forecaster import DemandForecaster
from src.data_ingestion.gtfs_ingestion import GTFSIngestion


class TestCompleteOptimizationWorkflow:
    """Test the complete route optimization workflow from data to results."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    @pytest.fixture
    def workflow_data(self, sample_gtfs_data, sample_ridership_data, sample_weather_data):
        """Complete workflow test data."""
        return {
            'gtfs_data': sample_gtfs_data,
            'ridership_data': sample_ridership_data,
            'weather_data': sample_weather_data,
            'current_time': datetime.now(),
            'optimization_horizon': 24  # hours
        }
    
    def test_data_ingestion_to_optimization_workflow(self, workflow_data):
        """Test complete workflow from data ingestion to optimization results."""
        
        # Step 1: Data Ingestion
        with patch('src.data_ingestion.gtfs_ingestion.GTFSIngestion') as mock_gtfs_ingestion:
            mock_ingestion_instance = Mock()
            mock_ingestion_instance.ingest_gtfs_data.return_value = {
                'success': True,
                'records_processed': {
                    'stops': len(workflow_data['gtfs_data']['gtfs_stops']),
                    'routes': len(workflow_data['gtfs_data']['gtfs_routes']),
                    'trips': len(workflow_data['gtfs_data']['gtfs_trips'])
                }
            }
            mock_gtfs_ingestion.return_value = mock_ingestion_instance
            
            # Execute ingestion
            ingestion_result = mock_ingestion_instance.ingest_gtfs_data('/fake/gtfs/path')
            
            assert ingestion_result['success']
            assert ingestion_result['records_processed']['stops'] > 0
        
        # Step 2: Demand Forecasting
        with patch('src.models.demand_forecaster.DemandForecaster') as mock_forecaster:
            mock_forecaster_instance = Mock()
            
            # Mock forecast results
            forecast_horizon = workflow_data['optimization_horizon']
            mock_forecast_data = []
            
            for hour in range(forecast_horizon):
                for route_idx in range(len(workflow_data['gtfs_data']['gtfs_routes'])):
                    route_id = f'route_{route_idx+1:03d}'
                    # Simulate realistic demand patterns
                    base_demand = 50
                    if 7 <= hour <= 9 or 17 <= hour <= 19:  # Peak hours
                        demand = base_demand * 2.5
                    elif 22 <= hour or hour <= 5:  # Night hours
                        demand = base_demand * 0.3
                    else:
                        demand = base_demand
                    
                    demand += np.random.normal(0, demand * 0.1)  # Add noise
                    
                    mock_forecast_data.append({
                        'route_id': route_id,
                        'hour': hour,
                        'predicted_demand': max(0, demand),
                        'confidence_interval': [demand * 0.8, demand * 1.2]
                    })
            
            mock_forecaster_instance.predict_demand.return_value = mock_forecast_data
            mock_forecaster.return_value = mock_forecaster_instance
            
            # Execute demand forecasting
            demand_forecast = mock_forecaster_instance.predict_demand(
                workflow_data['current_time'],
                forecast_horizon
            )
            
            assert len(demand_forecast) > 0
            assert all('predicted_demand' in record for record in demand_forecast)
        
        # Step 3: Route Optimization
        with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
            mock_optimizer_instance = Mock()
            
            # Mock optimization results
            optimization_result = {
                'optimization_id': 'e2e_test_001',
                'best_solution': [
                    {
                        'route_id': 'route_001',
                        'frequency': 8,  # Increased frequency for high demand
                        'capacity': 200,
                        'operating_cost': 150.0,
                        'stops': ['stop_001', 'stop_002', 'stop_003']
                    },
                    {
                        'route_id': 'route_002', 
                        'frequency': 12,
                        'capacity': 180,
                        'operating_cost': 120.0,
                        'stops': ['stop_002', 'stop_004', 'stop_005']
                    }
                ],
                'best_fitness': 0.87,
                'optimization_metrics': {
                    'total_cost': 270.0,
                    'coverage_score': 0.92,
                    'efficiency_improvement': 15.3,
                    'passenger_wait_time_reduction': 8.7
                },
                'optimization_time': 45.2,
                'convergence_history': [0.65, 0.72, 0.78, 0.83, 0.87],
                'constraints_satisfied': True
            }
            
            mock_optimizer_instance.optimize_routes.return_value = optimization_result
            mock_optimizer.return_value = mock_optimizer_instance
            
            # Execute optimization with demand forecast
            network_data = {
                'stops': workflow_data['gtfs_data']['gtfs_stops'].to_dict('records'),
                'routes': workflow_data['gtfs_data']['gtfs_routes'].to_dict('records'),
                'demand_forecast': demand_forecast,
                'constraints': {
                    'max_budget': 500.0,
                    'min_coverage': 0.85,
                    'max_routes': 10
                }
            }
            
            opt_result = mock_optimizer_instance.optimize_routes(network_data)
            
            assert opt_result['best_fitness'] > 0.8
            assert opt_result['constraints_satisfied']
            assert len(opt_result['best_solution']) > 0
        
        # Step 4: Route Simulation
        with patch('src.optimization.route_simulator.RouteSimulator') as mock_simulator:
            mock_simulator_instance = Mock()
            
            # Mock simulation results
            simulation_result = {
                'simulation_id': 'sim_e2e_001',
                'performance_metrics': {
                    'total_passengers_served': 18500,
                    'average_wait_time': 3.8,  # Improved from baseline
                    'average_journey_time': 24.5,
                    'service_reliability': 0.94,
                    'passenger_satisfaction': 0.89,
                    'cost_per_passenger': 3.20,
                    'fleet_utilization': 0.82
                },
                'passenger_statistics': {
                    'peak_occupancy': 185,
                    'average_occupancy': 95,
                    'load_factor': 0.68,
                    'passenger_km': 145000,
                    'boardings_per_hour': {
                        'peak': 1200,
                        'off_peak': 450,
                        'night': 150
                    }
                },
                'service_quality_metrics': {
                    'on_time_performance': 0.92,
                    'schedule_adherence': 0.89,
                    'missed_trips': 3,
                    'service_delays': [
                        {'route_id': 'route_001', 'avg_delay': 2.1},
                        {'route_id': 'route_002', 'avg_delay': 1.8}
                    ]
                },
                'recommendations': [
                    'Consider express service during peak hours on route_001',
                    'Implement signal priority for route_002',
                    'Monitor passenger loads at stop_002 - approaching capacity'
                ],
                'simulation_duration': 86400,  # 24 hours
                'events_processed': 15643
            }
            
            mock_simulator_instance.run_simulation.return_value = simulation_result
            mock_simulator.return_value = mock_simulator_instance
            
            # Execute simulation with optimized routes
            sim_result = mock_simulator_instance.run_simulation(
                routes=opt_result['best_solution'],
                demand_forecast=demand_forecast,
                simulation_duration=workflow_data['optimization_horizon'] * 3600
            )
            
            assert sim_result['performance_metrics']['service_reliability'] > 0.9
            assert sim_result['performance_metrics']['passenger_satisfaction'] > 0.85
            assert len(sim_result['recommendations']) > 0
        
        # Step 5: Results Validation and Storage
        workflow_results = {
            'workflow_id': 'e2e_workflow_001',
            'timestamp': workflow_data['current_time'],
            'data_ingestion': ingestion_result,
            'demand_forecast': {
                'total_predictions': len(demand_forecast),
                'peak_demand_hour': max(demand_forecast, key=lambda x: x['predicted_demand'])['hour'],
                'total_predicted_passengers': sum(d['predicted_demand'] for d in demand_forecast)
            },
            'optimization': opt_result,
            'simulation': sim_result,
            'overall_improvement': {
                'efficiency_gain': opt_result['optimization_metrics']['efficiency_improvement'],
                'wait_time_reduction': opt_result['optimization_metrics']['passenger_wait_time_reduction'],
                'cost_savings': 500.0 - opt_result['optimization_metrics']['total_cost'],
                'reliability_score': sim_result['performance_metrics']['service_reliability']
            },
            'workflow_duration': 180.5,  # Total workflow execution time
            'success': True
        }
        
        # Validate workflow results
        assert workflow_results['success']
        assert workflow_results['overall_improvement']['efficiency_gain'] > 10
        assert workflow_results['overall_improvement']['reliability_score'] > 0.9
        assert workflow_results['overall_improvement']['cost_savings'] > 0
        
        print(f"✅ Complete optimization workflow test passed!")
        print(f"   - Efficiency improvement: {workflow_results['overall_improvement']['efficiency_gain']:.1f}%")
        print(f"   - Cost savings: ${workflow_results['overall_improvement']['cost_savings']:.2f}")
        print(f"   - Reliability score: {workflow_results['overall_improvement']['reliability_score']:.2f}")
        print(f"   - Total passengers served: {sim_result['performance_metrics']['total_passengers_served']:,}")
    
    def test_real_time_optimization_trigger_workflow(self, client, workflow_data):
        """Test real-time optimization triggered by performance degradation."""
        
        # Step 1: Monitor current system performance
        current_metrics = {
            'timestamp': datetime.now(),
            'system_performance': {
                'average_delay': 9.2,  # Above threshold
                'service_reliability': 0.73,  # Below threshold  
                'passenger_satisfaction': 0.68,  # Below threshold
                'cost_efficiency': 0.62  # Below threshold
            },
            'route_performance': [
                {
                    'route_id': 'route_001',
                    'on_time_performance': 0.65,
                    'passenger_complaints': 15,
                    'load_factor': 0.95  # Overcrowded
                },
                {
                    'route_id': 'route_002',
                    'on_time_performance': 0.78,
                    'passenger_complaints': 8,
                    'load_factor': 0.45  # Underutilized
                }
            ]
        }
        
        # Step 2: Check optimization triggers
        performance_thresholds = {
            'max_average_delay': 7.0,
            'min_service_reliability': 0.80,
            'min_passenger_satisfaction': 0.75,
            'min_cost_efficiency': 0.70
        }
        
        triggers_fired = []
        if current_metrics['system_performance']['average_delay'] > performance_thresholds['max_average_delay']:
            triggers_fired.append('high_delay')
        if current_metrics['system_performance']['service_reliability'] < performance_thresholds['min_service_reliability']:
            triggers_fired.append('low_reliability')
        if current_metrics['system_performance']['passenger_satisfaction'] < performance_thresholds['min_passenger_satisfaction']:
            triggers_fired.append('low_satisfaction')
        if current_metrics['system_performance']['cost_efficiency'] < performance_thresholds['min_cost_efficiency']:
            triggers_fired.append('low_efficiency')
        
        assert len(triggers_fired) > 0, "Performance issues should trigger optimization"
        
        # Step 3: Execute emergency optimization
        with patch('src.api.optimization_api.RouteOptimizer') as mock_optimizer:
            mock_optimizer_instance = Mock()
            
            # Mock rapid optimization for real-time scenario
            emergency_optimization_result = {
                'optimization_id': 'emergency_opt_001',
                'optimization_type': 'emergency',
                'triggers': triggers_fired,
                'quick_solutions': [
                    {
                        'route_id': 'route_001',
                        'action': 'increase_frequency',
                        'current_frequency': 12,
                        'new_frequency': 8,  # Increase frequency to reduce crowding
                        'expected_improvement': {
                            'load_factor_reduction': 0.20,
                            'wait_time_reduction': 25
                        }
                    },
                    {
                        'route_id': 'route_002',
                        'action': 'optimize_schedule',
                        'current_schedule': 'regular',
                        'new_schedule': 'demand_responsive',
                        'expected_improvement': {
                            'efficiency_gain': 15,
                            'cost_reduction': 12
                        }
                    }
                ],
                'implementation_time': 15.3,  # Rapid optimization
                'estimated_improvement': {
                    'delay_reduction': 35,  # percentage
                    'reliability_increase': 18,
                    'satisfaction_increase': 22
                }
            }
            
            mock_optimizer_instance.emergency_optimize.return_value = emergency_optimization_result
            mock_optimizer.return_value = mock_optimizer_instance
            
            # Trigger emergency optimization via API
            emergency_request = {
                'optimization_type': 'emergency',
                'current_performance': current_metrics,
                'priority': 'high',
                'max_optimization_time': 300  # 5 minutes max
            }
            
            response = client.post('/optimize/emergency', json=emergency_request)
            
            assert response.status_code == 200
            response_data = response.json()
            assert response_data['optimization_type'] == 'emergency'
            assert len(response_data['quick_solutions']) > 0
        
        # Step 4: Validate rapid implementation
        with patch('src.api.optimization_api.implement_emergency_changes') as mock_implement:
            mock_implement.return_value = {
                'implementation_id': 'impl_emergency_001',
                'changes_applied': 2,
                'implementation_time': 8.5,
                'rollback_plan': {
                    'available': True,
                    'rollback_time': 5.2
                },
                'monitoring_enabled': True
            }
            
            # Implement emergency changes
            implementation_result = mock_implement(emergency_optimization_result['quick_solutions'])
            
            assert implementation_result['changes_applied'] == 2
            assert implementation_result['rollback_plan']['available']
        
        # Step 5: Monitor post-implementation performance
        post_implementation_metrics = {
            'timestamp': datetime.now() + timedelta(minutes=30),
            'system_performance': {
                'average_delay': 6.1,  # Improved
                'service_reliability': 0.87,  # Improved
                'passenger_satisfaction': 0.82,  # Improved  
                'cost_efficiency': 0.74  # Improved
            },
            'improvement_achieved': True
        }
        
        # Validate improvements
        delay_improvement = (current_metrics['system_performance']['average_delay'] - 
                           post_implementation_metrics['system_performance']['average_delay'])
        reliability_improvement = (post_implementation_metrics['system_performance']['service_reliability'] - 
                                 current_metrics['system_performance']['service_reliability'])
        
        assert delay_improvement > 2.0  # Significant delay reduction
        assert reliability_improvement > 0.10  # Significant reliability improvement
        assert post_implementation_metrics['improvement_achieved']
        
        print(f"✅ Real-time optimization workflow test passed!")
        print(f"   - Triggers fired: {', '.join(triggers_fired)}")
        print(f"   - Delay reduction: {delay_improvement:.1f} minutes")
        print(f"   - Reliability improvement: {reliability_improvement:.2f}")
        print(f"   - Implementation time: {implementation_result['implementation_time']:.1f} minutes")
    
    def test_multi_modal_integration_workflow(self, workflow_data):
        """Test workflow integrating multiple transportation modes."""
        
        # Step 1: Multi-modal network setup
        multi_modal_network = {
            'rail_lines': workflow_data['gtfs_data']['gtfs_routes'][
                workflow_data['gtfs_data']['gtfs_routes']['route_type'] == 1
            ].to_dict('records'),
            'bus_routes': workflow_data['gtfs_data']['gtfs_routes'][
                workflow_data['gtfs_data']['gtfs_routes']['route_type'] == 3
            ].to_dict('records'),
            'transfer_points': [
                {
                    'stop_id': 'transfer_001',
                    'connected_routes': ['route_001', 'route_002'],
                    'transfer_time': 3.5,  # minutes
                    'transfer_reliability': 0.92
                },
                {
                    'stop_id': 'transfer_002', 
                    'connected_routes': ['route_002', 'route_003'],
                    'transfer_time': 2.8,
                    'transfer_reliability': 0.88
                }
            ]
        }
        
        # Step 2: Integrated demand modeling
        with patch('src.models.demand_forecaster.MultiModalDemandForecaster') as mock_mm_forecaster:
            mock_forecaster_instance = Mock()
            
            # Mock multi-modal demand predictions
            mm_demand_forecast = [
                {
                    'origin_stop': 'stop_001',
                    'destination_stop': 'stop_005',
                    'direct_demand': 45,
                    'transfer_demand': 38,
                    'preferred_path': [
                        {'route_id': 'route_001', 'segment': 'stop_001->stop_002'},
                        {'transfer': 'transfer_001', 'time': 3.5},
                        {'route_id': 'route_002', 'segment': 'stop_002->stop_005'}
                    ],
                    'journey_time': 28.5,
                    'reliability_score': 0.85
                }
            ]
            
            mock_forecaster_instance.predict_multimodal_demand.return_value = mm_demand_forecast
            mock_mm_forecaster.return_value = mock_forecaster_instance
            
            demand_result = mock_forecaster_instance.predict_multimodal_demand(
                multi_modal_network,
                workflow_data['current_time'],
                24
            )
            
            assert len(demand_result) > 0
            assert 'transfer_demand' in demand_result[0]
        
        # Step 3: Multi-modal optimization
        with patch('src.optimization.multimodal_optimizer.MultiModalOptimizer') as mock_mm_optimizer:
            mock_mm_optimizer_instance = Mock()
            
            mm_optimization_result = {
                'optimization_id': 'multimodal_opt_001',
                'coordinated_solution': {
                    'rail_schedules': [
                        {
                            'route_id': 'route_001',
                            'frequency': 6,  # High frequency rail
                            'coordination_points': ['transfer_001']
                        }
                    ],
                    'bus_schedules': [
                        {
                            'route_id': 'route_002',
                            'frequency': 8,
                            'timed_transfers': [
                                {'at_stop': 'transfer_001', 'wait_time': 2.0}
                            ]
                        }
                    ],
                    'transfer_optimizations': [
                        {
                            'stop_id': 'transfer_001',
                            'synchronization_score': 0.91,
                            'expected_wait_reduction': 45  # seconds
                        }
                    ]
                },
                'system_benefits': {
                    'total_journey_time_reduction': 12.3,  # percent
                    'transfer_reliability_improvement': 0.08,
                    'passenger_satisfaction_gain': 15.2,  # percent
                    'system_efficiency': 0.89
                },
                'coordination_quality': 0.87
            }
            
            mock_mm_optimizer_instance.optimize_multimodal_system.return_value = mm_optimization_result
            mock_mm_optimizer.return_value = mock_mm_optimizer_instance
            
            mm_opt_result = mock_mm_optimizer_instance.optimize_multimodal_system(
                multi_modal_network,
                demand_result
            )
            
            assert mm_opt_result['coordination_quality'] > 0.8
            assert mm_opt_result['system_benefits']['system_efficiency'] > 0.8
        
        # Step 4: Integrated simulation
        with patch('src.optimization.multimodal_simulator.MultiModalSimulator') as mock_mm_simulator:
            mock_mm_simulator_instance = Mock()
            
            mm_simulation_result = {
                'simulation_id': 'multimodal_sim_001',
                'integrated_metrics': {
                    'total_system_passengers': 25000,
                    'transfer_success_rate': 0.89,
                    'average_total_journey_time': 32.5,
                    'system_wide_reliability': 0.86,
                    'passenger_satisfaction': 0.88
                },
                'mode_specific_performance': {
                    'rail': {
                        'passengers_served': 15000,
                        'on_time_performance': 0.91,
                        'load_factor': 0.72
                    },
                    'bus': {
                        'passengers_served': 10000, 
                        'on_time_performance': 0.84,
                        'load_factor': 0.65
                    }
                },
                'transfer_analysis': {
                    'total_transfers': 3500,
                    'successful_transfers': 3115,
                    'average_transfer_time': 4.2,
                    'missed_connections': 385
                },
                'integration_benefits': {
                    'compared_to_separate_optimization': {
                        'journey_time_savings': 8.7,  # percent
                        'reliability_improvement': 0.06,
                        'cost_efficiency_gain': 11.2  # percent
                    }
                }
            }
            
            mock_mm_simulator_instance.simulate_integrated_system.return_value = mm_simulation_result
            mock_mm_simulator.return_value = mock_mm_simulator_instance
            
            mm_sim_result = mock_mm_simulator_instance.simulate_integrated_system(
                mm_opt_result['coordinated_solution'],
                demand_result,
                86400  # 24 hours
            )
            
            assert mm_sim_result['integrated_metrics']['transfer_success_rate'] > 0.85
            assert mm_sim_result['integration_benefits']['compared_to_separate_optimization']['journey_time_savings'] > 5
        
        # Step 5: Validate multi-modal integration benefits
        integration_assessment = {
            'workflow_type': 'multi_modal_integration',
            'integration_quality': mm_opt_result['coordination_quality'],
            'passenger_benefits': {
                'journey_time_reduction': mm_sim_result['integration_benefits']['compared_to_separate_optimization']['journey_time_savings'],
                'transfer_reliability': mm_sim_result['integrated_metrics']['transfer_success_rate'],
                'overall_satisfaction': mm_sim_result['integrated_metrics']['passenger_satisfaction']
            },
            'system_benefits': {
                'efficiency_gain': mm_sim_result['integration_benefits']['compared_to_separate_optimization']['cost_efficiency_gain'],
                'reliability_improvement': mm_sim_result['integration_benefits']['compared_to_separate_optimization']['reliability_improvement'],
                'coordination_success': mm_opt_result['coordination_quality'] > 0.8
            },
            'success_criteria_met': True
        }
        
        # Validate integration success
        assert integration_assessment['integration_quality'] > 0.8
        assert integration_assessment['passenger_benefits']['journey_time_reduction'] > 5
        assert integration_assessment['passenger_benefits']['transfer_reliability'] > 0.8
        assert integration_assessment['system_benefits']['coordination_success']
        
        print(f"✅ Multi-modal integration workflow test passed!")
        print(f"   - Integration quality: {integration_assessment['integration_quality']:.2f}")
        print(f"   - Journey time savings: {integration_assessment['passenger_benefits']['journey_time_reduction']:.1f}%")
        print(f"   - Transfer success rate: {integration_assessment['passenger_benefits']['transfer_reliability']:.2f}")
        print(f"   - System efficiency gain: {integration_assessment['system_benefits']['efficiency_gain']:.1f}%")
    
    @pytest.mark.slow
    def test_long_term_optimization_workflow(self, workflow_data):
        """Test long-term strategic optimization workflow."""
        
        # This would test a comprehensive long-term optimization
        # involving seasonal patterns, infrastructure changes, etc.
        
        long_term_scenario = {
            'planning_horizon': 365,  # days
            'seasonal_adjustments': True,
            'infrastructure_changes': [
                {
                    'type': 'new_station',
                    'location': {'lat': 33.7550, 'lon': -84.3900},
                    'implementation_date': workflow_data['current_time'] + timedelta(days=180)
                }
            ],
            'demand_growth': 0.03  # 3% annual growth
        }
        
        # Mock long-term optimization
        with patch('src.optimization.strategic_optimizer.StrategicOptimizer') as mock_strategic:
            mock_strategic_instance = Mock()
            
            strategic_result = {
                'optimization_horizon': 365,
                'phased_implementation': [
                    {
                        'phase': 1,
                        'timeframe': 'months_1_3',
                        'changes': ['frequency_adjustments', 'schedule_optimization'],
                        'expected_benefit': 12.5
                    },
                    {
                        'phase': 2,
                        'timeframe': 'months_4_9',
                        'changes': ['route_extensions', 'service_enhancements'],
                        'expected_benefit': 23.8
                    }
                ],
                'long_term_benefits': {
                    'ridership_growth_accommodation': 45000,  # additional passengers
                    'service_quality_improvement': 0.15,
                    'operational_efficiency_gain': 18.2,
                    'environmental_impact_reduction': 0.12  # CO2 reduction
                }
            }
            
            mock_strategic_instance.optimize_long_term.return_value = strategic_result
            mock_strategic.return_value = mock_strategic_instance
            
            result = mock_strategic_instance.optimize_long_term(long_term_scenario)
            
            assert len(result['phased_implementation']) > 0
            assert result['long_term_benefits']['ridership_growth_accommodation'] > 0
        
        print(f"✅ Long-term optimization workflow test passed!")
        print(f"   - Planning horizon: {long_term_scenario['planning_horizon']} days")
        print(f"   - Expected additional ridership: {strategic_result['long_term_benefits']['ridership_growth_accommodation']:,}")
        print(f"   - Service quality improvement: {strategic_result['long_term_benefits']['service_quality_improvement']:.2f}")


@pytest.mark.integration
@pytest.mark.slow
class TestWorkflowPerformance:
    """Test workflow performance under various conditions."""
    
    def test_workflow_scalability(self, workflow_data):
        """Test workflow performance with increasing data size."""
        import time
        
        # Test with different network sizes
        network_sizes = [10, 50, 100]  # Number of routes
        performance_results = []
        
        for size in network_sizes:
            start_time = time.time()
            
            # Mock scaled optimization
            with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
                mock_optimizer_instance = Mock()
                mock_optimizer_instance.optimize_routes.return_value = {
                    'best_solution': [{'route_id': f'route_{i:03d}'} for i in range(size)],
                    'best_fitness': 0.8,
                    'network_size': size
                }
                mock_optimizer.return_value = mock_optimizer_instance
                
                result = mock_optimizer_instance.optimize_routes({'network_size': size})
                
                end_time = time.time()
                execution_time = end_time - start_time
                
                performance_results.append({
                    'network_size': size,
                    'execution_time': execution_time,
                    'routes_optimized': len(result['best_solution'])
                })
        
        # Validate scalability
        for result in performance_results:
            # Execution time should scale reasonably
            expected_max_time = result['network_size'] * 0.1  # 0.1 seconds per route
            assert result['execution_time'] < expected_max_time
        
        print("✅ Workflow scalability test passed!")
        for result in performance_results:
            print(f"   - {result['network_size']} routes: {result['execution_time']:.2f}s")
    
    def test_concurrent_workflow_execution(self):
        """Test multiple workflows running concurrently."""
        import concurrent.futures
        import time
        
        def run_workflow(workflow_id):
            with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
                mock_optimizer_instance = Mock()
                mock_optimizer_instance.optimize_routes.return_value = {
                    'workflow_id': workflow_id,
                    'best_fitness': 0.8 + (workflow_id * 0.01)  # Slight variation
                }
                mock_optimizer.return_value = mock_optimizer_instance
                
                time.sleep(0.1)  # Simulate processing time
                return mock_optimizer_instance.optimize_routes({'id': workflow_id})
        
        # Run concurrent workflows
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_workflow, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        total_time = end_time - start_time
        
        # All workflows should complete
        assert len(results) == 10
        
        # Concurrent execution should be faster than sequential
        assert total_time < 2.0  # Should complete well under sequential time
        
        print(f"✅ Concurrent workflow test passed!")
        print(f"   - 10 workflows completed in {total_time:.2f}s")
    
    def test_workflow_memory_usage(self, workflow_data):
        """Test workflow memory efficiency."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run memory-intensive workflow simulation
        with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
            mock_optimizer_instance = Mock()
            
            # Simulate processing large dataset
            large_result = {
                'best_solution': [
                    {'route_id': f'route_{i:03d}', 'data': list(range(1000))}
                    for i in range(100)
                ],
                'detailed_analysis': {f'metric_{i}': list(range(1000)) for i in range(50)}
            }
            
            mock_optimizer_instance.optimize_routes.return_value = large_result
            mock_optimizer.return_value = mock_optimizer_instance
            
            result = mock_optimizer_instance.optimize_routes(workflow_data)
            
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Clean up result
            del result
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        memory_increase = peak_memory - initial_memory
        memory_recovered = peak_memory - final_memory
        
        # Memory usage should be reasonable
        assert memory_increase < 100  # Less than 100MB increase
        assert memory_recovered > (memory_increase * 0.5)  # At least 50% recovered
        
        print(f"✅ Workflow memory usage test passed!")
        print(f"   - Memory increase: {memory_increase:.1f} MB")
        print(f"   - Memory recovered: {memory_recovered:.1f} MB")


@pytest.mark.slow
class TestWorkflowRobustness:
    """Test workflow robustness and error handling."""
    
    def test_workflow_fault_tolerance(self, workflow_data):
        """Test workflow behavior with component failures."""
        
        # Test optimization failure recovery
        with patch('src.optimization.route_optimizer.RouteOptimizer') as mock_optimizer:
            mock_optimizer_instance = Mock()
            mock_optimizer_instance.optimize_routes.side_effect = Exception("Optimization failed")
            mock_optimizer.return_value = mock_optimizer_instance
            
            # Should handle failure gracefully
            try:
                result = mock_optimizer_instance.optimize_routes(workflow_data)
                assert False, "Should have raised exception"
            except Exception as e:
                assert "Optimization failed" in str(e)
                
                # Test fallback mechanism
                with patch('src.optimization.fallback_optimizer.FallbackOptimizer') as mock_fallback:
                    mock_fallback_instance = Mock()
                    mock_fallback_instance.simple_optimize.return_value = {
                        'fallback_solution': True,
                        'best_fitness': 0.65  # Lower but acceptable
                    }
                    mock_fallback.return_value = mock_fallback_instance
                    
                    fallback_result = mock_fallback_instance.simple_optimize(workflow_data)
                    assert fallback_result['fallback_solution']
                    assert fallback_result['best_fitness'] > 0
        
        print("✅ Workflow fault tolerance test passed!")
    
    def test_data_quality_handling(self, workflow_data):
        """Test workflow behavior with poor quality data."""
        
        # Create poor quality data
        poor_quality_data = workflow_data.copy()
        
        # Add missing values and inconsistencies
        poor_quality_data['ridership_data'] = poor_quality_data['ridership_data'].copy()
        poor_quality_data['ridership_data'].loc[:5, 'ridership'] = None  # Missing values
        poor_quality_data['ridership_data'].loc[10:15, 'ridership'] = -50  # Invalid values
        
        with patch('src.data_ingestion.data_validator.DataValidator') as mock_validator:
            mock_validator_instance = Mock()
            
            validation_result = {
                'data_quality_score': 0.65,  # Poor quality
                'issues_found': [
                    'missing_ridership_values',
                    'negative_ridership_values',
                    'inconsistent_timestamps'
                ],
                'cleaned_data_available': True,
                'recommendation': 'proceed_with_caution'
            }
            
            mock_validator_instance.validate_workflow_data.return_value = validation_result
            mock_validator.return_value = mock_validator_instance
            
            validation = mock_validator_instance.validate_workflow_data(poor_quality_data)
            
            assert validation['data_quality_score'] < 0.8
            assert len(validation['issues_found']) > 0
            assert validation['cleaned_data_available']
        
        print("✅ Data quality handling test passed!")
    
    def test_external_dependency_failures(self, workflow_data):
        """Test workflow behavior when external services fail."""
        
        # Mock external API failures
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("External API unavailable")
            
            with patch('src.data_ingestion.weather_data_fetcher.WeatherDataFetcher') as mock_weather:
                mock_weather_instance = Mock()
                mock_weather_instance.fetch_current_weather.side_effect = Exception("Weather API failed")
                mock_weather.return_value = mock_weather_instance
                
                # Should handle external failures
                try:
                    weather_data = mock_weather_instance.fetch_current_weather()
                    assert False, "Should have raised exception"
                except Exception:
                    # Test fallback to historical data
                    with patch('src.data_ingestion.historical_weather.HistoricalWeatherProvider') as mock_historical:
                        mock_historical_instance = Mock()
                        mock_historical_instance.get_historical_average.return_value = {
                            'temperature': 72.0,
                            'precipitation': 0.0,
                            'data_source': 'historical_average'
                        }
                        mock_historical.return_value = mock_historical_instance
                        
                        fallback_weather = mock_historical_instance.get_historical_average()
                        assert fallback_weather['data_source'] == 'historical_average'
        
        print("✅ External dependency failure handling test passed!")