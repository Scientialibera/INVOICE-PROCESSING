# Fabric Notebook: 01_ingest_landing
# Medallion Layer: Landing -> Bronze
# Reads raw invoice data from Cosmos DB Change Feed and lands it in the Landing lakehouse.

# %% Parameters
COSMOS_ENDPOINT = ""  # Set via notebook parameters or linked service
COSMOS_DATABASE = "spend"
COSMOS_CONTAINER = "invoices"
LANDING_LAKEHOUSE = "lh_spend_landing"

# %% Read from Cosmos DB
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

df_cosmos = (
    spark.read
    .format("cosmos.oltp")
    .option("spark.cosmos.accountEndpoint", COSMOS_ENDPOINT)
    .option("spark.cosmos.database", COSMOS_DATABASE)
    .option("spark.cosmos.container", COSMOS_CONTAINER)
    .option("spark.cosmos.read.inferSchema.enabled", "true")
    .option("spark.cosmos.accountKey", "")  # Use Managed Identity / linked service in production
    .load()
)

print(f"Read {df_cosmos.count()} records from Cosmos DB")
df_cosmos.printSchema()

# %% Write to Landing lakehouse as Delta
from modules.helpers import write_delta, add_audit_columns

df_landing = add_audit_columns(df_cosmos)
write_delta(df_landing, LANDING_LAKEHOUSE, "raw_invoices", mode="overwrite")

print("Landing ingestion complete")
