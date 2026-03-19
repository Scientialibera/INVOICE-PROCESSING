"""
Shared helpers for Fabric medallion pipeline notebooks.
"""
import os
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, BooleanType, ArrayType, IntegerType


INVOICE_SCHEMA = StructType([
    StructField("id", StringType(), False),
    StructField("user_id", StringType(), True),
    StructField("source", StringType(), True),
    StructField("blob_path", StringType(), True),
    StructField("status", StringType(), True),
    StructField("vendor_name", StringType(), True),
    StructField("vendor_address", StringType(), True),
    StructField("customer_name", StringType(), True),
    StructField("invoice_number", StringType(), True),
    StructField("invoice_date", StringType(), True),
    StructField("due_date", StringType(), True),
    StructField("purchase_order", StringType(), True),
    StructField("total_amount", DoubleType(), True),
    StructField("subtotal", DoubleType(), True),
    StructField("total_tax", DoubleType(), True),
    StructField("currency", StringType(), True),
    StructField("spend_category", StringType(), True),
    StructField("subcategory", StringType(), True),
    StructField("is_likely_duplicate", BooleanType(), True),
    StructField("anomaly_flags", ArrayType(StringType()), True),
    StructField("classification_confidence", DoubleType(), True),
    StructField("classification_reasoning", StringType(), True),
    StructField("page_count", IntegerType(), True),
    StructField("processed_at", StringType(), True),
    StructField("correlation_id", StringType(), True),
])


def _get_workspace_id() -> str:
    try:
        return spark.conf.get("trident.workspace.id")
    except Exception:
        pass
    return os.environ.get("WORKSPACE_ID", os.environ.get("fabric_workspace_id", ""))


def get_lakehouse_path(lakehouse_id: str, zone: str = "Tables") -> str:
    ws = _get_workspace_id()
    return f"abfss://{ws}@onelake.dfs.fabric.microsoft.com/{lakehouse_id}/{zone}"


def read_delta(spark: SparkSession, lakehouse_id: str, table: str) -> DataFrame:
    path = f"{get_lakehouse_path(lakehouse_id)}/{table}"
    return spark.read.format("delta").load(path)


def write_delta(df: DataFrame, lakehouse_id: str, table: str, mode: str = "overwrite") -> None:
    """Write as managed Delta table via saveAsTable for proper catalog registration."""
    try:
        if mode == "overwrite":
            spark.sql(f"DROP TABLE IF EXISTS `{table}`")
        df.write.format("delta").mode(mode).option("overwriteSchema", "true").saveAsTable(table)
    except Exception as e:
        print(f"  [warn] saveAsTable failed for '{table}', falling back to path write: {e}")
        path = f"{get_lakehouse_path(lakehouse_id)}/{table}"
        df.write.format("delta").mode(mode).option("overwriteSchema", "true").save(path)


def add_audit_columns(df: DataFrame) -> DataFrame:
    return (
        df
        .withColumn("_ingested_at", F.current_timestamp())
        .withColumn("_source_file", F.input_file_name())
    )
