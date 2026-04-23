"""Cluster per-trajectory stop segments into spatially recurrent regions.

The `cbsmot process` step emits one segment per low-speed episode per
vehicle. A single congestion hotspot therefore shows up as many segments
clustered in the same place. This module groups those segments into
"regions" using DBSCAN on great-circle distances between segment
centroids, matching the "recurrent regions" concept in the CB-SMoT paper.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from shapely import wkt
from sklearn.cluster import DBSCAN

REGION_COLUMNS = [
    "region_id",
    "num_segments",
    "unique_vehicles",
    "num_routes",
    "centroid_latitude",
    "centroid_longitude",
    "mean_duration_seconds",
    "total_duration_seconds",
    "mean_average_speed_mps",
    "route_ids",
]

EARTH_RADIUS_METERS = 6_371_000.0


def _segment_centroids(segments: pd.DataFrame) -> np.ndarray:
    """Return an (N, 2) array of (latitude, longitude) centroids from WKT."""
    lats = np.empty(len(segments), dtype=float)
    lons = np.empty(len(segments), dtype=float)
    for i, wkt_str in enumerate(segments["geometry_wkt"].to_list()):
        geom = wkt.loads(wkt_str)
        centroid = geom.centroid
        lons[i] = centroid.x
        lats[i] = centroid.y
    return np.column_stack([lats, lons])


def cluster_regions(
    segments: pd.DataFrame,
    *,
    eps_meters: float = 150.0,
    min_samples: int = 3,
) -> pd.DataFrame:
    """Cluster segment centroids into recurrent regions via haversine DBSCAN.

    A region is emitted when at least `min_samples` distinct segments lie
    within `eps_meters` of each other. DBSCAN noise points (label -1) are
    dropped since they represent one-off stops, not recurrent hotspots.
    """
    if segments.empty:
        return pd.DataFrame(columns=REGION_COLUMNS)

    centroids_deg = _segment_centroids(segments)
    centroids_rad = np.radians(centroids_deg)
    eps_rad = eps_meters / EARTH_RADIUS_METERS

    labels = DBSCAN(
        eps=eps_rad,
        min_samples=min_samples,
        metric="haversine",
        algorithm="ball_tree",
    ).fit_predict(centroids_rad)

    labelled = segments.copy()
    labelled["_cluster"] = labels
    labelled["_centroid_lat"] = centroids_deg[:, 0]
    labelled["_centroid_lon"] = centroids_deg[:, 1]
    labelled = labelled[labelled["_cluster"] != -1]
    if labelled.empty:
        return pd.DataFrame(columns=REGION_COLUMNS)

    records = []
    for cluster_id, group in labelled.groupby("_cluster", sort=True):
        route_ids = sorted({int(r) for r in group["route_id"].dropna().unique()})
        records.append(
            {
                "region_id": int(cluster_id),
                "num_segments": int(len(group)),
                "unique_vehicles": int(group["vehicle_id"].nunique()),
                "num_routes": len(route_ids),
                "centroid_latitude": float(group["_centroid_lat"].mean()),
                "centroid_longitude": float(group["_centroid_lon"].mean()),
                "mean_duration_seconds": float(group["duration_seconds"].mean()),
                "total_duration_seconds": float(group["duration_seconds"].sum()),
                "mean_average_speed_mps": float(group["average_speed_mps"].mean()),
                "route_ids": ",".join(str(r) for r in route_ids),
            }
        )
    return pd.DataFrame.from_records(records, columns=REGION_COLUMNS)


def discover_regions(
    input_path: str | Path,
    output_path: str | Path,
    *,
    eps_meters: float = 150.0,
    min_samples: int = 3,
) -> pd.DataFrame:
    """Read a segments Parquet file, cluster into regions, write a regions Parquet file."""
    segments = pd.read_parquet(input_path)
    regions = cluster_regions(
        segments, eps_meters=eps_meters, min_samples=min_samples
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    regions.to_parquet(output_path, index=False)
    return regions
