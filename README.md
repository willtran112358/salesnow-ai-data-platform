# SalesNow AI Data Platform

> **Proposed data platform architecture** for [SalesNow](https://salesnow.jp/) (株式会社SalesNow) — Japan's leading B2B corporate database SaaS with **14M+ company records**, powering AI-driven sales intelligence.

![SalesNow Logo](docs/images/salesnow-logo.svg)

[![Database No.1](docs/images/badge-database-no1.svg)](https://salesnow.jp/)

---

## Executive Summary

SalesNow transforms raw enterprise signals into actionable sales intelligence. This repository proposes an **AI-driven data platform** that ingests, cleanses, enriches, and serves tens of terabytes of Japanese corporate data — aligned with SalesNow's production tech stack and the **Data Engineer (AI-driven Data Platform)** role.

| Metric | Value |
|--------|-------|
| Company records | 14M+ legal entities & organizations |
| Department contacts | 7.5M+ |
| Data refresh | As fast as every 1 minute |
| CRM integrations | Salesforce, HubSpot, API, MCP |
| AI use cases | Intent scoring, company summaries, hook-talk generation |

![Hero — AI × 14M company records](docs/images/hero-product.webp)

---

## Product Context

SalesNow helps sales teams answer three questions with data:

1. **Who** should we target? — High-precision list creation in under 1 minute
2. **When** should we reach out? — Activity signals (hiring, funding, news)
3. **What** should we say? — AI-generated company summaries & hook talks

### Three Core Product Features

| Feature | Description | Platform Image |
|---------|-------------|----------------|
| **List Creation** | Filter 14M+ records by industry, size, intent, hiring trends | ![List creation](docs/images/feature-list-creation.webp) |
| **CRM Integration** | Sync with Salesforce/HubSpot; unify deal history + firmographics | ![CRM integration](docs/images/feature-crm-integration.webp) |
| **Company Research** | One-click dossier: news, IR, jobs, employee growth, AI summary | ![Company research](docs/images/feature-company-research.webp) |

### Partner Ecosystem

![Salesforce AppExchange](docs/images/badge-appexchange.png)
![Salesforce Partner Since 2022](docs/images/badge-salesforce-partner.png)

---

## Data Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                                     │
│  Scrapy Crawlers (ECS Fargate) │ Government APIs │ CRM Webhooks │ n8n      │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ raw (JSON/Parquet)
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    AWS S3 — Data Lake (Bronze / Silver / Gold)              │
│   bronze/          silver/           gold/           ai-features/           │
│   raw crawl        cleansed          dimensional     embeddings, scores     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ MWAA (Airflow)   │  │ Databricks Spark │  │ Data Quality     │
│ Orchestration    │  │ ETL / ML         │  │ Great Expectations│
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SERVING LAYER — Aurora PostgreSQL                        │
│   companies │ activities │ contacts │ enrichment │ ai_summaries           │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│   SalesNow SaaS API (FastAPI) │ Salesforce │ HubSpot │ MCP / LLM Agents   │
└─────────────────────────────────────────────────────────────────────────────┘
```

See [docs/architecture.md](docs/architecture.md) for detailed design.

---

## Repository Structure

```
salesnow-ai-data-platform/
├── docs/
│   ├── architecture.md          # Platform design & data flows
│   ├── data-model.md            # Entity relationships
│   └── images/                  # Product screenshots from salesnow.jp
├── src/
│   ├── ingestion/               # Scrapy spiders, crawl utilities
│   ├── processing/              # Spark transforms, enrichment logic
│   ├── quality/                 # Validation rules & monitoring
│   └── ai/                      # Feature store, intent scoring
├── infra/
│   ├── airflow/dags/            # MWAA pipeline definitions
│   └── databricks/notebooks/    # PySpark batch jobs
├── sql/migrations/              # Aurora PostgreSQL DDL
├── requirements.txt
└── README.md
```

---

## Tech Stack (aligned with SalesNow JD)

| Layer | Technology |
|-------|------------|
| **Ingestion** | Python (Scrapy), AWS Fargate (ECS), Amazon MWAA (Airflow) |
| **Storage** | Amazon S3, Amazon Aurora PostgreSQL |
| **Processing** | Apache Spark (Databricks) |
| **Infrastructure** | AWS, Databricks |
| **AI / Workflow** | LLM enrichment, n8n orchestration, MCP integration |
| **DevOps** | GitHub, DataOps practices, quality gates |

---

## Data Domains

| Domain | Sources | Refresh | AI Output |
|--------|---------|---------|-----------|
| **Corporate Master** | gBizINFO, EDINET, corporate sites | Daily | Entity resolution, dedup |
| **Activity Signals** | Job boards, news, IR, funding | Hourly | Intent score, timing alerts |
| **Contacts** | Public directories, opt-out registry | Weekly | Department graph |
| **CRM Sync** | Salesforce, HubSpot webhooks | Real-time | Win-pattern segmentation |
| **Enrichment** | EC checker, tech stack detection | On-demand | Switch scores, hook talks |

---

## Quick Start (Local Development)

```bash
# Clone
git clone https://github.com/willtran112358/salesnow-ai-data-platform.git
cd salesnow-ai-data-platform

# Virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run data quality checks (sample)
python -m src.quality.validator --dataset sample

# Run enrichment demo
python -m src.processing.enrichment --company "株式会社SalesNow"
```

---

## Pipeline Overview

| DAG | Schedule | Purpose |
|-----|----------|---------|
| `crawl_corporate_sites` | Every 6h | Scrapy → S3 bronze |
| `ingest_government_master` | Daily | gBizINFO / tax registry sync |
| `silver_cleansing` | Hourly | Normalize, deduplicate, validate |
| `gold_dimensional_model` | Daily | Star schema for analytics & AI |
| `activity_signal_detection` | Every 15m | Hiring, news, funding deltas |
| `ai_feature_generation` | Daily | Summaries, embeddings, scores |
| `crm_enrichment_sync` | Every 5m | Push attributes to Salesforce/HubSpot |
| `data_quality_monitoring` | Hourly | Great Expectations + Slack alerts |

---

## Data Quality Framework

Four pillars aligned with SalesNow's **名寄せ (entity resolution)** and enrichment SLAs:

1. **Completeness** — Required fields per entity type (法人番号, 社名, 住所)
2. **Freshness** — Staleness thresholds per domain (activities < 1h, master < 24h)
3. **Accuracy** — Cross-source validation against government registries
4. **Uniqueness** — Deduplication via corporate number + fuzzy name matching

```python
# Example: run validation suite
from src.quality.validator import CompanyRecordValidator

validator = CompanyRecordValidator()
result = validator.validate_batch(records)
assert result.pass_rate >= 0.995  # 99.5% SLA
```

---

## AI Feature Layer

Supports SalesNow product capabilities:

| Feature | Data Inputs | Model / Logic |
|---------|-------------|---------------|
| **Company AI Summary** | News, IR, jobs, employee trend | LLM summarization |
| **Intent Score** | Hiring velocity, funding, web traffic | Gradient boosting |
| **Win Pattern** | CRM deal history + firmographics | Segmentation clustering |
| **Hook Talk Generator** | Activity deltas + lost-deal context | LLM prompt chain |
| **EC Switch Score** | Website tech detection | Rule + ML hybrid |

---

## Cost & Scale Considerations

| Concern | Strategy |
|---------|----------|
| **TB-scale storage** | S3 lifecycle: bronze 90d → Glacier; gold retained |
| **Crawl cost** | Fargate spot tasks; domain-aware rate limiting |
| **Spark jobs** | Databricks job clusters with autoscaling; partition by `prefecture` |
| **Aurora serving** | Read replicas for search API; connection pooling |
| **AI inference** | Batch pre-compute summaries; cache in Redis |

---

## Roadmap

- [ ] **Phase 1** — Bronze/Silver pipelines for corporate master + activities
- [ ] **Phase 2** — Gold dimensional model + CRM enrichment sync (5-min SLA)
- [ ] **Phase 3** — Real-time activity streaming (Kinesis → Spark Structured Streaming)
- [ ] **Phase 4** — Feature store for ML; A/B test intent scoring models
- [ ] **Phase 5** — Self-serve data quality dashboard for CS & product teams

---

## About SalesNow

| | |
|---|---|
| **Company** | 株式会社SalesNow (SalesNow Co., Ltd.) |
| **Founded** | 2019, Tokyo |
| **Industry** | B2B Sales Intelligence / Corporate Database |
| **Funding** | Series A (JPY 650M+, Nov 2024) |
| **Website** | [salesnow.jp](https://salesnow.jp/) |
| **Careers** | [Data Engineer — AI-driven Data Platform](https://herp.careers/v1/salesnow0801/aLtdW6WbCZ0h) |

---

## Disclaimer

This repository is an **independent architecture proposal** created for portfolio and interview preparation. It is not affiliated with or endorsed by SalesNow Co., Ltd. Product images are sourced from [salesnow.jp](https://salesnow.jp/) for illustrative purposes.

---

## License

MIT License — see [LICENSE](LICENSE).
