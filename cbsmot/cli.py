"""Command-line entry point: `python -m cbsmot ingest|process|regions|report`."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .algorithm import DEFAULT_MAX_GAP_SECONDS
from .ingest import ingest
from .process import process
from .regions import discover_regions
from .report import build_report, print_report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cbsmot")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("process", help="Detect low-speed segments from a trajectories Parquet file.")
    p.add_argument("input", type=Path, help="Input Parquet file with trajectory points.")
    p.add_argument("output", type=Path, help="Output Parquet file to write detected segments to.")
    p.add_argument("--max-speed", type=float, default=3.0, help="Max avg speed (m/s) for a segment. Default: 3.0")
    p.add_argument("--min-time", type=float, default=60.0, help="Min segment duration (s). Default: 60.0")
    p.add_argument(
        "--max-gap",
        type=float,
        default=DEFAULT_MAX_GAP_SECONDS,
        help=(
            f"Max gap (s) between consecutive points before the stop breaks. "
            f"Tune to the polling cadence. Default: {DEFAULT_MAX_GAP_SECONDS}"
        ),
    )
    p.add_argument("--vehicle-ids", type=int, nargs="+", help="Restrict to these vehicle IDs.")
    p.add_argument("--route-ids", type=int, nargs="+", help="Restrict to these route IDs (ignored if --vehicle-ids set).")

    r = sub.add_parser("report", help="Print a statistical report over a segments Parquet file.")
    r.add_argument("input", type=Path, help="Segments Parquet file produced by `cbsmot process`.")
    r.add_argument("--top-n-routes", type=int, default=5, help="Number of top routes to list. Default: 5")

    rg = sub.add_parser(
        "regions",
        help="Cluster segments into recurrent stop regions via DBSCAN over segment centroids.",
    )
    rg.add_argument("input", type=Path, help="Segments Parquet file produced by `cbsmot process`.")
    rg.add_argument("output", type=Path, help="Output Parquet file to write detected regions to.")
    rg.add_argument("--eps-meters", type=float, default=150.0, help="DBSCAN epsilon in meters. Default: 150.0")
    rg.add_argument("--min-samples", type=int, default=3, help="DBSCAN min samples per cluster. Default: 3")

    i = sub.add_parser("ingest", help="Poll SPTrans Olho Vivo and write a trajectories Parquet file.")
    i.add_argument("output", type=Path, help="Output Parquet file for collected trajectory rows.")
    i.add_argument("--routes", type=int, nargs="+", required=True, help="SPTrans route codes (codigoLinha) to poll.")
    i.add_argument("--duration", type=float, default=3600.0, help="Total polling duration in seconds. Default: 3600")
    i.add_argument("--interval", type=float, default=15.0, help="Seconds between polls. Default: 15")
    i.add_argument("--token", help="SPTrans API token (falls back to $SPTRANS_TOKEN).")

    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    if args.command == "process":
        segments = process(
            args.input,
            args.output,
            max_speed=args.max_speed,
            min_time=args.min_time,
            max_gap_seconds=args.max_gap,
            vehicle_ids=args.vehicle_ids,
            route_ids=args.route_ids if not args.vehicle_ids else None,
        )
        print(f"Wrote {len(segments)} segments to {args.output}")
    elif args.command == "report":
        print_report(build_report(args.input, top_n_routes=args.top_n_routes))
    elif args.command == "regions":
        regions = discover_regions(
            args.input,
            args.output,
            eps_meters=args.eps_meters,
            min_samples=args.min_samples,
        )
        print(f"Wrote {len(regions)} recurrent regions to {args.output}")
    elif args.command == "ingest":
        token = args.token or os.environ.get("SPTRANS_TOKEN")
        if not token:
            raise SystemExit("SPTrans token required via --token or $SPTRANS_TOKEN.")
        df = ingest(
            token=token,
            route_codes=args.routes,
            output_path=args.output,
            duration_seconds=args.duration,
            interval_seconds=args.interval,
        )
        print(f"Wrote {len(df)} trajectory rows to {args.output}")


if __name__ == "__main__":
    main()
