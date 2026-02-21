"""
Inventory Reconciliation Script

This script compares two inventory snapshots taken at different points in time
and produces a structured reconciliation report.

It identifies:
- Items present in both snapshots and whether their quantities changed
- Items removed since the previous snapshot
- Items newly added in the latest snapshot
- Common data quality issues that could affect reporting accuracy
"""

from pathlib import Path
import pandas as pd

# -------------------------------------------------------------------
# File system configuration
# -------------------------------------------------------------------

DATA_DIR = Path("data")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# -------------------------------------------------------------------
# Data loading & normalization
# -------------------------------------------------------------------

"""
Data loading and normalization for inventory reconciliation.

This module standardizes inventory snapshot data so that
records from different systems can be reliably compared.
"""

# ---------------------------------------------------------
# Standardize SKU
# ---------------------------------------------------------

def normalize_sku(raw_sku: str) -> str:
    """
    Normalize SKU formatting without changing identity.

    Examples:
    SKU005   -> SKU-005
    sku-008  -> SKU-008
    SKU-001  -> SKU-001
    """

    if pd.isna(raw_sku):
        return raw_sku

    sku = str(raw_sku).strip().upper()

    # Standardize SKU### -> SKU-###
    if sku.startswith("SKU") and not sku.startswith("SKU-"):
        suffix = sku.replace("SKU", "")
        if suffix.isdigit():
            sku = f"SKU-{suffix.zfill(3)}"

    return sku


def load_snapshot(path: Path) -> pd.DataFrame:
    """
    Load an inventory snapshot CSV and normalize schema differences.

    Returns a cleaned DataFrame with a consistent schema.
    """

    df = pd.read_csv(path)

    # Normalize column names
    df.columns = [col.strip().lower() for col in df.columns]

    # Validate SKU
    if "sku" not in df.columns:
        raise ValueError(f"Missing required 'sku' column in {path.name}")

    # Preserve raw SKU for auditing
    df["sku_raw"] = df["sku"]

    # Normalize SKU format
    df["sku"] = df["sku"].apply(normalize_sku)

    # Normalize quantity column
    if "quantity" in df.columns:
        pass
    elif "qty" in df.columns:
        df = df.rename(columns={"qty": "quantity"})
    else:
        raise ValueError(f"No quantity column found in {path.name}")

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")

    # Normalize location / warehouse
    if "warehouse" in df.columns and "location" not in df.columns:
        df = df.rename(columns={"warehouse": "location"})

    if "location" not in df.columns:
        df["location"] = pd.NA

    # Normalize product name
    if "product_name" in df.columns and "name" not in df.columns:
        df = df.rename(columns={"product_name": "name"})

    if "name" not in df.columns:
        df["name"] = pd.NA

    # Final column order
    df = df[["sku", "sku_raw", "quantity", "location", "name"]]

    return df


# -------------------------------------------------------------------
# Reconciliation logic
# -------------------------------------------------------------------

def reconcile_snapshots(df_old: pd.DataFrame, df_new: pd.DataFrame) -> dict:
    """
    Reconcile two inventory snapshots per the problem specification.
    """

    report = {
        "items_in_both": [],
        "removed_items": [],
        "new_items": [],
        "data_quality_issues": []
    }

    merged = df_old.merge(
        df_new,
        on="sku",
        how="outer",
        suffixes=("_old", "_new"),
        indicator=True
    )

    # Items present in both snapshots
    both = merged[merged["_merge"] == "both"]
    for _, row in both.iterrows():
        report["items_in_both"].append({
            "sku": row["sku"],
            "old_quantity": row["quantity_old"],
            "new_quantity": row["quantity_new"],
            "quantity_changed": row["quantity_old"] != row["quantity_new"]
        })

    # Items removed (only in snapshot 1)
    removed = merged[merged["_merge"] == "left_only"]
    for _, row in removed.iterrows():
        report["removed_items"].append({
            "sku": row["sku"],
            "last_known_quantity": row["quantity_old"]
        })

    # Items newly added (only in snapshot 2)
    added = merged[merged["_merge"] == "right_only"]
    for _, row in added.iterrows():
        report["new_items"].append({
            "sku": row["sku"],
            "quantity": row["quantity_new"]
        })

    # ----------------------------------------------------------------
    # Data quality issues
    # ----------------------------------------------------------------

    # SKU formatting inconsistencies
    if (df_old["sku"] != df_old["sku_raw"]).any() or (df_new["sku"] != df_new["sku_raw"]).any():
        report["data_quality_issues"].append(
            "Inconsistent SKU formatting detected and normalized"
        )

    # Missing or invalid quantities
    if merged.filter(like="quantity").isna().any().any():
        report["data_quality_issues"].append(
            "Missing or non-numeric quantity values detected"
        )

    # Duplicate SKUs
    if df_old["sku"].duplicated().any():
        report["data_quality_issues"].append(
            "Duplicate SKUs detected in snapshot_1"
        )

    if df_new["sku"].duplicated().any():
        report["data_quality_issues"].append(
            "Duplicate SKUs detected in snapshot_2"
        )

    # Negative quantities
    if (df_old["quantity"] < 0).any() or (df_new["quantity"] < 0).any():
        report["data_quality_issues"].append(
            "Negative quantity values detected"
        )

    return report


# -------------------------------------------------------------------
# Reporting helpers
# -------------------------------------------------------------------

def report_to_tables(report: dict) -> dict[str, pd.DataFrame]:
    """
    Convert report sections into DataFrames for easy viewing.
    """

    return {
        "items_in_both": pd.DataFrame(report["items_in_both"]),
        "removed_items": pd.DataFrame(report["removed_items"]),
        "new_items": pd.DataFrame(report["new_items"]),
        "data_quality_issues": pd.DataFrame(
            {"issue": report["data_quality_issues"]}
        )
    }


# -------------------------------------------------------------------
# Script entry point
# -------------------------------------------------------------------

def main():
    # Load and clean data
    snapshot_1 = load_snapshot(DATA_DIR / "snapshot_1.csv")
    snapshot_2 = load_snapshot(DATA_DIR / "snapshot_2.csv")

    # Reconcile
    report = reconcile_snapshots(snapshot_1, snapshot_2)

    # Write JSON output
    output_path = OUTPUT_DIR / "reconciliation_report.json"
    pd.Series(report).to_json(output_path, indent=2)

    print(f"\nJSON report written to {output_path}\n")

    # Print tables for human readability
    tables = report_to_tables(report)
    for name, df in tables.items():
        print(f"===== {name.upper()} =====")
        if df.empty:
            print("(no rows)")
        else:
            print(df.to_string(index=False))
        print()


if __name__ == "__main__":
    main()