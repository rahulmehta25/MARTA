"""
Unit tests for route optimization modules in the MARTA platform.
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import tempfile
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

# Test imports
from src.optimization.route_optimizer import RouteOptimizer
from src.optimization.route_simulator import RouteSimulator
from src.optimization.optimization_orchestrator import OptimizationOrchestrator


@dataclass
class MockRoute:
    """Mock route for testing."""
    route_id: str
    stops: List[str]
    frequency: int  # minutes between trips
    capacity: int
    operating_cost: float


@dataclass
class MockDemand:
    """Mock demand data for testing."""
    origin: str
    destination: str
    demand: float
    time_period: int


class TestRouteOptimizer:
    """Test suite for route optimization functionality."""
    
    @pytest.fixture
    def route_optimizer(self):
        """Create route optimizer instance."""
        return RouteOptimizer(
            optimization_method='genetic_algorithm',
            config={
                'population_size': 50,
                'generations': 20,
                'mutation_rate': 0.1,
                'crossover_rate': 0.8,
                'elite_size': 5
            }
        )
    
    @pytest.fixture
    def sample_network(self):
        """Create sample transit network for testing."""
        stops = ['stop_001', 'stop_002', 'stop_003', 'stop_004', 'stop_005']
        
        routes = [
            MockRoute('route_001', ['stop_001', 'stop_002', 'stop_003'], 10, 200, 100.0),
            MockRoute('route_002', ['stop_002', 'stop_004', 'stop_005'], 15, 150, 80.0),
            MockRoute('route_003', ['stop_001', 'stop_004', 'stop_005'], 20, 180, 90.0)
        ]
        
        # Travel time matrix (minutes)
        travel_times = np.array([
            [0, 5, 10, 15, 20],
            [5, 0, 6, 8, 12],
            [10, 6, 0, 7, 9],
            [15, 8, 7, 0, 5],
            [20, 12, 9, 5, 0]
        ])
        
        # Demand matrix (passengers per hour)
        demand_matrix = np.array([
            [0, 50, 30, 40, 20],
            [50, 0, 60, 45, 35],
            [30, 60, 0, 55, 40],
            [40, 45, 55, 0, 30],
            [20, 35, 40, 30, 0]
        ])
        
        return {
            'stops': stops,
            'routes': routes,
            'travel_times': travel_times,
            'demand_matrix': demand_matrix
        }
    
    def test_initialization(self, route_optimizer):
        """Test route optimizer initialization."""
        assert route_optimizer.optimization_method == 'genetic_algorithm'
        assert route_optimizer.config['population_size'] == 50
        assert route_optimizer.config['generations'] == 20
        assert route_optimizer.population is None  # Not initialized yet
    
    def test_calculate_route_efficiency(self, route_optimizer, sample_network):
        """Test route efficiency calculation."""
        route = sample_network['routes'][0]
        demand_matrix = sample_network['demand_matrix']
        travel_times = sample_network['travel_times']
        
        efficiency = route_optimizer.calculate_route_efficiency(
            route, demand_matrix, travel_times
        )
        
        # Efficiency should be a positive number
        assert efficiency > 0
        assert isinstance(efficiency, (int, float))
    
    def test_calculate_coverage_score(self, route_optimizer, sample_network):
        """Test network coverage calculation."""
        routes = sample_network['routes']
        stops = sample_network['stops']
        
        coverage = route_optimizer.calculate_coverage_score(routes, stops)
        
        # Coverage should be between 0 and 1
        assert 0 <= coverage <= 1
        assert isinstance(coverage, (int, float))
    
    def test_calculate_total_cost(self, route_optimizer, sample_network):
        """Test total operating cost calculation."""
        routes = sample_network['routes']
        
        total_cost = route_optimizer.calculate_total_cost(routes)
        
        # Should sum up all route costs
        expected_cost = sum(route.operating_cost for route in routes)
        assert total_cost == expected_cost
        assert total_cost > 0
    
    def test_evaluate_solution(self, route_optimizer, sample_network):
        """Test solution evaluation function."""
        routes = sample_network['routes']
        
        with patch.object(route_optimizer, 'calculate_route_efficiency', return_value=0.8), \
             patch.object(route_optimizer, 'calculate_coverage_score', return_value=0.9), \
             patch.object(route_optimizer, 'calculate_total_cost', return_value=270.0):
            
            fitness = route_optimizer.evaluate_solution(routes, sample_network)
            
            # Fitness should be positive (higher is better)
            assert fitness > 0
            assert isinstance(fitness, (int, float))
    
    def test_generate_initial_population(self, route_optimizer, sample_network):
        """Test initial population generation for GA."""
        population_size = 10
        
        population = route_optimizer.generate_initial_population(
            sample_network, population_size
        )
        
        # Check population structure
        assert len(population) == population_size
        assert all(isinstance(individual, list) for individual in population)
        
        # Each individual should have routes
        for individual in population:
            assert len(individual) > 0
            assert all(hasattr(route, 'route_id') for route in individual)
    
    def test_crossover_operation(self, route_optimizer, sample_network):
        """Test genetic algorithm crossover."""
        parent1 = sample_network['routes'][:2]
        parent2 = sample_network['routes'][1:]
        
        child1, child2 = route_optimizer.crossover(parent1, parent2)
        
        # Children should be valid solutions
        assert isinstance(child1, list)
        assert isinstance(child2, list)
        assert len(child1) > 0
        assert len(child2) > 0
        
        # Children should combine elements from parents
        all_parent_routes = set(r.route_id for r in parent1 + parent2)
        child1_routes = set(r.route_id for r in child1)
        child2_routes = set(r.route_id for r in child2)
        
        assert child1_routes.issubset(all_parent_routes)
        assert child2_routes.issubset(all_parent_routes)
    
    def test_mutation_operation(self, route_optimizer, sample_network):
        """Test genetic algorithm mutation."""
        individual = sample_network['routes'][:2]
        
        mutated = route_optimizer.mutate(individual, sample_network)
        
        # Mutated individual should still be valid
        assert isinstance(mutated, list)
        assert len(mutated) >= len(individual)  # May add/remove routes
        assert all(hasattr(route, 'route_id') for route in mutated)
    
    def test_selection_operation(self, route_optimizer, sample_network):
        """Test selection for genetic algorithm."""
        population = route_optimizer.generate_initial_population(sample_network, 10)
        
        # Mock fitness values
        fitness_values = [0.5, 0.8, 0.3, 0.9, 0.6, 0.7, 0.4, 0.2, 0.1, 0.95]
        
        selected = route_optimizer.selection(population, fitness_values, 5)
        
        # Should select specified number of individuals
        assert len(selected) == 5
        assert all(individual in population for individual in selected)
    
    def test_optimize_routes_genetic_algorithm(self, route_optimizer, sample_network):
        """Test complete genetic algorithm optimization."""
        # Use smaller parameters for testing
        route_optimizer.config.update({
            'population_size': 10,
            'generations': 5,
            'elite_size': 2
        })
        
        with patch.object(route_optimizer, 'evaluate_solution', return_value=0.8):
            result = route_optimizer.optimize_routes(sample_network)
        
        # Check optimization result structure
        assert 'best_solution' in result
        assert 'best_fitness' in result
        assert 'convergence_history' in result
        assert 'optimization_stats' in result
        
        # Best solution should be a list of routes
        assert isinstance(result['best_solution'], list)
        assert len(result['best_solution']) > 0
        
        # Fitness should be positive
        assert result['best_fitness'] > 0
    
    def test_optimize_routes_simulated_annealing(self):
        """Test simulated annealing optimization method."""
        optimizer = RouteOptimizer(
            optimization_method='simulated_annealing',
            config={
                'initial_temperature': 100,
                'cooling_rate': 0.95,
                'min_temperature': 0.01,
                'max_iterations': 100
            }
        )
        
        # Mock network data
        network = {
            'stops': ['A', 'B', 'C'],
            'routes': [MockRoute('1', ['A', 'B'], 10, 100, 50)],
            'travel_times': np.array([[0, 5, 10], [5, 0, 6], [10, 6, 0]]),
            'demand_matrix': np.array([[0, 20, 15], [20, 0, 25], [15, 25, 0]])
        }
        
        with patch.object(optimizer, 'evaluate_solution', return_value=0.7):
            result = optimizer.optimize_routes(network)
        
        assert 'best_solution' in result
        assert 'best_fitness' in result
        assert result['best_fitness'] > 0
    
    def test_constraint_validation(self, route_optimizer, sample_network):
        """Test constraint validation for solutions."""
        # Valid solution
        valid_routes = sample_network['routes'][:2]
        
        # Invalid solution (exceeds budget)
        expensive_route = MockRoute('expensive', ['stop_001'], 5, 300, 1000.0)
        invalid_routes = sample_network['routes'] + [expensive_route]
        
        constraints = {
            'max_budget': 500.0,
            'min_coverage': 0.8,
            'max_routes': 5
        }
        
        assert route_optimizer.validate_constraints(valid_routes, constraints, sample_network)
        assert not route_optimizer.validate_constraints(invalid_routes, constraints, sample_network)
    
    def test_route_modification_operations(self, route_optimizer, sample_network):
        """Test route modification operations."""
        route = sample_network['routes'][0]
        
        # Test adding stop
        modified_route = route_optimizer.add_stop_to_route(route, 'stop_004', position=2)
        assert 'stop_004' in modified_route.stops
        assert len(modified_route.stops) == len(route.stops) + 1
        
        # Test removing stop
        shortened_route = route_optimizer.remove_stop_from_route(route, 'stop_002')
        assert 'stop_002' not in shortened_route.stops
        assert len(shortened_route.stops) == len(route.stops) - 1
        
        # Test frequency adjustment
        adjusted_route = route_optimizer.adjust_frequency(route, new_frequency=12)
        assert adjusted_route.frequency == 12


class TestRouteSimulator:
    """Test suite for route simulation functionality."""
    
    @pytest.fixture
    def route_simulator(self):
        """Create route simulator instance."""
        return RouteSimulator(
            simulation_duration=3600,  # 1 hour in seconds
            time_step=60  # 1 minute time steps
        )
    
    @pytest.fixture
    def simulation_config(self):
        """Configuration for simulation testing."""
        return {
            'passenger_arrival_rate': 2.0,  # passengers per minute
            'boarding_time': 5,  # seconds per passenger
            'dwell_time_base': 30,  # base dwell time in seconds
            'max_occupancy': 200,
            'service_reliability': 0.95
        }
    
    def test_initialization(self, route_simulator):
        """Test route simulator initialization."""
        assert route_simulator.simulation_duration == 3600
        assert route_simulator.time_step == 60
        assert route_simulator.current_time == 0
        assert len(route_simulator.events) == 0
    
    def test_passenger_generation(self, route_simulator, simulation_config):
        """Test passenger generation logic."""
        stop_id = 'stop_001'
        arrival_rate = simulation_config['passenger_arrival_rate']
        
        passengers = route_simulator.generate_passengers(
            stop_id, arrival_rate, time_period=60
        )
        
        # Should generate reasonable number of passengers
        assert len(passengers) >= 0
        assert all('arrival_time' in p for p in passengers)
        assert all('origin' in p for p in passengers)
        assert all('destination' in p for p in passengers)
    
    def test_vehicle_movement(self, route_simulator, sample_network):
        """Test vehicle movement simulation."""
        route = sample_network['routes'][0]
        travel_times = sample_network['travel_times']
        
        vehicle = {
            'vehicle_id': 'vehicle_001',
            'route_id': route.route_id,
            'current_stop_index': 0,
            'passengers': [],
            'capacity': route.capacity,
            'arrival_time': 0
        }
        
        # Simulate movement to next stop
        updated_vehicle = route_simulator.move_vehicle(
            vehicle, route, travel_times
        )
        
        assert updated_vehicle['current_stop_index'] > vehicle['current_stop_index']
        assert updated_vehicle['arrival_time'] > vehicle['arrival_time']
    
    def test_passenger_boarding_alighting(self, route_simulator):
        """Test passenger boarding and alighting."""
        vehicle = {
            'vehicle_id': 'vehicle_001',
            'passengers': [],
            'capacity': 200,
            'current_stop': 'stop_002'
        }
        
        waiting_passengers = [
            {'passenger_id': 'p1', 'destination': 'stop_003'},
            {'passenger_id': 'p2', 'destination': 'stop_004'},
            {'passenger_id': 'p3', 'destination': 'stop_002'}  # Already at destination
        ]
        
        # Add some existing passengers
        vehicle['passengers'] = [
            {'passenger_id': 'p4', 'destination': 'stop_002'},  # Getting off
            {'passenger_id': 'p5', 'destination': 'stop_005'}   # Staying on
        ]
        
        updated_vehicle, boarding_count, alighting_count = route_simulator.process_passenger_exchange(
            vehicle, waiting_passengers
        )
        
        # Check boarding and alighting logic
        assert alighting_count >= 1  # At least p4 should get off
        assert boarding_count >= 0   # May board depending on capacity
        assert len(updated_vehicle['passengers']) <= vehicle['capacity']
    
    def test_dwell_time_calculation(self, route_simulator, simulation_config):
        """Test dwell time calculation."""
        boarding_passengers = 10
        alighting_passengers = 5
        
        dwell_time = route_simulator.calculate_dwell_time(
            boarding_passengers, 
            alighting_passengers,
            simulation_config['boarding_time'],
            simulation_config['dwell_time_base']
        )
        
        # Dwell time should account for passenger exchange
        expected_min = simulation_config['dwell_time_base']
        expected_passenger_time = (boarding_passengers + alighting_passengers) * simulation_config['boarding_time']
        
        assert dwell_time >= expected_min
        assert dwell_time >= expected_passenger_time
    
    def test_delay_simulation(self, route_simulator):
        """Test delay injection in simulation."""
        base_travel_time = 300  # 5 minutes
        reliability = 0.9  # 90% on time
        
        # Run multiple simulations to test delay distribution
        travel_times = [
            route_simulator.apply_service_reliability(base_travel_time, reliability)
            for _ in range(100)
        ]
        
        # Most trips should be close to base time
        on_time_trips = sum(1 for t in travel_times if t <= base_travel_time * 1.1)
        delayed_trips = len(travel_times) - on_time_trips
        
        # Should have some delays but mostly on time
        assert on_time_trips > delayed_trips
        assert all(t >= base_travel_time for t in travel_times)  # No trips faster than base
    
    def test_capacity_constraints(self, route_simulator):
        """Test vehicle capacity constraints."""
        vehicle = {
            'vehicle_id': 'vehicle_001',
            'passengers': [{'id': f'p{i}'} for i in range(180)],  # Near capacity
            'capacity': 200
        }
        
        waiting_passengers = [{'id': f'waiting_p{i}'} for i in range(30)]
        
        can_board = route_simulator.calculate_boarding_capacity(vehicle, waiting_passengers)
        
        # Should not exceed capacity
        assert can_board <= (vehicle['capacity'] - len(vehicle['passengers']))
        assert can_board >= 0
    
    def test_simulation_metrics_collection(self, route_simulator, sample_network):
        """Test collection of simulation metrics."""
        # Mock a completed simulation
        route_simulator.simulation_results = {
            'passenger_wait_times': [2, 5, 3, 8, 1, 6],
            'vehicle_occupancies': [50, 120, 80, 200, 150],
            'service_delays': [0, 120, 60, 300, 0],
            'passenger_journeys': 100,
            'total_distance': 500
        }
        
        metrics = route_simulator.calculate_performance_metrics()
        
        # Check key performance indicators
        assert 'average_wait_time' in metrics
        assert 'average_occupancy' in metrics
        assert 'service_reliability' in metrics
        assert 'passenger_throughput' in metrics
        
        # Values should be reasonable
        assert metrics['average_wait_time'] > 0
        assert 0 <= metrics['average_occupancy'] <= 200
        assert 0 <= metrics['service_reliability'] <= 1
    
    def test_run_simulation(self, route_simulator, sample_network, simulation_config):
        """Test running complete simulation."""
        routes = sample_network['routes'][:1]  # Use one route for testing
        travel_times = sample_network['travel_times']
        demand_patterns = {
            'stop_001': {'hourly_demand': 60, 'peak_factor': 1.5},
            'stop_002': {'hourly_demand': 45, 'peak_factor': 1.2},
            'stop_003': {'hourly_demand': 30, 'peak_factor': 1.0}
        }
        
        # Use shorter simulation for testing
        route_simulator.simulation_duration = 1800  # 30 minutes
        
        result = route_simulator.run_simulation(
            routes, travel_times, demand_patterns, simulation_config
        )
        
        # Check simulation results structure
        assert 'performance_metrics' in result
        assert 'passenger_statistics' in result
        assert 'vehicle_statistics' in result
        assert 'simulation_events' in result
        
        # Performance metrics should be calculated
        metrics = result['performance_metrics']
        assert 'total_passengers_served' in metrics
        assert 'average_journey_time' in metrics
        assert 'system_efficiency' in metrics


class TestOptimizationOrchestrator:
    """Test suite for optimization orchestration."""
    
    @pytest.fixture
    def orchestrator(self):
        """Create optimization orchestrator instance."""
        return OptimizationOrchestrator(
            db_config={'host': 'localhost', 'database': 'test_db'},
            optimization_config={
                'methods': ['genetic_algorithm', 'simulated_annealing'],
                'evaluation_criteria': ['efficiency', 'coverage', 'cost'],
                'multi_objective': True
            }
        )
    
    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.db_config['host'] == 'localhost'
        assert 'genetic_algorithm' in orchestrator.optimization_config['methods']
        assert orchestrator.optimization_config['multi_objective']
    
    def test_data_preparation(self, orchestrator, sample_network):
        """Test preparation of optimization data."""
        with patch.object(orchestrator, '_load_network_data', return_value=sample_network):
            network_data = orchestrator.prepare_optimization_data()
            
            assert 'stops' in network_data
            assert 'routes' in network_data
            assert 'travel_times' in network_data
            assert 'demand_matrix' in network_data
    
    def test_multi_objective_optimization(self, orchestrator, sample_network):
        """Test multi-objective optimization."""
        objectives = ['minimize_cost', 'maximize_coverage', 'maximize_efficiency']
        
        with patch.object(orchestrator, 'run_single_optimization') as mock_optimize:
            mock_optimize.return_value = {
                'best_solution': sample_network['routes'][:2],
                'fitness_scores': {'cost': 200, 'coverage': 0.85, 'efficiency': 0.75}
            }
            
            result = orchestrator.multi_objective_optimize(sample_network, objectives)
            
            assert 'pareto_front' in result
            assert 'best_solutions' in result
            assert 'objective_values' in result
    
    def test_solution_comparison(self, orchestrator, sample_network):
        """Test comparing different optimization solutions."""
        solution1 = {
            'routes': sample_network['routes'][:2],
            'metrics': {'cost': 180, 'coverage': 0.8, 'efficiency': 0.7}
        }
        
        solution2 = {
            'routes': sample_network['routes'][1:],
            'metrics': {'cost': 220, 'coverage': 0.9, 'efficiency': 0.6}
        }
        
        comparison = orchestrator.compare_solutions([solution1, solution2])
        
        assert 'ranking' in comparison
        assert 'tradeoff_analysis' in comparison
        assert len(comparison['ranking']) == 2
    
    def test_optimization_validation(self, orchestrator, sample_network):
        """Test validation of optimization results."""
        solution = {
            'routes': sample_network['routes'],
            'total_cost': 270,
            'coverage': 0.95,
            'efficiency': 0.8
        }
        
        constraints = {
            'max_budget': 300,
            'min_coverage': 0.9,
            'max_routes': 5
        }
        
        validation_result = orchestrator.validate_solution(solution, constraints)
        
        assert validation_result['is_valid']
        assert validation_result['constraint_violations'] == []
    
    def test_sensitivity_analysis(self, orchestrator, sample_network):
        """Test sensitivity analysis of optimization parameters."""
        base_solution = {
            'routes': sample_network['routes'],
            'fitness': 0.8
        }
        
        parameter_ranges = {
            'demand_multiplier': [0.8, 0.9, 1.0, 1.1, 1.2],
            'cost_weight': [0.3, 0.5, 0.7]
        }
        
        with patch.object(orchestrator, 'run_single_optimization') as mock_opt:
            mock_opt.return_value = base_solution
            
            sensitivity_results = orchestrator.sensitivity_analysis(
                sample_network, parameter_ranges
            )
            
            assert 'parameter_effects' in sensitivity_results
            assert 'robustness_metrics' in sensitivity_results
    
    def test_optimization_history_tracking(self, orchestrator):
        """Test tracking optimization run history."""
        run_data = {
            'run_id': 'test_run_001',
            'method': 'genetic_algorithm',
            'parameters': {'population_size': 50, 'generations': 100},
            'results': {'best_fitness': 0.85, 'convergence_time': 45.2}
        }
        
        with patch.object(orchestrator, '_save_optimization_run'):
            orchestrator.save_optimization_run(run_data)
        
        # Mock loading historical data
        with patch.object(orchestrator, '_load_optimization_history') as mock_load:
            mock_load.return_value = [run_data]
            
            history = orchestrator.get_optimization_history()
            
            assert len(history) == 1
            assert history[0]['run_id'] == 'test_run_001'
    
    def test_real_time_optimization_trigger(self, orchestrator):
        """Test triggering optimization based on real-time conditions."""
        current_performance = {
            'avg_delay': 8.5,  # minutes
            'passenger_satisfaction': 0.72,
            'cost_efficiency': 0.65
        }
        
        thresholds = {
            'max_avg_delay': 7.0,
            'min_satisfaction': 0.75,
            'min_cost_efficiency': 0.7
        }
        
        should_optimize = orchestrator.should_trigger_optimization(
            current_performance, thresholds
        )
        
        # Current performance violates thresholds, so should optimize
        assert should_optimize
        
        # Test with good performance
        good_performance = {
            'avg_delay': 5.0,
            'passenger_satisfaction': 0.85,
            'cost_efficiency': 0.8
        }
        
        should_not_optimize = orchestrator.should_trigger_optimization(
            good_performance, thresholds
        )
        
        assert not should_not_optimize


@pytest.mark.integration
class TestOptimizationIntegration:
    """Integration tests for optimization modules."""
    
    def test_optimization_simulation_pipeline(self, optimization_test_data):
        """Test complete optimization followed by simulation."""
        # This would test the full pipeline from optimization to simulation
        optimizer = RouteOptimizer('genetic_algorithm', {'generations': 5})
        simulator = RouteSimulator(simulation_duration=1800)
        
        # Mock optimization result
        optimized_routes = optimization_test_data['routes']
        
        # Mock simulation result
        simulation_result = {
            'performance_metrics': {
                'total_passengers_served': 1000,
                'average_journey_time': 25,
                'system_efficiency': 0.8
            }
        }
        
        with patch.object(optimizer, 'optimize_routes') as mock_opt, \
             patch.object(simulator, 'run_simulation', return_value=simulation_result) as mock_sim:
            
            mock_opt.return_value = {'best_solution': optimized_routes}
            
            # Run optimization
            opt_result = optimizer.optimize_routes(optimization_test_data)
            
            # Simulate optimized routes
            sim_result = simulator.run_simulation(
                opt_result['best_solution'],
                optimization_test_data['travel_times'],
                {},  # demand patterns
                {}   # simulation config
            )
            
            assert opt_result['best_solution'] == optimized_routes
            assert sim_result['performance_metrics']['system_efficiency'] == 0.8
    
    def test_multi_period_optimization(self, optimization_test_data):
        """Test optimization across multiple time periods."""
        # Test optimizing for different time periods (morning, afternoon, evening)
        # This would involve different demand patterns for each period
        pass
    
    def test_constraint_handling_integration(self, optimization_test_data):
        """Test integration with various constraint types."""
        # Test optimization with budget, coverage, capacity, and regulatory constraints
        pass