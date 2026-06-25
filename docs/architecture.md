# SalesNow AI Data Platform — Architecture

## 1. Business Context

SalesNow operates Japan's largest B2B corporate database (14M+ records). The data platform must:

- Ingest heterogeneous web and API sources at scale (tens of TB)
- Maintain sub-minute freshness for high-value activity signals
- Power AI features: company summaries, intent scoring, hook-talk generation
- Sync enriched data to Salesforce, HubSpot, and the SalesNow SaaS API

See [business-requirements.md](business-requirements.md) for revenue, market share, and growth analysis.

---

## 2. End-to-End Solution Architecture

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'fontSize': '14px'}}}%%
flowchart TB
    subgraph SOURCES["Data Sources"]
        direction LR
        S1[("Corporate Websites")]
        S2[("gBizINFO / EDINET")]
        S3[("Job Boards & News")]
        S4[("Salesforce / HubSpot")]
        S5[("IR & Funding Feeds")]
    end

    subgraph INGEST["Ingestion Layer"]
        direction LR
        I1["Scrapy Spiders"]
        I2["API Connectors"]
        I3["CRM Webhooks"]
        I4["n8n Workflows"]
    end

    subgraph ORCHESTRATE["Orchestration — MWAA Airflow"]
        AF["DAG Scheduler"]
    end

    subgraph LAKE["AWS S3 Data Lake — Medallion"]
        direction TB
        B[("Bronze<br/>Raw JSONL")]
        SL[("Silver<br/>Cleansed Parquet")]
        G[("Gold<br/>Star Schema")]
        AI[("AI Features<br/>Scores & Embeddings")]
        B --> SL --> G --> AI
    end

    subgraph PROCESS["Processing — Databricks"]
        direction LR
        P1["Entity Resolution"]
        P2["Activity Delta Detection"]
        P3["Intent Scoring"]
        P4["AI Summary Batch"]
    end

    subgraph QUALITY["Data Quality"]
        Q1["Great Expectations"]
        Q2["SLA Monitors"]
        Q3["Slack Alerts"]
    end

    subgraph SERVE["Serving Layer"]
        DB[("Aurora PostgreSQL")]
        CACHE[("Redis Cache")]
    end

    subgraph CONSUMERS["Downstream Consumers"]
        direction LR
        C1["SalesNow SaaS API"]
        C2["Salesforce AppExchange"]
        C3["HubSpot Sync"]
        C4["MCP / LLM Agents"]
    end

    SOURCES --> INGEST
    INGEST --> AF
    AF --> B
    SL --> PROCESS
    PROCESS --> G
    PROCESS --> AI
    G --> QUALITY
    G --> DB
    AI --> DB
    AI --> CACHE
    DB --> CONSUMERS
    CACHE --> CONSUMERS

    classDef source fill:#ebf8ff,stroke:#3182ce,color:#1a365d
    classDef ingest fill:#e9d8fd,stroke:#805ad5,color:#44337a
    classDef lake fill:#fefcbf,stroke:#d69e2e,color:#744210
    classDef process fill:#c6f6d5,stroke:#38a169,color:#22543d
    classDef serve fill:#fed7d7,stroke:#e53e3e,color:#742a2a
    classDef consumer fill:#e2e8f0,stroke:#4a5568,color:#1a202c

    class S1,S2,S3,S4,S5 source
    class I1,I2,I3,I4 ingest
    class B,SL,G,AI lake
    class P1,P2,P3,P4 process
    class DB,CACHE serve
    class C1,C2,C3,C4 consumer
```

---

## 3. Data Pipeline — Medallion Flow

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    subgraph BRONZE["Bronze Zone"]
        direction TB
        B1["crawl/corporate_sites<br/>dt=YYYY-MM-DD/hour=HH"]
        B2["crawl/job_boards"]
        B3["api/gbizinfo"]
        B4["crm/salesforce/webhooks"]
    end

    subgraph SILVER["Silver Zone"]
        direction TB
        SV1["companies<br/>deduplicated"]
        SV2["activities<br/>normalized"]
        SV3["contacts<br/>opt-out filtered"]
        SV4["crm_deals<br/>conformed"]
    end

    subgraph GOLD["Gold Zone"]
        direction TB
        G1["dim_company"]
        G2["fact_activity"]
        G3["fact_employee_trend"]
        G4["mart_intent_scores"]
    end

    subgraph AI_ZONE["AI Features"]
        direction TB
        A1["intent_scores"]
        A2["ai_summaries"]
        A3["embeddings"]
    end

    B1 & B2 & B3 --> SV1 & SV2
    B4 --> SV4
    SV1 --> G1
    SV2 --> G2
    SV1 --> G3
    G1 & G2 --> G4
    G4 --> A1
    G1 & G2 --> A2
    G2 --> A3

    style BRONZE fill:#fff5f5,stroke:#fc8181
    style SILVER fill:#fffff0,stroke:#ecc94b
    style GOLD fill:#f0fff4,stroke:#68d391
    style AI_ZONE fill:#ebf8ff,stroke:#63b3ed
```

---

## 4. Pipeline DAG Orchestration

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    START((Start)) --> CRAWL

    subgraph SCHEDULED["Scheduled Pipelines"]
        CRAWL["crawl_corporate_sites<br/>every 6h"]
        GOV["ingest_government_master<br/>daily 02:00 JST"]
        SILVER["silver_cleansing<br/>hourly"]
        GOLD["gold_dimensional_model<br/>daily 04:00 JST"]
        ACTIVITY["activity_signal_detection<br/>every 15m"]
        AIJOB["ai_feature_generation<br/>daily 05:00 JST"]
    end

    subgraph REALTIME["Near-Real-Time"]
        CRM["crm_enrichment_sync<br/>every 5m"]
    end

    subgraph MONITOR["Observability"]
        DQ["data_quality_monitoring<br/>hourly"]
        ALERT{{"SLA Breach?<br/>Slack #data-alerts"}}
    end

    CRAWL --> SILVER
    GOV --> SILVER
    SILVER --> DQ
    SILVER --> GOLD
    SILVER --> ACTIVITY
    GOLD --> AIJOB
    GOLD --> CRM
    ACTIVITY --> AIJOB
    DQ --> ALERT
    AIJOB --> ENDNODE((Complete))
    CRM --> ENDNODE

    style SCHEDULED fill:#e9d8fd,stroke:#805ad5
    style REALTIME fill:#fed7e2,stroke:#d53f8c
    style MONITOR fill:#feebc8,stroke:#dd6b20
```

---

## 5. Web Crawl Pipeline Detail

```mermaid
sequenceDiagram
    autonumber
    participant AF as Airflow MWAA
    participant ECS as ECS Fargate
    participant SP as Scrapy Spider
    participant S3 as S3 Bronze
    participant DBX as Databricks
    participant S3S as S3 Silver
    participant AUR as Aurora PostgreSQL

    AF->>ECS: Trigger crawl_corporate_sites task
    ECS->>SP: Launch container with seed URLs
    loop Per domain (rate-limited)
        SP->>SP: Parse HTML + extract fields
        SP->>S3: Write JSONL.gz partition
    end
    SP-->>ECS: Crawl complete
    ECS-->>AF: Task success signal
    AF->>DBX: Trigger silver_cleansing job
    DBX->>S3: Read bronze partition
    DBX->>DBX: Normalize, dedup, validate
    DBX->>S3S: Write Parquet silver
    AF->>DBX: Trigger gold_dimensional_model
    DBX->>AUR: Incremental upsert dim_company
```

---

## 6. CRM Enrichment Pipeline (5-Min SLA)

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart LR
    SF["Salesforce<br/>New Lead Event"] --> WH["Webhook<br/>API Gateway"]
    WH --> S3B[("S3 Bronze<br/>crm/webhooks")]
    S3B --> MATCH{"Entity<br/>Resolution"}
    MATCH -->|"法人番号 match"| ENRICH["Enrichment<br/>Lookup"]
    MATCH -->|"fuzzy name"| FUZZY["Fuzzy Match<br/>+ Review Queue"]
    MATCH -->|"no match"| CRAWL["Trigger<br/>On-demand Crawl"]
    ENRICH --> AUR[("Aurora<br/>companies")]
    FUZZY --> AUR
    CRAWL --> AUR
    AUR --> PUSH["Push Attributes<br/>to Salesforce"]
    PUSH --> SF2["Lead Enriched<br/>< 5 minutes"]

    style SF fill:#00a1e0,color:#fff
    style SF2 fill:#00a1e0,color:#fff
    style MATCH fill:#fefcbf,stroke:#d69e2e
```

---

## 7. AI Feature Pipeline

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    subgraph INPUTS["Gold Layer Inputs"]
        I1["fact_activity"]
        I2["fact_employee_trend"]
        I3["dim_company"]
        I4["CRM deal history"]
    end

    subgraph FEATURES["Feature Engineering — Spark"]
        F1["Hiring velocity<br/>30d vs prev 30d"]
        F2["Employee growth rate"]
        F3["Funding event flags"]
        F4["News mention count"]
    end

    subgraph MODELS["AI / ML Layer"]
        M1["Intent Score<br/>XGBoost"]
        M2["Company Summary<br/>LLM Batch"]
        M3["Hook Talk<br/>LLM Chain"]
        M4["EC Switch Score<br/>Rule + ML"]
    end

    subgraph OUTPUT["Serving"]
        O1[("intent_scores table")]
        O2[("ai_summaries table")]
        O3["Redis cache"]
        O4["MCP API endpoint"]
    end

    I1 --> F1 & F4
    I2 --> F2
    I1 --> F3
    I3 & I4 --> M1
    F1 & F2 & F3 & F4 --> M1
    I1 & I3 --> M2
    I1 & I4 --> M3
    I3 --> M4

    M1 --> O1
    M2 --> O2
    M2 --> O3
    O1 & O2 --> O4

    style MODELS fill:#e9d8fd,stroke:#805ad5
    style OUTPUT fill:#c6f6d5,stroke:#38a169
```

---

## 8. Data Model (ER Diagram)

```mermaid
erDiagram
    DIM_INDUSTRY ||--o{ DIM_COMPANY : classifies
    DIM_PREFECTURE ||--o{ DIM_COMPANY : located_in
    DIM_COMPANY ||--o{ FACT_ACTIVITY : has
    DIM_COMPANY ||--o{ FACT_EMPLOYEE_TREND : tracks
    DIM_COMPANY ||--o{ CONTACTS : has
    DIM_COMPANY ||--o| AI_SUMMARIES : summarized_by
    DIM_COMPANY ||--o{ INTENT_SCORES : scored_daily

    DIM_COMPANY {
        uuid company_id PK
        varchar corporate_number UK
        varchar company_name
        varchar prefecture_code
        int employee_count
        varchar salesforce_account_id
        timestamptz updated_at
    }

    FACT_ACTIVITY {
        uuid activity_id PK
        uuid company_id FK
        varchar activity_type
        timestamptz activity_date
        float signal_strength
        jsonb raw_payload
    }

    INTENT_SCORES {
        uuid company_id FK
        date score_date PK
        float hiring_intent
        float growth_intent
        float composite_score
    }

    AI_SUMMARIES {
        uuid company_id PK
        text summary_text
        varchar model_version
        timestamptz expires_at
    }
```

---

## 9. Data Quality Monitoring Flow

```mermaid
%%{init: {'theme': 'base'}}%%
stateDiagram-v2
    [*] --> Ingested: Raw data lands in Bronze

    Ingested --> Validating: Silver ETL starts
    Validating --> Passed: pass_rate >= 99.5%
    Validating --> Failed: SLA breach

    Passed --> Published: Load to Gold + Aurora
    Failed --> Quarantined: Write to silver/quarantine/
    Quarantined --> Alerting: Slack #data-alerts
    Alerting --> ManualReview: Data engineer triage
    ManualReview --> Validating: Fix + reprocess

    Published --> Monitoring: Hourly DQ checks
    Monitoring --> Passed: Freshness OK
    Monitoring --> Failed: Stale or incomplete

    Published --> [*]
```

### SLAs

| Metric | Target | Alert Channel |
|--------|--------|---------------|
| Corporate master completeness | ≥ 99.5% | Slack #data-alerts |
| Activity freshness (p95) | < 60 min | PagerDuty |
| Entity resolution match rate | ≥ 98% | Weekly report |
| CRM enrichment latency | < 5 min | Slack #crm-sync |
| Duplicate rate | < 0.1% | Dashboard |

---

## 10. Security & Disaster Recovery

```mermaid
%%{init: {'theme': 'base'}}%%
flowchart TB
    subgraph SECURITY["Security Controls"]
        SEC1["S3 SSE-KMS encryption"]
        SEC2["IAM roles per pipeline"]
        SEC3["Opt-out PII filtering"]
        SEC4["CloudTrail audit logs"]
        SEC5["VPC private subnets"]
    end

    subgraph DR["Disaster Recovery"]
        DR1["S3 versioning<br/>RPO: 0"]
        DR2["Aurora PITR<br/>RPO: 5 min"]
        DR3["Airflow metadata backup<br/>RPO: 1h"]
        DR4["Cross-region S3 replica<br/>RTO: < 1h"]
    end

    SECURITY --> DR

    style SECURITY fill:#fff5f5,stroke:#e53e3e
    style DR fill:#ebf8ff,stroke:#3182ce
```

| Component | RPO | RTO |
|-----------|-----|-----|
| S3 data lake | 0 (versioning) | < 1h |
| Aurora PostgreSQL | 5 min (PITR) | < 30 min |
| Airflow DAG state | 1h | < 2h |
| Databricks jobs | Re-run from checkpoint | < 4h |
