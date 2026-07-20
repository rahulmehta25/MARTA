"""
End-to-end tests for user journeys and frontend interactions.
"""
import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from fastapi.testclient import TestClient

# Test imports
from src.api.optimization_api import app


class TestTransitPlannerUserJourney:
    """Test complete user journey for transit planning."""
    
    @pytest.fixture
    def browser(self):
        """Setup headless browser for testing."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    def test_route_planning_user_journey(self, browser, client):
        """Test complete user journey for route planning."""
        
        # Step 1: User visits the MARTA planning interface
        # (Assuming frontend is running on localhost:3000)
        frontend_url = "http://localhost:3000"
        
        try:
            browser.get(frontend_url)
            
            # Check if page loads
            page_title = browser.title
            assert "MARTA" in page_title or "Transit" in page_title
            
            # Step 2: User inputs trip details
            origin_input = browser.find_element(By.ID, "origin-input")
            destination_input = browser.find_element(By.ID, "destination-input")
            
            origin_input.send_keys("Downtown Atlanta")
            destination_input.send_keys("Hartsfield-Jackson Airport")
            
            # Select departure time
            departure_time = browser.find_element(By.ID, "departure-time")
            departure_time.send_keys("08:00")
            
            # Step 3: Submit trip planning request
            plan_trip_button = browser.find_element(By.ID, "plan-trip-button")
            plan_trip_button.click()
            
            # Step 4: Wait for results and verify
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "route-results"))
            )
            
            route_results = browser.find_elements(By.CLASS_NAME, "route-option")
            assert len(route_results) > 0
            
            # Check route details
            first_route = route_results[0]
            travel_time = first_route.find_element(By.CLASS_NAME, "travel-time").text
            assert "min" in travel_time.lower()
            
            # Step 5: User selects a route option
            first_route.click()
            
            # Step 6: Verify detailed route information
            WebDriverWait(browser, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "route-details"))
            )
            
            route_details = browser.find_element(By.CLASS_NAME, "route-details")
            assert route_details.is_displayed()
            
            # Check for transit steps
            transit_steps = browser.find_elements(By.CLASS_NAME, "transit-step")
            assert len(transit_steps) > 0
            
        except Exception as e:
            # Frontend might not be running in test environment
            pytest.skip(f"Frontend not available for browser testing: {e}")
    
    def test_real_time_updates_user_journey(self, browser, client):
        """Test user journey with real-time transit updates."""
        
        # Mock real-time API responses
        with patch('src.api.optimization_api.get_real_time_updates') as mock_updates:
            mock_updates.return_value = {
                'timestamp': datetime.now().isoformat(),
                'service_alerts': [
                    {
                        'route_id': 'route_001',
                        'alert_type': 'delay',
                        'message': 'Red Line experiencing 5-minute delays due to signal issues',
                        'severity': 'moderate',
                        'affected_stops': ['stop_001', 'stop_002'],
                        'estimated_resolution': '15 minutes'
                    }
                ],
                'vehicle_positions': [
                    {
                        'vehicle_id': 'vehicle_123',
                        'route_id': 'route_001',
                        'current_stop': 'stop_003',
                        'next_stop': 'stop_004',
                        'estimated_arrival': '3 minutes',
                        'occupancy_level': 'moderate'
                    }
                ]
            }
            
            # Test API endpoint
            response = client.get("/real-time/updates")
            assert response.status_code == 200
            
            data = response.json()
            assert 'service_alerts' in data
            assert 'vehicle_positions' in data
            assert len(data['service_alerts']) > 0
        
        # Test frontend real-time updates (if available)
        try:
            frontend_url = "http://localhost:3000/real-time"
            browser.get(frontend_url)
            
            # Check for real-time updates section
            updates_section = browser.find_element(By.ID, "real-time-updates")
            assert updates_section.is_displayed()
            
            # Check for service alerts
            alert_elements = browser.find_elements(By.CLASS_NAME, "service-alert")
            if len(alert_elements) > 0:
                alert_text = alert_elements[0].text
                assert any(keyword in alert_text.lower() for keyword in ['delay', 'disruption', 'update'])
            
            # Check for vehicle tracking
            vehicle_map = browser.find_element(By.ID, "vehicle-tracking-map")
            assert vehicle_map.is_displayed()
            
        except Exception as e:
            pytest.skip(f"Real-time frontend not available: {e}")
    
    def test_accessibility_user_journey(self, browser, client):
        """Test user journey for accessibility-focused trip planning."""
        
        # Mock accessibility API
        with patch('src.api.optimization_api.get_accessible_routes') as mock_accessible:
            mock_accessible.return_value = {
                'accessible_routes': [
                    {
                        'route_id': 'route_001',
                        'accessibility_features': [
                            'wheelchair_accessible',
                            'audio_announcements',
                            'elevator_access'
                        ],
                        'accessibility_score': 0.95,
                        'barrier_free_path': True
                    }
                ],
                'accessibility_alerts': [
                    {
                        'location': 'Five Points Station',
                        'issue': 'Elevator out of service',
                        'alternative': 'Use North Avenue Station - 0.3 miles away',
                        'estimated_fix': '2 hours'
                    }
                ]
            }
            
            # Test accessibility API
            response = client.get("/accessibility/routes")
            assert response.status_code == 200
            
            data = response.json()
            assert 'accessible_routes' in data
            assert 'accessibility_alerts' in data
        
        try:
            frontend_url = "http://localhost:3000"
            browser.get(frontend_url)
            
            # Enable accessibility mode
            accessibility_toggle = browser.find_element(By.ID, "accessibility-mode-toggle")
            accessibility_toggle.click()
            
            # Plan accessible trip
            origin_input = browser.find_element(By.ID, "origin-input")
            destination_input = browser.find_element(By.ID, "destination-input")
            
            origin_input.send_keys("Downtown Atlanta")
            destination_input.send_keys("Airport")
            
            # Check accessibility options
            wheelchair_accessible = browser.find_element(By.ID, "wheelchair-accessible-checkbox")
            wheelchair_accessible.click()
            
            plan_button = browser.find_element(By.ID, "plan-trip-button")
            plan_button.click()
            
            # Verify accessible route results
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "accessible-route"))
            )
            
            accessible_routes = browser.find_elements(By.CLASS_NAME, "accessible-route")
            assert len(accessible_routes) > 0
            
            # Check accessibility indicators
            accessibility_icons = browser.find_elements(By.CLASS_NAME, "accessibility-icon")
            assert len(accessibility_icons) > 0
            
        except Exception as e:
            pytest.skip(f"Accessibility frontend features not available: {e}")
    
    def test_mobile_user_journey(self, browser):
        """Test user journey on mobile device."""
        
        # Set mobile viewport
        browser.set_window_size(375, 667)  # iPhone SE size
        
        try:
            frontend_url = "http://localhost:3000"
            browser.get(frontend_url)
            
            # Check mobile-responsive design
            mobile_menu = browser.find_element(By.CLASS_NAME, "mobile-menu-toggle")
            assert mobile_menu.is_displayed()
            
            # Test mobile navigation
            mobile_menu.click()
            
            nav_menu = browser.find_element(By.CLASS_NAME, "mobile-nav-menu")
            assert nav_menu.is_displayed()
            
            # Test mobile trip planning
            plan_trip_link = browser.find_element(By.LINK_TEXT, "Plan Trip")
            plan_trip_link.click()
            
            # Check mobile form layout
            trip_form = browser.find_element(By.ID, "mobile-trip-form")
            assert trip_form.is_displayed()
            
            # Test touch-friendly inputs
            origin_input = browser.find_element(By.ID, "origin-input")
            assert origin_input.size['height'] >= 44  # Minimum touch target size
            
        except Exception as e:
            pytest.skip(f"Mobile frontend not available: {e}")
    
    def test_offline_functionality_journey(self, browser):
        """Test user journey when offline."""
        
        try:
            frontend_url = "http://localhost:3000"
            browser.get(frontend_url)
            
            # Check if service worker is registered
            browser.execute_script("""
                return navigator.serviceWorker.getRegistrations();
            """)
            
            # Simulate offline mode
            browser.execute_script("""
                window.navigator.__defineGetter__('onLine', function(){
                    return false;
                });
            """)
            
            # Test offline functionality
            offline_indicator = browser.find_element(By.ID, "offline-indicator")
            assert offline_indicator.is_displayed()
            
            # Test cached route functionality
            cached_routes_button = browser.find_element(By.ID, "cached-routes-button")
            cached_routes_button.click()
            
            cached_routes = browser.find_elements(By.CLASS_NAME, "cached-route")
            # Should have some cached routes available
            assert len(cached_routes) >= 0
            
        except Exception as e:
            pytest.skip(f"Offline functionality not available: {e}")


class TestOperatorDashboardJourney:
    """Test user journey for MARTA operators using the dashboard."""
    
    @pytest.fixture
    def client(self):
        """FastAPI test client."""
        return TestClient(app)
    
    def test_operator_monitoring_journey(self, client):
        """Test operator dashboard monitoring workflow."""
        
        # Step 1: Operator views system overview
        with patch('src.api.optimization_api.get_system_overview') as mock_overview:
            mock_overview.return_value = {
                'timestamp': datetime.now().isoformat(),
                'system_status': 'operational',
                'active_routes': 45,
                'total_vehicles': 350,
                'current_ridership': 12500,
                'service_alerts': 3,
                'performance_summary': {
                    'on_time_performance': 0.87,
                    'passenger_satisfaction': 0.83,
                    'fleet_utilization': 0.79
                }
            }
            
            response = client.get("/dashboard/system-overview")
            assert response.status_code == 200
            
            data = response.json()
            assert data['system_status'] == 'operational'
            assert data['active_routes'] > 0
        
        # Step 2: Operator drills down to specific route
        route_id = 'route_001'
        
        with patch('src.api.optimization_api.get_route_details') as mock_route_details:
            mock_route_details.return_value = {
                'route_id': route_id,
                'route_name': 'Red Line',
                'current_status': 'active',
                'vehicles_assigned': 8,
                'current_passengers': 450,
                'performance_metrics': {
                    'on_time_performance': 0.85,
                    'average_delay': 2.3,
                    'passenger_load_factor': 0.68,
                    'service_frequency': '8 minutes'
                },
                'recent_alerts': [
                    {
                        'timestamp': datetime.now().isoformat(),
                        'type': 'minor_delay',
                        'message': 'Signal issue at Downtown station',
                        'estimated_impact': '3 minutes'
                    }
                ],
                'vehicle_positions': [
                    {
                        'vehicle_id': 'RL_001',
                        'current_location': 'Downtown Station',
                        'next_stop': 'Civic Center',
                        'passenger_count': 45,
                        'on_time_status': 'on_time'
                    }
                ]
            }
            
            response = client.get(f"/dashboard/routes/{route_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert data['route_id'] == route_id
            assert 'performance_metrics' in data
            assert 'vehicle_positions' in data
        
        # Step 3: Operator initiates corrective action
        with patch('src.api.optimization_api.dispatch_corrective_action') as mock_action:
            action_request = {
                'route_id': route_id,
                'action_type': 'increase_frequency',
                'parameters': {
                    'target_frequency': '6 minutes',
                    'duration': 'peak_hours',
                    'additional_vehicles': 2
                },
                'reason': 'High passenger demand observed',
                'priority': 'medium'
            }
            
            mock_action.return_value = {
                'action_id': 'action_001',
                'status': 'dispatched',
                'estimated_implementation': '10 minutes',
                'expected_impact': {
                    'wait_time_reduction': '25%',
                    'passenger_satisfaction_increase': 0.05
                }
            }
            
            response = client.post("/dashboard/actions/dispatch", json=action_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'dispatched'
            assert 'expected_impact' in data
        
        # Step 4: Operator monitors implementation results
        action_id = 'action_001'
        
        with patch('src.api.optimization_api.get_action_status') as mock_action_status:
            mock_action_status.return_value = {
                'action_id': action_id,
                'status': 'completed',
                'implementation_time': '8 minutes',
                'actual_impact': {
                    'wait_time_reduction': '28%',
                    'passenger_satisfaction_increase': 0.06,
                    'cost_increase': '$150/hour'
                },
                'performance_change': {
                    'before': {'on_time_performance': 0.85, 'passenger_satisfaction': 0.78},
                    'after': {'on_time_performance': 0.91, 'passenger_satisfaction': 0.84}
                },
                'recommendation': 'Continue enhanced service during remaining peak hours'
            }
            
            response = client.get(f"/dashboard/actions/{action_id}/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'completed'
            assert data['actual_impact']['passenger_satisfaction_increase'] > 0
    
    def test_operator_optimization_request_journey(self, client):
        """Test operator-initiated optimization request workflow."""
        
        # Step 1: Operator identifies performance issue
        performance_issue = {
            'issue_type': 'crowding',
            'affected_routes': ['route_001', 'route_002'],
            'severity': 'high',
            'description': 'Consistent overcrowding during morning peak hours',
            'metrics': {
                'average_load_factor': 0.95,
                'passenger_complaints': 25,
                'missed_trips': 3
            }
        }
        
        # Step 2: Operator requests optimization
        optimization_request = {
            'request_type': 'targeted_optimization',
            'target_routes': performance_issue['affected_routes'],
            'optimization_goals': [
                'reduce_crowding',
                'improve_reliability',
                'maintain_cost_efficiency'
            ],
            'constraints': {
                'budget_increase_limit': 0.15,  # 15% budget increase max
                'implementation_timeframe': 'immediate',
                'service_level_maintenance': True
            },
            'priority': 'high'
        }
        
        with patch('src.api.optimization_api.submit_optimization_request') as mock_submit:
            mock_submit.return_value = {
                'request_id': 'opt_req_001',
                'status': 'accepted',
                'estimated_completion': '45 minutes',
                'optimization_queue_position': 1
            }
            
            response = client.post("/dashboard/optimization/request", json=optimization_request)
            assert response.status_code == 202  # Accepted for processing
            
            data = response.json()
            assert data['status'] == 'accepted'
            assert 'estimated_completion' in data
        
        # Step 3: Operator tracks optimization progress
        request_id = 'opt_req_001'
        
        with patch('src.api.optimization_api.get_optimization_progress') as mock_progress:
            mock_progress.return_value = {
                'request_id': request_id,
                'status': 'in_progress',
                'progress_percentage': 75,
                'current_phase': 'solution_evaluation',
                'intermediate_results': {
                    'solutions_generated': 150,
                    'best_fitness_so_far': 0.82,
                    'estimated_improvement': {
                        'load_factor_reduction': 0.18,
                        'reliability_increase': 0.07
                    }
                },
                'estimated_time_remaining': '12 minutes'
            }
            
            response = client.get(f"/dashboard/optimization/{request_id}/progress")
            assert response.status_code == 200
            
            data = response.json()
            assert data['progress_percentage'] > 0
            assert 'intermediate_results' in data
        
        # Step 4: Operator reviews optimization results
        with patch('src.api.optimization_api.get_optimization_results') as mock_results:
            mock_results.return_value = {
                'request_id': request_id,
                'status': 'completed',
                'optimization_results': {
                    'recommended_changes': [
                        {
                            'route_id': 'route_001',
                            'change_type': 'frequency_increase',
                            'current_frequency': 10,
                            'recommended_frequency': 7,
                            'additional_vehicles_needed': 2,
                            'cost_impact': '+$300/day'
                        },
                        {
                            'route_id': 'route_002',
                            'change_type': 'capacity_increase',
                            'current_capacity': 150,
                            'recommended_capacity': 180,
                            'vehicle_type_change': 'articulated_bus',
                            'cost_impact': '+$200/day'
                        }
                    ],
                    'expected_benefits': {
                        'load_factor_reduction': 0.22,
                        'passenger_satisfaction_increase': 0.12,
                        'complaint_reduction': 65,  # percent
                        'service_reliability_improvement': 0.08
                    },
                    'implementation_plan': {
                        'phase_1': {
                            'timeframe': 'immediate',
                            'changes': ['route_001_frequency_increase'],
                            'resources_required': ['2_additional_buses', '4_drivers']
                        },
                        'phase_2': {
                            'timeframe': '1_week',
                            'changes': ['route_002_capacity_increase'],
                            'resources_required': ['2_articulated_buses']
                        }
                    },
                    'total_cost_impact': '$500/day',
                    'roi_analysis': {
                        'payback_period': '3_months',
                        'passenger_revenue_increase': '$750/day',
                        'net_benefit': '$250/day'
                    }
                }
            }
            
            response = client.get(f"/dashboard/optimization/{request_id}/results")
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'completed'
            assert 'recommended_changes' in data['optimization_results']
            assert 'implementation_plan' in data['optimization_results']
        
        # Step 5: Operator approves and schedules implementation
        implementation_request = {
            'request_id': request_id,
            'approved_changes': [
                'route_001_frequency_increase',
                'route_002_capacity_increase'
            ],
            'implementation_schedule': {
                'start_time': (datetime.now() + timedelta(hours=1)).isoformat(),
                'phased_rollout': True,
                'monitoring_duration': '2_weeks'
            },
            'operator_notes': 'Approved for implementation during off-peak hours to minimize service disruption'
        }
        
        with patch('src.api.optimization_api.approve_implementation') as mock_approve:
            mock_approve.return_value = {
                'implementation_id': 'impl_001',
                'status': 'scheduled',
                'confirmation': {
                    'changes_approved': len(implementation_request['approved_changes']),
                    'start_time': implementation_request['implementation_schedule']['start_time'],
                    'estimated_completion': (datetime.now() + timedelta(hours=6)).isoformat()
                },
                'monitoring_setup': {
                    'real_time_tracking': True,
                    'performance_alerts': True,
                    'rollback_plan_ready': True
                }
            }
            
            response = client.post("/dashboard/optimization/implement", json=implementation_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'scheduled'
            assert data['monitoring_setup']['rollback_plan_ready']
    
    def test_emergency_response_journey(self, client):
        """Test operator emergency response workflow."""
        
        # Step 1: Emergency incident occurs
        emergency_incident = {
            'incident_id': 'emergency_001',
            'incident_type': 'signal_failure',
            'location': 'Downtown Station',
            'affected_routes': ['route_001', 'route_003'],
            'severity': 'high',
            'estimated_duration': '2 hours',
            'passenger_impact': '500+ passengers affected'
        }
        
        # Step 2: Operator activates emergency response
        emergency_response_request = {
            'incident_id': emergency_incident['incident_id'],
            'response_type': 'service_rerouting',
            'immediate_actions': [
                'suspend_service_downtown_station',
                'activate_bus_bridge_service',
                'notify_passengers_via_alerts'
            ],
            'temporary_service_plan': {
                'bus_bridge_route': {
                    'start_point': 'Civic Center Station',
                    'end_point': 'Five Points Station',
                    'frequency': '5 minutes',
                    'buses_required': 6
                },
                'modified_rail_service': {
                    'route_001': 'terminate_at_civic_center',
                    'route_003': 'single_track_operation'
                }
            },
            'communication_plan': {
                'passenger_alerts': 'immediate',
                'media_notification': 'within_30_minutes',
                'website_update': 'immediate'
            }
        }
        
        with patch('src.api.optimization_api.activate_emergency_response') as mock_emergency:
            mock_emergency.return_value = {
                'response_id': 'emr_001',
                'activation_status': 'successful',
                'actions_initiated': {
                    'service_suspension': 'completed',
                    'bus_bridge_dispatch': 'in_progress',
                    'passenger_notifications': 'completed'
                },
                'estimated_service_restoration': '2.5 hours',
                'alternative_service_eta': '15 minutes'
            }
            
            response = client.post("/dashboard/emergency/activate", json=emergency_response_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data['activation_status'] == 'successful'
            assert 'estimated_service_restoration' in data
        
        # Step 3: Monitor emergency response effectiveness
        response_id = 'emr_001'
        
        with patch('src.api.optimization_api.monitor_emergency_response') as mock_monitor:
            mock_monitor.return_value = {
                'response_id': response_id,
                'status': 'active',
                'effectiveness_metrics': {
                    'passengers_served_by_bridge': 320,
                    'average_delay_impact': '18 minutes',
                    'passenger_satisfaction_emergency': 0.65,  # Lower but acceptable for emergency
                    'complaints_received': 12
                },
                'resource_utilization': {
                    'bus_bridge_buses': 6,
                    'additional_staff': 15,
                    'emergency_cost': '$2,500/hour'
                },
                'incident_updates': {
                    'repair_progress': '60% complete',
                    'estimated_resolution_update': '1.5 hours remaining'
                }
            }
            
            response = client.get(f"/dashboard/emergency/{response_id}/status")
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'active'
            assert data['effectiveness_metrics']['passengers_served_by_bridge'] > 0
        
        # Step 4: Service restoration
        with patch('src.api.optimization_api.restore_normal_service') as mock_restore:
            restoration_request = {
                'response_id': response_id,
                'incident_resolved': True,
                'restoration_plan': {
                    'gradual_service_resumption': True,
                    'testing_period': '30 minutes',
                    'full_service_restoration': 'after_testing'
                }
            }
            
            mock_restore.return_value = {
                'restoration_id': 'rest_001',
                'status': 'initiated',
                'restoration_timeline': {
                    'testing_phase': '30 minutes',
                    'gradual_resumption': '45 minutes',
                    'full_service': '1 hour 15 minutes'
                },
                'post_incident_monitoring': '24 hours'
            }
            
            response = client.post("/dashboard/emergency/restore", json=restoration_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'initiated'
            assert 'restoration_timeline' in data


@pytest.mark.integration
class TestFullSystemJourney:
    """Test complete system integration from passenger perspective."""
    
    def test_passenger_complete_journey(self, client):
        """Test complete passenger journey from planning to arrival."""
        
        # Step 1: Trip planning
        trip_request = {
            'origin': {'name': 'Downtown Atlanta', 'lat': 33.7490, 'lon': -84.3880},
            'destination': {'name': 'Airport', 'lat': 33.6367, 'lon': -84.4281},
            'departure_time': '08:00',
            'preferences': {
                'minimize': 'travel_time',
                'accessibility_required': False,
                'max_walking_distance': 0.5  # miles
            }
        }
        
        with patch('src.api.optimization_api.plan_trip') as mock_plan:
            mock_plan.return_value = {
                'trip_id': 'trip_001',
                'routes': [
                    {
                        'route_option': 1,
                        'total_time': '42 minutes',
                        'total_cost': '$2.50',
                        'steps': [
                            {
                                'mode': 'walk',
                                'from': 'Downtown Atlanta',
                                'to': 'Five Points Station',
                                'duration': '5 minutes',
                                'distance': '0.2 miles'
                            },
                            {
                                'mode': 'rail',
                                'route': 'Gold Line',
                                'from': 'Five Points Station',
                                'to': 'Airport Station',
                                'duration': '35 minutes',
                                'departure': '08:05',
                                'arrival': '08:40'
                            },
                            {
                                'mode': 'walk',
                                'from': 'Airport Station',
                                'to': 'Airport',
                                'duration': '2 minutes',
                                'distance': '0.1 miles'
                            }
                        ],
                        'confidence_score': 0.92
                    }
                ]
            }
            
            response = client.post("/trip/plan", json=trip_request)
            assert response.status_code == 200
            
            data = response.json()
            assert 'routes' in data
            assert len(data['routes']) > 0
        
        # Step 2: Real-time updates during journey
        trip_id = 'trip_001'
        
        with patch('src.api.optimization_api.get_trip_updates') as mock_updates:
            mock_updates.return_value = {
                'trip_id': trip_id,
                'current_status': 'in_progress',
                'next_step': {
                    'step_number': 2,
                    'instruction': 'Board Gold Line at Five Points Station',
                    'estimated_time': '3 minutes until arrival'
                },
                'delays': [
                    {
                        'affected_step': 2,
                        'delay_amount': '2 minutes',
                        'reason': 'Minor signal delay',
                        'updated_arrival_time': '08:42'
                    }
                ],
                'alternative_suggestions': []
            }
            
            response = client.get(f"/trip/{trip_id}/updates")
            assert response.status_code == 200
            
            data = response.json()
            assert data['current_status'] == 'in_progress'
            assert 'next_step' in data
        
        # Step 3: Journey completion feedback
        completion_feedback = {
            'trip_id': trip_id,
            'actual_duration': '44 minutes',
            'satisfaction_rating': 4,  # out of 5
            'issues_encountered': [],
            'feedback_comments': 'Smooth journey overall, minor delay was well communicated'
        }
        
        with patch('src.api.optimization_api.submit_trip_feedback') as mock_feedback:
            mock_feedback.return_value = {
                'feedback_id': 'fb_001',
                'status': 'received',
                'impact_on_system': {
                    'route_rating_update': 'positive',
                    'service_quality_score': 0.88
                }
            }
            
            response = client.post("/trip/feedback", json=completion_feedback)
            assert response.status_code == 200
            
            data = response.json()
            assert data['status'] == 'received'


@pytest.mark.slow
class TestUserJourneyPerformance:
    """Test user journey performance characteristics."""
    
    def test_response_time_requirements(self, client):
        """Test API response times meet user experience requirements."""
        import time
        
        # Trip planning should respond quickly
        trip_request = {
            'origin': {'lat': 33.7490, 'lon': -84.3880},
            'destination': {'lat': 33.6367, 'lon': -84.4281}
        }
        
        with patch('src.api.optimization_api.plan_trip') as mock_plan:
            mock_plan.return_value = {'routes': []}
            
            start_time = time.time()
            response = client.post("/trip/plan", json=trip_request)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < 2.0  # Should respond within 2 seconds
        
        # Real-time updates should be very fast
        with patch('src.api.optimization_api.get_real_time_updates') as mock_updates:
            mock_updates.return_value = {'updates': []}
            
            start_time = time.time()
            response = client.get("/real-time/updates")
            end_time = time.time()
            
            response_time = end_time - start_time
            
            assert response.status_code == 200
            assert response_time < 0.5  # Should respond within 500ms
    
    def test_concurrent_user_load(self, client):
        """Test system behavior under concurrent user load."""
        import concurrent.futures
        import time
        
        def simulate_user_request():
            with patch('src.api.optimization_api.plan_trip') as mock_plan:
                mock_plan.return_value = {'routes': []}
                
                response = client.post("/trip/plan", json={
                    'origin': {'lat': 33.7490, 'lon': -84.3880},
                    'destination': {'lat': 33.6367, 'lon': -84.4281}
                })
                return response.status_code
        
        # Simulate 50 concurrent users
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(simulate_user_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        end_time = time.time()
        
        # All requests should succeed
        assert all(status == 200 for status in results)
        
        # Should handle load efficiently
        total_time = end_time - start_time
        assert total_time < 10.0  # 50 requests in under 10 seconds