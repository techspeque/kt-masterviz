"""Unit tests for the master-CSV loader."""

from __future__ import annotations

import pandas as pd
import pytest

from kt_masterviz.loader import (
    detect_hyperparameter_columns,
    detect_metric_columns,
    load_master_csv,
)


class TestLoadMasterCsv:
    def test_reads_complete_csv(self, sample_csv):
        df = load_master_csv(sample_csv)
        assert len(df) == 6
        assert df["trial_id"].nunique() == 2
        assert list(df.columns) == [
            "trial_id",
            "epoch",
            "lr",
            "units",
            "dataset",
            "loss",
            "val_loss",
            "accuracy",
            "val_accuracy",
        ]

    def test_tolerates_partial_last_line(self, csv_with_partial_last_line):
        """Reader must not crash if writer is mid-row.

        pandas pads missing trailing fields with NaN — which is the
        right behavior for a live dashboard. The partial row's identity
        columns (trial_id, epoch) are preserved, so the trial shows up
        immediately; only the metric column is NaN until the row finishes
        being written. Charts handle NaN as gaps; idxmin/idxmax ignore it.
        """
        df = load_master_csv(csv_with_partial_last_line)
        assert len(df) == 3
        # The complete rows are intact.
        assert df.iloc[0]["loss"] == 0.82
        assert df.iloc[1]["loss"] == 0.65
        # The partial row preserves identity but has NaN for missing fields.
        assert df.iloc[-1]["trial_id"] == 2
        assert df.iloc[-1]["epoch"] == 1
        assert pd.isna(df.iloc[-1]["loss"])

    def test_empty_csv_returns_empty_dataframe(self, empty_csv):
        df = load_master_csv(empty_csv)
        assert df.empty
        assert list(df.columns) == [
            "trial_id",
            "epoch",
            "lr",
            "units",
            "loss",
            "val_loss",
        ]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_master_csv(tmp_path / "does_not_exist.csv")


class TestColumnDetection:
    def test_detect_hyperparameter_columns(self, sample_csv):
        df = load_master_csv(sample_csv)
        hp_cols = detect_hyperparameter_columns(df)
        # lr, units are real hps; dataset is an extra_field but passes the
        # filter (no metric substrings), which is intentional — extra_fields
        # are useful for grouping in the dashboard.
        assert set(hp_cols) == {"lr", "units", "dataset"}

    def test_detect_metric_columns(self, sample_csv):
        df = load_master_csv(sample_csv)
        metric_cols = detect_metric_columns(df)
        assert set(metric_cols) == {"loss", "val_loss", "accuracy", "val_accuracy"}

    def test_reserved_columns_never_in_either_list(self, sample_csv):
        df = load_master_csv(sample_csv)
        hp = detect_hyperparameter_columns(df)
        metric = detect_metric_columns(df)
        assert "trial_id" not in hp and "trial_id" not in metric
        assert "epoch" not in hp and "epoch" not in metric

    def test_hp_and_metric_sets_are_disjoint(self, sample_csv):
        df = load_master_csv(sample_csv)
        hp = set(detect_hyperparameter_columns(df))
        metric = set(detect_metric_columns(df))
        assert hp.isdisjoint(metric)
