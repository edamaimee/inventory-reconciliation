import pandas as pd
import sys
from pathlib import Path

# Add project root to Python path so tests can import reconcile.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from reconcile import (
    load_snapshot,
    reconcile_snapshots,
    normalize_sku
)


# -------------------------------------------------------------------
# SKU normalization
# -------------------------------------------------------------------

def test_normalize_sku_formats():
    assert normalize_sku("SKU001") == "SKU-001"
    assert normalize_sku("sku-008") == "SKU-008"
    assert normalize_sku("SKU-010") == "SKU-010"
    assert normalize_sku(" SKU005 ") == "SKU-005"


# -------------------------------------------------------------------
# Reconciliation logic
# -------------------------------------------------------------------

def test_quantity_change_detected():
    df_old = pd.DataFrame({
        "sku": ["SKU-001"],
        "sku_raw": ["SKU-001"],
        "quantity": [10],
        "location": ["A"],
        "name": ["Widget"]
    })

    df_new = pd.DataFrame({
        "sku": ["SKU-001"],
        "sku_raw": ["SKU-001"],
        "quantity": [15],
        "location": ["A"],
        "name": ["Widget"]
    })

    report = reconcile_snapshots(df_old, df_new)

    assert len(report["items_in_both"]) == 1
    assert report["items_in_both"][0]["quantity_changed"] is True


def test_no_quantity_change():
    df_old = pd.DataFrame({
        "sku": ["SKU-002"],
        "sku_raw": ["SKU-002"],
        "quantity": [20],
        "location": ["B"],
        "name": ["Gadget"]
    })

    df_new = pd.DataFrame({
        "sku": ["SKU-002"],
        "sku_raw": ["SKU-002"],
        "quantity": [20],
        "location": ["B"],
        "name": ["Gadget"]
    })

    report = reconcile_snapshots(df_old, df_new)

    assert report["items_in_both"][0]["quantity_changed"] is False


def test_removed_item_detected():
    df_old = pd.DataFrame({
        "sku": ["SKU-003"],
        "sku_raw": ["SKU-003"],
        "quantity": [5],
        "location": ["C"],
        "name": ["Cable"]
    })

    df_new = pd.DataFrame(
        columns=["sku", "sku_raw", "quantity", "location", "name"]
    )

    report = reconcile_snapshots(df_old, df_new)

    assert len(report["removed_items"]) == 1
    assert report["removed_items"][0]["sku"] == "SKU-003"


def test_new_item_detected():
    df_old = pd.DataFrame(
        columns=["sku", "sku_raw", "quantity", "location", "name"]
    )

    df_new = pd.DataFrame({
        "sku": ["SKU-004"],
        "sku_raw": ["SKU-004"],
        "quantity": [50],
        "location": ["D"],
        "name": ["Adapter"]
    })

    report = reconcile_snapshots(df_old, df_new)

    assert len(report["new_items"]) == 1
    assert report["new_items"][0]["sku"] == "SKU-004"


# -------------------------------------------------------------------
# Data quality issues
# -------------------------------------------------------------------

def test_sku_normalization_flagged():
    df_old = pd.DataFrame({
        "sku": ["SKU-005"],
        "sku_raw": ["SKU005"],
        "quantity": [10],
        "location": ["A"],
        "name": ["Mouse"]
    })

    df_new = pd.DataFrame({
        "sku": ["SKU-005"],
        "sku_raw": ["SKU005"],
        "quantity": [10],
        "location": ["A"],
        "name": ["Mouse"]
    })

    report = reconcile_snapshots(df_old, df_new)

    assert any(
        "SKU formatting" in issue
        for issue in report["data_quality_issues"]
    )


def test_missing_quantity_flagged():
    df_old = pd.DataFrame({
        "sku": ["SKU-006"],
        "sku_raw": ["SKU-006"],
        "quantity": [None],
        "location": ["A"],
        "name": ["Keyboard"]
    })

    df_new = pd.DataFrame({
        "sku": ["SKU-006"],
        "sku_raw": ["SKU-006"],
        "quantity": [5],
        "location": ["A"],
        "name": ["Keyboard"]
    })

    report = reconcile_snapshots(df_old, df_new)

    assert any(
        "quantity" in issue.lower()
        for issue in report["data_quality_issues"]
    )