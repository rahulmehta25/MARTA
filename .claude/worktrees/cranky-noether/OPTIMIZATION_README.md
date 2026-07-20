# MARTA Route Optimization & Simulation Engine

## 🚇 Overview

The MARTA Route Optimization & Simulation Engine is a comprehensive system that uses machine learning predictions to optimize transit routes and simulate their impact. This system provides data-driven recommendations for route improvements, including short-turn loops, headway optimizations, and network-wide enhancements.

## 🏗️ Architecture

### Core Components

1. **Route Optimizer** (`src/optimization/route_optimizer.py`)
   - Uses ML predictions to identify overloaded segments
   - Proposes short-turn loops and headway optimizations
   - Calculates impact metrics and cost savings

2. **Route Simulator** (`src/optimization/route_simulator.py`)
   - Discrete event simulation of transit operations
   - Models passenger demand, bus operations, and service quality
   - Compares baseline vs optimized scenarios

3. **Optimization Orchestrator** (`src/optimization/optimization_orchestrator.py`)
   - Coordinates the optimization workflow
   - Manages script execution and result collection
   - Generates comprehensive reports

4. **Runner Script** (`run_optimization.py`)
   - Simple interface to execute the complete workflow
   - Handles error checking and user feedback

## 🚀 Quick Start

### Prerequisites

1. **Database Setup**: Ensure GTFS data is loaded in PostgreSQL
2. **ML Models**: Train and save ML models (optional, fallback methods available)
3. **Dependencies**: Install required packages

```bash
# Install optimization dependencies
pip install simpy scipy networkx shapely

# Ensure database is running and accessible
export DB_HOST=localhost
export DB_NAME=marta_db
export DB_USER=marta_user
export DB_PASSWORD=marta_password
```

### Running the Optimization

```bash
# Execute complete optimization workflow
python run_optimization.py
```

This will:
1. Check data availability
2. Run route optimization using ML predictions
3. Simulate baseline and optimized scenarios
4. Generate comprehensive reports
5. Save results to files

## 📊 Optimization Features

### 1. Demand-Based Route Optimization

The system uses ML predictions to identify:
- **Overloaded Segments**: Routes/stops with predicted high demand
- **Peak Hour Patterns**: Time-based demand variations
- **Service Gaps**: Areas with insufficient service

### 2. Short-Turn Loop Proposals

For overloaded segments, the system proposes:
- **Turnaround Points**: Strategic locations for route termination
- **Feasibility Analysis**: Physical and operational constraints
- **Impact Assessment**: Expected demand reduction and cost savings

### 3. Headway Optimization

Based on predicted demand, the system recommends:
- **Optimal Frequencies**: Bus arrival intervals
- **Peak vs Off-Peak**: Different service levels
- **Resource Allocation**: Bus deployment strategies

### 4. Network-Wide Analysis

The system provides:
- **Overall Impact Metrics**: System-wide improvements
- **Cost-Benefit Analysis**: Financial implications
- **Operational Efficiency**: Resource utilization improvements

## 🎮 Simulation Capabilities

### Discrete Event Simulation

The simulation engine models:
- **Passenger Arrivals**: Time-based demand generation
- **Bus Operations**: Route traversal and scheduling
- **Passenger Boarding/Alighting**: Capacity constraints
- **Service Quality**: Wait times and satisfaction

### Key Metrics

The simulation tracks:
- **Average Wait Time**: Passenger experience metric
- **Passenger Satisfaction**: Service quality indicator
- **Vehicle Utilization**: Resource efficiency
- **On-Time Performance**: Schedule adherence
- **Load Factor**: Capacity utilization

### Scenario Comparison

The system compares:
- **Baseline Scenario**: Current route configuration
- **Optimized Scenario**: Proposed improvements
- **Impact Quantification**: Measurable improvements

## 📈 Output and Reports

### Generated Files

1. **Optimization Results** (`optimization_results_YYYYMMDD_HHMMSS.pkl`)
   - Route optimization proposals
   - Impact metrics and cost analysis
   - Feasibility scores

2. **Simulation Results** (`simulation_results_YYYYMMDD_HHMMSS.pkl`)
   - Performance metrics
   - Scenario comparisons
   - Statistical analysis

3. **Workflow Summary** (`optimization_workflow_results_YYYYMMDD_HHMMSS.pkl`)
   - Complete workflow execution log
   - Success/failure status
   - Execution times

### Report Contents

The system generates comprehensive reports including:
- **Executive Summary**: High-level findings and recommendations
- **Technical Details**: Optimization algorithms and parameters
- **Financial Impact**: Cost savings and revenue implications
- **Operational Impact**: Service quality improvements
- **Implementation Guidance**: Next steps and considerations

## ⚙️ Configuration

### Optimization Parameters

```python
OPTIMIZATION_CONFIG = {
    'max_short_turns': 3,        # Maximum short-turn loops per route
    'max_detour_time': 15,       # Maximum detour time (minutes)
    'min_headway': 5,            # Minimum headway (minutes)
    'max_headway': 30,           # Maximum headway (minutes)
    'bus_capacity': 50,          # Bus capacity (passengers)
    'overload_threshold': 0.8,   # 80% capacity threshold
    'optimization_timeout': 300, # 5 minutes timeout
    'population_size': 50,       # Genetic algorithm population
    'generations': 100           # Genetic algorithm generations
}
```

### Simulation Parameters

```python
SIMULATION_CONFIG = {
    'simulation_hours': 24,      # Hours to simulate
    'time_step': 1,              # Minutes per time step
    'bus_capacity': 50,          # Passengers per bus
    'max_wait_time': 30,         # Maximum acceptable wait time
    'boarding_time': 2,          # Seconds per passenger boarding
    'alighting_time': 1,         # Seconds per passenger alighting
    'travel_speed': 20,          # Average speed (mph)
    'random_seed': 42            # For reproducible results
}
```

## 🔧 Advanced Usage

### Custom Optimization Workflows

You can modify the optimization workflow by editing `OPTIMIZATION_WORKFLOW` in the orchestrator:

```python
OPTIMIZATION_WORKFLOW = [
    {
        'name': 'Custom Optimization',
        'script': 'path/to/custom_script.py',
        'description': 'Custom optimization logic',
        'required': True,
        'timeout': 600
    }
]
```

### Integration with ML Models

The system integrates with trained ML models for:
- **Demand Prediction**: Stop-level demand forecasting
- **Dwell Time Prediction**: Stop service time estimation
- **Load Classification**: Overload detection

### Custom Simulation Scenarios

You can create custom simulation scenarios by:
1. Modifying passenger demand generation
2. Adjusting bus schedules and capacities
3. Adding custom optimization proposals
4. Implementing new performance metrics

## 📋 Implementation Guidelines

### 1. Data Requirements

Ensure the following data is available:
- **GTFS Static Data**: Routes, stops, trips, schedules
- **ML Features**: Engineered features for prediction
- **Historical Data**: Past performance metrics

### 2. Model Training

Before running optimization:
1. Train demand prediction models
2. Train dwell time prediction models
3. Validate model performance
4. Save models in the expected format

### 3. Validation Process

After optimization:
1. Review optimization proposals
2. Validate simulation results
3. Compare with business requirements
4. Plan implementation strategy

### 4. Production Deployment

For production use:
1. Set up automated scheduling
2. Implement monitoring and alerting
3. Create feedback loops
4. Establish review processes

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify database credentials
   - Check network connectivity
   - Ensure database is running

2. **Missing ML Models**
   - Train models first using `run_model_training.py`
   - Check model file paths
   - Verify model format compatibility

3. **Simulation Timeouts**
   - Reduce simulation hours
   - Increase timeout values
   - Optimize simulation parameters

4. **Memory Issues**
   - Reduce data sample sizes
   - Increase system resources
   - Optimize data processing

### Debug Mode

Enable detailed logging by modifying the logging configuration:

```python
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## 🔮 Future Enhancements

### Planned Features

1. **Real-Time Optimization**
   - Live demand monitoring
   - Dynamic route adjustments
   - Real-time simulation updates

2. **Advanced Algorithms**
   - Multi-objective optimization
   - Genetic algorithms
   - Reinforcement learning

3. **Integration Capabilities**
   - API endpoints for external systems
   - Real-time data feeds
   - Automated implementation

4. **Enhanced Visualization**
   - Interactive dashboards
   - Geographic visualization
   - Real-time monitoring

### Research Areas

1. **Predictive Analytics**
   - Event-based demand prediction
   - Weather impact modeling
   - Seasonal pattern analysis

2. **Optimization Algorithms**
   - Multi-modal optimization
   - Network effects modeling
   - Stochastic optimization

3. **Simulation Improvements**
   - Agent-based modeling
   - Microsimulation
   - Real-time calibration

## 📞 Support

For technical support or questions:
1. Check the logs in the `logs/` directory
2. Review the generated reports
3. Consult the troubleshooting section
4. Contact the development team

## 📄 License

This optimization engine is part of the MARTA Demand Forecasting & Route Optimization Platform. Please refer to the main project license for usage terms and conditions. 