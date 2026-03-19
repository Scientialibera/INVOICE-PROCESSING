# Fabric Notebook: 04_aggregate_gold
# Medallion Layer: Silver -> Gold
# Creates business-ready aggregation tables for reporting.

# %% Parameters
SILVER_LAKEHOUSE = "lh_spend_silver"
GOLD_LAKEHOUSE = "lh_spend_gold"

# %% Read from Silver
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from modules.helpers import read_delta, write_delta

spark = SparkSession.builder.getOrCreate()

df_silver = read_delta(spark, SILVER_LAKEHOUSE, "invoices_silver")
print(f"Read {df_silver.count()} silver records")

# %% 1. Spend by Category (monthly)
df_spend_category = (
    df_silver
    .groupBy("fiscal_year", "fiscal_quarter", "fiscal_month", "spend_category")
    .agg(
        F.count("id").alias("invoice_count"),
        F.sum("total_amount").alias("total_spend"),
        F.avg("total_amount").alias("avg_invoice_amount"),
        F.min("total_amount").alias("min_invoice_amount"),
        F.max("total_amount").alias("max_invoice_amount"),
        F.sum(F.when(F.col("is_likely_duplicate"), 1).otherwise(0)).alias("duplicate_count"),
        F.sum(F.col("anomaly_count")).alias("total_anomaly_flags"),
    )
    .orderBy("fiscal_year", "fiscal_month", "spend_category")
)

write_delta(df_spend_category, GOLD_LAKEHOUSE, "spend_by_category", mode="overwrite")
print(f"  spend_by_category: {df_spend_category.count()} rows")

# %% 2. Vendor Analysis
df_vendor_analysis = (
    df_silver
    .groupBy("vendor_name_clean", "spend_category")
    .agg(
        F.count("id").alias("invoice_count"),
        F.sum("total_amount").alias("total_spend"),
        F.avg("total_amount").alias("avg_invoice_amount"),
        F.min("invoice_date_parsed").alias("first_invoice_date"),
        F.max("invoice_date_parsed").alias("last_invoice_date"),
        F.avg("days_to_due").alias("avg_days_to_due"),
        F.sum(F.when(F.col("is_likely_duplicate"), 1).otherwise(0)).alias("duplicate_count"),
    )
    .orderBy(F.desc("total_spend"))
)

write_delta(df_vendor_analysis, GOLD_LAKEHOUSE, "vendor_analysis", mode="overwrite")
print(f"  vendor_analysis: {df_vendor_analysis.count()} rows")

# %% 3. Monthly Trend
df_monthly_trend = (
    df_silver
    .groupBy("fiscal_year", "fiscal_month")
    .agg(
        F.count("id").alias("invoice_count"),
        F.sum("total_amount").alias("total_spend"),
        F.countDistinct("vendor_name_clean").alias("unique_vendors"),
        F.sum(F.col("anomaly_count")).alias("total_anomalies"),
    )
    .orderBy("fiscal_year", "fiscal_month")
)

write_delta(df_monthly_trend, GOLD_LAKEHOUSE, "monthly_trend", mode="overwrite")
print(f"  monthly_trend: {df_monthly_trend.count()} rows")

# %% 4. Anomaly Summary
df_anomaly_summary = (
    df_silver
    .filter(F.col("anomaly_count") > 0)
    .select(
        "id", "vendor_name_clean", "total_amount", "spend_category",
        "invoice_date_parsed", "anomaly_flags", "anomaly_count",
        "is_likely_duplicate", "is_high_value",
    )
    .orderBy(F.desc("total_amount"))
)

write_delta(df_anomaly_summary, GOLD_LAKEHOUSE, "anomaly_summary", mode="overwrite")
print(f"  anomaly_summary: {df_anomaly_summary.count()} rows")

print("\nGold aggregation complete -- all tables ready for reporting")
