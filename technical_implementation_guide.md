# Technical Implementation Guide: MARTA Demand Forecasting & Route Optimization Platform

## 1. System Architecture Design

The MARTA Demand Forecasting & Route Optimization Platform is designed as a modular, scalable, and data-driven system. It follows a microservices-oriented architecture, allowing for independent development, deployment, and scaling of its core components. The architecture emphasizes data ingestion, processing, machine learning model training and inference, and interactive visualization.

### 1.1. High-Level Architecture Overview

The system can be broadly divided into the following logical layers:

1.  **Data Ingestion Layer**: Responsible for collecting and normalizing raw GTFS static, GTFS-Realtime, ridership metrics, and external data sources (weather, events).
2.  **Data Processing & Feature Engineering Layer**: Handles data cleaning, transformation, historical trip reconstruction, dwell time inference, and the creation of features for machine learning models.
3.  **Machine Learning Layer**: Encompasses the demand forecasting models (LSTM, XGBoost, STGCN) and the route optimization simulation engine.
4.  **Serving & API Layer**: Provides interfaces for model inference and serves processed data to the visualization layer.
5.  **Visualization & Reporting Layer**: Offers interactive dashboards for monitoring, validation, and operational insights.

This layered approach ensures a clear separation of concerns, facilitating maintainability and future enhancements. The use of cloud-native principles and containerization (e.g., Docker) is recommended for deployment to ensure scalability and reliability.

### 1.2. Detailed Component Breakdown

#### 1.2.1. Data Ingestion & Storage Subsystem

This subsystem is the entry point for all data flowing into the platform. It is critical for ensuring data quality and availability for downstream processes.

*   **GTFS Static Data Ingestor**: This component will be responsible for periodically downloading the GTFS static ZIP files from the [MARTA Developer Portal](https://itsmarta.com/app-developer-resources.aspx). It will parse the CSV files (`stops.txt`, `routes.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt`, `shapes.txt`) and load them into a relational database. Data validation against the GTFS specification will be performed during ingestion to ensure data integrity. An ETL pipeline orchestrated by a tool like Apache Airflow can automate this process.

*   **GTFS-Realtime (GTFS-RT) Stream Processor**: This component will continuously poll the [MARTA GTFS-RT API](https://itsmarta.com/app-developer-resources.aspx) for Vehicle Positions and Trip Updates. It will use `gtfs-realtime-bindings` (Python library) to parse the Protocol Buffer messages. The parsed real-time data will be timestamped and published to a message queue (e.g., Apache Kafka) for real-time processing and historical archiving. This component will ensure data freshness, adhering to the best practice of data not being older than 90 seconds for vehicle positions and trip updates [1].

*   **Ridership Metrics Collector**: This component will scrape or extract monthly ridership data from [MARTA's Monthly KPI Reports](https://itsmarta.com/KPIRidership.aspx). Given the HTML/CSV format, a web scraping library (e.g., BeautifulSoup, Pandas `read_html`) can be used. The extracted data will be stored in the data warehouse for model validation and historical analysis.

*   **GIS Layers Ingestor**: This component will ingest static GIS data, such as MARTA station shapefiles and transit corridors, from sources like [opendata.atlantaregional.com](https://opendata.atlantaregional.com/datasets/marta-rail-stations). GeoJSON format will be processed and stored in a geospatial database or a data warehouse with geospatial capabilities.

*   **External Data Connectors (Weather, Events)**:
    *   **Weather Data**: An API client will fetch historical and real-time weather data for Atlanta from services like OpenWeatherMap API or NOAA. This data will be integrated into the feature store.
    *   **Event Data**: A web scraper will collect event schedules from major venues (e.g., Mercedes-Benz Stadium, Georgia Tech). This data will be processed to create binary event flags or other relevant features.

*   **Data Lake/Warehouse**: A centralized repository for storing all raw and processed data. Object storage (e.g., Amazon S3, Google Cloud Storage) is suitable for raw data, while a data warehouse (e.g., PostgreSQL with PostGIS extension, Google BigQuery) can store structured and semi-structured data for analytical queries and feature serving. This storage solution must be scalable, available, secure, and performant [1].

#### 1.2.2. Data Processing & Feature Engineering Subsystem

This subsystem transforms raw ingested data into a clean, unified, and feature-rich dataset suitable for machine learning.

*   **Data Unification & Normalization Engine**: This component will join GTFS static and GTFS-RT data based on `trip_id` and `stop_sequence` to create a unified trip-stop-level dataset. It will normalize various data formats and ensure consistency across all data sources. This engine will output a unified table with fields such as `trip_id`, `stop_id`, `timestamp`, `route_id`, `lat/lon`, `vehicle_id`, `delay`, and `stop_sequence`.

*   **Historical Trip Reconstruction Module**: This module will reconstruct historical trips by aligning real-time vehicle positions and trip updates with scheduled GTFS data. It will infer dwell times at each stop by analyzing arrival vs. departure time differences or vehicle position stalling near stops. Dwell time will serve as a proxy signal for boarding volume, allowing for the inference of demand [1].

*   **Feature Engineering Module**: This module will generate a comprehensive set of features for the demand forecasting models. It will create:
    *   **Trip-Level Features**: `route_id`, `trip_id`, `start_time`, `day_of_week`, `delay_minutes`, `trip_duration`, `trip_distance` (from `shapes.txt`), `realized_vs_scheduled_time_diff`.
    *   **Stop-Level Features**: `stop_id`, `stop_lat`, `stop_lon`, `stop_sequence`, `zone_id` (derived from GIS layers), `nearby_POIs_count` (optional, from OSM), `historical_dwell_time`, `historical_headway`.
    *   **Contextual Features**: `weather_condition`, `precipitation`, `temperature` (from weather API), `event_flag` (from event data).
    *   **Time-Series Specific Features**: Lag features, rolling window statistics, and cyclical features (e.g., sine/cosine transformations for hour of day, day of week) [1].

*   **Feature Store**: A centralized repository for managing and serving features. This ensures consistency and reusability of features across different models and environments (training, inference). Tools like Feast or Hopsworks can be considered.

#### 1.2.3. Machine Learning Subsystem

This subsystem houses the core intelligence of the platform, including demand forecasting and route optimization.

*   **Demand Forecasting Model (DFM)**:
    *   **Model Types**: The MVP will start with LSTM or XGBoost models to forecast demand per stop per 15-minute window. For advanced capabilities, a Spatio-Temporal GCN + LSTM Hybrid model will be implemented to leverage full graph-based demand forecasting [1].
    *   **Training Pipeline**: An automated pipeline for training and retraining the DFM using historical data from the feature store. This pipeline will include data splitting, model training, hyperparameter tuning, and model evaluation.
    *   **Model Registry**: A system to store, version, and manage trained models. MLflow or a similar tool can be used for this purpose.
    *   **Output**: The DFM will output the predicted number of riders per `stop_id` × `timestamp` and classify stop load (Underloaded, Normal, Overloaded).

*   **Route Optimization Simulation Engine (ROSE)**:
    *   **Input**: The ROSE will take the forecasted demand heatmap from the DFM, route topology (from GTFS `shapes.txt`), and bus capacity assumptions as input.
    *   **Optimization Logic**: It will employ heuristic or greedy optimization algorithms to propose new or modified routes. This includes logic for rerouting low-utilization trips, adding short-turn loops or shuttles on overloaded segments, and simulating headway adjustments [1].
    *   **Simulation Module**: This module will simulate the impact of proposed route changes on key metrics such as passenger wait time, coverage score, and vehicle utilization. Discrete Event Simulation (DES) or Agent-Based Modeling (ABM) techniques can be employed for this [1].
    *   **Output**: The ROSE will output proposed new/modified routes, a simulation of load balancing, and impact metrics.

#### 1.2.4. Serving & API Subsystem

This subsystem exposes the functionalities of the ML models and processed data to other applications and the visualization layer.

*   **Prediction API**: A RESTful API endpoint for real-time demand forecasting. This API will receive requests for specific `stop_id` and `timestamp` and return predicted rider numbers and load classification. This can be implemented using Flask or FastAPI.

*   **Optimization API**: A RESTful API endpoint that accepts parameters (e.g., current demand, operational constraints) and returns proposed route optimizations. This API will trigger the ROSE and return its outputs.

*   **Data Access API**: Provides programmatic access to the unified dataset, historical trip data, and feature store for analytical purposes and dashboard population.

#### 1.2.5. Visualization & Reporting Subsystem

This subsystem provides interactive dashboards for monitoring, validation, and operational decision-making.

*   **Interactive Dashboards**: Built using Streamlit or Dash, these dashboards will provide:
    *   **Predicted vs. Actual Heatmaps**: Visualizing stop-level demand, allowing for comparison with actual ridership data.
    *   **Route Change Simulation Overlays**: Displaying proposed route modifications on an interactive map (using Folium) and their simulated impact.
    *   **KPI Comparisons**: Visualizing key performance indicators against official MARTA metrics for validation.
    *   **Model Performance Monitoring**: Dashboards to track DFM accuracy, drift, and other relevant metrics.

*   **Reporting Module**: Generates periodic reports (e.g., daily, weekly) summarizing demand forecasts, optimization recommendations, and system performance.

### 1.3. Infrastructure Requirements

*   **Cloud Platform**: Recommend a cloud provider (e.g., Google Cloud Platform, AWS, Azure) for scalability, managed services, and ease of deployment.
*   **Compute**: Virtual machines or container orchestration platforms (e.g., Kubernetes) for running data processing jobs, model training, and serving APIs. GPUs will be necessary for training Spatio-Temporal GCN models.
*   **Database**: PostgreSQL with PostGIS extension for relational and geospatial data, or a cloud-native data warehouse solution.
*   **Message Queue**: Apache Kafka or a managed equivalent for real-time data streaming.
*   **Orchestration**: Apache Airflow for scheduling and managing data pipelines and model training workflows.
*   **Containerization**: Docker for packaging applications and ensuring consistent environments across development and production.
*   **Version Control**: Git for code management.
*   **MLOps Tools**: MLflow for experiment tracking, model registry, and deployment.

## References

[1] Research Findings. `/home/ubuntu/research_findings.md`




### 1.4. Data Models and Database Schema

Effective data modeling is crucial for storing and retrieving transit data efficiently. The proposed schema leverages a relational database (e.g., PostgreSQL with PostGIS for geospatial capabilities) to store GTFS static data, processed real-time data, and features.

#### 1.4.1. GTFS Static Data Schema

The GTFS static data will be stored in tables closely mirroring the GTFS specification, with appropriate primary and foreign keys for relationships.

| Table Name | Key Fields | Description |
|---|---|---|
| `stops` | `stop_id` (PK) | Geographic locations of stops. |
| `routes` | `route_id` (PK) | Route information. |
| `trips` | `trip_id` (PK), `route_id` (FK) | Trips for each route. |
| `stop_times` | `trip_id` (FK), `stop_sequence` (PK) | Times that a vehicle arrives at and departs from individual stops for each trip. |
| `calendar` | `service_id` (PK) | Dates for which service is available for a service ID. |
| `shapes` | `shape_id` (PK), `shape_pt_sequence` (PK) | Geographic paths of routes. |

#### 1.4.2. Unified Real-time & Historical Data Schema

This schema combines static GTFS information with processed real-time data and inferred metrics, forming the basis for historical analysis and feature generation.

| Field Name | Data Type | Description |
|---|---|---|
| `record_id` | UUID (PK) | Unique identifier for each record. |
| `timestamp` | TIMESTAMP | Time of the real-time observation. |
| `trip_id` | TEXT (FK to `trips`) | Identifier for the trip. |
| `route_id` | TEXT (FK to `routes`) | Identifier for the route. |
| `stop_id` | TEXT (FK to `stops`) | Identifier for the stop. |
| `stop_sequence` | INTEGER | Order of the stop within the trip. |
| `vehicle_id` | TEXT | Identifier for the vehicle. |
| `latitude` | NUMERIC | Latitude of the vehicle/stop. |
| `longitude` | NUMERIC | Longitude of the vehicle/stop. |
| `scheduled_arrival_time` | TIMESTAMP | Scheduled arrival time at the stop. |
| `actual_arrival_time` | TIMESTAMP | Actual arrival time at the stop (from GTFS-RT). |
| `scheduled_departure_time` | TIMESTAMP | Scheduled departure time from the stop. |
| `actual_departure_time` | TIMESTAMP | Actual departure time from the stop (from GTFS-RT). |
| `delay_minutes` | NUMERIC | Delay in minutes (actual - scheduled). |
| `inferred_dwell_time_seconds` | NUMERIC | Inferred time vehicle spent at the stop. |
| `inferred_demand_level` | TEXT | Categorical demand level (e.g., 'Low', 'Medium', 'High', 'Overloaded'). |
| `weather_condition` | TEXT | Weather condition at the time (e.g., 'Clear', 'Rainy'). |
| `temperature_celsius` | NUMERIC | Temperature in Celsius. |
| `precipitation_mm` | NUMERIC | Precipitation in millimeters. |
| `event_flag` | BOOLEAN | True if a major event was occurring nearby. |
| `day_of_week` | TEXT | Day of the week (e.g., 'Monday'). |
| `hour_of_day` | INTEGER | Hour of the day (0-23). |
| `is_weekend` | BOOLEAN | True if it's a weekend. |
| `is_holiday` | BOOLEAN | True if it's a public holiday. |
| `zone_id` | TEXT | Geographic zone identifier for the stop. |
| `nearby_pois_count` | INTEGER | Count of nearby Points of Interest. |
| `historical_dwell_time_avg` | NUMERIC | Average historical dwell time for this stop/time. |
| `historical_headway_avg` | NUMERIC | Average historical headway for this stop/time. |

#### 1.4.3. Feature Store Schema (Conceptual)

The feature store will conceptually hold pre-computed features for efficient model training and inference. While the physical implementation might vary (e.g., a dedicated feature store solution, or views/tables in the data warehouse), the logical structure for features would be:

| Feature Name | Data Type | Description |
|---|---|---|
| `feature_id` | UUID (PK) | Unique identifier for the feature set. |
| `timestamp` | TIMESTAMP | Time for which the features are valid. |
| `stop_id` | TEXT (FK to `stops`) | Stop identifier. |
| `route_id` | TEXT (FK to `routes`) | Route identifier. |
| `lag_demand_1hr` | NUMERIC | Demand from 1 hour ago. |
| `lag_demand_24hr` | NUMERIC | Demand from 24 hours ago. |
| `rolling_avg_demand_3hr` | NUMERIC | Rolling average demand over last 3 hours. |
| `sin_hour_of_day` | NUMERIC | Sine transformation of hour of day. |
| `cos_hour_of_day` | NUMERIC | Cosine transformation of hour of day. |
| `sin_day_of_week` | NUMERIC | Sine transformation of day of week. |
| `cos_day_of_week` | NUMERIC | Cosine transformation of day of week. |
| ... | ... | Additional engineered features. |

This structured approach to data ensures that all necessary information is readily available and properly linked for analysis, model training, and real-time predictions.



### 1.5. APIs and Interfaces Between Components

Clear and well-defined APIs (Application Programming Interfaces) and interfaces are essential for enabling seamless communication and data flow between the various components of the MARTA Demand Forecasting & Route Optimization Platform. This section outlines the primary interfaces.

#### 1.5.1. Internal APIs

These APIs facilitate communication between the core subsystems of the platform.

*   **Data Ingestion to Data Processing Interface**: 
    *   **Mechanism**: Message Queue (e.g., Apache Kafka).
    *   **Purpose**: Real-time GTFS-RT data, once parsed, will be published to Kafka topics. The Data Processing & Feature Engineering Subsystem will consume messages from these topics.
    *   **Data Format**: Protocol Buffer messages (after initial parsing by `gtfs-realtime-bindings`) or JSON.

*   **Data Processing to Feature Store Interface**: 
    *   **Mechanism**: Feature Store SDK/API (e.g., Feast Python SDK).
    *   **Purpose**: The Feature Engineering Module will write engineered features to the Feature Store for both online serving (low-latency inference) and offline training (batch processing).
    *   **Data Format**: Structured data (e.g., Pandas DataFrames) mapped to feature definitions in the Feature Store.

*   **Feature Store to ML Model Training Interface**: 
    *   **Mechanism**: Feature Store SDK/API.
    *   **Purpose**: The ML Training Pipeline will retrieve historical features from the Feature Store for model training and retraining.
    *   **Data Format**: Batch features (e.g., Pandas DataFrames, Spark DataFrames).

*   **Feature Store to ML Model Serving Interface**: 
    *   **Mechanism**: Feature Store SDK/API (online store).
    *   **Purpose**: The Prediction API will fetch real-time features from the Feature Store for low-latency model inference.
    *   **Data Format**: Real-time features for a single prediction request.

*   **Demand Forecasting Model to Route Optimization Interface**: 
    *   **Mechanism**: Internal REST API or direct function call within a shared service.
    *   **Purpose**: The DFM will provide forecasted demand heatmaps and load classifications to the Route Optimization Simulation Engine.
    *   **Data Format**: JSON or a structured data object containing `stop_id`, `timestamp`, `predicted_riders`, `demand_level`.

#### 1.5.2. External APIs

These APIs expose the platform's capabilities to external systems or the visualization layer.

*   **Prediction API (RESTful)**:
    *   **Endpoint**: `/predict/demand`
    *   **Method**: `POST`
    *   **Request Body (JSON)**:
        ```json
        {
            "stop_id": "string",
            "timestamp": "datetime_string"
        }
        ```
    *   **Response Body (JSON)**:
        ```json
        {
            "stop_id": "string",
            "timestamp": "datetime_string",
            "predicted_riders": "integer",
            "demand_level": "string"  // "Underloaded", "Normal", "Overloaded"
        }
        ```
    *   **Purpose**: Allows external applications or the visualization dashboard to request real-time demand forecasts for specific stops and times.

*   **Optimization API (RESTful)**:
    *   **Endpoint**: `/optimize/routes`
    *   **Method**: `POST`
    *   **Request Body (JSON)**:
        ```json
        {
            "forecasted_demand_heatmap": "array_of_objects", // Data from DFM
            "current_route_topology": "array_of_objects", // GTFS shapes data
            "bus_capacity_assumptions": "integer",
            "optimization_constraints": "object" // e.g., max_reroutes, max_delay_tolerance
        }
        ```
    *   **Response Body (JSON)**:
        ```json
        {
            "proposed_routes": "array_of_objects", // New/modified route definitions
            "load_balancing_simulation": "object", // Simulation results
            "impact_metrics": "object" // e.g., passenger_wait_time, vehicle_utilization
        }
        ```
    *   **Purpose**: Enables the visualization layer or other operational tools to trigger route optimization simulations and retrieve proposed changes.

*   **Data Access API (RESTful/GraphQL)**:
    *   **Endpoint**: `/data/historical_trips`, `/data/features`
    *   **Method**: `GET` (with query parameters for filtering)
    *   **Purpose**: Provides programmatic access to the unified historical trip data and engineered features for ad-hoc analysis, reporting, and populating dashboards.

#### 1.5.3. External Data Source Integrations

These are the interfaces for pulling data from external providers.

*   **MARTA Developer Portal (GTFS Static)**:
    *   **Mechanism**: HTTP GET request to download ZIP files.
    *   **Format**: ZIP containing CSV files.

*   **MARTA GTFS-RT API**: 
    *   **Mechanism**: HTTP GET request to specific endpoints (`/vehicle.pb`, `/tripupdate.pb`).
    *   **Format**: Protocol Buffers.

*   **MARTA Monthly KPI Reports**: 
    *   **Mechanism**: Web scraping (HTTP GET, HTML parsing).
    *   **Format**: HTML or CSV.

*   **Atlanta Regional Commission Open Data Portal (GIS Layers)**:
    *   **Mechanism**: HTTP GET to download GeoJSON files.
    *   **Format**: GeoJSON.

*   **OpenWeatherMap API / NOAA**: 
    *   **Mechanism**: RESTful API calls (HTTP GET).
    *   **Format**: JSON.

*   **Event Data Sources**: 
    *   **Mechanism**: Web scraping or dedicated event APIs (if available).
    *   **Format**: HTML parsing or JSON.

This comprehensive API strategy ensures that each component can interact effectively, supporting both real-time operational needs and batch analytical processes.



### 1.6. Infrastructure Requirements

The successful deployment and operation of the MARTA Demand Forecasting & Route Optimization Platform require a robust and scalable infrastructure. This section outlines the key infrastructure components and considerations.

#### 1.6.1. Cloud Platform

Leveraging a cloud computing platform is highly recommended due to its inherent scalability, flexibility, and managed services. Major cloud providers such as Google Cloud Platform (GCP), Amazon Web Services (AWS), or Microsoft Azure offer a comprehensive suite of services suitable for this project.

*   **Recommendation**: A cloud-agnostic approach where possible, but for initial deployment, choosing one provider and utilizing its managed services can accelerate development and reduce operational overhead.

#### 1.6.2. Compute Resources

Various components of the platform will require different types of compute resources.

*   **Data Ingestion & Processing**: 
    *   **Batch Processing**: For initial GTFS static data ingestion and large-scale historical data processing, distributed processing frameworks like Apache Spark (e.g., Dataproc on GCP, EMR on AWS, HDInsight on Azure) running on virtual machines (VMs) or managed clusters are suitable.
    *   **Stream Processing**: For continuous GTFS-RT data ingestion and real-time processing, stream processing engines like Apache Flink or Spark Streaming, deployed on dedicated VMs or containerized environments, will be necessary.
*   **Machine Learning Model Training**: 
    *   **CPU-intensive**: For XGBoost models and general data preparation, standard CPU-optimized VMs are sufficient.
    *   **GPU-intensive**: For training deep learning models like LSTM and especially Spatio-Temporal GCNs, access to GPUs (e.g., NVIDIA Tesla V100 or A100) via specialized VM instances or managed ML platforms (e.g., Vertex AI on GCP, SageMaker on AWS, Azure Machine Learning) is crucial for accelerating training times.
*   **Model Serving (Prediction & Optimization APIs)**: 
    *   **Containerization**: Deploying APIs as Docker containers on container orchestration platforms like Kubernetes (e.g., GKE on GCP, EKS on AWS, AKS on Azure) or serverless container platforms (e.g., Cloud Run on GCP, AWS Fargate) provides scalability, high availability, and efficient resource utilization.
    *   **Auto-scaling**: Configure auto-scaling policies based on demand (e.g., CPU utilization, request queue length) to handle varying loads.

#### 1.6.3. Storage Solutions

Diverse data storage needs will require a combination of solutions.

*   **Object Storage**: For raw, immutable data (e.g., GTFS static ZIP files, raw GTFS-RT protobuf messages, historical ridership reports, GIS layers). Cloud object storage services (e.g., Google Cloud Storage, Amazon S3, Azure Blob Storage) offer high durability, scalability, and cost-effectiveness.
*   **Relational Database**: For structured GTFS static data, unified historical trip data, and metadata. PostgreSQL with the PostGIS extension is highly recommended for its geospatial capabilities. Managed database services (e.g., Cloud SQL for PostgreSQL on GCP, Amazon RDS for PostgreSQL on AWS, Azure Database for PostgreSQL) simplify administration.
*   **Time-Series Database (Optional but Recommended)**: For high-volume, time-stamped GTFS-RT data and inferred metrics. Solutions like InfluxDB, TimescaleDB (an extension for PostgreSQL), or managed time-series databases (e.g., Amazon Timestream) can optimize storage and querying of time-series data.
*   **Feature Store**: A dedicated feature store (e.g., Feast, Hopsworks) can be deployed on top of existing storage (e.g., a data warehouse or object storage) to manage and serve features consistently for training and inference.

#### 1.6.4. Message Queue / Streaming Platform

Essential for real-time data ingestion and inter-service communication.

*   **Recommendation**: Apache Kafka or a managed Kafka service (e.g., Confluent Cloud, Google Cloud Pub/Sub, Amazon Kinesis, Azure Event Hubs). Kafka provides high-throughput, fault-tolerant, and scalable message queuing capabilities, crucial for handling the continuous stream of GTFS-RT data.

#### 1.6.5. Workflow Orchestration

For managing and scheduling complex data pipelines and ML workflows.

*   **Recommendation**: Apache Airflow. It allows for defining workflows as Directed Acyclic Graphs (DAGs) and provides robust scheduling, monitoring, and error handling capabilities. Managed Airflow services (e.g., Cloud Composer on GCP, Amazon MWAA on AWS) can reduce operational burden.

#### 1.6.6. Containerization

*   **Tool**: Docker. All application components (data ingestors, processing modules, ML APIs) should be containerized using Docker. This ensures consistent environments across development, testing, and production, simplifying deployment and dependency management.

#### 1.6.7. Version Control

*   **Tool**: Git. A robust version control system is essential for managing source code, configuration files, and potentially data and models (using Git LFS or DVC). Platforms like GitHub, GitLab, or Bitbucket provide hosted Git repositories.

#### 1.6.8. MLOps Tools

To streamline the ML lifecycle from experimentation to production.

*   **Experiment Tracking & Model Registry**: MLflow is a popular open-source platform for managing the end-to-end machine learning lifecycle, including experiment tracking, model packaging, and model registry. This helps in reproducibility and model governance.
*   **CI/CD (Continuous Integration/Continuous Deployment)**: Tools like Jenkins, GitLab CI/CD, GitHub Actions, or cloud-native CI/CD services (e.g., Google Cloud Build, AWS CodePipeline, Azure DevOps) for automating code integration, testing, and deployment of the platform components.

#### 1.6.9. Monitoring and Logging

*   **Centralized Logging**: A centralized logging solution (e.g., ELK Stack - Elasticsearch, Logstash, Kibana; or cloud-native services like Google Cloud Logging, Amazon CloudWatch Logs, Azure Monitor Logs) for collecting, storing, and analyzing logs from all components.
*   **Monitoring & Alerting**: Tools for monitoring system health, resource utilization, application performance, and model performance (e.g., Prometheus and Grafana, cloud-native monitoring services). Set up alerts for anomalies or critical failures.

This infrastructure setup provides the necessary foundation for building, deploying, and operating a high-performance and reliable MARTA Demand Forecasting & Route Optimization Platform.



## 2. Detailed Implementation Guide

This section provides a detailed, step-by-step guide for implementing each component of the MARTA Demand Forecasting & Route Optimization Platform. It includes practical considerations, recommended tools, and code examples where applicable.

### 2.1. Data Ingestion & Normalization

This crucial first step involves collecting raw data from various sources and transforming it into a unified, clean, and usable format. We will focus on Python-based implementations for data processing.

#### 2.1.1. Setting Up the Environment

Before proceeding, ensure your development environment is set up with the necessary libraries. It is highly recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python3 -m venv marta_env

# Activate the virtual environment
source marta_env/bin/activate

# Install core libraries
pip install pandas psycopg2-binary requests beautifulsoup4 protobuf google-transit-gtfs-realtime

# For geospatial operations (if using PostGIS)
pip install geoalchemy2 shapely fiona pyproj

# For feature store (if using Feast)
pip install feast
```

#### 2.1.2. GTFS Static Data Ingestion

GTFS static data provides the foundational schedule and geographic information. This data is typically downloaded as a ZIP file and contains several CSV files. We will use `pandas` for CSV parsing and `psycopg2` for PostgreSQL interaction.

**Step 1: Download GTFS Static Data**

Manually download the latest GTFS static data ZIP file from the [MARTA Developer Portal](https://itsmarta.com/app-developer-resources.aspx) and place it in a designated `data/static` directory within your project.

**Step 2: Database Schema Creation**

Define the PostgreSQL schema for GTFS static data. This can be done using SQL scripts. Below is an example for `stops.txt` and `routes.txt`. Similar scripts would be created for `trips.txt`, `stop_times.txt`, `calendar.txt`, and `shapes.txt`.

```sql
-- stops.sql
CREATE TABLE IF NOT EXISTS gtfs_stops (
    stop_id VARCHAR(255) PRIMARY KEY,
    stop_code VARCHAR(255),
    stop_name VARCHAR(255),
    stop_desc TEXT,
    stop_lat NUMERIC,
    stop_lon NUMERIC,
    zone_id VARCHAR(255),
    stop_url TEXT,
    location_type INTEGER,
    parent_station VARCHAR(255),
    wheelchair_boarding INTEGER,
    platform_code VARCHAR(255)
);

-- routes.sql
CREATE TABLE IF NOT EXISTS gtfs_routes (
    route_id VARCHAR(255) PRIMARY KEY,
    agency_id VARCHAR(255),
    route_short_name VARCHAR(255),
    route_long_name VARCHAR(255),
    route_desc TEXT,
    route_type INTEGER,
    route_url TEXT,
    route_color VARCHAR(6),
    route_text_color VARCHAR(6),
    route_sort_order INTEGER,
    continuous_pickup INTEGER,
    continuous_dropoff INTEGER
);
```

**Step 3: Python Script for Ingestion**

Create a Python script (e.g., `ingest_gtfs_static.py`) to read the CSV files and load them into the PostgreSQL database.

```python
import pandas as pd
import zipfile
import io
import psycopg2
from psycopg2 import extras
import os

# Database connection details (replace with your actual credentials)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "marta_db")
DB_USER = os.getenv("DB_USER", "marta_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "marta_password")

GTFS_ZIP_PATH = "data/static/gtfs.zip" # Path to your downloaded GTFS zip file

def create_db_connection():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    return conn

def load_csv_to_db(conn, zip_file_obj, csv_filename, table_name, columns):
    print(f"Loading {csv_filename} into {table_name}...")
    with zip_file_obj.open(csv_filename) as f:
        df = pd.read_csv(io.TextIOWrapper(f, encoding='utf-8'))
        # Ensure column names match database schema and handle missing columns
        df = df.reindex(columns=columns, fill_value=None)
        # Convert DataFrame to list of tuples for psycopg2.extras.execute_values
        data_to_insert = [tuple(row) for row in df.values]

        if not data_to_insert:
            print(f"No data to insert for {csv_filename}.")
            return

        # Prepare the INSERT statement
        cols_str = ', '.join(columns)
        vals_str = ', '.join([f'%s' for _ in columns])
        insert_query = f"INSERT INTO {table_name} ({cols_str}) VALUES ({vals_str}) ON CONFLICT ({columns[0]}) DO UPDATE SET {', '.join([f'{col} = EXCLUDED.{col}' for col in columns[1:]])};"
        # Using ON CONFLICT for upsert capability based on the first column (PK)

        with conn.cursor() as cursor:
            try:
                extras.execute_values(cursor, insert_query, data_to_insert, page_size=1000)
                conn.commit()
                print(f"Successfully loaded {len(data_to_insert)} rows into {table_name}.")
            except Exception as e:
                conn.rollback()
                print(f"Error loading {csv_filename}: {e}")


def ingest_gtfs_static():
    conn = None
    try:
        conn = create_db_connection()
        
        # Define columns for each GTFS file to ensure correct mapping and handling of optional fields
        # This list should be exhaustive for all fields you expect to handle from GTFS spec
        gtfs_files_config = {
            "stops.txt": {"table": "gtfs_stops", "columns": [
                "stop_id", "stop_code", "stop_name", "stop_desc", "stop_lat", "stop_lon",
                "zone_id", "stop_url", "location_type", "parent_station", "wheelchair_boarding",
                "platform_code"
            ]},
            "routes.txt": {"table": "gtfs_routes", "columns": [
                "route_id", "agency_id", "route_short_name", "route_long_name", "route_desc",
                "route_type", "route_url", "route_color", "route_text_color", "route_sort_order",
                "continuous_pickup", "continuous_dropoff"
            ]},
            "trips.txt": {"table": "gtfs_trips", "columns": [
                "route_id", "service_id", "trip_id", "trip_short_name", "trip_headsign",
                "direction_id", "block_id", "shape_id", "wheelchair_accessible", "bikes_allowed"
            ]},
            "stop_times.txt": {"table": "gtfs_stop_times", "columns": [
                "trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence",
                "stop_headsign", "pickup_type", "drop_off_type", "shape_dist_traveled",
                "timepoint"
            ]},
            "calendar.txt": {"table": "gtfs_calendar", "columns": [
                "service_id", "monday", "tuesday", "wednesday", "thursday", "friday",
                "saturday", "sunday", "start_date", "end_date"
            ]},
            "shapes.txt": {"table": "gtfs_shapes", "columns": [
                "shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence", "shape_dist_traveled"
            ]}
        }

        with zipfile.ZipFile(GTFS_ZIP_PATH, 'r') as zf:
            for gtfs_file, config in gtfs_files_config.items():
                if gtfs_file in zf.namelist():
                    load_csv_to_db(conn, zf, gtfs_file, config["table"], config["columns"])
                else:
                    print(f"Warning: {gtfs_file} not found in zip file.")

    except Exception as e:
        print(f"An error occurred during GTFS static ingestion: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # Before running, ensure your PostgreSQL database is running and accessible,
    # and the necessary tables (gtfs_stops, gtfs_routes, etc.) are created.
    # You might need to set environment variables for DB_HOST, DB_NAME, DB_USER, DB_PASSWORD.
    # Example: export DB_HOST=localhost DB_NAME=marta_db DB_USER=marta_user DB_PASSWORD=marta_password
    ingest_gtfs_static()
```

#### 2.1.3. GTFS-Realtime (GTFS-RT) Stream Processing

GTFS-RT data provides real-time updates. We will set up a continuous polling mechanism to fetch and process this data.

**Step 1: Define Protocol Buffer Message Structure**

The `google-transit-gtfs-realtime` library provides the necessary classes to parse GTFS-RT feeds. You typically import `gtfs_realtime_pb2`.

**Step 2: Python Script for Real-time Ingestion**

Create a Python script (e.g., `ingest_gtfs_realtime.py`) to continuously fetch GTFS-RT feeds, parse them, and store the relevant information. For simplicity, this example will print the parsed data; in a production system, it would publish to Kafka or a similar message queue.

```python
import requests
import time
from google.transit import gtfs_realtime_pb2
from datetime import datetime

# MARTA GTFS-RT API Endpoints
VEHICLE_POSITIONS_URL = "https://api.marta.io/gtfs-rt/vehicle-positions/vehicle.pb"
TRIP_UPDATES_URL = "https://api.marta.io/gtfs-rt/trip-updates/tripupdate.pb"

# API Key (replace with your actual key or use environment variable)
# MARTA API requires an API key, which is usually passed as a header or query parameter.
# Refer to MARTA Developer Portal for exact authentication method.
# For demonstration, we'll assume it's passed as a header 'x-api-key'.
API_KEY = os.getenv("MARTA_API_KEY", "YOUR_MARTA_API_KEY") 
HEADERS = {"x-api-key": API_KEY}

def fetch_and_parse_feed(url, feed_type):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        return feed
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {feed_type} feed from {url}: {e}")
        return None
    except Exception as e:
        print(f"Error parsing {feed_type} feed: {e}")
        return None

def process_vehicle_positions(feed):
    if not feed:
        return []
    processed_data = []
    for entity in feed.entity:
        if entity.HasField('vehicle'):
            vehicle = entity.vehicle
            processed_data.append({
                "id": entity.id,
                "trip_id": vehicle.trip.trip_id,
                "route_id": vehicle.trip.route_id,
                "vehicle_id": vehicle.vehicle.id,
                "latitude": vehicle.position.latitude,
                "longitude": vehicle.position.longitude,
                "bearing": vehicle.position.bearing,
                "speed": vehicle.position.speed,
                "timestamp": datetime.fromtimestamp(vehicle.timestamp).isoformat() if vehicle.HasField('timestamp') else None,
                "current_status": gtfs_realtime_pb2.VehiclePosition.VehicleStopStatus.Name(vehicle.current_status) if vehicle.HasField('current_status') else None
            })
    return processed_data

def process_trip_updates(feed):
    if not feed:
        return []
    processed_data = []
    for entity in feed.entity:
        if entity.HasField('trip_update'):
            trip_update = entity.trip_update
            updates = []
            for stop_time_update in trip_update.stop_time_update:
                updates.append({
                    "stop_id": stop_time_update.stop_id,
                    "stop_sequence": stop_time_update.stop_sequence,
                    "arrival_delay": stop_time_update.arrival.delay if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('delay') else None,
                    "arrival_time": datetime.fromtimestamp(stop_time_update.arrival.time).isoformat() if stop_time_update.HasField('arrival') and stop_time_update.arrival.HasField('time') else None,
                    "departure_delay": stop_time_update.departure.delay if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('delay') else None,
                    "departure_time": datetime.fromtimestamp(stop_time_update.departure.time).isoformat() if stop_time_update.HasField('departure') and stop_time_update.departure.HasField('time') else None,
                })
            processed_data.append({
                "id": entity.id,
                "trip_id": trip_update.trip.trip_id,
                "route_id": trip_update.trip.route_id,
                "direction_id": trip_update.trip.direction_id if trip_update.trip.HasField('direction_id') else None,
                "start_time": trip_update.trip.start_time if trip_update.trip.HasField('start_time') else None,
                "start_date": trip_update.trip.start_date if trip_update.trip.HasField('start_date') else None,
                "timestamp": datetime.fromtimestamp(trip_update.timestamp).isoformat() if trip_update.HasField('timestamp') else None,
                "stop_time_updates": updates
            })
    return processed_data

def ingest_gtfs_realtime_stream(interval_seconds=30):
    print(f"Starting GTFS-RT ingestion stream, polling every {interval_seconds} seconds...")
    while True:
        print(f"\n--- Fetching GTFS-RT data at {datetime.now().isoformat()} ---")
        
        # Fetch and process Vehicle Positions
        vp_feed = fetch_and_parse_feed(VEHICLE_POSITIONS_URL, "Vehicle Positions")
        vehicle_positions_data = process_vehicle_positions(vp_feed)
        if vehicle_positions_data:
            print(f"Fetched {len(vehicle_positions_data)} vehicle positions.")
            # In a real system, publish to Kafka or save to a time-series database
            # Example: kafka_producer.send('vehicle_positions_topic', value=vehicle_positions_data)
            # For now, just print a sample
            # print(vehicle_positions_data[0] if vehicle_positions_data else "")

        # Fetch and process Trip Updates
        tu_feed = fetch_and_parse_feed(TRIP_UPDATES_URL, "Trip Updates")
        trip_updates_data = process_trip_updates(tu_feed)
        if trip_updates_data:
            print(f"Fetched {len(trip_updates_data)} trip updates.")
            # In a real system, publish to Kafka or save to a time-series database
            # Example: kafka_producer.send('trip_updates_topic', value=trip_updates_data)
            # For now, just print a sample
            # print(trip_updates_data[0] if trip_updates_data else "")

        time.sleep(interval_seconds)

if __name__ == "__main__":
    # Ensure you have a valid MARTA_API_KEY set as an environment variable.
    # Example: export MARTA_API_KEY="YOUR_ACTUAL_API_KEY"
    ingest_gtfs_realtime_stream()
```

**Step 3: Data Unification and Normalization (Conceptual)**

This step is where GTFS static and GTFS-RT data are combined and normalized into the `unified_realtime_historical_data` schema defined in Section 1.4.2. This process would typically happen in a stream processing application (e.g., Apache Flink, Spark Streaming) consuming from Kafka topics, or in batch jobs processing historical data from a data lake.

*   **Matching Logic**: Join `trip_updates` and `vehicle_positions` from GTFS-RT with `trips` and `stop_times` from the static GTFS data using `trip_id` and `stop_sequence`.
*   **Delay Calculation**: Calculate `delay_minutes` by comparing `actual_arrival_time`/`actual_departure_time` from GTFS-RT with `scheduled_arrival_time`/`scheduled_departure_time` from static GTFS.
*   **Inferred Dwell Time**: Estimate `inferred_dwell_time_seconds` by subtracting `actual_arrival_time` from `actual_departure_time` at a stop. If only vehicle positions are available, infer dwell time by detecting when a vehicle's position remains constant near a stop for a period.

This unification process is complex and forms the core of the data processing layer. It would involve a dedicated service or set of functions that continuously process the incoming real-time data and enrich it with static context. The output would then be stored in the `unified_realtime_historical_data` table in your PostgreSQL database or a time-series database.

#### 2.1.4. Ridership Metrics and GIS Layers Ingestion

These are typically batch ingestion processes.

**Ridership Metrics**: Use `requests` and `BeautifulSoup` (for HTML) or `pandas.read_csv` (if direct CSV link) to scrape/read monthly KPI reports. Store this data in your data warehouse.

**GIS Layers**: Download GeoJSON files from the Atlanta Regional Commission. Use `fiona` and `shapely` to read and process these files, then load them into a PostGIS-enabled PostgreSQL database.

```python
# Example for GIS Layer Ingestion (Conceptual)
import fiona
from shapely.geometry import mapping, shape
import psycopg2

# Assuming you have a GeoJSON file downloaded
GIS_GEOJSON_PATH = "data/gis/marta_rail_stations.geojson"

def ingest_geojson_to_postgis(conn, geojson_path, table_name):
    print(f"Ingesting {geojson_path} into {table_name}...")
    with fiona.open(geojson_path, 'r') as source:
        # You would need to define your table schema in PostGIS beforehand
        # Example: CREATE TABLE marta_stations (id VARCHAR(255) PRIMARY KEY, name VARCHAR(255), geom GEOMETRY(Point, 4326));
        with conn.cursor() as cursor:
            for feature in source:
                props = feature['properties']
                geom = shape(feature['geometry'])
                # Example insert - adapt to your specific schema and properties
                insert_query = f"INSERT INTO {table_name} (id, name, geom) VALUES (%s, %s, ST_SetSRID(ST_GeomFromText(%s), 4326)) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, geom = EXCLUDED.geom;"
                cursor.execute(insert_query, (props.get('station_id'), props.get('station_name'), geom.wkt))
            conn.commit()
            print(f"Successfully ingested features into {table_name}.")

# Example usage (within a main function or similar)
# conn = create_db_connection()
# ingest_geojson_to_postgis(conn, GIS_GEOJSON_PATH, "marta_stations")
# conn.close()
```

#### 2.1.5. External Data Connectors (Weather, Events)

**Weather Data**: Use the `requests` library to interact with the OpenWeatherMap API. Store the fetched weather data (temperature, precipitation, conditions) in your data warehouse, linked by timestamp and location (e.g., nearest stop).

```python
# Example for OpenWeatherMap API (Conceptual)
import requests
import os

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "YOUR_OPENWEATHER_API_KEY")
ATLANTA_LAT = 33.7490
ATLANTA_LON = -84.3880

def fetch_weather_data(lat, lon, api_key, timestamp=None):
    # For historical data, you might need a different endpoint or a paid plan
    # This example fetches current weather
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        weather_info = {
            "timestamp": datetime.now().isoformat(),
            "temperature": data['main']['temp'],
            "weather_condition": data['weather'][0]['main'],
            "precipitation": data.get('rain', {}).get('1h', 0) # Rain in last 1 hour
        }
        return weather_info
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return None

# Example usage
# weather_data = fetch_weather_data(ATLANTA_LAT, ATLANTA_LON, OPENWEATHER_API_KEY)
# if weather_data:
#     print(weather_data)
#     # Store weather_data in your database
```

**Event Data**: This typically involves web scraping specific event websites (e.g., Mercedes-Benz Stadium schedule). This requires careful parsing of HTML content. The extracted event information (date, time, location, type) can then be used to create `event_flag` features.

```python
# Example for Event Data Scraping (Conceptual - highly dependent on website structure)
from bs4 import BeautifulSoup
import requests

def scrape_mercedes_benz_events(url="https://www.mercedesbenzstadium.com/events/"):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        events = []
        # This is a placeholder; actual parsing depends on the website's HTML structure
        for event_div in soup.find_all('div', class_='event-item'): 
            title = event_div.find('h3', class_='event-title').text.strip()
            date = event_div.find('span', class_='event-date').text.strip()
            events.append({"title": title, "date": date})
        return events
    except requests.exceptions.RequestException as e:
        print(f"Error scraping events: {e}")
        return None
    except Exception as e:
        print(f"Error parsing event data: {e}")
        return None

# Example usage
# events = scrape_mercedes_benz_events()
# if events:
#     print(events)
#     # Process events to create event_flag features based on date and proximity to stops
```

This concludes the detailed implementation steps for the Data Ingestion & Normalization layer. The next section will cover Historical Trip Reconstruction and Feature Engineering.



### 2.2. Historical Trip Reconstruction & Demand Inference

This section details how to reconstruct historical transit trips by combining static GTFS data with real-time GTFS-RT updates, and how to infer rider demand from observed dwell times.

#### 2.2.1. Unifying Static and Real-time Data

The goal is to create a comprehensive dataset that captures the actual movement of vehicles and their interactions with stops, enriched with scheduled information. This process typically involves joining data from your `gtfs_trips`, `gtfs_stop_times`, and the processed real-time data (vehicle positions and trip updates).

**Conceptual Logic:**

1.  **Load Static Data**: Load relevant static GTFS data (trips, stop times, stops) into memory or queryable structures.
2.  **Process Real-time Streams**: Continuously consume processed GTFS-RT `vehicle_positions` and `trip_updates` (e.g., from Kafka topics or a time-series database).
3.  **Match Real-time to Static**: For each real-time update, identify the corresponding static `trip_id` and `stop_sequence`.
    *   **Vehicle Positions**: Match `vehicle_id` to `trip_id` and then use `latitude`/`longitude` to determine the nearest `stop_id` and `stop_sequence` on the `trip`.
    *   **Trip Updates**: Directly use `trip_id` and `stop_id`/`stop_sequence` provided in the update.
4.  **Calculate Actual Times and Delays**: For each `stop_time_update` in GTFS-RT, record the `actual_arrival_time` and `actual_departure_time`. Compare these with `scheduled_arrival_time` and `scheduled_departure_time` from `gtfs_stop_times` to calculate `delay_minutes`.
5.  **Infer Dwell Time**: Calculate `inferred_dwell_time_seconds` as `actual_departure_time - actual_arrival_time`. If only vehicle positions are available, infer dwell time by detecting periods where a vehicle's `latitude` and `longitude` remain within a small radius of a `stop_id`.
6.  **Store Unified Data**: Persist the unified records into the `unified_realtime_historical_data` table (as defined in Section 1.4.2).

**Python Implementation Snippet (Conceptual for a batch process on historical data):**

```python
import pandas as pd
from datetime import datetime, timedelta

def reconstruct_historical_trips(static_gtfs_df, realtime_df):
    # This is a simplified conceptual example. 
    # In reality, this would involve more complex joins and temporal logic
    # especially for streaming data or large datasets.

    # Merge static GTFS stop_times with trips for scheduled info
    merged_df = pd.merge(
        static_gtfs_df["gtfs_stop_times"], 
        static_gtfs_df["gtfs_trips"], 
        on="trip_id", 
        how="left"
    )
    merged_df = pd.merge(
        merged_df, 
        static_gtfs_df["gtfs_stops"], 
        on="stop_id", 
        how="left"
    )

    # Assuming realtime_df contains processed GTFS-RT data with 
    # 'trip_id', 'stop_id', 'actual_arrival_time', 'actual_departure_time'
    # and 'timestamp' for vehicle positions

    # For simplicity, let's assume realtime_df is already aligned with stop_times
    # In a real scenario, you'd match based on trip_id, stop_id, and approximate time
    unified_df = pd.merge(
        merged_df,
        realtime_df, # This would be your processed GTFS-RT data
        on=["trip_id", "stop_id", "stop_sequence"], # Simplified join keys
        how="left",
        suffixes=('_scheduled', '_actual')
    )

    # Calculate delay (example for arrival delay)
    unified_df["delay_minutes"] = (unified_df["actual_arrival_time"] - unified_df["scheduled_arrival_time"]).dt.total_seconds() / 60

    # Infer dwell time
    unified_df["inferred_dwell_time_seconds"] = (unified_df["actual_departure_time"] - unified_df["actual_arrival_time"]).dt.total_seconds()
    unified_df["inferred_dwell_time_seconds"] = unified_df["inferred_dwell_time_seconds"].fillna(0) # Handle cases where only one time is available

    # Further processing to handle vehicle positions for dwell time inference
    # (This would be a separate function, potentially using geospatial libraries)
    # Example: if actual_arrival_time is null, use vehicle position data to estimate

    return unified_df

def infer_demand_from_dwell_time(unified_df):
    # This is a conceptual function. The actual inference model would be more sophisticated.
    # It could involve statistical models, regression, or simple heuristics.

    # Example: Simple heuristic for demand level based on dwell time
    def get_demand_level(dwell_time):
        if dwell_time > 120: # e.g., > 2 minutes
            return "Overloaded"
        elif dwell_time > 60: # e.g., > 1 minute
            return "High"
        elif dwell_time > 30:
            return "Normal"
        else:
            return "Low"

    unified_df["inferred_demand_level"] = unified_df["inferred_dwell_time_seconds"].apply(get_demand_level)

    return unified_df

# Example Usage (assuming you have loaded data into pandas DataFrames)
# static_gtfs_data = {
#     "gtfs_trips": pd.DataFrame(...),
#     "gtfs_stop_times": pd.DataFrame(...),
#     "gtfs_stops": pd.DataFrame(...)
# }
# realtime_processed_data = pd.DataFrame(...)

# unified_historical_data = reconstruct_historical_trips(static_gtfs_data, realtime_processed_data)
# unified_historical_data = infer_demand_from_dwell_time(unified_historical_data)
# print(unified_historical_data.head())

# Store unified_historical_data to your database (e.g., PostgreSQL)
# unified_historical_data.to_sql("unified_realtime_historical_data", engine, if_exists="append", index=False)
```

#### 2.2.2. Considerations for Dwell Time Inference

*   **Data Granularity**: The accuracy of dwell time inference depends heavily on the frequency and precision of GTFS-RT vehicle position updates. Higher frequency (e.g., every 5-10 seconds) provides better estimates.
*   **Geospatial Proximity**: When inferring dwell time from vehicle positions, define a reasonable buffer around each `stop_id` to determine if a vehicle is 



    at a stop. Use geospatial libraries (e.g., `shapely`, `geopandas`) for accurate calculations.
*   **Noise Filtering**: GPS data can be noisy. Implement filtering techniques (e.g., Kalman filters, simple averaging) to smooth vehicle position data before inferring dwell times.
*   **Validation**: If possible, validate inferred dwell times and demand levels against any available ground truth data (e.g., manual counts, limited APC data) to refine the inference logic.

### 2.3. Feature Engineering

Feature engineering is the process of transforming raw data into features that better represent the underlying problem to predictive models. This section outlines the creation of trip-level, stop-level, contextual, and time-series specific features.

#### 2.3.1. Setting Up for Feature Engineering

Ensure you have the `unified_realtime_historical_data` available, either in a database or as a Pandas DataFrame. We will primarily use `pandas` for feature creation.

```python
import pandas as pd
import numpy as np
from datetime import datetime

# Assuming unified_historical_data_df is loaded from your database
# Example: unified_historical_data_df = pd.read_sql("SELECT * FROM unified_realtime_historical_data", conn)
```

#### 2.3.2. Trip-Level Features

These features describe characteristics of individual trips.

```python
def create_trip_features(df):
    # Ensure timestamp columns are datetime objects
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["scheduled_arrival_time"] = pd.to_datetime(df["scheduled_arrival_time"])
    df["scheduled_departure_time"] = pd.to_datetime(df["scheduled_departure_time"])
    df["actual_arrival_time"] = pd.to_datetime(df["actual_arrival_time"])
    df["actual_departure_time"] = pd.to_datetime(df["actual_departure_time"])

    # Day of week, hour of day, is_weekend
    df["day_of_week"] = df["timestamp"].dt.day_name()
    df["hour_of_day"] = df["timestamp"].dt.hour
    df["is_weekend"] = df["timestamp"].dt.dayofweek >= 5 # Saturday=5, Sunday=6

    # Trip duration (using scheduled times for consistency, or actual if preferred)
    df["trip_duration_minutes"] = (df["scheduled_departure_time"] - df["scheduled_arrival_time"]).dt.total_seconds() / 60

    # Realized vs. scheduled time difference (adherence to schedule)
    # This assumes a 'trip_start_time' or similar for the entire trip
    # For simplicity, let's use the first stop's scheduled departure vs actual departure
    # In a real scenario, you'd calculate this per trip, perhaps at the origin.
    # For now, we'll use delay_minutes already calculated.
    df["realized_vs_scheduled_time_diff"] = df["delay_minutes"]

    # Trip distance (requires pre-calculated distances from shapes.txt)
    # Assuming you have a lookup table or function for trip_id to trip_distance
    # df["trip_distance_km"] = df["trip_id"].map(trip_distance_lookup)

    return df
```

#### 2.3.3. Stop-Level Features

These features describe characteristics of individual stops.

```python
def create_stop_features(df):
    # Zone ID (assuming you have a function or lookup for stop_lat/lon to zone_id)
    # df["zone_id"] = df.apply(lambda row: get_zone_id(row["stop_lat"], row["stop_lon"]), axis=1)

    # Nearby POIs count (requires OSM data processing and spatial joins)
    # df["nearby_pois_count"] = df.apply(lambda row: count_pois_nearby(row["stop_lat"], row["stop_lon"]), axis=1)

    # Historical Dwell Time and Headway (requires aggregation of historical data)
    # This would typically be pre-computed and joined, or calculated using rolling windows
    # Example: Calculate average historical dwell time per stop_id, hour_of_day, day_of_week
    df["historical_dwell_time_avg"] = df.groupby(["stop_id", "hour_of_day", "day_of_week"])
                                        ["inferred_dwell_time_seconds"].transform(lambda x: x.rolling(window=7, min_periods=1).mean().shift(1))
    # Shift(1) to avoid data leakage (using past data to predict future)

    # Historical Headway (more complex, requires knowing previous vehicle arrival times at a stop)
    # This would typically be calculated in a separate process and joined.

    return df
```

#### 2.3.4. Contextual Features

These features capture external factors influencing demand.

```python
def create_contextual_features(df, weather_df, events_df):
    # Merge weather data
    # Ensure weather_df has a 'timestamp' column and 'latitude', 'longitude' for merging
    # For simplicity, assuming weather data is merged based on nearest timestamp and location
    # In a real system, you'd use a more robust temporal-spatial join.
    df["weather_condition"] = None # Placeholder
    df["temperature_celsius"] = None # Placeholder
    df["precipitation_mm"] = None # Placeholder

    # Merge event data
    # Assuming events_df has 'event_date' and 'event_location' or 'event_coordinates'
    # df["event_flag"] = df.apply(lambda row: is_event_nearby(row["timestamp"].date(), row["stop_lat"], row["stop_lon"], events_df), axis=1)

    return df
```

#### 2.3.5. Time-Series Specific Feature Engineering

These are crucial for time-series forecasting models.

```python
def create_time_series_features(df):
    # Lag Features for inferred_demand_level (or predicted riders)
    # Sort by stop_id and timestamp first
    df = df.sort_values(by=["stop_id", "timestamp"])

    # Example: Lag of inferred_dwell_time_seconds (as a proxy for demand)
    df["lag_dwell_time_1hr"] = df.groupby("stop_id")["inferred_dwell_time_seconds"].shift(1) # Lag by 1 time step (e.g., 1 hour if data is hourly)
    df["lag_dwell_time_24hr"] = df.groupby("stop_id")["inferred_dwell_time_seconds"].shift(24) # Lag by 24 time steps

    # Rolling Window Statistics
    df["rolling_avg_dwell_time_3hr"] = df.groupby("stop_id")["inferred_dwell_time_seconds"].transform(lambda x: x.rolling(window=3, min_periods=1).mean().shift(1))
    df["rolling_max_dwell_time_3hr"] = df.groupby("stop_id")["inferred_dwell_time_seconds"].transform(lambda x: x.rolling(window=3, min_periods=1).max().shift(1))

    # Cyclical Features for hour_of_day and day_of_week
    df["sin_hour"] = np.sin(2 * np.pi * df["hour_of_day"] / 24)
    df["cos_hour"] = np.cos(2 * np.pi * df["hour_of_day"] / 24)
    
    # For day of week, map to 0-6 (Monday=0, Sunday=6)
    df["day_of_week_num"] = df["timestamp"].dt.dayofweek
    df["sin_day_of_week"] = np.sin(2 * np.pi * df["day_of_week_num"] / 7)
    df["cos_day_of_week"] = np.cos(2 * np.pi * df["day_of_week_num"] / 7)

    return df
```

#### 2.3.6. Feature Store Integration

Once features are engineered, they should be published to a Feature Store (e.g., Feast) for consistent access during training and inference. This involves defining feature views and entities in Feast and then ingesting the data.

**Example Feast Feature Definition (Conceptual `feature_store.py`):**

```python
from feast import FeatureStore, Entity, FeatureView, Field, ValueType
from feast.types import Int64, Float32, String

# Define an entity for stops
stop = Entity(name="stop_id", value_type=ValueType.STRING, description="MARTA Stop ID")

# Define a feature view for stop-level features
stop_features = FeatureView(
    name="stop_level_features",
    entities=[stop],
    ttl=timedelta(days=365), # Time-to-live for features
    schema=[
        Field(name="inferred_dwell_time_seconds", dtype=Float32),
        Field(name="lag_dwell_time_1hr", dtype=Float32),
        Field(name="rolling_avg_dwell_time_3hr", dtype=Float32),
        Field(name="sin_hour", dtype=Float32),
        Field(name="cos_hour", dtype=Float32),
        Field(name="sin_day_of_week", dtype=Float32),
        Field(name="cos_day_of_week", dtype=Float32),
        Field(name="weather_condition", dtype=String),
        # ... add all other features
    ],
    source=FileSource(path="data/features/stop_features.parquet"), # Or a BigQuerySource, RedshiftSource etc.
    # You would typically define a batch source for historical features
)

# Define a feature view for trip-level features
trip_features = FeatureView(
    name="trip_level_features",
    entities=[Entity(name="trip_id", value_type=ValueType.STRING)],
    ttl=timedelta(days=365),
    schema=[
        Field(name="trip_duration_minutes", dtype=Float32),
        Field(name="delay_minutes", dtype=Float32),
        # ...
    ],
    source=FileSource(path="data/features/trip_features.parquet"),
)

# Initialize the feature store
# fs = FeatureStore(repo_path=".")
# fs.apply([stop, stop_features, trip_features])

# To ingest data into the feature store (offline store)
# fs.ingest(stop_features, feature_df)
```

This structured approach to feature engineering and management ensures that your models have access to high-quality, consistent data, which is critical for accurate demand forecasting. The next section will delve into the implementation of the Demand Forecasting Model.



### 2.4. Demand Forecasting Model (DFM)

This section outlines the implementation of the Demand Forecasting Model, starting with an LSTM-based approach for time-series forecasting of rider demand at stop-level.

#### 2.4.1. LSTM Model Implementation

LSTM (Long Short-Term Memory) networks are a type of recurrent neural network (RNN) well-suited for sequence prediction problems, making them ideal for time-series demand forecasting. We will use TensorFlow/Keras for implementation.

**Step 1: Prepare Data for LSTM**

LSTM models require input data to be in a specific 3D format: `(samples, timesteps, features)`. This involves creating sequences from your engineered features.

```python
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split

def create_sequences(data, sequence_length):
    xs, ys = [], []
    for i in range(len(data) - sequence_length):
        x = data[i:(i + sequence_length)]
        y = data[i + sequence_length]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

def prepare_lstm_data(df, target_column, features_columns, sequence_length):
    # Ensure data is sorted by stop_id and timestamp
    df = df.sort_values(by=["stop_id", "timestamp"])

    all_sequences_X = []
    all_sequences_y = []

    # Process each stop_id separately to avoid mixing sequences across different stops
    for stop_id in df["stop_id"].unique():
        stop_df = df[df["stop_id"] == stop_id].copy()
        
        # Select features and target
        data = stop_df[features_columns + [target_column]].values
        
        # Scale features (important for LSTMs)
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(data)
        
        # Create sequences
        X, y = create_sequences(scaled_data, sequence_length)
        
        if len(X) > 0:
            all_sequences_X.append(X)
            all_sequences_y.append(y)

    if not all_sequences_X:
        return None, None, None # No data to process

    X_combined = np.concatenate(all_sequences_X, axis=0)
    y_combined = np.concatenate(all_sequences_y, axis=0)
    
    # Split data into training and testing sets
    # For time series, it's often better to split chronologically or use time-series cross-validation
    # For simplicity here, we use random split, but be aware of potential data leakage.
    X_train, X_test, y_train, y_test = train_test_split(X_combined, y_combined, test_size=0.2, random_state=42)

    return X_train, X_test, y_train, y_test, scaler # Return scaler to inverse transform predictions

# Example Usage:
# Assuming `unified_historical_data_df` is your DataFrame with engineered features
# target_column = "inferred_dwell_time_seconds" # Or "predicted_riders" if you have it
# features_columns = [col for col in unified_historical_data_df.columns if col not in ["stop_id", "timestamp", target_column]]
# sequence_length = 24 # Use last 24 time steps (e.g., 24 hours) to predict next

# X_train, X_test, y_train, y_test, scaler = prepare_lstm_data(unified_historical_data_df, target_column, features_columns, sequence_length)
# if X_train is not None:
#     print(f"X_train shape: {X_train.shape}") # (samples, timesteps, features)
#     print(f"y_train shape: {y_train.shape}") # (samples, features_including_target)
```

**Step 2: Build and Train LSTM Model**

```python
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping

def build_lstm_model(input_shape, output_features):
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=input_shape))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=output_features)) # Output layer for regression
    model.compile(optimizer="adam", loss="mse") # Mean Squared Error for regression
    return model

# Example Usage:
# input_shape = (X_train.shape[1], X_train.shape[2]) # (timesteps, features)
# output_features = y_train.shape[1] # Number of features in the target (including the actual target column)

# model = build_lstm_model(input_shape, output_features)
# model.summary()

# early_stopping = EarlyStopping(monitor=\'val_loss\', patience=10, restore_best_weights=True)

# history = model.fit(
#     X_train, y_train,
#     epochs=100,
#     batch_size=32,
#     validation_split=0.1,
#     callbacks=[early_stopping],
#     verbose=1
# )
```

**Step 3: Make Predictions and Evaluate**

```python
from sklearn.metrics import mean_squared_error, mean_absolute_error

def evaluate_lstm_model(model, X_test, y_test, scaler, target_column_index):
    predictions_scaled = model.predict(X_test)
    
    # Create a dummy array with the same shape as original data for inverse_transform
    # Fill with zeros for non-target features, and predictions for the target feature
    dummy_array_predictions = np.zeros((predictions_scaled.shape[0], scaler.n_features_in_))
    dummy_array_predictions[:, target_column_index] = predictions_scaled[:, target_column_index] # Assuming target is the last column
    predictions = scaler.inverse_transform(dummy_array_predictions)[:, target_column_index]

    dummy_array_actual = np.zeros((y_test.shape[0], scaler.n_features_in_))
    dummy_array_actual[:, target_column_index] = y_test[:, target_column_index]
    actuals = scaler.inverse_transform(dummy_array_actual)[:, target_column_index]

    rmse = np.sqrt(mean_squared_error(actuals, predictions))
    mae = mean_absolute_error(actuals, predictions)

    print(f"LSTM Model RMSE: {rmse:.2f}")
    print(f"LSTM Model MAE: {mae:.2f}")
    
    return predictions, actuals

# Example Usage:
# target_column_index = features_columns.index(target_column) + len(features_columns) # Index of target in scaled_data
# predictions, actuals = evaluate_lstm_model(model, X_test, y_test, scaler, target_column_index)
```

#### 2.4.2. XGBoost Model Implementation

XGBoost is a powerful gradient boosting framework that can also be effectively used for time-series forecasting by framing the problem as a supervised learning task with engineered lag features.

**Step 1: Prepare Data for XGBoost**

XGBoost expects a 2D array of features and a 1D array for the target. The time-series aspect is captured through lag features and other temporal features created during feature engineering.

```python
import xgboost as xgb

def prepare_xgboost_data(df, target_column, features_columns):
    # Ensure no NaNs in features or target, as XGBoost handles them differently or not at all
    df = df.dropna(subset=features_columns + [target_column])

    X = df[features_columns].values
    y = df[target_column].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    return X_train, X_test, y_train, y_test

# Example Usage:
# Assuming `unified_historical_data_df` is your DataFrame with engineered features
# target_column = "inferred_dwell_time_seconds"
# features_columns = [col for col in unified_historical_data_df.columns if col.startswith("lag_") or col.startswith("rolling_") or col in ["day_of_week_num", "hour_of_day", "sin_hour", "cos_hour", "sin_day_of_week", "cos_day_of_week", "temperature_celsius", "precipitation_mm", "event_flag"]]

# X_train_xgb, X_test_xgb, y_train_xgb, y_test_xgb = prepare_xgboost_data(unified_historical_data_df, target_column, features_columns)
# if X_train_xgb is not None:
#     print(f"X_train_xgb shape: {X_train_xgb.shape}")
#     print(f"y_train_xgb shape: {y_train_xgb.shape}")
```

**Step 2: Build and Train XGBoost Model**

```python
def build_and_train_xgboost_model(X_train, y_train):
    model = xgb.XGBRegressor(
        objective=\'reg:squarederror\', # For regression tasks
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=5,
        subsample=0.7,
        colsample_bytree=0.7,
        random_state=42,
        n_jobs=-1
    )
    
    model.fit(X_train, y_train,
              eval_set=[(X_train, y_train)],
              early_stopping_rounds=50, # Stop if validation metric doesn't improve for 50 rounds
              verbose=False)
    return model

# Example Usage:
# xgb_model = build_and_train_xgboost_model(X_train_xgb, y_train_xgb)
```

**Step 3: Make Predictions and Evaluate**

```python
def evaluate_xgboost_model(model, X_test, y_test):
    predictions = model.predict(X_test)
    
    rmse = np.sqrt(mean_squared_error(y_test, predictions))
    mae = mean_absolute_error(y_test, predictions)

    print(f"XGBoost Model RMSE: {rmse:.2f}")
    print(f"XGBoost Model MAE: {mae:.2f}")
    
    return predictions, y_test

# Example Usage:
# xgb_predictions, xgb_actuals = evaluate_xgboost_model(xgb_model, X_test_xgb, y_test_xgb)
```

#### 2.4.3. Spatio-Temporal Graph Convolutional Networks (STGCN) + LSTM Hybrid (Advanced)

Implementing STGCNs is significantly more complex and typically requires specialized libraries like PyTorch Geometric (PyG) or Deep Graph Library (DGL). This section provides a conceptual overview and highlights key steps.

**Conceptual Steps:**

1.  **Graph Construction**: Define the graph structure of your transit network. Nodes are `stop_id`s, and edges represent connections (e.g., direct route segments, proximity). An adjacency matrix or adjacency list will represent this graph.
2.  **Data Preparation**: Data needs to be structured as a sequence of graph signals. For each time step, each node (stop) will have a vector of features (e.g., historical demand, weather, time-of-day indicators).
3.  **Model Architecture**: Combine Graph Convolutional Layers (to capture spatial dependencies) with Temporal Layers (like LSTM or 1D CNNs to capture temporal dependencies).

    ```python
    # Conceptual PyTorch/PyG-like structure
    import torch
    import torch.nn as nn
    # from torch_geometric.nn import GCNConv # Requires PyTorch Geometric

    class STGCN(nn.Module):
        def __init__(self, num_nodes, num_features, num_timesteps_input, num_timesteps_output):
            super(STGCN, self).__init__()
            # Example: Two GCN layers followed by LSTM
            # self.gcn1 = GCNConv(num_features, 64)
            # self.gcn2 = GCNConv(64, 32)
            self.lstm = nn.LSTM(input_size=32 * num_nodes, hidden_size=128, batch_first=True)
            self.fc = nn.Linear(128, num_nodes * num_timesteps_output) # Output for each node for future timesteps

        def forward(self, x, edge_index): # x: (batch_size, num_timesteps_input, num_nodes, num_features)
            # Apply GCNs at each timestep (conceptual)
            # spatial_features = []
            # for t in range(x.size(1)):
            #     h = F.relu(self.gcn1(x[:, t, :, :].view(x.size(0), -1), edge_index)) # Flatten features for GCN
            #     h = F.relu(self.gcn2(h, edge_index))
            #     spatial_features.append(h.view(x.size(0), -1)) # Flatten back for LSTM
            
            # temporal_input = torch.stack(spatial_features, dim=1) # (batch_size, num_timesteps_input, num_nodes * 32)
            
            # lstm_out, _ = self.lstm(temporal_input)
            # output = self.fc(lstm_out[:, -1, :]) # Use last LSTM output for prediction
            # return output.view(-1, num_nodes, num_timesteps_output)
            pass # Placeholder for actual implementation

    # Training and evaluation would follow standard PyTorch practices.
    ```

4.  **Training and Evaluation**: Similar to other deep learning models, this involves defining a loss function (e.g., MSE), an optimizer, and training the model on historical spatio-temporal data. Evaluation metrics would include RMSE, MAE, and potentially spatial correlation metrics.

This concludes the implementation details for the Demand Forecasting Model. The next section will cover the Route Optimization Simulation.



### 2.5. Route Optimization Simulation Engine (ROSE)

The Route Optimization Simulation Engine (ROSE) takes the forecasted demand and current route topology to propose optimized routes. This section outlines the implementation of heuristic/greedy optimization algorithms and simulation techniques.

#### 2.5.1. Input Data for Optimization

The ROSE requires several inputs:

*   **Forecasted Demand Heatmap**: Predicted rider numbers per `stop_id` × `timestamp` from the DFM. This can be represented as a dictionary or DataFrame mapping `(stop_id, timestamp)` to `predicted_riders`.
*   **Route Topology**: Static GTFS `shapes.txt` and `trips.txt` data, providing the geographic paths and sequence of stops for each route.
*   **Bus Capacity Assumptions**: Maximum passenger capacity for different bus types.
*   **Operational Constraints**: User-defined constraints such as maximum allowable detour time, minimum headway, maximum number of short-turn loops, etc.

#### 2.5.2. Heuristic/Greedy Optimization Algorithm

For the MVP, a heuristic or greedy approach can be implemented to quickly generate route adjustments. This example focuses on a simplified greedy approach for adding short-turn loops to alleviate overcrowding.

**Conceptual Algorithm: Short-Turn Loop Addition**

1.  **Identify Overloaded Segments**: Based on the forecasted demand heatmap and bus capacity, identify `stop_id`s or segments of routes that are predicted to be overloaded during specific time windows.
2.  **Prioritize Overloaded Segments**: Rank overloaded segments by severity (e.g., highest predicted overcrowding).
3.  **Propose Short-Turn Loops**: For the highest-priority overloaded segment:
    *   Identify a suitable `start_stop` and `end_stop` for a short-turn loop within or around the overloaded segment.
    *   Ensure the `start_stop` and `end_stop` are existing stops on the route.
    *   The loop should ideally start before the overloaded segment and end after it, or within it.
4.  **Simulate Impact**: Run a simulation (see Section 2.5.3) with the proposed short-turn loop to evaluate its impact on load balancing, passenger wait times, and vehicle utilization.
5.  **Accept/Reject**: If the simulation shows significant improvement and meets operational constraints, accept the proposed change. Otherwise, try another short-turn loop or a different optimization strategy.

**Python Implementation Snippet (Conceptual):**

```python
def identify_overloaded_segments(forecasted_demand, bus_capacity):
    overloaded_segments = []
    # This function would iterate through forecasted_demand
    # and compare predicted_riders with bus_capacity for each stop/time window.
    # It would also consider the sequence of stops to identify 'segments'.
    # Example: if predicted_riders > 1.2 * bus_capacity for 3 consecutive stops,
    # mark that segment as overloaded.
    
    # For demonstration, let's assume a simple output format:
    # [(route_id, start_stop_id, end_stop_id, predicted_overload_factor, time_window), ...]
    return overloaded_segments

def propose_short_turn_loop(route_topology, overloaded_segment):
    route_id, seg_start_stop, seg_end_stop, _, time_window = overloaded_segment
    
    # Logic to find suitable start and end stops for a short-turn loop
    # This would involve looking at the route_topology (stop sequences for the route)
    # and identifying stops that could serve as turnaround points.
    
    # Example: Find stops on the route before seg_start_stop and after seg_end_stop
    # that are suitable for a loop (e.g., near a depot, or a major intersection).
    
    proposed_loop = {
        "route_id": route_id,
        "original_trip_id": "some_trip_id", # The trip to be modified
        "new_trip_segment": ["stop_A", "stop_B", "stop_C"], # The new path for the short-turn
        "loop_start_stop_id": seg_start_stop,
        "loop_end_stop_id": seg_end_stop,
        "time_window": time_window
    }
    return proposed_loop

def run_greedy_optimization(forecasted_demand, route_topology, bus_capacity, operational_constraints):
    optimized_routes = []
    overloaded_segments = identify_overloaded_segments(forecasted_demand, bus_capacity)
    
    # Sort segments by severity (e.g., highest overload first)
    overloaded_segments.sort(key=lambda x: x[3], reverse=True)

    for segment in overloaded_segments:
        proposed_loop = propose_short_turn_loop(route_topology, segment)
        if proposed_loop:
            # Simulate the impact of this proposed loop
            # (This would call the simulation module)
            # simulation_results = simulate_route_change(route_topology, proposed_loop, forecasted_demand)
            
            # if simulation_results["load_balancing_improvement"] > threshold and \
            #    simulation_results["passenger_wait_time_increase"] < max_allowed_increase:
            optimized_routes.append(proposed_loop)
            # Update forecasted_demand to reflect the impact of this accepted change
            # break # For a simple greedy, accept first good one and move on

    return optimized_routes
```

#### 2.5.3. Route Simulation Techniques

Simulation is critical for evaluating the impact of proposed route changes. Discrete Event Simulation (DES) is a suitable approach for modeling transit systems.

**Conceptual Steps for Discrete Event Simulation (DES):**

1.  **Define Entities**: Passengers (with origin, destination, desired travel time), Vehicles (with capacity, current location, schedule), Stops.
2.  **Define Events**: Passenger arrival at stop, Vehicle arrival at stop, Vehicle departure from stop, Passenger boarding, Passenger alighting.
3.  **Simulation Clock**: Advance time based on events.
4.  **Event Logic**: For each event, update system state and schedule future events.
    *   **Passenger Arrival**: Passenger arrives at a stop, joins queue. Schedules next passenger arrival.
    *   **Vehicle Arrival**: Vehicle arrives at a stop. Passengers alight. Passengers board (if space and destination matches). Dwell time calculated. Schedules Vehicle Departure.
    *   **Vehicle Departure**: Vehicle leaves stop. Schedules next Vehicle Arrival at next stop.

**Key Metrics to Track in Simulation:**

*   **Passenger Wait Time**: Time from passenger arrival at stop to boarding a vehicle.
*   **Passenger Travel Time**: Total time from origin to destination.
*   **Vehicle Utilization**: Percentage of time vehicles are carrying passengers vs. empty.
*   **Load Balancing**: Distribution of passengers across vehicles and routes.
*   **Headway Adherence**: How well vehicles maintain scheduled headways.

**Python Library for DES**: Libraries like `SimPy` can be used to build discrete event simulations.

```python
import simpy
import random

class Passenger:
    def __init__(self, env, name, origin_stop, destination_stop, arrival_time):
        self.env = env
        self.name = name
        self.origin_stop = origin_stop
        self.destination_stop = destination_stop
        self.arrival_time = arrival_time
        self.wait_start_time = None
        self.board_time = None
        self.alight_time = None
        self.total_wait_time = 0
        self.total_travel_time = 0

    def arrive_at_stop(self):
        print(f"Passenger {self.name} arrived at {self.origin_stop} at {self.env.now:.2f}")
        self.wait_start_time = self.env.now
        # Add self to stop queue

class Bus:
    def __init__(self, env, name, route, capacity):
        self.env = env
        self.name = name
        self.route = route
        self.capacity = capacity
        self.passengers = []
        self.current_stop_index = 0

    def run(self):
        while True:
            current_stop = self.route[self.current_stop_index]
            print(f"Bus {self.name} arrived at {current_stop} at {self.env.now:.2f}")

            # Alighting passengers
            alighted_count = 0
            for p in list(self.passengers):
                if p.destination_stop == current_stop:
                    self.passengers.remove(p)
                    p.alight_time = self.env.now
                    p.total_travel_time = p.alight_time - p.board_time
                    alighted_count += 1
            print(f"Bus {self.name} alighted {alighted_count} passengers at {current_stop}")

            # Boarding passengers
            boarded_count = 0
            # Logic to board passengers from current_stop queue up to capacity
            # For simplicity, assume passengers are waiting and board if space
            while len(self.passengers) < self.capacity and random.random() < 0.8: # Simulate some boarding
                # Get passenger from queue (conceptual)
                new_passenger = Passenger(self.env, f"P{random.randint(100,999)}", current_stop, random.choice(self.route[self.current_stop_index+1:]), self.env.now)
                self.passengers.append(new_passenger)
                new_passenger.board_time = self.env.now
                new_passenger.total_wait_time = new_passenger.board_time - new_passenger.wait_start_time if new_passenger.wait_start_time else 0
                boarded_count += 1
            print(f"Bus {self.name} boarded {boarded_count} passengers at {current_stop}. Current load: {len(self.passengers)}")

            dwell_time = random.uniform(10, 30) # Simulate dwell time
            yield self.env.timeout(dwell_time)
            print(f"Bus {self.name} departed from {current_stop} at {self.env.now:.2f}")

            # Move to next stop
            self.current_stop_index = (self.current_stop_index + 1) % len(self.route)
            travel_time = random.uniform(60, 180) # Simulate travel time between stops
            yield self.env.timeout(travel_time)

def simulate_route_change(original_route, proposed_route_change, forecasted_demand):
    env = simpy.Environment()
    
    # Initialize buses with original route
    bus1 = Bus(env, "Bus-A", original_route, capacity=50)
    env.process(bus1.run())

    # If proposed_route_change is applied, modify bus route or add new bus
    # For simplicity, let's just run a short simulation
    env.run(until=3600) # Simulate for 1 hour

    # Collect and return metrics (conceptual)
    return {
        "load_balancing_improvement": 0.1, # Example value
        "passenger_wait_time_increase": -5, # Example value (reduction)
        "vehicle_utilization": 0.75 # Example value
    }

# Example Usage:
# original_marta_route = ["Stop1", "Stop2", "Stop3", "Stop4", "Stop5"]
# proposed_short_turn = {"route_id": "RouteX", "new_trip_segment": ["Stop2", "Stop3", "Stop2"], ...}
# forecasted_demand_data = {...}

# simulation_results = simulate_route_change(original_marta_route, proposed_short_turn, forecasted_demand_data)
# print(simulation_results)
```

#### 2.5.4. Integration with Optimization Algorithm

The simulation module will be called by the optimization algorithm to evaluate the effectiveness of each proposed route modification. This iterative process allows the optimizer to select the best changes based on simulated outcomes.

*   **Feedback Loop**: The simulation results (e.g., improved load balancing, reduced wait times) serve as feedback to the optimization algorithm, guiding it towards better solutions.
*   **Computational Cost**: Running detailed simulations can be computationally expensive. For real-time optimization, consider using faster, simplified simulation models or pre-computed lookup tables based on extensive offline simulations.

This section provides a foundation for implementing the Route Optimization Simulation Engine. The next and final implementation section will cover Visualization & Validation.



### 2.6. Visualization & Validation

Interactive dashboards are crucial for monitoring the platform's performance, validating model predictions against actual data, and providing actionable insights for route optimization. This section outlines the use of Streamlit, Plotly, and Folium for building these dashboards.

#### 2.6.1. Setting Up for Visualization

Ensure you have the necessary libraries installed. If you haven't already, install Streamlit, Plotly, and Folium:

```bash
pip install streamlit plotly folium
```

#### 2.6.2. Building an Interactive Dashboard with Streamlit

Streamlit allows for rapid development of web applications using pure Python. We will create a `dashboard.py` file.

**Step 1: Basic Streamlit App Structure**

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static

st.set_page_config(layout="wide")
st.title("MARTA Demand Forecasting & Route Optimization Dashboard")

# --- Data Loading (Placeholder - In a real app, this would query your database/feature store) ---
@st.cache_data
def load_data():
    # Replace with actual data loading from your unified_realtime_historical_data table
    # For demonstration, creating dummy data
    data = {
        "timestamp": pd.to_datetime(pd.date_range(start="2025-01-01", periods=100, freq="H")),
        "stop_id": [f"Stop_{i%5 + 1}" for i in range(100)],
        "predicted_riders": np.random.randint(10, 150, 100),
        "actual_riders": np.random.randint(5, 160, 100),
        "stop_lat": np.random.uniform(33.7, 33.8, 100),
        "stop_lon": np.random.uniform(-84.4, -84.3, 100),
        "demand_level": np.random.choice(["Underloaded", "Normal", "Overloaded"], 100, p=[0.2, 0.6, 0.2])
    }
    df = pd.DataFrame(data)
    return df

df = load_data()

# --- Sidebar Filters ---
st.sidebar.header("Filters")
selected_stop = st.sidebar.selectbox("Select Stop", options=df["stop_id"].unique())

# Filter data based on selection
filtered_df = df[df["stop_id"] == selected_stop]

# --- Display KPIs ---
st.subheader("Key Performance Indicators")
col1, col2, col3 = st.columns(3)

with col1:
    avg_predicted = filtered_df["predicted_riders"].mean()
    st.metric(label="Avg. Predicted Riders", value=f"{avg_predicted:.0f}")

with col2:
    avg_actual = filtered_df["actual_riders"].mean()
    st.metric(label="Avg. Actual Riders", value=f"{avg_actual:.0f}")

with col3:
    # Example: Calculate prediction error
    if not filtered_df.empty:
        mae = np.mean(np.abs(filtered_df["predicted_riders"] - filtered_df["actual_riders"]))
        st.metric(label="Mean Absolute Error", value=f"{mae:.0f}")
    else:
        st.metric(label="Mean Absolute Error", value="N/A")

# --- Predicted vs. Actual Ridership Over Time (Plotly) ---
st.subheader("Predicted vs. Actual Ridership Over Time")
fig_time_series = px.line(filtered_df, x="timestamp", y=["predicted_riders", "actual_riders"],
                          title=f"Ridership at {selected_stop}")
st.plotly_chart(fig_time_series, use_container_width=True)

# --- Demand Level Distribution (Plotly) ---
st.subheader("Demand Level Distribution")
demand_counts = filtered_df["demand_level"].value_counts().reset_index()
demand_counts.columns = ["Demand Level", "Count"]
fig_pie = px.pie(demand_counts, values="Count", names="Demand Level", title="Demand Level Distribution")
st.plotly_chart(fig_pie, use_container_width=True)

# --- Map Visualization (Folium) ---
st.subheader("Stop Location and Demand Heatmap")

# Create a base map centered around Atlanta
m = folium.Map(location=[33.7490, -84.3880], zoom_start=12)

# Add markers for all stops
for idx, row in df.drop_duplicates(subset=["stop_id"]).iterrows():
    folium.Marker(
        location=[row["stop_lat"], row["stop_lon"]],
        popup=f"Stop ID: {row["stop_id"]}<br>Avg. Predicted: {df[df["stop_id"]==row["stop_id"]]["predicted_riders"].mean():.0f}"
    ).add_to(m)

# Add a simple heatmap layer based on predicted ridership (conceptual)
# For a real heatmap, you'd aggregate predicted ridership spatially
# from folium.plugins import HeatMap
# HeatMap(data=df[["stop_lat", "stop_lon", "predicted_riders"]].values.tolist()).add_to(m)

# Display the map
folium_static(m)

# --- Route Optimization Simulation Overlays (Conceptual) ---
st.subheader("Route Optimization Simulation Overlays")
st.write("This section would display proposed route changes and their simulated impact on the map.")
st.write("Example: Overlay new short-turn loops or modified route segments.")

# You would add logic here to load and display GeoJSON or other spatial data
# representing proposed route changes, potentially with color-coding for impact.

# --- KPI Comparisons with Official MARTA Metrics ---
st.subheader("KPI Comparisons with Official MARTA Metrics")
st.write("This section would compare the platform's calculated KPIs (e.g., average delay, passenger wait times) with official MARTA reported metrics.")
st.write("This helps in validating the model's accuracy and the simulation's realism.")

# Example: Display a table or bar chart comparing predicted vs. actual monthly boardings
# st.dataframe(comparison_df)
```

**Step 2: Run the Streamlit App**

Save the above code as `dashboard.py` in your project root. To run the dashboard, open your terminal in the project directory and execute:

```bash
streamlit run dashboard.py
```

This will open the dashboard in your web browser, typically at `http://localhost:8501`. You can interact with the filters and observe the dynamic updates to the charts and map.

#### 2.6.3. Validation Strategy

Validation is an ongoing process to ensure the accuracy and effectiveness of the demand forecasting model and the route optimization engine.

*   **Model Performance Metrics**: Continuously monitor standard ML metrics for the DFM (e.g., RMSE, MAE, R-squared for regression; precision, recall, F1-score for classification of demand levels). Track these metrics over time to detect model drift.
*   **Backtesting**: Regularly backtest the DFM on historical data to assess its performance on unseen past periods. This involves training the model on data up to a certain point and evaluating it on subsequent periods.
*   **Comparison with Ground Truth**: Whenever possible, compare predicted demand and inferred dwell times with actual ridership data (e.g., from MARTA's monthly KPI reports or any available APC data). This is crucial for validating the accuracy of the demand inference process.
*   **A/B Testing (Controlled Rollout)**: For route optimization, a phased rollout or A/B testing approach can be used in collaboration with MARTA operations. This involves implementing proposed changes on a small scale or in specific areas and comparing their real-world impact against control groups.
*   **Operational Feedback**: Establish a feedback loop with MARTA operations personnel. Their qualitative insights on route performance, congestion points, and passenger experience are invaluable for refining both the forecasting model and the optimization algorithms.
*   **Simulation Validation**: Validate the simulation model itself by comparing its outputs (e.g., simulated vehicle travel times, dwell times) against historical real-world observations. If the simulation accurately reflects reality, its predictions for optimized routes will be more reliable.

By implementing these visualization and validation strategies, the MARTA Demand Forecasting & Route Optimization Platform can continuously improve its accuracy and deliver tangible benefits to transit operations.

