# Azure Functions -- Processing Pipeline

Python Azure Functions on Flex Consumption plan. Handles invoice ingestion and processing via Event Grid and Service Bus triggers.

## Architecture

```mermaid
flowchart TB
  subgraph triggers [Function Triggers]
    intake["InvoiceIntake\nEvent Grid: BlobCreated"]
    process["InvoiceProcess\nService Bus: q-invoice-process"]
  end

  subgraph pipeline [Processing Pipeline]
    download["Download Blob"]
    extract["Extract\nDoc Intelligence\nprebuilt-invoice"]
    classify["Classify\nOpenAI Function Calling"]
    enrich["Enrich\nDuplicate Detection\nLine Item Normalization"]
    persist["Persist\nCosmos + AI Search"]
  end

  subgraph adapters [Adapters]
    docIntel["doc_intelligence_client.py"]
    openaiClient["openai_client.py"]
    cosmosClient["cosmos_client.py"]
    searchClient["search_client.py"]
    blobClient["blob_storage_client.py"]
  end

  intake -->|"parse event\nbuild InvoiceMessage\nenqueue"| process
  process --> download --> extract --> classify --> enrich --> persist
  extract --> docIntel
  classify --> openaiClient
  persist --> cosmosClient
  persist --> searchClient
  download --> blobClient
```

## Functions

| Function | Trigger | Purpose |
|----------|---------|---------|
| `InvoiceIntake` | Event Grid (`BlobCreated`) | Parse blob event, build `InvoiceMessage`, enqueue to Service Bus |
| `InvoiceProcess` | Service Bus (`q-invoice-process`) | Full extraction, classification, enrichment, and persistence pipeline |

## Pipeline Steps

1. **Download**: Fetch the uploaded file from blob storage
2. **Extract**: Send to Document Intelligence `prebuilt-invoice` to get structured fields (vendor, date, total, line items, currency)
3. **Classify**: Send extracted text to Azure OpenAI with `classify_invoice` function calling tool to get spend category, subcategory, anomaly flags
4. **Enrich**: Detect potential duplicates (same vendor + amount + date), normalize line items
5. **Persist**: Upsert to Cosmos DB `invoices` container, index content + embeddings to AI Search

## Configuration

Settings are loaded from environment variables (set by `deploy-infra.ps1`). Prompts and function definitions use blob-first loading with local file fallback.
