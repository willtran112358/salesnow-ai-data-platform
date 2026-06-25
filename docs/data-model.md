# Data Model

## Entity Relationship

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
```

## S3 Partition Flow

```mermaid
flowchart LR
  subgraph Bronze
    B1["bronze/crawl/corporate_sites/dt=YYYY-MM-DD/hour=HH/"]
    B2["bronze/api/gbizinfo/dt=YYYY-MM-DD/"]
    B3["bronze/crm/salesforce/webhooks/dt=YYYY-MM-DD/"]
  end

  subgraph Silver
    S1["silver/companies/dt=YYYY-MM-DD/"]
    S2["silver/activities/dt=YYYY-MM-DD/"]
    S3["silver/contacts/dt=YYYY-MM-DD/"]
  end

  subgraph Gold
    G1["gold/dim_company/"]
    G2["gold/fact_activity/"]
    G3["gold/mart_intent_scores/"]
  end

  B1 --> S1
  B2 --> S1
  B1 --> S2
  B3 --> S2
  S1 --> G1
  S2 --> G2
  G1 & G2 --> G3
```

## dim_company

| Column | Type | Description |
|--------|------|-------------|
| `company_id` | UUID | Surrogate key |
| `corporate_number` | VARCHAR(13) | 法人番号 (natural key) |
| `company_name` | VARCHAR(500) | Official name |
| `company_name_normalized` | VARCHAR(500) | For matching |
| `prefecture_code` | CHAR(2) | JIS prefecture |
| `address` | TEXT | Headquarters address |
| `industry_code` | VARCHAR(10) | JSIC industry code |
| `employee_count` | INTEGER | Latest headcount |
| `capital_amount` | BIGINT | 資本金 (JPY) |
| `listing_status` | VARCHAR(20) | 上場区分 |
| `founded_date` | DATE | 設立年月 |
| `website_url` | VARCHAR(500) | Corporate website |
| `salesforce_account_id` | VARCHAR(18) | CRM external ID |
| `hubspot_company_id` | VARCHAR(50) | CRM external ID |
| `created_at` | TIMESTAMPTZ | Record creation |
| `updated_at` | TIMESTAMPTZ | Last enrichment |

## fact_activity

| Column | Type | Description |
|--------|------|-------------|
| `activity_id` | UUID | Surrogate key |
| `company_id` | UUID | FK → dim_company |
| `activity_type` | VARCHAR(50) | `job_posting`, `news`, `funding`, `ir_filing` |
| `activity_date` | TIMESTAMPTZ | Event timestamp |
| `title` | TEXT | Headline / job title |
| `source_url` | VARCHAR(1000) | Origin URL |
| `signal_strength` | FLOAT | 0.0–1.0 relevance score |
| `raw_payload` | JSONB | Original extracted data |

## intent_scores

| Column | Type | Description |
|--------|------|-------------|
| `company_id` | UUID | FK → dim_company |
| `score_date` | DATE | Scoring date |
| `hiring_intent` | FLOAT | Job posting velocity signal |
| `growth_intent` | FLOAT | Employee count trend |
| `funding_intent` | FLOAT | Capital event signal |
| `composite_score` | FLOAT | Weighted combination |
| `model_version` | VARCHAR(20) | Scoring model ID |
