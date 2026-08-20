# Task 5 — Scaling Architecture Blueprint (5,000 Concurrent Gig Workers)

## Executive Summary
This document analyzes the catastrophic failure modes of a monolithic synchronous backend when subjected to a sudden surge of **5,000 gig workers submitting audio recordings simultaneously on the same day**. It presents a cloud-native, event-driven architecture designed to handle peak bursts with zero data loss, sub-100ms API response times, and complete AWS cost optimization (~$97.90/month).

---

## 1. What Breaks First? (Failure Mode Analysis)

```text
  [5,000 Gig Workers] ───(Simultaneous Audio Uploads)───► [Monolithic Single-Server Bottleneck]
                                                                     │
                                                                     ▼
                                     💥 1. Network Ingress Saturation (2.5 Gbps Burst)
                                     💥 2. Synchronous Audio CPU Locks Web Worker Threads
                                     💥 3. Local Disk IOPS Exhaustion & File Write Locks
                                     💥 4. MySQL Connection Pool Exhaustion (Max 150 Connections)
                                     💥 5. Cascading 504 Gateway Timeouts & System Outage
```

### Mathematical Breakdown of Failure Points:

1. **Synchronous Audio Signal Processing Locks CPU Threads (The Primary Killer)**:
   - Converting WebM audio blobs, reading raw PCM byte buffers, computing RMS dBFS loudness, and running FFT spectral analysis for SNR estimation consumes **~100–300ms of intensive CPU computation per file**.
   - 5,000 concurrent submissions require **500 CPU-seconds of continuous compute**. On a standard 4-core application server, worker thread pools (Uvicorn/Gunicorn) immediately stall, leading to request queue overflows and **504 Gateway Timeouts**.

2. **Network Bandwidth & RAM Exhaustion**:
   - 5,000 concurrent audio uploads of ~5 MB each represent **25 GB of inbound raw data** arriving within a 60-second window (~**2.5 Gbps ingress burst**).
   - Buffering multipart stream buffers in backend RAM triggers immediate OS Out-Of-Memory (OOM) kernel kills.

3. **Storage IOPS Contention**:
   - Writing 5,000 files concurrently to a single local filesystem saturates disk IOPS, causing disk write locks and cascading thread freezes.

4. **Database Connection Pool Collapses**:
   - Standard MySQL configurations allow **150 max connections**. 5,000 worker API processes attempting direct SQL inserts cause `Too many connections` exceptions and transaction failures.

---

## 2. Cloud-Native Scaled Architecture

```text
┌────────────────┐        1. Request Presigned Upload URL        ┌────────────────────────┐
│  Gig Worker    ├──────────────────────────────────────────────►│  FastAPI / API Gateway │
│ (Browser/App)  │◄──────────────────────────────────────────────┤  (Stateless Container) │
└───────┬────────┘        2. Returns Presigned S3 PUT URL        └────────────────────────┘
        │
        │ 3. Direct Audio Binary Upload (Zero CPU on App Server)
        ▼
┌────────────────────────┐
│    Amazon S3 Bucket    │
│  (Direct Audio Store)  │
└───────┬────────────────┘
        │
        │ 4. S3 ObjectCreated Event Notification
        ▼
┌────────────────────────┐
│    Amazon SQS Queue    │ ◄─── Buffers bursts of 10,000+ incoming audio files
└───────┬────────────────┘
        │
        │ 5. Auto-Scaling Ingestion (Scale on Queue Depth Metric)
        ▼
┌────────────────────────────────────────────────────────┐
│      Audio Signal Processing Fleet (AWS Lambda / ECS)  │
│  • Downloads audio chunk from S3                       │
│  • Computes Duration, Sample Rate, Bitrate, RMS dBFS   │
│  • Computes SNR (Signal-to-Noise Ratio) & Quality Score│
└───────────────────────┬────────────────────────────────┘
                        │
                        │ 6. Multiplexed Bulk SQL Connection
                        ▼
        ┌───────────────────────────────┐
        │   AWS RDS Proxy (Pooler)      │
        └───────────────┬───────────────┘
                        │
                        ▼
        ┌───────────────────────────────┐
        │   Amazon Aurora MySQL Server  │
        └───────────────────────────────┘
```

### Core Architectural Upgrades:

1. **Direct-to-S3 Pre-signed Uploads**:
   - The Angular 19 client requests a short-lived, pre-signed AWS S3 PUT URL from FastAPI (`POST /api/audio/presigned-url`).
   - The client streams audio directly to S3 via HTTPS.
   - **Benefit**: Zero audio payload bytes touch application server CPU or memory.

2. **Decoupled Asynchronous Queueing (Amazon SQS FIFO)**:
   - S3 emits an `ObjectCreated` event to **Amazon SQS**.
   - The API returns `202 Accepted` to the gig worker in **< 80 ms**.

3. **Auto-Scaling Audio Extraction Fleet (AWS Lambda / ECS Fargate)**:
   - Worker functions automatically scale horizontally based on the SQS metric `ApproximateNumberOfMessagesVisible`.
   - Each Lambda worker processes an audio file in isolated micro-containers, computing duration, sample rate, bitrate, RMS dBFS loudness, and SNR quality scores.

4. **Database Connection Pooling via AWS RDS Proxy**:
   - Multiplexes thousands of serverless execution instances into a stable pool of 20-30 connections against **Amazon Aurora MySQL**.

5. **Sub-Millisecond Edge Delivery (CloudFront CDN + S3)**:
   - The Angular 19 SPA frontend is distributed globally via AWS CloudFront CDN with edge asset caching.

---

## 3. Detailed Monthly Cloud Cost Model (AWS)

Assuming **5,000 active gig workers** submitting **2 audio recordings per week** (~**40,000 submissions / month**, ~200 GB raw audio data):

| Cloud Component | AWS Service & Allocation | Operational Metric | Estimated Monthly Cost (USD) |
|---|---|---|---|
| **Audio Object Storage** | Amazon S3 Standard | 200 GB storage + lifecycle policy moving to Glacier after 30 days | **$4.60 / mo** |
| **Ingress & API Requests** | Amazon S3 Data Transfer | Ingress is FREE; 80,000 S3 GET/PUT API requests | **$0.45 / mo** |
| **Audio DSP Processing** | AWS Lambda (Auto-Scaling) | 40,000 invocations @ 1024 MB RAM (~2.0s compute per file) | **$1.35 / mo** |
| **Buffer Queue** | Amazon SQS | 80,000 queue operations (Covered by AWS 1M Free Tier) | **$0.00 / mo** |
| **Relational Database** | Amazon RDS MySQL (`db.t4g.medium`) | 2 vCPU, 4 GB RAM, Multi-AZ deployment + 100 GB SSD | **$52.00 / mo** |
| **Database Pooler** | Amazon RDS Proxy | Manages connection scaling across serverless worker fleet | **$15.00 / mo** |
| **API Gateway / Containers** | AWS ECS Fargate / App Runner | 2 Stateless Tasks (0.5 vCPU, 1 GB RAM) | **$18.00 / mo** |
| **Frontend CDN Hosting** | AWS CloudFront CDN | 50 GB Edge Data Transfer + Custom Domain SSL | **$3.50 / mo** |
| **Monitoring & Telemetry** | Amazon CloudWatch | Error logging, metrics retention, and automated alarms | **$3.00 / mo** |
| **ESTIMATED TOTAL** | | | **~$97.90 / month** |

---

## 4. Comprehensive Trade-offs Matrix

| Architectural Dimension | Chosen Approach | Alternative Considered | Engineering Trade-off & Rationale |
|---|---|---|---|
| **Processing Pattern** | Asynchronous SQS + Worker Fleet | Synchronous HTTP Ingestion | **Trade-off**: Workers receive immediate `202 Accepted` response while extracted metrics update asynchronously via RxJS polling / WebSockets.<br>**Benefit**: Guarantees zero request timeouts or dropped recordings under 5,000 worker bursts. |
| **Compute Model** | AWS Lambda / ECS Fargate | Persistent EC2 Instance Fleet | **Trade-off**: Brief ~500ms cold start latency during unexpected traffic spikes.<br>**Benefit**: Scales instantly from 0 to 1,000 concurrent audio processors with zero idle cost. |
| **Audio Compression** | Enforce Opus/WebM in Browser | Uncompressed PCM WAV Uploads | **Trade-off**: Requires HTML5 MediaRecorder browser API.<br>**Benefit**: Reduces file size from ~5 MB (WAV) to ~350 KB (WebM), slashing mobile bandwidth usage by **93%**. |
| **Data Persistence** | Amazon Aurora MySQL + RDS Proxy | MongoDB / NoSQL Document DB | **Trade-off**: Requires strict schema definition and proxy connection pooling.<br>**Benefit**: Guarantees strict ACID transactions, foreign key integrity, and instant relational joins across candidate master tables. |
