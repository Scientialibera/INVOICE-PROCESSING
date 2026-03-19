# Fabric Notebook: 03_enrich_silver
# Medallion Layer: Bronze -> Silver
# Enriches data with fiscal periods, vendor normalization, and anomaly scoring.

# %% Parameters
BRONZE_LAKEHOUSE = "lh_spend_bronze"
SILVER_LAKEHOUSE = "lh_spend_silver"

# %% Read from Bronze
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from modules.helpers import read_delta, write_delta

spark = SparkSession.builder.getOrCreate()

df_bronze = read_delta(spark, BRONZE_LAKEHOUSE, "invoices_bronze")
print(f"Read {df_bronze.count()} bronze records")

# %% Add fiscal periods
df_fiscal = (
    df_bronze
    .withColumn("fiscal_year", F.year("invoice_date_parsed"))
    .withColumn("fiscal_quarter", F.quarter("invoice_date_parsed"))
    .withColumn("fiscal_month", F.month("invoice_date_parsed"))
    .withColumn("fiscal_period",
        F.concat(
            F.col("fiscal_year").cast("string"),
            F.lit("-Q"),
            F.col("fiscal_quarter").cast("string"),
        )
    )
)

# %% Vendor normalization (group similar names)
vendor_window = Window.partitionBy("vendor_name_clean")

df_vendor = (
    df_fiscal
    .withColumn("vendor_invoice_count", F.count("id").over(vendor_window))
    .withColumn("vendor_total_spend", F.sum("total_amount").over(vendor_window))
    .withColumn("vendor_avg_amount", F.avg("total_amount").over(vendor_window))
)

# %% Anomaly scoring
df_silver = (
    df_vendor
    .withColumn("anomaly_count", F.size(F.coalesce(F.col("anomaly_flags"), F.array())))
    .withColumn("is_high_value",
        F.when(F.col("total_amount") > F.col("vendor_avg_amount") * 3, True)
        .otherwise(False)
    )
    .withColumn("days_to_due",
        F.datediff("due_date_parsed", "invoice_date_parsed")
    )
)

print(f"Silver records after enrichment: {df_silver.count()}")

# %% Write to Silver
write_delta(df_silver, SILVER_LAKEHOUSE, "invoices_silver", mode="overwrite")
print("Silver enrichment complete")
