# Fabric Notebook: 02_transform_bronze
# Medallion Layer: Landing -> Bronze
# Cleans and standardizes raw invoice data.

# %% Parameters
LANDING_LAKEHOUSE = "lh_spend_landing"
BRONZE_LAKEHOUSE = "lh_spend_bronze"

# %% Read from Landing
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from modules.helpers import read_delta, write_delta

spark = SparkSession.builder.getOrCreate()

df_raw = read_delta(spark, LANDING_LAKEHOUSE, "raw_invoices")
print(f"Read {df_raw.count()} raw records from landing")

# %% Cleanse and standardize
df_bronze = (
    df_raw
    .filter(F.col("status") == "processed")
    .withColumn("invoice_date_parsed", F.to_date("invoice_date", "yyyy-MM-dd"))
    .withColumn("due_date_parsed", F.to_date("due_date", "yyyy-MM-dd"))
    .withColumn("processed_at_ts", F.to_timestamp("processed_at"))
    .withColumn("total_amount", F.col("total_amount").cast("double"))
    .withColumn("subtotal", F.col("subtotal").cast("double"))
    .withColumn("total_tax", F.col("total_tax").cast("double"))
    .withColumn("vendor_name_clean", F.upper(F.trim(F.col("vendor_name"))))
    .withColumn("currency", F.upper(F.coalesce(F.col("currency"), F.lit("USD"))))
    .dropDuplicates(["id"])
)

print(f"Bronze records after cleansing: {df_bronze.count()}")

# %% Write to Bronze
write_delta(df_bronze, BRONZE_LAKEHOUSE, "invoices_bronze", mode="overwrite")
print("Bronze transformation complete")
