"""
Route optimization service.
"""
import random
from datetime import datetime
from typing import Dict, List, Optional, Any

from backend.api.core.logging import get_logger
from backend.api.models.routes import HeadwayOptimization, ShortTurnProposal

logger = get_logger(__name__)


class OptimizationService:
    """Service for route optimization."""

    def __init__(self):
        self.optimizer = None
        self._load_optimizer()

    def _load_optimizer(self):
        """Load route optimizer."""
        try:
            from src.optimization.route_optimizer import RouteOptimizer
            self.optimizer = RouteOptimizer()
            self.optimizer.load_route_data()
            self.optimizer.load_ml_models()
            logger.info("Loaded route optimizer")
        except Exception as e:
            logger.warning(f"Could not load route optimizer: {e}")
            self.optimizer = None

    async def optimize_headways(
        self,
        route_ids: List[str],
        target_time: datetime,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> List[HeadwayOptimization]:
        """Optimize headways for given routes."""
        logger.info(
            "Optimizing headways",
            routes=len(route_ids),
            target_time=target_time,
        )

        results = []

        if self.optimizer is not None:
            try:
                for route_id in route_ids:
                    opt = self.optimizer.optimize_headways(route_id, target_time)
                    if opt:
                        results.append(HeadwayOptimization(
                            route_id=route_id,
                            current_headway_minutes=opt.get("current_headway", 15),
                            optimal_headway_minutes=opt.get("optimal_headway", 12),
                            demand_level=opt.get("demand_level", "Normal"),
                            recommended_frequency=opt.get("recommended_frequency", 5),
                        ))
                return results
            except Exception as e:
                logger.error(f"Headway optimization failed: {e}")

        # Generate demo results
        return self.generate_demo_headway_results(route_ids)

    async def propose_short_turns(
        self,
        route_ids: List[str],
        target_time: datetime,
    ) -> List[ShortTurnProposal]:
        """Propose short-turn loops for congested segments."""
        logger.info(
            "Proposing short turns",
            routes=len(route_ids),
        )

        if self.optimizer is not None:
            try:
                all_proposals = []
                for route_id in route_ids:
                    segments = self.optimizer.identify_overloaded_segments(
                        route_id, target_time
                    )
                    if segments:
                        proposals = self.optimizer.propose_short_turn_loops(
                            route_id, segments
                        )
                        for p in proposals:
                            all_proposals.append(ShortTurnProposal(
                                route_id=p["route_id"],
                                start_stop_id=p["start_stop_id"],
                                end_stop_id=p["end_stop_id"],
                                turnaround_stop_id=p["turnaround_stop_id"],
                                feasibility_score=p["feasibility_score"],
                                estimated_impact=p["estimated_impact"],
                            ))
                return all_proposals
            except Exception as e:
                logger.error(f"Short turn proposal failed: {e}")

        return self.generate_demo_short_turns()

    def calculate_impact(
        self,
        headway_optimizations: List[HeadwayOptimization],
        short_turn_proposals: List[ShortTurnProposal],
    ) -> Dict[str, float]:
        """Calculate overall impact of optimizations."""
        total_wait_reduction = 0.0
        total_cost_savings = 0.0

        for opt in headway_optimizations:
            diff = opt.current_headway_minutes - opt.optimal_headway_minutes
            if diff > 0:
                # Each minute of headway reduction saves ~2 min average wait
                total_wait_reduction += diff * 0.5
                total_cost_savings += diff * 50  # $50 per minute saved

        for proposal in short_turn_proposals:
            impact = proposal.estimated_impact
            total_wait_reduction += impact.get("wait_time_reduction", 0)
            total_cost_savings += impact.get("cost_savings", 0)

        return {
            "wait_time_reduction_minutes": round(total_wait_reduction, 1),
            "cost_savings_dollars": round(total_cost_savings, 0),
            "capacity_improvement_percent": round(len(short_turn_proposals) * 3.5, 1),
            "routes_optimized": len(headway_optimizations),
            "short_turns_proposed": len(short_turn_proposals),
        }

    def generate_demo_headway_results(
        self,
        route_ids: Optional[List[str]] = None,
    ) -> List[HeadwayOptimization]:
        """Generate demo headway optimization results."""
        if not route_ids:
            route_ids = ["BLUE", "RED", "GOLD", "GREEN"]

        results = []
        for route_id in route_ids[:5]:  # Limit to 5
            current = random.uniform(12, 20)
            optimal = current - random.uniform(1, 4)
            demand_levels = ["Low", "Normal", "High"]

            results.append(HeadwayOptimization(
                route_id=route_id,
                current_headway_minutes=round(current, 1),
                optimal_headway_minutes=round(max(5, optimal), 1),
                demand_level=random.choice(demand_levels),
                recommended_frequency=round(60 / optimal, 1),
                expected_wait_time_reduction_minutes=round((current - optimal) / 2, 1),
            ))

        return results

    def generate_demo_short_turns(self) -> List[ShortTurnProposal]:
        """Generate demo short-turn proposals."""
        return [
            ShortTurnProposal(
                route_id="BLUE",
                start_stop_id="FIVE_POINTS",
                end_stop_id="HAMILTON_E_HOLMES",
                turnaround_stop_id="VINE_CITY",
                feasibility_score=0.85,
                estimated_impact={
                    "demand_reduction": 0.25,
                    "wait_time_reduction": 2.5,
                    "cost_savings": 500,
                },
            ),
            ShortTurnProposal(
                route_id="RED",
                start_stop_id="NORTH_SPRINGS",
                end_stop_id="AIRPORT",
                turnaround_stop_id="LINDBERGH",
                feasibility_score=0.72,
                estimated_impact={
                    "demand_reduction": 0.20,
                    "wait_time_reduction": 2.0,
                    "cost_savings": 400,
                },
            ),
        ]
