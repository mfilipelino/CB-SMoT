# CB-SMoT
The CB-SMoT (Clustering-Based Approach for Discovering Interesting Places in a Single Trajectory)

## Identificação semântica de regiões de congestionamento no transporte público da cidade de São Paulo, utilizando API Olho Vivo
Slides: [CB-SMoT Project Presentation](https://drive.google.com/open?id=108H7DcA4e-1lTS9Nd5uoH5anfThruVe14oZFPv1kka0)

## Data Analysis and Reporting Enhancements

This project has been enhanced with new features focused on persistent storage of detected low-speed segments, streamlined data processing, and comprehensive statistical reporting. These additions significantly improve the project's data science capabilities by enabling:

*   **Structured Analysis:** Storing detected segments in a database allows for more organized and repeatable analysis.
*   **Feature Engineering:** The attributes of detected segments (e.g., duration, average speed, geometry) can serve as features for further machine learning models or deeper data mining.
*   **Quantitative Insights:** Statistical reports provide measurable insights into traffic patterns, congestion hotspots, and operational characteristics of public transport.
*   **Historical Tracking:** Persisting segments allows for tracking changes and trends over time if data is processed periodically.

### New Django Model: `DetectedSegment`

This model is designed to store the low-speed or "stop" segments identified from vehicle trajectories by the CB-SMoT algorithm.

**Key Fields:**

*   `vehicle`: A foreign key to the `Vehicle` model, indicating which vehicle generated the segment.
*   `route`: A foreign key to the `Route` model, indicating the route the vehicle was on (if available).
*   `start_time`: DateTimeField indicating the beginning of the segment.
*   `end_time`: DateTimeField indicating the end of the segment.
*   `duration_seconds`: FloatField storing the segment's duration in seconds.
*   `distance_meters`: FloatField storing the distance covered within the segment in meters.
*   `num_points`: IntegerField for the number of trajectory points that constitute the segment.
*   `average_speed_mps`: FloatField for the calculated average speed within the segment in meters per second.
*   `trajectory_points`: A ManyToManyField linking to the `Trajectory` model, storing the actual points that make up this segment.
*   `segment_geometry`: A LineStringField (GIS) storing the geographical path of the segment.

### New Management Commands

Two new Django management commands have been introduced to facilitate the processing and analysis of trajectory data.

#### 1. `process_trajectories`

This command processes raw trajectory data (assumed to be populated in the `Trajectory` model) using the underlying CB-SMoT algorithm. It identifies low-speed segments and saves them as `DetectedSegment` instances in the database.

**Key Command-Line Arguments:**

*   `--vehicle_ids <id1> <id2> ...`: Process trajectories only for the specified vehicle IDs.
*   `--route_ids <id1> <id2> ...`: Process trajectories for all vehicles associated with the specified route IDs. (Ignored if `--vehicle_ids` is used).
*   `--max_speed <float>`: Sets the maximum average speed in meters per second for a sequence of points to be considered a low-speed segment. Default: `3.0`.
*   `--min_time <float>`: Sets the minimum time duration in seconds for a low-speed segment to be considered valid. Default: `60.0`.
*   `--clear_existing`: If provided, all previously stored `DetectedSegment` records will be deleted before processing new ones.

**Example Usage:**

To process trajectories using a maximum speed of 2.5 m/s and a minimum segment duration of 90 seconds:
```bash
python manage.py process_trajectories --max_speed 2.5 --min_time 90
```

To process trajectories only for vehicle IDs 101 and 102:
```bash
python manage.py process_trajectories --vehicle_ids 101 102
```

#### 2. `report_segments`

This command generates a statistical report based on the `DetectedSegment` data stored in the database. It provides insights into the characteristics and distribution of detected low-speed segments.

**Statistics Provided:**

*   Overall averages: Total segments, average duration, average speed, average number of points per segment, and total distance covered by segments.
*   Top N routes: Lists routes with the highest number of detected segments.
*   Hourly distribution: Shows the number of segments that started in each hour of the day.

**Key Command-Line Arguments:**

*   `--top_n_routes <int>`: Customizes the number of top routes to display in the report. Default: `5`.

**Example Usage:**

To generate a report showing the top 3 routes by segment count:
```bash
python manage.py report_segments --top_n_routes 3
```

To generate a report with default settings:
```bash
python manage.py report_segments
```

### Typical Workflow

1.  **Data Population:** Ensure that vehicle trajectory data is loaded into the system's `Trajectory` model. (This step is typically handled by other processes, e.g., `populate_database` or `run_service_tracks` based on existing commands).
2.  **Process Trajectories:** Run the `process_trajectories` command to analyze the raw trajectories. This will identify low-speed segments and populate the `DetectedSegment` table in the database.
    ```bash
    python manage.py process_trajectories --max_speed 2.0 --min_time 120
    ```
3.  **Generate Report:** After processing, run the `report_segments` command to generate statistical insights from the newly populated `DetectedSegment` data.
    ```bash
    python manage.py report_segments --top_n_routes 10
    ```
This workflow allows users to transform raw GPS tracks into actionable insights about low-speed events, potentially indicating congestion or operational stops, and then quantify these events through statistical summaries.
