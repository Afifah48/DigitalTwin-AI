from pathlib import Path

import pandas as pd

from backend.app.models.anomaly.service import AnomalyService
from backend.bottleneck.pipeline import (
    BottleneckPipeline,
    Phase4ServiceAdapter,
)
from backend.models.enums import StationId


ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data" / "station_telemetry.parquet"
ARTIFACTS = ROOT / "backend" / "models" / "anomaly"
OUTPUT = ROOT / "data" / "phase4_phase5_integration.parquet"


def main():
    print("=" * 70)
    print("PHASE 4 -> PHASE 5 REAL DATA INTEGRATION")
    print("=" * 70)

    # ---------------------------------------------------------
    # Load real telemetry
    # ---------------------------------------------------------
    df = pd.read_parquet(DATA)

    print(f"Dataset rows: {len(df):,}")
    print(f"Dataset columns: {len(df.columns)}")
    print(f"Stations: {sorted(df['station_id'].unique())}")

    df = df.sort_values(
        ["episode_id", "timestamp", "station_id"]
    )

    # ---------------------------------------------------------
    # Load Phase 4 saved model/artifacts
    # ---------------------------------------------------------
    phase4 = AnomalyService()

    phase4.load_artifacts(
        str(ARTIFACTS),
        preferred_model="lstm",
    )

    print("\nPhase 4 loaded")
    print(f"Model: {phase4.model.model_name}")
    print(f"Version: {phase4.model.version}")
    print(f"Window size: {phase4.window_size}")
    print(f"Threshold: {phase4.model.threshold}")
    print(f"Scaler fitted: {phase4.scaler.is_fitted}")

    # ---------------------------------------------------------
    # Phase 4 -> Phase 5 adapter
    # ---------------------------------------------------------
    adapter = Phase4ServiceAdapter(phase4)

    pipeline = BottleneckPipeline(
        anomaly_provider=adapter
    )

    results = []

    # Process one episode at a time.
    # This prevents temporal state from leaking between runs.
    for episode_id, episode in df.groupby(
        "episode_id",
        sort=True
    ):

        print(f"\nProcessing {episode_id} ...")

        for timestamp, snapshot in episode.groupby(
            "timestamp",
            sort=True
        ):

            station_telemetries = {}

            for _, row in snapshot.iterrows():

                station_id = StationId(
                    str(row["station_id"])
                )

                telemetry = row.to_dict()

                telemetry.pop("episode_id", None)
                telemetry.pop("station_id", None)
                telemetry.pop("timestamp", None)

                station_telemetries[station_id] = telemetry

            if not station_telemetries:
                continue

            # -------------------------------------------------
            # Phase 5 factory inference
            # -------------------------------------------------
            analysis = pipeline.analyze_snapshot(
                timestamp=float(timestamp),
                station_telemetries=station_telemetries,
                buffer_occupancies={},
            )

            # -------------------------------------------------
            # Save station-level outputs
            # -------------------------------------------------
            for station in analysis.station_ranking:

                results.append(
                    {
                        "episode_id": episode_id,
                        "timestamp": float(timestamp),
                        "station_id": station.station_id.value,

                        # Phase 5
                        "risk_score": float(
                            station.risk_score
                        ),
                        "prediction": (
                            station.prediction.value
                        ),
                        "confidence": float(
                            station.confidence
                        ),
                        "persistence_score": float(
                            station.persistence_score
                        ),

                        # Phase 4
                        "anomaly_score": float(
                            station.anomaly_score
                        ),
                        "anomaly_probability": (
                            station.anomaly_probability
                        ),
                        "anomaly_detected": bool(
                            station.anomaly_detected
                        ),

                        # Spatial propagation
                        "upstream_blocking_risk": float(
                            station.upstream_blocking_risk
                        ),
                        "downstream_starvation_risk": float(
                            station.downstream_starvation_risk
                        ),
                        "propagation_score": float(
                            station.propagation_score
                        ),
                        "affected_stations": [
                            s.value
                            for s in station.affected_stations
                        ],
                    }
                )

    # ---------------------------------------------------------
    # Save integration output
    # ---------------------------------------------------------
    output_df = pd.DataFrame(results)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output_df.to_parquet(
        OUTPUT,
        index=False
    )

    print("\n" + "=" * 70)
    print("INTEGRATION COMPLETE")
    print("=" * 70)

    print(f"Output rows: {len(output_df):,}")
    print(f"Output: {OUTPUT}")

    if not output_df.empty:

        print("\nStation counts:")
        print(
            output_df["station_id"]
            .value_counts()
            .sort_index()
        )

        print("\nRisk summary:")
        print(
            output_df
            .groupby("station_id")["risk_score"]
            .agg(["min", "mean", "max"])
            .round(4)
        )

        print("\nAnomaly detections:")
        print(
            output_df
            .groupby("station_id")["anomaly_detected"]
            .sum()
        )

        print("\nHighest-risk observations:")
        print(
            output_df
            .sort_values(
                "risk_score",
                ascending=False
            )
            .head(10)
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()