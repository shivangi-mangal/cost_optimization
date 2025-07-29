# cost_optimization
Hybrid “Fast‑Archive” Architecture

API read/write     
   ↓
[ Cosmos DB container: “hot+warm data” (<= 3 months) ]
   ↓───────────────┬──────────────┐
                   │              │
      New writes always go          │
      → hot segment                 │
                   │              │
    1. Archive job: move >3m data   │
       • Extract old items using change feed
       • Store items in Azure Blob Storage (Cool tier, optionally Archive) as blobs/compressed JSON
       • Keep a stub/metadata document in Cosmos DB linking to blob location (or delete entire item)
    2. On read of stub: fetch blob from storage (Cool = sub‑second; Archive needs rehydration)
                   │              │
                   └─────────────>│
                                  │
[ Blob Storage container: “archival store” ]

Writes: unchanged — still go to Cosmos.

Reads:

1. If record in Cosmos (<= 3 m old): regular fast Cosmos query.

2. If record moved (stub exists): fetch blob via Storage SDK, decompress, return—milliseconds (cool tier).

3. No API client change → all logic in service layer/code.

Cost Optimization Elements
1. Thin hot dataset + small Cosmos container(s)
Only recent 3‑month data stored, drastically smaller. Minimal RU cost, low storage overhead.

2. Archive old data to Azure Blob Storage (Cool or Archive)
Cool tier: milliseconds reads, low storage cost (~$0.01/GB) with modest transaction costs.
Archive tier: ultra‑cheap (~$0.002/GB) but read latency up to 15 hours—not ideal for your “seconds” SLA. So choose Cool tier unless access nearly zero. 

3. Use TTL or delete in Cosmos
After blob archiving, you can delete the full record in Cosmos or mark it with TTL. TTL auto‑removes after a safe buffer, ensuring ∼no dual‑writes or downtime. 

4. Tune indexing policy
Large records (~300 KB) bloat index size/RUs; exclude unqueried large fields (maybe the detailed payload) from indexing to reduce storage and RU cost.

 Implementation Plan
A. Backfill Archive Job (scheduled, e.g. Azure Function or Data Factory pipeline)
archive_job.py

B. Read Logic in API service:
api_layer.py 

C. TTL Cleanup Configuration:
Set TTL on container so stub removed automatically after buffer.

D. Indexing policy adjustment.

🛠 No Downtime, No API Changes
1. API endpoints remain unchanged; internal routing handles archive vs live.
2. Migration runs in background; initial data pull then incremental (via change feed).
3. Cosmos always available; storage reads via Blob SDK are fast.

📦 Additional Optimizations
1. Autoscale or provisioned throughput: if serverless RU limits constrain, migrate to provisioned throughput with dynamic scaling via Azure SDK (no code change) to support growth. 
2. Compression: we gzip blobs to minimize blob storage cost.
3. Batch processing: incremental archive via Cosmos Change Feed instead of full scan.

📅 Cost Projections (Illustrative):
1. Cosmos: store only ~600 GB × 3 m = ~150 GB hot data → ~US $0.25/GB → ~$37.5/month storage, plus much smaller RU cost for index & reads.
2. Blob Cool tier: ~450 GB in Cool → ~$4.5/month, plus low read cost.
3. Overall savings: > 90 % on storage cost, plus RU cost reduction.

🏗 Full Architecture Diagram (ASCII)
pgsql
Copy
Edit
Client API
    |
[Billing Service Layer]
    ├─ Query Cosmos → if stub → fetch blob from Azure Blob Storage
    ├─ Write Cosmos normally
    └─ Archive Function job (on schedule / change‑feed):
           → migrate old items to blob → stub → delete original → TTL cleans stubs
