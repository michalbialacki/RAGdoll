# RAGdoll — Enterprise RAG Hybrid Search

A production-shaped Retrieval-Augmented Generation service built from the ground up on **AWS Bedrock** and **Qdrant**, combining **dense (semantic) and sparse (BM25) retrieval fused with Reciprocal Rank Fusion (RRF)**.

Unlike a managed-RAG setup (e.g. Bedrock Knowledge Base), this project implements the retrieval mechanics directly — custom chunking, its own embedding pipeline, and a self-configured vector store — to demonstrate understanding of how hybrid search actually works, not just how to wire up a managed service.

> Status: **in progress**. See [`Markdowns/PhasePlan.md`](Markdowns/PhasePlan.md) for the phased build plan and [`Markdowns/HANDOFF.md`](Markdowns/HANDOFF.md) for current progress.

## Why hybrid search

Dense embeddings capture semantic similarity well but routinely lose exact lexical matches — identifiers, error codes, version strings, proper nouns. A query for an exact technical term can score worse under pure dense search than a plain keyword match would. This project runs two independent ranking mechanisms per query — a dense vector search (Bedrock Titan Embeddings V2, HNSW index) and a sparse BM25 search (`fastembed`) — and fuses the two ranked lists with RRF, instead of relying on dense similarity alone.

## Architecture

```
                          INTERNET
                             │
                    Application Load Balancer
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
             FastAPI Task 1        FastAPI Task 2      ← ECS Fargate, public subnet (no NAT)
                  │                     │
                  └──────────┬──────────┘
                             ▼
                        Qdrant (dense + sparse vectors, HNSW)
```

**Ingestion pipeline:**

```
PDF (S3) → text extraction → chunking (500 tok / 50 overlap)
              │
              ├─▶ Bedrock Titan Embeddings V2 ─▶ dense vector
              └─▶ fastembed BM25 encoder       ─▶ sparse vector
                             │
                             ▼
                   Qdrant point: {id, dense_vector, sparse_vector, payload}
```

**Query pipeline:**

```
User query
   ├─▶ Titan Embeddings V2 ─▶ dense query vector ─▶ HNSW prefetch (top-k)
   └─▶ fastembed BM25      ─▶ sparse query vector ─▶ sparse prefetch (top-k)
                  │
                  ▼
        Reciprocal Rank Fusion (Qdrant Query API, fusion=RRF)
                  │
                  ▼
        Top-k context ─▶ prompt injection ─▶ Bedrock LLM ─▶ response
```

## Stack

| Layer | Choice |
|---|---|
| API | FastAPI (async) |
| Vector store | Qdrant — dense (HNSW) + sparse (BM25) on the same point |
| Dense embeddings | AWS Bedrock Titan Embeddings V2 |
| Sparse embeddings | `fastembed` (BM25) |
| LLM | AWS Bedrock, `anthropic.claude-haiku-4-5` via cross-region inference profile |
| Infra | Terraform (VPC, ALB, ECS Fargate, public subnet — no NAT Gateway) |
| CI/CD | GitHub Actions (lint + tests + `terraform plan`/`apply`/`destroy` around integration tests) |

## Getting started (local)

Requires [`uv`](https://docs.astral.sh/uv/) and Docker.

```bash
uv sync
docker compose up --build
curl http://localhost:8000/health
```

## Development

```bash
uv run pytest        # tests
uv run ruff check .  # lint
uv run mypy src       # type check
```

## Project layout

```
src/ragdoll/
├── api/         # FastAPI app + endpoints
├── ingestion/   # chunking, dense/sparse embedding, Qdrant writes
├── retrieval/   # query embedding, RRF fusion
└── generation/  # prompt/context injection, Bedrock LLM calls
```

## Cost awareness

This project deliberately avoids a NAT Gateway (~$32/month flat, billed by the minute regardless of traffic) by placing ECS Fargate tasks in a public subnet behind a security group — a documented, cost-driven trade-off for a portfolio/dev environment, not a production security posture. Terraform is applied and destroyed around integration test runs; nothing is left running. Full cost breakdown in [`Markdowns/EnterpriseRAGWriteup.md`](Markdowns/EnterpriseRAGWriteup.md).

## Background

Full design rationale, decision log, and the competency gap this project addresses relative to prior work: [`Markdowns/EnterpriseRAGWriteup.md`](Markdowns/EnterpriseRAGWriteup.md).
