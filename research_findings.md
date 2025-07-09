# Research Findings

## 1. General ML System Architecture Patterns

Machine Learning (ML) architecture refers to the structured organization of components and processes within an ML system. A well-designed architecture is crucial for building scalable, maintainable, and efficient ML applications. Key considerations include data processing, model training and evaluation, and prediction generation. The specific architecture often depends on the unique use case and system requirements.

### Core Components:

*   **Data Ingestion**: The process of acquiring and preparing data for ML models. This involves:
    *   **Data Collection**: Gathering information from various sources (databases, APIs, sensors, external datasets).
    *   **Data Cleansing**: Identifying and correcting errors, inconsistencies, or missing values to ensure high data quality.
    *   **Data Transformation**: Converting raw data into a suitable format for ML algorithms, often to improve performance (e.g., in NLP applications).
    *   **Data Integration**: Merging data from multiple sources into a unified dataset.
    *   **Data Sampling**: Selecting a representative subset of data for training, especially for large datasets, to ensure balanced representation.
    *   **Data Splitting**: Partitioning data into training, validation, and testing sets to evaluate model performance and prevent overfitting.
    
    Common ingestion types include batch, real-time, Change Data Capture (CDC), and streaming. Popular tools include Apache Kafka, Apache Spark, Amazon S3, Apache Nifi, Google Cloud Dataflow.

*   **Data Storage**: Critical for all phases of an ML project, accommodating various dataset versions and model experiments. Storage solutions must be:
    *   **Scalable**: Able to handle increasing data volumes without significant adjustments.
    *   **Available**: Ensuring timely access and processing of data requests.
    *   **Secure**: Protecting data at rest and in transit, with authentication, authorization, encryption, and retention policies.
    *   **Performant**: Optimized for high throughput and minimal latency, especially crucial during model training.
    
    Common storage environments include local file storage (for PoC), Network-Attached Storage (NAS), Storage-Area Networks (SAN), Distributed File Systems (DFS) like HDFS, and Object Storage (e.g., Amazon S3, Azure Blob Storage, Google Cloud Storage).

*   **Data Processing/Feature Engineering**: Transforming raw data into features that can be used by ML models. This often involves statistical methods, aggregation, and domain-specific transformations.

*   **Model Training and Evaluation**: The process of feeding prepared data to ML algorithms to learn patterns and relationships, followed by assessing the model's performance using evaluation metrics.

*   **Model Deployment and Serving**: Making the trained model available for predictions in a production environment. This can involve batch predictions, real-time API endpoints, or edge deployments.

*   **Monitoring and Feedback Loop**: Continuously tracking model performance, data drift, and system health in production. The feedback loop involves retraining models with new data to maintain accuracy and relevance.

### Design Principles for MLOps:

Many software engineering principles apply to MLOps (Machine Learning Operations):

*   **Separation of Concerns**: Components should be designed to perform a single, well-defined task.
*   **Principle of Least Surprise**: Architecture should be intuitive and predictable to those with domain knowledge.
*   **Principle of Least Effort**: Design should be as simple as possible to encourage adoption and reduce shortcuts.
*   **SOLID Principles (adapted for ML systems)**:
    *   **Single Responsibility**: Each module or component should have only one reason to change.
    *   **Open/Closed**: Components should be open for extension but closed for modification.
    *   **Liskov Substitution**: Components should be replaceable by their subtypes without altering system correctness.
    *   **Interface Segregation**: Clients should not be forced to depend on interfaces they do not use.
    *   **Dependency Inversion**: High-level modules should not depend on low-level modules; both should depend on abstractions.

## 2. Data Ingestion & Normalization for GTFS and GTFS-RT

### GTFS Static Data Ingestion:

GTFS (General Transit Feed Specification) static data provides information about public transit schedules, routes, stops, and other static elements. It typically comes as a ZIP archive containing several CSV files.

*   **Best Practices for Ingestion**: 
    *   **Relational Database Schema**: Ingesting GTFS static data into a relational database (e.g., PostgreSQL, SQLite) is a common and effective approach. This allows for efficient querying and joining of data across different tables (`stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`, `shapes.txt`).
    *   **Data Validation**: Before ingestion, validate the GTFS data against the official GTFS specification to ensure compliance and identify any errors or inconsistencies. Tools like `gtfs-validator` can be used.
    *   **Indexing**: Properly index relevant columns (e.g., `stop_id`, `route_id`, `trip_id`) in the database to optimize query performance.
    *   **ETL Pipelines**: Use ETL (Extract, Transform, Load) pipelines to automate the process of downloading, unzipping, parsing, and loading GTFS data into the database. Apache Airflow is a popular choice for orchestrating such pipelines.

### GTFS-Realtime (GTFS-RT) Data Ingestion & Normalization:

GTFS-RT provides real-time updates on vehicle positions, trip updates, and service alerts. It is typically delivered in Protocol Buffer format.

*   **Continuous Ingestion**: GTFS-RT feeds are dynamic and require continuous or frequent batch ingestion to capture real-time changes. This can be achieved through polling the GTFS-RT API at regular intervals (e.g., every 10-30 seconds).
*   **Protocol Buffer Parsing**: Use `gtfs-realtime-bindings` (available in Python and other languages) to parse the Protocol Buffer messages into a more usable format (e.g., Python objects, JSON).
*   **Normalization and Unification**: The goal is to normalize the real-time data and unify it with the static GTFS data. This involves:
    *   **Joining Data**: Join GTFS-RT data (e.g., `vehicle_positions`, `trip_updates`) with GTFS static data using common identifiers like `trip_id` and `route_id`.
    *   **Timestamping**: Ensure all real-time records are timestamped accurately to maintain temporal context.
    *   **Unified Schema**: Create a unified data schema that combines static and real-time information, including fields like `trip_id`, `stop_id`, `timestamp`, `route_id`, `lat/lon`, `vehicle_id`, `delay`, `stop_sequence`.
    *   **Handling Delays and Cancellations**: Process `TripUpdates` to reflect actual arrival/departure times and identify delays or cancellations. This often involves comparing scheduled times from static GTFS with real-time predictions.
    *   **Data Freshness**: GTFS-RT best practices suggest that data should not be older than 90 seconds for Vehicle Positions and Trip Updates, and not older than 10 minutes for Service Alerts. Implement mechanisms to discard or flag stale data.
*   **Storage for Real-time Data**: Given the continuous nature, consider time-series databases or data lakes for storing raw and processed GTFS-RT data. This allows for historical analysis and efficient querying of time-stamped events.

## 3. Reconstructing Historical Trips and Inferring Demand from Dwell Time

### Reconstructing Historical Trips:

Reconstructing historical trips involves combining static GTFS schedule data with real-time GTFS-RT data to get a true picture of past transit operations.

*   **Matching Static and Real-time Data**: The core of this step is to accurately match `TripUpdates` and `VehiclePositions` from GTFS-RT to their corresponding scheduled `trips` and `stop_times` in the static GTFS data. This can be challenging due to potential discrepancies or missing data.
    *   **`trip_id` and `stop_sequence`**: Use these fields to link real-time updates to specific stops within a scheduled trip.
    *   **Temporal Alignment**: Align real-time events (vehicle arrivals/departures) with scheduled times. Calculate deviations (delays or early arrivals).
*   **Estimating Dwell Times**: Dwell time is the duration a vehicle spends at a stop. It's a crucial indicator for inferring demand.
    *   **Arrival vs. Departure Times**: If available in GTFS-RT `stop_time_updates`, the difference between actual arrival and departure times at a stop provides a direct measure of dwell time.
    *   **Vehicle Position Stalling**: If precise arrival/departure times are not available, infer dwell time by observing `VehiclePositions`. When a vehicle's `lat/lon` coordinates remain constant (or within a small radius) near a `stop_id` for a certain duration, it indicates a dwell event.
    *   **GPS Data Analysis**: For more granular analysis, processing raw GPS data from vehicles can provide highly accurate dwell time estimations by identifying periods of zero or near-zero speed at designated stops.

### Inferring Demand from Dwell Time:

Dwell time can serve as a proxy for rider demand, especially when direct Automatic Passenger Counter (APC) data is unavailable. Longer dwell times often correlate with higher boarding/alighting volumes.

*   **Correlation Analysis**: Conduct statistical analysis to establish the relationship between observed dwell times and known ridership metrics (e.g., monthly KPI reports). This can help in calibrating the inferred demand.
*   **Modeling Dwell Time**: Develop models that predict dwell time based on various factors (time of day, day of week, stop location, route, vehicle type, and potentially inferred demand). Conversely, these models can be inverted or used in a Bayesian framework to infer demand from observed dwell times.
*   **Heuristic Rules**: Simple heuristic rules can be applied initially:
    *   *Increased Dwell Time = Increased Demand*: A longer-than-average dwell time at a stop suggests higher boarding/alighting activity.
    *   *Thresholding*: Define thresholds for dwell time to categorize demand levels (e.g., short dwell = low demand, medium dwell = normal demand, long dwell = high demand/overcrowding).
*   **Limitations**: It's important to acknowledge that dwell time is an imperfect proxy. Factors like operational issues, driver behavior, or accessibility needs can also influence dwell time, so it should be used in conjunction with other data sources if possible.

## 4. Feature Engineering

Feature engineering is the process of transforming raw data into features that better represent the underlying problem to predictive models, leading to improved model performance. For transit demand forecasting, both time-series and spatial features are critical.

### Trip-Level Features:

These features describe characteristics of individual trips.

*   **Temporal Features**: Extract from `trips.txt` and real-time data:
    *   `day_of_week`: (Monday, Tuesday, etc.) - important for weekly patterns.
    *   `hour_of_day`: (0-23) - crucial for daily peaks and troughs.
    *   `is_weekend`/`is_holiday`: Binary flags for special days.
    *   `start_time`: Scheduled start time of the trip.
    *   `trip_duration`: Calculated from `stop_times.txt` or real-time `TripUpdates`.
*   **Operational Features**: From `trips.txt` and `GTFS-RT`:
    *   `route_id`, `trip_id`.
    *   `delay_minutes`: Difference between actual and scheduled arrival/departure times.
    *   `realized_vs_scheduled_time_diff`: A measure of adherence to schedule.
    *   `trip_distance`: Calculated from `shapes.txt` (sum of segment lengths for the trip's shape).
    *   `vehicle_id`: If available, can capture vehicle-specific performance.

### Stop-Level Features:

These features describe characteristics of individual stops.

*   **Geospatial Features**: From `stops.txt` and GIS layers:
    *   `stop_id`, `stop_lat`, `stop_lon`.
    *   `stop_sequence`: Order of the stop within a trip.
    *   `zone_id`: Assigning stops to predefined geographic zones (e.g., based on Atlanta Regional Commission GIS data) for spatial aggregation and modeling.
    *   `nearby_POIs_count`: Number of Points of Interest (e.g., commercial, residential, educational) within a certain radius of the stop (can be derived from OpenStreetMap data).
    *   `distance_to_CBD`: Distance from the stop to the Central Business District or other key attractors.
*   **Historical Performance Features**: Derived from reconstructed historical trips:
    *   `historical_dwell_time`: Average, median, or percentile dwell times at a specific stop for similar time periods (e.g., average dwell time on a Tuesday morning).
    *   `historical_headway`: Average time between consecutive vehicles on a route at a specific stop.
    *   `historical_ridership`: If any historical ridership data is available (e.g., from monthly KPI reports, even if aggregated), it can be used to create features like `average_monthly_boardings_at_stop`.

### Contextual Features:

These features capture external factors influencing demand.

*   **Weather Data**: From OpenWeatherMap API or NOAA data for Atlanta:
    *   `temperature` (Celsius/Fahrenheit).
    *   `precipitation` (rain, snow, etc.).
    *   `weather_condition` (e.g., clear, cloudy, rainy, snowy).
    *   `wind_speed`, `humidity`.
*   **Event Data**: Scraped from event schedules for major venues:
    *   `event_flag`: Binary flag indicating if a major event is occurring near a stop or along a route.
    *   `event_type`: Categorical feature (e.g., concert, sports game, convention).
    *   `estimated_attendance`: If available, can be a numerical feature.
*   **Socio-economic Data (Optional)**: From census data or other demographic sources:
    *   `population_density_around_stop`.
    *   `income_level_around_stop`.
    *   `employment_density_around_stop`.

### Time-Series Specific Feature Engineering:

*   **Lag Features**: Past values of the target variable (demand) or other relevant features. For example, demand at `stop_id` `X` at `t-1` hour, `t-24` hours, `t-7` days.
*   **Rolling Window Statistics**: Mean, median, min, max, standard deviation of features over a defined past window (e.g., average demand over the last 3 hours).
*   **Cyclical Features**: Encode cyclical temporal features (hour of day, day of week, month of year) using sine and cosine transformations to preserve their cyclical nature and avoid arbitrary ordering.
    *   `sin(2 * pi * hour / 24)`, `cos(2 * pi * hour / 24)`
*   **Trend Features**: Linear or non-linear trends over time.

## 5. Demand Forecasting Models

### LSTM (Long Short-Term Memory Networks):

*   **Type**: A type of Recurrent Neural Network (RNN) particularly well-suited for sequence prediction problems due to their ability to learn long-term dependencies.
*   **Application**: Ideal for forecasting time-series data like rider demand, where past patterns influence future values.
*   **Best Practices**: 
    *   **Data Preprocessing**: Normalize or scale input data (e.g., Min-Max scaling, StandardScaler) to improve training stability and performance.
    *   **Sequence Length**: Determine an appropriate look-back window (sequence length) for the LSTM input, representing how many past time steps are used to predict the next.
    *   **Architecture**: Experiment with the number of LSTM layers, units per layer, and dropout rates to prevent overfitting.
    *   **Stateful vs. Stateless**: For continuous time series, stateful LSTMs can maintain internal state across batches, which might be beneficial but requires careful handling of batching and resetting states.
    *   **Hyperparameter Tuning**: Optimize learning rate, batch size, number of epochs, and optimizer (e.g., Adam).
    *   **Output Layer**: For regression (predicting rider count), a dense layer with a linear activation function is typically used. For classification (overloaded/normal/underloaded), a softmax activation with appropriate loss function.

### XGBoost (Extreme Gradient Boosting):

*   **Type**: A highly efficient and scalable implementation of gradient boosting machines, known for its speed and performance in structured data tasks.
*   **Application**: Can be effectively used for time-series forecasting by transforming the problem into a supervised learning task using lag features and other engineered features.
*   **Best Practices**: 
    *   **Feature Engineering**: XGBoost thrives on well-engineered features. Lag features, rolling window statistics, and temporal indicators (day of week, hour of day) are crucial.
    *   **Cross-Validation**: Use time-series specific cross-validation techniques (e.g., rolling origin cross-validation) to ensure the model generalizes well to future data.
    *   **Hyperparameter Tuning**: Tune parameters like `n_estimators`, `learning_rate`, `max_depth`, `subsample`, `colsample_bytree`, and `reg_alpha`/`reg_lambda`.
    *   **Handling Categorical Features**: Encode categorical features (e.g., one-hot encoding, label encoding) before feeding them to XGBoost.
    *   **Early Stopping**: Use early stopping during training to prevent overfitting and find the optimal number of boosting rounds.

### Spatio-Temporal Graph Convolutional Networks (STGCN) + LSTM Hybrid:

*   **Type**: Advanced models designed to capture both spatial dependencies (e.g., relationships between nearby stops) and temporal dependencies (time-series patterns) in data.
*   **Application**: Ideal for complex demand forecasting in transit networks where demand at one stop is influenced by demand at neighboring stops and historical patterns.
*   **Architecture**: 
    *   **Graph Convolutional Network (GCN)**: Processes the spatial relationships. The transit network (stops as nodes, routes as edges) can be represented as a graph. GCNs learn features by aggregating information from a node's neighbors.
    *   **Temporal Component (e.g., LSTM, CNN)**: Processes the time-series aspect of the data. An LSTM layer can follow the GCN output to capture temporal dynamics.
*   **Best Practices**: 
    *   **Graph Construction**: Define the adjacency matrix for the graph, representing connections between stops (e.g., direct route connections, proximity).
    *   **Data Representation**: Input data needs to be structured as a sequence of graph signals, where each node (stop) has a time-series of features (e.g., historical demand, weather).
    *   **Computational Resources**: STGCNs can be computationally intensive, requiring GPUs for efficient training.
    *   **Frameworks**: Libraries like PyTorch Geometric (PyG) or Deep Graph Library (DGL) provide implementations for GCNs and other graph neural networks.
    *   **Hybrid Models**: Combining GCNs with LSTMs or 1D CNNs allows for capturing both spatial and temporal patterns effectively. The GCN can extract spatial features at each time step, which are then fed into the LSTM/CNN for temporal modeling.

## 6. Route Optimization Algorithms and Simulation Techniques

### Route Optimization Algorithms:

Route optimization aims to find the most efficient paths for vehicles, considering various constraints (e.g., capacity, time windows, demand). For the MARTA system, this involves optimizing routes based on forecasted demand to reduce congestion and improve service efficiency.

*   **Heuristic Algorithms**: These algorithms aim to find good, but not necessarily optimal, solutions within a reasonable computation time. They are often used for complex problems where finding the exact optimal solution is computationally intractable.
    *   **Greedy Algorithms**: Make the locally optimal choice at each step with the hope of finding a global optimum. For route optimization, a greedy approach might involve always selecting the closest unvisited stop or the stop with the highest predicted demand. While simple and fast, they can get stuck in local optima.
    *   **Examples**: Nearest Neighbor, Savings Algorithm (Clarke and Wright).
*   **Metaheuristic Algorithms**: Higher-level procedures that guide a subordinate heuristic to search for optimal solutions. They are designed to escape local optima.
    *   **Tabu Search**: Explores the solution space by moving from one solution to a better one, while using a 



### Simulation Techniques:

Simulation is crucial for evaluating the effectiveness of proposed route optimizations before real-world implementation. It allows for testing different scenarios and assessing their impact on key metrics.

*   **Discrete Event Simulation (DES)**: Models the system as a sequence of events occurring over time. For transit, events could include vehicle departures, arrivals, passenger boardings/alightings, and delays. DES can simulate the movement of individual vehicles and passengers, capturing complex interactions.
*   **Agent-Based Modeling (ABM)**: Simulates the actions and interactions of autonomous agents (e.g., individual passengers, vehicles) to assess their effects on the system as a whole. ABM can be used to model passenger behavior (route choice, waiting times) and vehicle movements under different optimization strategies.
*   **Traffic Flow Simulation**: Utilizes macroscopic or microscopic models to simulate traffic patterns and congestion, providing insights into how route changes might affect overall network flow.
*   **Key Metrics for Simulation**: 
    *   **Passenger Wait Time**: Average and maximum waiting times at stops.
    *   **Coverage Score**: How well the optimized routes cover demand hotspots.
    *   **Vehicle Utilization**: Efficiency of vehicle deployment.
    *   **Travel Time Reliability**: Consistency of travel times.
    *   **Operational Costs**: Fuel consumption, driver hours.

## 7. Visualization & Validation Tools

Interactive dashboards are essential for visualizing predicted demand, simulated route changes, and comparing KPIs with actual metrics. Streamlit, Dash, Plotly, and Folium are excellent Python-based tools for this purpose.

### Streamlit:

*   **Overview**: An open-source Python framework that allows data scientists and ML engineers to quickly build and share interactive web applications and dashboards with minimal code.
*   **Strengths**: Simplicity, rapid prototyping, Python-native, easy deployment.
*   **Use Cases**: Building interactive dashboards for predicted vs. actual heatmaps, displaying model performance metrics, and allowing users to interact with simulation parameters.

### Dash (Plotly Dash):

*   **Overview**: A productive Python framework for building analytical web applications. It's built on top of Flask, React.js, and Plotly.js.
*   **Strengths**: Highly customizable, powerful for complex interactive dashboards, integrates seamlessly with Plotly for rich visualizations, good for production-grade applications.
*   **Use Cases**: Creating sophisticated dashboards with multiple linked plots, cross-filtering capabilities, and custom UI components for detailed analysis of demand forecasts and route optimization results.

### Plotly:

*   **Overview**: A graphing library that makes interactive, publication-quality graphs in Python (and other languages). It's the underlying graphing engine for Dash.
*   **Strengths**: Wide range of chart types (scatter plots, line plots, bar charts, heatmaps), interactive features (zoom, pan, hover information), excellent for creating visually appealing and informative data visualizations.
*   **Use Cases**: Generating predicted vs. actual demand heatmaps, time-series plots of demand, and various KPI comparisons.

### Folium:

*   **Overview**: A Python library that helps visualize geospatial data on an interactive Leaflet map.
*   **Strengths**: Easy to create interactive maps, supports various tile layers, allows adding markers, popups, and GeoJSON overlays, ideal for visualizing spatial data.
*   **Use Cases**: Displaying MARTA station locations, overlaying demand heatmaps on a map, visualizing proposed route changes, and showing transit corridors and boundaries from GIS layers. Can be integrated with Streamlit or Dash to create map-centric dashboards.

### Integration:

*   Streamlit and Dash can both leverage Plotly for generating interactive charts and Folium for interactive maps. This allows for building comprehensive dashboards that combine various visualization types to present the MARTA demand model's insights effectively.

