"""Route optimization using genetic algorithms and simulation."""

import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import random
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

@dataclass
class OptimizedRoute:
    """Container for optimized route configuration."""
    route_id: str
    stops: List[str]
    frequency_minutes: int
    vehicle_assignments: List[str]
    expected_wait_time: float
    expected_travel_time: float
    capacity_utilization: float
    improvement_percentage: float
    modifications: List[str]

@dataclass
class SimulationResult:
    """Results from route simulation."""
    total_passengers_served: int
    average_wait_time: float
    average_travel_time: float
    on_time_performance: float
    crowding_incidents: int
    total_delay_minutes: float
    efficiency_score: float

class RouteOptimizer:
    """Optimize routes using simulation and genetic algorithms."""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._default_config()
        self.current_routes = {}
        self.demand_matrix = {}
        self.traffic_data = {}
        self.fleet_availability = {}

    def _default_config(self) -> Dict:
        """Default optimization configuration."""
        return {
            "population_size": 50,
            "generations": 100,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "elite_size": 5,
            "simulation_duration_hours": 24,
            "optimization_objectives": [
                "minimize_wait_time",
                "minimize_crowding",
                "maximize_coverage",
                "minimize_deadhead"
            ]
        }

    def optimize_route(self,
                      route_id: str,
                      demand_forecast: List[Dict],
                      constraints: Optional[Dict] = None) -> OptimizedRoute:
        """Optimize a single route based on demand forecast."""

        # Get current route configuration
        current_config = self._get_current_route(route_id)

        # Initialize genetic algorithm
        population = self._initialize_population(current_config, constraints)

        # Run genetic algorithm
        best_solution = None
        best_fitness = float('-inf')

        for generation in range(self.config["generations"]):
            # Evaluate fitness of each solution
            fitness_scores = []
            for solution in population:
                fitness = self._evaluate_fitness(
                    solution, demand_forecast, constraints
                )
                fitness_scores.append(fitness)

                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = solution

            # Select parents
            parents = self._selection(population, fitness_scores)

            # Create next generation
            next_generation = self._create_next_generation(
                parents, self.config["population_size"]
            )

            population = next_generation

            # Log progress
            if generation % 10 == 0:
                logger.info(f"Generation {generation}: Best fitness = {best_fitness:.3f}")

        # Convert best solution to OptimizedRoute
        return self._solution_to_route(best_solution, route_id, current_config)

    def simulate_network(self,
                        routes: List[Dict],
                        demand_data: Dict,
                        duration_hours: int = 24) -> SimulationResult:
        """Simulate entire network performance."""

        simulation_state = {
            "time": datetime.now(),
            "vehicles": {},
            "stops": {},
            "passengers": [],
            "metrics": {
                "total_served": 0,
                "total_wait_time": 0,
                "total_travel_time": 0,
                "delays": 0,
                "crowding_events": 0
            }
        }

        # Initialize vehicles and stops
        simulation_state = self._initialize_simulation(routes, simulation_state)

        # Run simulation
        end_time = simulation_state["time"] + timedelta(hours=duration_hours)
        time_step = timedelta(minutes=1)

        while simulation_state["time"] < end_time:
            # Generate new passengers based on demand
            new_passengers = self._generate_passengers(
                demand_data, simulation_state["time"]
            )
            simulation_state["passengers"].extend(new_passengers)

            # Move vehicles
            simulation_state = self._move_vehicles(simulation_state, time_step)

            # Board/alight passengers
            simulation_state = self._handle_passenger_flow(simulation_state)

            # Update metrics
            simulation_state = self._update_metrics(simulation_state)

            # Advance time
            simulation_state["time"] += time_step

        # Calculate final metrics
        return self._calculate_simulation_results(simulation_state)

    def reposition_vehicles(self,
                           current_positions: Dict,
                           demand_surge: Dict,
                           available_vehicles: List[str]) -> List[Dict]:
        """Reposition vehicles to handle demand surges."""

        repositioning_commands = []

        # Identify high-demand areas
        surge_locations = sorted(
            demand_surge.items(),
            key=lambda x: x[1]["surge_magnitude"],
            reverse=True
        )

        # Find nearest available vehicles
        for location, surge_info in surge_locations[:len(available_vehicles)]:
            nearest_vehicle = self._find_nearest_vehicle(
                location, available_vehicles, current_positions
            )

            if nearest_vehicle:
                repositioning_commands.append({
                    "vehicle_id": nearest_vehicle,
                    "from_location": current_positions[nearest_vehicle],
                    "to_location": location,
                    "reason": f"Demand surge: {surge_info['surge_magnitude']:.1f}x normal",
                    "estimated_arrival": self._estimate_travel_time(
                        current_positions[nearest_vehicle], location
                    ),
                    "priority": "high" if surge_info["surge_magnitude"] > 2.0 else "normal"
                })

                available_vehicles.remove(nearest_vehicle)

        return repositioning_commands

    def _initialize_population(self, current_config: Dict, constraints: Dict) -> List[Dict]:
        """Initialize population for genetic algorithm."""
        population = []

        # Always include current configuration
        population.append(current_config)

        # Generate random variations
        for _ in range(self.config["population_size"] - 1):
            variant = self._create_route_variant(current_config, constraints)
            population.append(variant)

        return population

    def _create_route_variant(self, base_config: Dict, constraints: Dict) -> Dict:
        """Create a variant of the base route configuration."""
        variant = deepcopy(base_config)

        # Randomly modify frequency
        if random.random() < 0.3:
            variant["frequency"] = max(
                constraints.get("min_frequency", 5),
                min(constraints.get("max_frequency", 60),
                    variant["frequency"] + random.randint(-10, 10))
            )

        # Randomly modify stop pattern (skip-stop)
        if random.random() < 0.2:
            stops = variant["stops"]
            if len(stops) > 10:
                # Create express pattern by skipping some stops
                skip_pattern = random.choice([
                    [i for i in range(len(stops)) if i % 2 == 0],  # Even stops
                    [i for i in range(len(stops)) if i % 3 != 0],  # Skip every 3rd
                    list(range(len(stops)))  # All stops (normal)
                ])
                variant["stops"] = [stops[i] for i in skip_pattern]
                variant["pattern"] = "express" if len(skip_pattern) < len(stops) else "local"

        # Randomly modify vehicle allocation
        if random.random() < 0.3:
            current_vehicles = variant.get("num_vehicles", 5)
            variant["num_vehicles"] = max(
                constraints.get("min_vehicles", 2),
                min(constraints.get("max_vehicles", 20),
                    current_vehicles + random.randint(-2, 2))
            )

        return variant

    def _evaluate_fitness(self, solution: Dict, demand_forecast: List[Dict], constraints: Dict) -> float:
        """Evaluate fitness of a route configuration."""
        fitness = 0.0

        # Simulate route performance
        sim_result = self._quick_simulation(solution, demand_forecast)

        # Calculate fitness components
        wait_time_score = 100 / (1 + sim_result["avg_wait_time"])
        crowding_score = 100 / (1 + sim_result["crowding_incidents"])
        coverage_score = sim_result["coverage_percentage"]
        efficiency_score = sim_result["vehicle_utilization"]

        # Weighted combination
        weights = {
            "wait_time": 0.3,
            "crowding": 0.3,
            "coverage": 0.2,
            "efficiency": 0.2
        }

        fitness = (
            weights["wait_time"] * wait_time_score +
            weights["crowding"] * crowding_score +
            weights["coverage"] * coverage_score +
            weights["efficiency"] * efficiency_score
        )

        # Apply penalties for constraint violations
        if solution["frequency"] < constraints.get("min_frequency", 5):
            fitness *= 0.5
        if solution.get("num_vehicles", 5) > constraints.get("max_vehicles", 20):
            fitness *= 0.7

        return fitness

    def _quick_simulation(self, config: Dict, demand_forecast: List[Dict]) -> Dict:
        """Quick simulation for fitness evaluation."""
        # Simplified simulation for genetic algorithm
        frequency = config.get("frequency", 15)
        num_vehicles = config.get("num_vehicles", 5)
        num_stops = len(config.get("stops", []))

        # Estimate wait time
        avg_wait_time = frequency / 2

        # Estimate crowding based on demand and capacity
        total_demand = sum(d.get("predicted_demand", 0) for d in demand_forecast)
        hourly_capacity = (60 / frequency) * num_vehicles * 60  # 60 passengers per vehicle
        crowding_ratio = total_demand / (hourly_capacity * 24) if hourly_capacity > 0 else 1

        crowding_incidents = int(crowding_ratio * 10) if crowding_ratio > 0.8 else 0

        # Coverage (percentage of stops served)
        total_stops = 50  # Assume route could have 50 stops
        coverage_percentage = (num_stops / total_stops) * 100

        # Vehicle utilization
        vehicle_utilization = min(95, crowding_ratio * 100)

        return {
            "avg_wait_time": avg_wait_time,
            "crowding_incidents": crowding_incidents,
            "coverage_percentage": coverage_percentage,
            "vehicle_utilization": vehicle_utilization
        }

    def _selection(self, population: List[Dict], fitness_scores: List[float]) -> List[Dict]:
        """Select parents for next generation using tournament selection."""
        parents = []
        tournament_size = 3

        for _ in range(len(population) // 2):
            # Tournament selection
            tournament_indices = random.sample(range(len(population)), tournament_size)
            tournament_fitness = [fitness_scores[i] for i in tournament_indices]
            winner_idx = tournament_indices[np.argmax(tournament_fitness)]
            parents.append(population[winner_idx])

        return parents

    def _create_next_generation(self, parents: List[Dict], population_size: int) -> List[Dict]:
        """Create next generation through crossover and mutation."""
        next_gen = []

        # Elite selection (keep best solutions)
        elite_size = self.config["elite_size"]
        next_gen.extend(parents[:elite_size])

        # Crossover and mutation
        while len(next_gen) < population_size:
            if random.random() < self.config["crossover_rate"]:
                parent1, parent2 = random.sample(parents, 2)
                child = self._crossover(parent1, parent2)
            else:
                child = deepcopy(random.choice(parents))

            if random.random() < self.config["mutation_rate"]:
                child = self._mutate(child)

            next_gen.append(child)

        return next_gen[:population_size]

    def _crossover(self, parent1: Dict, parent2: Dict) -> Dict:
        """Perform crossover between two parent solutions."""
        child = deepcopy(parent1)

        # Mix attributes from both parents
        if random.random() < 0.5:
            child["frequency"] = parent2["frequency"]
        if random.random() < 0.5:
            child["num_vehicles"] = parent2.get("num_vehicles", 5)
        if random.random() < 0.5 and "stops" in parent2:
            child["stops"] = parent2["stops"]

        return child

    def _mutate(self, solution: Dict) -> Dict:
        """Apply random mutation to a solution."""
        mutated = deepcopy(solution)

        # Random mutation type
        mutation_type = random.choice(["frequency", "vehicles", "stops"])

        if mutation_type == "frequency":
            mutated["frequency"] = max(5, min(60,
                mutated["frequency"] + random.randint(-5, 5)))
        elif mutation_type == "vehicles":
            mutated["num_vehicles"] = max(2, min(20,
                mutated.get("num_vehicles", 5) + random.randint(-1, 1)))
        elif mutation_type == "stops" and "stops" in mutated:
            # Randomly remove or add a stop
            if len(mutated["stops"]) > 5 and random.random() < 0.5:
                # Remove a random stop
                idx = random.randint(1, len(mutated["stops"]) - 2)
                mutated["stops"].pop(idx)

        return mutated

    def _solution_to_route(self, solution: Dict, route_id: str, original: Dict) -> OptimizedRoute:
        """Convert GA solution to OptimizedRoute object."""
        modifications = []

        # Identify modifications
        if solution["frequency"] != original["frequency"]:
            modifications.append(
                f"Frequency changed from {original['frequency']} to {solution['frequency']} minutes"
            )

        if solution.get("num_vehicles") != original.get("num_vehicles"):
            modifications.append(
                f"Vehicle allocation changed from {original.get('num_vehicles', 5)} to {solution.get('num_vehicles', 5)}"
            )

        if len(solution.get("stops", [])) != len(original.get("stops", [])):
            modifications.append(
                f"Stop pattern modified: {len(solution.get('stops', []))} stops (was {len(original.get('stops', []))})"
            )

        # Calculate improvement
        original_score = self._evaluate_fitness(original, [], {})
        optimized_score = self._evaluate_fitness(solution, [], {})
        improvement = ((optimized_score - original_score) / original_score * 100) if original_score > 0 else 0

        return OptimizedRoute(
            route_id=route_id,
            stops=solution.get("stops", []),
            frequency_minutes=solution["frequency"],
            vehicle_assignments=[f"vehicle_{i}" for i in range(solution.get("num_vehicles", 5))],
            expected_wait_time=solution["frequency"] / 2,
            expected_travel_time=len(solution.get("stops", [])) * 2.5,  # 2.5 min per stop
            capacity_utilization=0.75,  # Estimated
            improvement_percentage=improvement,
            modifications=modifications
        )

    def _get_current_route(self, route_id: str) -> Dict:
        """Get current route configuration."""
        # Would fetch from database
        return {
            "route_id": route_id,
            "stops": [f"stop_{i}" for i in range(1, 21)],
            "frequency": 15,  # minutes
            "num_vehicles": 5,
            "pattern": "local"
        }

    def _find_nearest_vehicle(self, location: str, available: List[str], positions: Dict) -> Optional[str]:
        """Find nearest available vehicle to a location."""
        if not available:
            return None

        min_distance = float('inf')
        nearest = None

        for vehicle in available:
            if vehicle in positions:
                distance = self._calculate_distance(positions[vehicle], location)
                if distance < min_distance:
                    min_distance = distance
                    nearest = vehicle

        return nearest

    def _estimate_travel_time(self, from_loc: str, to_loc: str) -> str:
        """Estimate travel time between locations."""
        # Simplified - would use actual routing
        distance = self._calculate_distance(from_loc, to_loc)
        travel_minutes = distance * 3  # Assume 3 minutes per unit distance
        arrival_time = datetime.now() + timedelta(minutes=travel_minutes)
        return arrival_time.isoformat()

    def _calculate_distance(self, loc1: str, loc2: str) -> float:
        """Calculate distance between two locations."""
        # Simplified - would use actual geographic distance
        return abs(hash(loc1) % 10 - hash(loc2) % 10)

    def _initialize_simulation(self, routes: List[Dict], state: Dict) -> Dict:
        """Initialize simulation state."""
        # Set up vehicles
        vehicle_id = 0
        for route in routes:
            for _ in range(route.get("num_vehicles", 5)):
                state["vehicles"][f"vehicle_{vehicle_id}"] = {
                    "route_id": route["route_id"],
                    "current_stop": 0,
                    "passengers": [],
                    "capacity": 60
                }
                vehicle_id += 1

        # Set up stops
        for route in routes:
            for stop in route.get("stops", []):
                if stop not in state["stops"]:
                    state["stops"][stop] = {
                        "waiting_passengers": [],
                        "routes": []
                    }
                state["stops"][stop]["routes"].append(route["route_id"])

        return state

    def _generate_passengers(self, demand_data: Dict, current_time: datetime) -> List[Dict]:
        """Generate new passengers based on demand."""
        passengers = []
        hour = current_time.hour

        # Generate passengers based on hourly demand
        for stop_id, demand in demand_data.items():
            hourly_demand = demand.get(hour, 10)
            num_passengers = np.random.poisson(hourly_demand / 60)  # Per minute

            for _ in range(num_passengers):
                passengers.append({
                    "id": f"p_{len(passengers)}",
                    "origin": stop_id,
                    "destination": random.choice(list(demand_data.keys())),
                    "arrival_time": current_time,
                    "wait_time": 0,
                    "travel_time": 0
                })

        return passengers

    def _move_vehicles(self, state: Dict, time_step: timedelta) -> Dict:
        """Move vehicles along their routes."""
        for vehicle_id, vehicle in state["vehicles"].items():
            # Simple movement: advance to next stop every 3 minutes
            if random.random() < 0.33:  # 1/3 chance per minute
                vehicle["current_stop"] = (vehicle["current_stop"] + 1) % 20

        return state

    def _handle_passenger_flow(self, state: Dict) -> Dict:
        """Handle passenger boarding and alighting."""
        for vehicle_id, vehicle in state["vehicles"].items():
            current_stop = f"stop_{vehicle['current_stop'] + 1}"

            # Alight passengers
            vehicle["passengers"] = [
                p for p in vehicle["passengers"]
                if p["destination"] != current_stop
            ]

            # Board passengers
            if current_stop in state["stops"]:
                waiting = state["stops"][current_stop]["waiting_passengers"]
                capacity_available = vehicle["capacity"] - len(vehicle["passengers"])

                boarding = waiting[:capacity_available]
                vehicle["passengers"].extend(boarding)
                state["stops"][current_stop]["waiting_passengers"] = waiting[capacity_available:]

                # Update metrics
                for passenger in boarding:
                    state["metrics"]["total_served"] += 1

        return state

    def _update_metrics(self, state: Dict) -> Dict:
        """Update simulation metrics."""
        # Update wait times
        for stop in state["stops"].values():
            for passenger in stop["waiting_passengers"]:
                passenger["wait_time"] += 1

        # Update travel times
        for vehicle in state["vehicles"].values():
            for passenger in vehicle["passengers"]:
                passenger["travel_time"] += 1

        # Check for crowding
        for vehicle in state["vehicles"].values():
            if len(vehicle["passengers"]) > vehicle["capacity"] * 0.9:
                state["metrics"]["crowding_events"] += 1

        return state

    def _calculate_simulation_results(self, state: Dict) -> SimulationResult:
        """Calculate final simulation results."""
        metrics = state["metrics"]

        return SimulationResult(
            total_passengers_served=metrics["total_served"],
            average_wait_time=metrics["total_wait_time"] / max(metrics["total_served"], 1),
            average_travel_time=metrics["total_travel_time"] / max(metrics["total_served"], 1),
            on_time_performance=0.85,  # Simplified
            crowding_incidents=metrics["crowding_events"],
            total_delay_minutes=metrics["delays"],
            efficiency_score=min(100, metrics["total_served"] / 100)
        )