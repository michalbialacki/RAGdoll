# Plan faz – Enterprise RAG Hybrid Search (Bedrock + Qdrant)

Źródło prawdy: `Markdowns/EnterpriseRAGWriteup.md`. Każda faza kończy się testami (pytest) jako obowiązkowym ostatnim krokiem — nie przechodzimy dalej z czerwonymi testami.

## Decyzje architektoniczne (sesja 2026-07-08)
- Qdrant (nie pgvector) jako baza wektorowa — natywne wsparcie dla dwóch typów wektorów (dense + sparse/BM25) na tym samym punkcie, bez dodatkowej infrastruktury.
- Dense embeddings: Bedrock Titan Embeddings V2. Sparse: BM25 przez `fastembed` (lokalny sparse encoder, `Qdrant/bm25` model) — zatwierdzone 2026-07-08.
- Fuzja rankingów: RRF przez natywny Qdrant Query API (`prefetch` + `fusion=RRF`), bez własnej implementacji łączenia list.
- LLM generacyjny: `anthropic.claude-haiku-4-5-20251001-v1:0` przez cross-region inference profile `eu.anthropic.claude-haiku-4-5-20251001-v1:0` — zatwierdzone 2026-07-08 (niski koszt, streaming wspierany na przyszłość dla Phase 07). Model wymaga inference profile, nie bezpośredniego on-demand `InvokeModel` z gołym `modelId` — analogicznie do doświadczenia z IAMTheGateway (Nova Lite).
- Streaming SSE — świadomie odłożone do Fazy 7 (nice-to-have); MVP zwraca pełną odpowiedź.
- Terraform: publiczna podsieć + Security Group zamiast NAT Gateway (ryzyko kosztowe ~32 USD/mies. z writeupu, sekcja 7).

---

## Phase 00 – Szkielet repo i środowisko lokalne
- Step 01 – `uv init` (jeśli brak `pyproject.toml`) + `uv venv`; struktura src-layout: `src/ragdoll/{ingestion,retrieval,generation,api}/`
- Step 02 – Zależności bazowe: `fastapi`, `uvicorn`, `qdrant-client`, `boto3`, `pydantic-settings`; dev: `pytest`, `ruff`, `mypy`
- Step 03 – `ruff.toml` / konfiguracja w `pyproject.toml` (lint + format), `mypy` config (strict na warstwie domenowej)
- Step 04 – `docker-compose.yml`: FastAPI (build lokalny) + Qdrant (obraz oficjalny), sieć wspólna, wolumeny na dane Qdrant
- Step 05 – FastAPI app factory (boilerplate, bez logiki biznesowej) + health-check endpoint (`/health`)
- Step 06 – Test: `docker-compose up` działa, `/health` zwraca 200, `uv run pytest` (pusty, ale zielony) i `uv run ruff check .` przechodzą

## Phase 01 – Ingestion: chunking + dense/sparse embedding → Qdrant
- Step 01 – Ekstrakcja tekstu z PDF (lokalny plik testowy, np. dokumentacja techniczna) → surowy tekst
- Step 02 – Chunking stałej długości: 500 tokenów / 50 overlap (PoC, zgodnie z writeup sekcja 3)
- Step 03 – Konfiguracja kolekcji Qdrant z dwoma typami wektorów na punkcie: `dense_vector` (HNSW) + `sparse_vector` (BM25) — decyzja o parametrach HNSW (m, ef_construct) do uzasadnienia
- Step 04 – Dense embedding: batching chunków → Bedrock Titan Embeddings V2 (async, żeby nie blokować event loop)
- Step 05 – Sparse embedding: `fastembed` BM25 encoder (`Qdrant/bm25`) → sparse vector (indeksy tokenów + wagi)
- Step 06 – Zapis punktu do Qdrant: `{id, dense_vector, sparse_vector, payload}` (payload = metadane: źródło, numer chunku, tekst)
- Step 07 – Testy: unit (chunking granice/overlap, mock Bedrock dla embeddingów), integration (zapis + odczyt z lokalnego Qdrant przez docker-compose)

## Phase 02 – Query pipeline: dense + sparse prefetch → fuzja RRF
- Step 01 – Endpoint `/query` (FastAPI, async): przyjmuje zapytanie tekstowe
- Step 02 – Wektoryzacja zapytania: dense (Bedrock Titan) + sparse (BM25) równolegle
- Step 03 – Qdrant Query API: `prefetch` dense (HNSW top-k) + `prefetch` sparse (top-k), `fusion=RRF`
- Step 04 – Zwrot top-k finalnego kontekstu (bez jeszcze LLM) — endpoint zwraca same chunki + score
- Step 05 – Testy: unit (poprawność wywołania Query API, mock Qdrant), integration (zapytanie z przykładowym dokładnym identyfikatorem — dowód, że sparse łapie to, co dense gubi)

## Phase 03 – Context injection + Bedrock LLM generation
- Step 01 – Konfiguracja klienta Bedrock dla `anthropic.claude-haiku-4-5-20251001-v1:0` przez inference profile `eu.anthropic.claude-haiku-4-5-20251001-v1:0` (IAM policy musi zezwalać na `bedrock:InvokeModel` na ARN profilu, nie tylko modelu)
- Step 02 – Budowa promptu: context injection z top-k chunków + zapytanie użytkownika
- Step 03 – Wywołanie `bedrock:InvokeModel` (async, bez streamingu) → pełna odpowiedź
- Step 04 – Endpoint `/query` rozszerzony: zwraca finalną odpowiedź LLM zamiast samych chunków
- Step 05 – Testy: unit (budowa promptu, mock Bedrock LLM), integration (pełny przepływ query→retrieval→generation lokalnie)

## Phase 04 – Dowód hybrid: test porównawczy dense vs hybrid
- Step 01 – Zestaw testowych pytań zawierający: pytania semantyczne (dense powinno wygrywać) + pytania z dokładnym identyfikatorem/kodem/nazwą własną (sparse/hybrid powinno wygrywać)
- Step 02 – Tryb "dense-only" w retrieval (flaga/parametr wyłączający prefetch sparse) do porównania
- Step 03 – Skrypt/test uruchamiający ten sam zestaw pytań na dense-only i hybrid, zapisujący wyniki obok siebie
- Step 04 – Testy: assercja, że dla przynajmniej jednego przypadku z dokładnym identyfikatorem hybrid zwraca lepszy/poprawny kontekst niż dense-only (dowód pokrycia nazwy projektu w danych)

## Phase 05 – Terraform: infrastruktura AWS
> Ryzyko kosztowe do przypomnienia przed generowaniem: NAT Gateway (~32 USD/mies. per minuta) — używamy publicznej podsieci + Security Group zamiast NAT (writeup sekcja 7). Multi-AZ RDS podwaja koszt (jeśli w ogóle używamy RDS — do potwierdzenia, czy potrzebne obok Qdrant Cloud).
- Step 01 – Terraform project setup: provider AWS, remote state (S3 + lock), zmienne, outputs
- Step 02 – VPC: publiczna podsieć (bez NAT), Internet Gateway, routing
- Step 03 – Security Groups: ALB (inbound 443/80 z internetu), ECS Fargate (inbound tylko z ALB SG)
- Step 04 – ALB + target group + listener → ECS Fargate service
- Step 05 – ECS Fargate: task definition (`cpu=256`, `memory=512`), IAM role least-privilege (`bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`, dostęp do Qdrant Cloud/endpoint)
- Step 06 – AWS Budget alert (zabezpieczenie kosztowe, zgodnie z writeup sekcja 6)
- Step 07 – Testy: `terraform validate` + `terraform plan` (dry-run, bez apply na tym etapie)

## Phase 06 – CI/CD (GitHub Actions)
- Step 01 – Workflow: lint (`ruff check`) + testy jednostkowe (offline, bez AWS/Qdrant Cloud) na każdy push/PR
- Step 02 – Workflow: `terraform validate` + `terraform plan` (dry-run) jako osobny job
- Step 03 – Job integracyjny: `terraform apply` → testy integracyjne (Phase 01–04 przeniesione na żywą infrę) → `terraform destroy` (zawsze wykonywany, nawet przy błędzie testów — `if: always()`)
- Step 04 – Testy: pełen przebieg pipeline na branchu testowym, weryfikacja, że `destroy` faktycznie usuwa zasoby (brak kosztów wiszących)

---

## Future scope (nice-to-have, po MVP)
- Phase 07 – Streaming SSE zamiast pełnej odpowiedzi na raz
- Phase 08 – Semantic chunking zamiast podziału na sztywną liczbę tokenów
- Phase 09 – Reranking (cross-encoder) jako krok po fuzji RRF, przed context injection
- Phase 10 – Cache semantyczny dla powtarzalnych zapytań (analogicznie do Phase 11 z IAMTheGateway)
