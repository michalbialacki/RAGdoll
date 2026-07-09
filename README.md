
# RAGdoll — Enterprise RAG Hybrid Search

*English version: [README.en.md](README.en.md).*

Usługa RAG (Retrieval-Augmented Generation) zbudowana od podstaw na **AWS Bedrock** i **Qdrant**, łącząca **wyszukiwanie gęste (semantyczne) i rzadkie (BM25) fuzjonowane metodą Reciprocal Rank Fusion (RRF)**.

W przeciwieństwie do konfiguracji opartej o usługę zarządzaną (np. Bedrock Knowledge Base), ten projekt implementuje mechanikę wyszukiwania bezpośrednio — własny chunking, własny pipeline embeddingów i samodzielnie skonfigurowaną bazę wektorową — żeby pokazać zrozumienie działania hybrid search "pod maską", a nie tylko umiejętność podłączenia usługi zarządzanej.

> Status: **w trakcie realizacji**. Plan faz: [`Markdowns/PhasePlan.md`](Markdowns/PhasePlan.md), bieżący postęp: [`Markdowns/HANDOFF.md`](Markdowns/HANDOFF.md).

## Dlaczego hybrid search

Gęste embeddingi dobrze łapią podobieństwo semantyczne, ale regularnie gubią dokładne dopasowania leksykalne — identyfikatory, kody błędów, numery wersji, nazwy własne. Zapytanie o dokładny termin techniczny może uzyskać gorszy wynik przy samym wyszukiwaniu gęstym niż zwykłe dopasowanie słów kluczowych. Ten projekt uruchamia dwa niezależne mechanizmy rankingu dla każdego zapytania — wyszukiwanie gęste (Bedrock Titan Embeddings V2, indeks HNSW) i wyszukiwanie rzadkie BM25 (`fastembed`) — i łączy obie listy wyników metodą RRF, zamiast polegać wyłącznie na podobieństwie gęstym.

## Architektura

```
                          INTERNET
                             │
                    Application Load Balancer
                             │
                  ┌──────────┴──────────┐
                  ▼                     ▼
             FastAPI Task 1        FastAPI Task 2      ← ECS Fargate, publiczna podsieć (bez NAT)
                  │                     │
                  └──────────┬──────────┘
                             ▼
                        Qdrant (wektory gęste + rzadkie, HNSW)
```

**Pipeline ingestii:**

```
PDF (S3) → ekstrakcja tekstu → chunking (500 tok / 50 overlap)
              │
              ├─▶ Bedrock Titan Embeddings V2 ─▶ wektor gęsty
              └─▶ fastembed BM25 encoder       ─▶ wektor rzadki
                             │
                             ▼
                   Punkt w Qdrant: {id, dense_vector, sparse_vector, payload}
```

**Pipeline zapytania:**

```
Zapytanie użytkownika
   ├─▶ Titan Embeddings V2 ─▶ gęsty wektor zapytania ─▶ prefetch HNSW (top-k)
   └─▶ fastembed BM25      ─▶ rzadki wektor zapytania ─▶ prefetch sparse (top-k)
                  │
                  ▼
        Reciprocal Rank Fusion (Qdrant Query API, fusion=RRF)
                  │
                  ▼
        Top-k kontekst ─▶ context injection ─▶ Bedrock LLM ─▶ odpowiedź
```

## Stack

| Warstwa | Wybór |
|---|---|
| API | FastAPI (async) |
| Baza wektorowa | Qdrant — gęste (HNSW) + rzadkie (BM25) na tym samym punkcie |
| Embeddingi gęste | AWS Bedrock Titan Embeddings V2 |
| Embeddingi rzadkie | `fastembed` (BM25) |
| LLM | AWS Bedrock, `anthropic.claude-haiku-4-5` przez cross-region inference profile |
| Infrastruktura | Terraform (VPC, ALB, ECS Fargate, publiczna podsieć — bez NAT Gateway) |
| CI/CD | GitHub Actions (lint + testy + `terraform plan`/`apply`/`destroy` wokół testów integracyjnych) |

## Uruchomienie lokalne

Wymaga [`uv`](https://docs.astral.sh/uv/) i Dockera.

```bash
uv sync
docker compose up --build
curl http://localhost:8000/health
```

## Rozwój

```bash
uv run pytest        # testy
uv run ruff check .  # lint
uv run mypy src       # type check
```

## Struktura projektu

```
src/ragdoll/
├── api/         # aplikacja FastAPI + endpointy
├── ingestion/   # chunking, embeddingi gęste/rzadkie, zapis do Qdrant
├── retrieval/   # embedding zapytania, fuzja RRF
└── generation/  # context injection, wywołania Bedrock LLM
```

## Świadomość kosztowa

Projekt świadomie unika NAT Gateway (~32 USD/mies. naliczane per minuta, niezależnie od ruchu), umieszczając zadania ECS Fargate w publicznej podsieci za security groupem — udokumentowany, kosztowy kompromis dla środowiska portfolio/dev, nie postawa produkcyjna. Terraform jest stosowany i niszczony wokół uruchomień testów integracyjnych — nic nie zostaje uruchomione na stałe. Pełne rozbicie kosztów w [`Markdowns/EnterpriseRAGWriteup.md`](Markdowns/EnterpriseRAGWriteup.md).

## Kontekst

Pełne uzasadnienie decyzji architektonicznych i luka kompetencyjna, którą wypełnia ten projekt względem wcześniejszych: [`Markdowns/EnterpriseRAGWriteup.md`](Markdowns/EnterpriseRAGWriteup.md).
