# Plan faz — RAGdoll na AWS Managed Services (ścieżka praktyczna)

## Cel tego dokumentu i relacja do `Markdowns/PhasePlan.md`

Główny `PhasePlan.md` (Faza 00–06 + nice-to-have) to ścieżka **teoretyczna/mechaniczna**: hand-rolled RRF, własna implementacja chunkingu, dense/sparse embedding, Qdrant jako vector store, którym sterujemy sami na poziomie API. Cel: rozumieć *co się dzieje pod spodem*, żeby móc to uzasadnić na rozmowie technicznej.

Ten dokument to ścieżka **praktyczna**: ten sam produkt (RAG nad dokumentami, hybrid search), ale zbudowany na **AWS Bedrock Knowledge Bases** — usłudze zarządzanej, która robi chunking, embedding, indexing i hybrid retrieval za nas. Cel: nauka kodowania pod AWS, Terraform, IAM, planowania faz w kontekście realnej infrastruktury chmurowej — czyli praktyka inżynierska, nie mechanika RAG (tę już zamyka główny tor).

**Dlaczego oba tory, a nie jeden:** Teoria bez pokrycia w praktyce + 'reinventing the wheel'

Nie zaczynamy tego toru równolegle z głównym w tej samej sesji bez wyraźnej decyzji, na czym pracujemy — żeby nie mieszać kontekstu (Qdrant lokalny vs AWS managed to inne mentalne tryby).

---

## Decyzje architektoniczne do potwierdzenia na starcie Fazy A0

- **Vector store pod Bedrock Knowledge Base** — do wyboru między:
  - **OpenSearch Serverless** (natywna integracja z Bedrock KB, hybrid search wspierany) — **ryzyko kosztowe: minimum 2 OCU indexing + 2 OCU search nawet przy zerowym ruchu, płatne w trybie ciągłym, rzędu kilkuset USD/mies. jeśli zostawione włączone** — wymaga jawnego apply→test→destroy, tak jak NAT Gateway w głównym writeup.
  - **Aurora PostgreSQL Serverless v2 + pgvector** — tańszy przy niskim/zerowym ruchu (skaluje do ~0.5 ACU), ale hybrid search (dense+sparse) wymaga własnej konfiguracji, mniej "z pudełka" niż OpenSearch.
  - **Amazon Kendra GenAI Index** — najbardziej "managed", ale osobny cennik i mniej kontroli nad parametrami fuzji.
  - Decyzja do podjęcia na starcie Fazy A0, z jawnym porównaniem kosztu i tego, co dokładnie tracimy/zyskujemy względem hand-rolled Qdrant.
- **Model generacyjny** — ten sam co w głównym torze (`anthropic.claude-haiku-4-5-20251001-v1:0` przez inference profile), żeby porównanie było miarodajne (ta sama warstwa generacji, różna warstwa retrieval).
- **Dane wejściowe** — ten sam dokument testowy co w Fazie 01 głównego toru, żeby dało się porównać jakość/koszt/latencję managed vs hand-rolled na identycznym materiale.

---

## Phase A0 — Setup i decyzja o vector store
- Step 01 — Terraform project dla tego toru: osobny state (nie mieszać z głównym torem Fazy 05), provider AWS, zmienne
- Step 02 — Porównanie kosztowe OpenSearch Serverless vs Aurora Serverless v2 pgvector vs Kendra dla skali PoC (niski ruch, krótki czas testów) — decyzja pisemna w tym pliku (aktualizacja sekcji "Decyzje" powyżej)
- Step 03 — S3 bucket jako data source dla Bedrock Knowledge Base (upload tego samego dokumentu testowego co w głównym torze)
- Step 04 — Test: `terraform validate` + `terraform plan`, bucket istnieje, dokument wgrany

## Phase A1 — Bedrock Knowledge Base: ingestion zarządzany
- Step 01 — IAM rola serwisowa dla Bedrock KB (least-privilege: dostęp do S3 bucketu źródłowego, do modelu embeddingowego, do vector store)
- Step 02 — Utworzenie Knowledge Base (Terraform: `aws_bedrockagent_knowledge_base` + data source), konfiguracja chunkingu (porównanie: fixed-size z głównego toru vs opcje KB — hierarchical/semantic chunking dostępne "z pudełka")
- Step 03 — Uruchomienie sync joba (ingestion), weryfikacja przez AWS Console/API że dokument został zindeksowany
- Step 04 — Test: sync job status = `COMPLETE`, prosty `Retrieve` call zwraca niepuste wyniki

## Phase A2 — Hybrid retrieval przez Bedrock KB API
- Step 01 — Wywołanie `Retrieve` API (hybrid search, jeśli backend to wspiera) z tym samym zestawem pytań testowych co w Fazie 04 głównego toru (semantyczne + z dokładnym identyfikatorem)
- Step 02 — Analiza porównawcza: które parametry fuzji są w ogóle widoczne/konfigurowalne przez Bedrock KB API względem tego, co kontrolowaliśmy ręcznie w Qdrant (`prefetch limit`, `k` w RRF, wybór modelu sparse) — zapis wniosków (to jest materiał na pytanie "co gotowiec ukrywa" z rozmowy technicznej)
- Step 03 — Test: te same pytania testowe co w głównym torze, zapis wyników obok wyników z Fazy 04 głównego toru

## Phase A3 — RetrieveAndGenerate: zarządzany RAG end-to-end
- Step 01 — Wywołanie `RetrieveAndGenerate` API (retrieval + prompt injection + generacja w jednym wywołaniu zarządzanym)
- Step 02 — Konfiguracja custom prompt template (na ile Bedrock KB pozwala nadpisać domyślny prompt injection)
- Step 03 — Test: pełny przepływ pytanie → odpowiedź, porównanie jakości odpowiedzi z głównym torem (Faza 03) na tym samym zestawie pytań

## Phase A4 — Warstwa API: Lambda + API Gateway
- Step 01 — Lambda function wywołująca `RetrieveAndGenerate` (Python, boto3), IAM rola least-privilege (`bedrock:RetrieveAndGenerate` na konkretny ARN KB, nie `*`)
- Step 02 — API Gateway (REST lub HTTP API) jako front, endpoint `/query`
- Step 03 — Test: request przez API Gateway → Lambda → Bedrock KB → odpowiedź, end-to-end

## Phase A5 — Terraform: pełny stack + cykl kosztowy
> Przypomnienie ryzyka kosztowego przed apply: wybrany vector store z Fazy A0 (szczególnie jeśli OpenSearch Serverless — koszt ciągły niezależny od ruchu). Knowledge Base sama w sobie nie generuje kosztu poza zapytaniami, ale backend vector store już tak.
- Step 01 — Konsolidacja modułów z A0–A4 w jeden Terraform root (lub moduły), remote state
- Step 02 — AWS Budget alert dedykowany temu torowi (osobny od głównego toru, żeby było jasne który stack generuje koszt)
- Step 03 — Cykl **apply → test (Fazy A1–A4 na żywo) → destroy** — jawny, `destroy` zawsze wykonywany na koniec sesji testowej tego toru
- Step 04 — Test: `terraform destroy` faktycznie usuwa wszystko, weryfikacja w AWS Console że brak wiszących zasobów (szczególnie OpenSearch Serverless collection, jeśli wybrana)

## Phase A6 — CI/CD dla toru AWS
- Step 01 — Osobny workflow GitHub Actions (albo osobny job w tym samym repo) — `terraform plan` dry-run na PR dotykający `terraform-aws/`
- Step 02 — Job integracyjny on-demand (nie na każdy push — koszt): `apply` → smoke test `/query` przez API Gateway → `destroy` (`if: always()`)
- Step 03 — Test: pełen przebieg na branchu testowym, potwierdzenie że destroy sprząta

---

## Future scope (po zamknięciu A0–A6)
- Phase A7 — Bedrock Guardrails (content filtering) na warstwie generacji
- Phase A8 — Bedrock Knowledge Base evaluation (wbudowana ocena jakości retrieval/generation) — porównanie z ręcznym dowodem z Fazy 04 głównego toru
- Phase A9 — Koszt i latencja: zestawienie liczbowe managed (ten tor) vs self-hosted Qdrant (główny tor) na identycznym zbiorze pytań — to jest materiał na najmocniejszy argument w rozmowie technicznej ("zbudowałem oba, oto różnica")

---

## Status

Nierozpoczęte. Do uruchomienia w osobnej sesji/branchu od głównego toru, po jawnej decyzji, że przechodzimy na pracę praktyczną w AWS zamiast kontynuacji Fazy 02+ głównego toru (Qdrant/RRF).
