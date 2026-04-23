# CB-SMoT

CB-SMoT (Clustering-Based Stops and Moves of Trajectories) applied to São Paulo public-transport GPS traces. Detects low-speed segments in bus trajectories, clusters recurrent segments into hotspot regions, and produces statistical summaries.

Slides: [CB-SMoT Project Presentation](https://drive.google.com/open?id=108H7DcA4e-1lTS9Nd5uoH5anfThruVe14oZFPv1kka0)

## Design

The pipeline is file-based and framework-light: Parquet in, Parquet out. Core dependencies are pandas, pyarrow, shapely, and scikit-learn.

```
SPTrans API  ──► cbsmot ingest ──►  trajectories.parquet
                                           │
                                           ▼
                                   cbsmot process  ──► segments.parquet
                                           │                   │
                                           ▼                   ▼
                                   cbsmot regions        cbsmot report
                                           │
                                           ▼
                                   regions.parquet
```

- **`cbsmot/algorithm.py`** — the pure CB-SMoT algorithm; no I/O, no dependencies.
- **`cbsmot/ingest.py`** — polls SPTrans Olho Vivo for vehicle positions and writes a trajectory Parquet. The poll time is stored as `datetime`; the raw API timestamp is preserved as `source_datetime`.
- **`cbsmot/process.py`** — reads a trajectory Parquet, groups points by vehicle, runs the algorithm, writes a segment Parquet with WKT geometries.
- **`cbsmot/regions.py`** — clusters segment centroids with DBSCAN to recover recurrent stop regions.
- **`cbsmot/report.py`** — aggregates a segment Parquet into summary statistics.
- **`cbsmot/cli.py`** — `python -m cbsmot ingest | process | regions | report` entry point.

## Input schema (`trajectories.parquet`)

| column        | type      | notes                                  |
|---------------|-----------|----------------------------------------|
| `vehicle_id`  | int       | stable per-vehicle identifier          |
| `route_id`    | int/null  | route the vehicle was serving, if any  |
| `datetime`    | timestamp | poll-observation time used for segmentation |
| `source_datetime` | timestamp/null | raw SPTrans `ta` timestamp, preserved for provenance |
| `latitude`    | float     | decimal degrees (WGS84)                |
| `longitude`   | float     | decimal degrees (WGS84)                |

## Output schema (`segments.parquet`)

`vehicle_id`, `route_id`, `start_time`, `end_time`, `duration_seconds`, `distance_meters`, `num_points`, `average_speed_mps`, `geometry_wkt` (LINESTRING).

## Usage

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Collect trajectories by polling SPTrans for 1 hour (requires a token).
export SPTRANS_TOKEN=your_token_here
python -m cbsmot ingest trajectories.parquet \
    --routes 8000 8100 --duration 3600 --interval 15

# Detect segments.
python -m cbsmot process trajectories.parquet segments.parquet \
    --max-speed 2.5 --min-time 90

# Cluster recurrent regions from the detected segments.
python -m cbsmot regions segments.parquet regions.parquet \
    --eps-meters 150 --min-samples 3

# Restrict to specific vehicles or routes.
python -m cbsmot process trajectories.parquet segments.parquet \
    --vehicle-ids 101 102

# Summarize.
python -m cbsmot report segments.parquet --top-n-routes 10
```

Obtain an SPTrans API token at <https://www.sptrans.com.br/desenvolvedores/>.

Programmatic use:

```python
import pandas as pd
from cbsmot.process import detect_segments
from cbsmot.regions import cluster_regions
from cbsmot.report import build_report

trajectories = pd.read_parquet("trajectories.parquet")
segments = detect_segments(trajectories, max_speed=2.5, min_time=90)
segments.to_parquet("segments.parquet", index=False)
regions = cluster_regions(segments, eps_meters=150, min_samples=3)
regions.to_parquet("regions.parquet", index=False)

report = build_report("segments.parquet", top_n_routes=10)
```

## Tests

```bash
python -m unittest discover -s tests
```

## Algorithm notes

Segmentation uses the poll-observation timestamp stored in `datetime`, not the raw SPTrans `ta`, because `ta` can repeat while a bus is stationary. A point joins the current stop only when the gap to the previous point is under `max_gap` seconds and the instantaneous speed is under `max_speed`; duplicate stationary fixes with zero elapsed time do not break an in-progress stop. The gap bound prevents sparse data from inflating a segment. A stop is emitted only if its accumulated duration exceeds `min_time`. All distances use haversine and are reported in meters; speeds are meters per second.
