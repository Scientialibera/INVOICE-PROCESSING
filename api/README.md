# API Backend

FastAPI application deployed to Azure App Service. Serves the React SPA as static files and exposes REST + SSE endpoints for the frontend.

## Architecture

```mermaid
flowchart TB
  subgraph routes [Routes]
    chat["POST /api/chat\nSSE streaming"]
    upload["POST /api/upload\nmultipart files"]
    invoices["GET /api/invoices\nlist + detail"]
    dashboard["GET /api/dashboard/*\naggregated data"]
    history["GET /api/chat/history"]
    reset["POST /api/chat/reset"]
  end

  subgraph auth [Auth Layer]
    tokenVal["token_validator.py\nAzure AD JWT"]
    deps["dependencies.py\nFastAPI Depends"]
  end

  subgraph services [Services]
    agentFactory["agent_factory.py\nbuild_agent()"]
    sessionStore["session_store.py\nCosmos user_sessions"]
    blobGW["blob_gateway.py\nprompt loading"]
  end

  subgraph tools [Tools -- Auto-Discovered]
    invoiceTools["invoice_tools.py"]
    analyticsTools["analytics_tools.py"]
    storageTools["storage_tools.py"]
  end

  subgraph adapters [Adapters]
    cosmosAd["cosmos_adapter.py"]
    searchAd["search_adapter.py"]
    blobAd["blob_adapter.py"]
  end

  routes --> auth
  chat --> agentFactory
  agentFactory --> tools
  tools --> adapters
  agentFactory --> sessionStore
  sessionStore --> cosmosAd
