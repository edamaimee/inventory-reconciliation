# inventory-reconciliation
You're working with inventory data from a warehouse management system. Two snapshots were taken a week apart, and you need to reconcile them to understand what changed.

# How I approached the problem

I started by cleaning and standardizing the inventory data before doing any comparisons. In real systems, snapshots often come from different sources or change over time, so I focused first on making sure the two files could be compared reliably.

After normalization, I reconciled the snapshots using SKU as the unique identifier. I used a full outer join to group items into three categories: items present in both snapshots, items that were removed, and items that were newly added. For items present in both snapshots, I compared quantities to see whether inventory levels changed.

The final results are written to json files so they’re easy to review and work with.

# Key decisions and assumptions

SKUs uniquely identify inventory items.

Quantity changes are the main signal of change, based on the problem description.

Data should be normalized and validated before reconciliation.

Tests should focus on business logic rather than file reading or pandas behavior.

# Data quality issues found

While working with the data, I handled and flagged several common issues:

Inconsistent SKU formatting (e.g. SKU005 vs SKU-005)

Missing or non-numeric quantity values

Duplicate SKUs within a snapshot

Slight schema differences between snapshots (e.g. qty vs quantity)

These issues were normalized where possible and flagged so they’re visible rather than hidden.

# Testing

I added unit tests that use small in-memory datasets to verify that the reconciliation logic correctly identifies quantity changes, added items, removed items, and data quality issues.
