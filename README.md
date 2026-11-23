# Empório da Música - AI customer service agent

A Python prototype for the Artefact AI Engineer case. A customer sends a text message; the model chooses a read-only tool for catalog, orders, or store policy, then drafts a concise answer in Brazilian Portuguese. A limited offline mode makes the service runnable without an API key.

## Run

The case ZIP provides six CSV files and the internal policy PDF. Keep those files private. Put the `data` directory from the ZIP anywhere on your machine, then point `DATA_DIR` to it. The program needs `products`, `categories`, `promotions`, `orders`, and `customers` CSV files plus the one policy PDF. The `order_items` CSV is not needed for the current scope.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DATA_DIR=/absolute/path/to/case/data
export AGENT_MODE=offline
uvicorn api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the simple chat interface, `http://127.0.0.1:8000/docs` for API documentation, or call:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"demo1","message":"Quais violões estão disponíveis por até R$ 1.000?"}'
```

For the LLM mode, set `AGENT_MODE=openai` and `OPENAI_API_KEY` in the environment. `OPENAI_MODEL` defaults to `gpt-5.4-mini` and can be changed to another model with Responses function calling support. The model API requires internet and may incur charges. No key is stored in the repository. To use the CLI instead: `python agent.py --data-dir "$DATA_DIR" --offline`, or omit `--offline` with a configured API key. `--demo` prints retrieval results without a conversation.

Docker runs the same API, with the private data mounted read-only:

```bash
docker build -t emporio-agent .
docker run --rm -p 8000:8000 -e AGENT_MODE=offline -v "$DATA_DIR:/data:ro" emporio-agent
```

For hosted LLM mode, add `-e AGENT_MODE=openai -e OPENAI_API_KEY` to the `docker run` command. Do not bake the key or customer data into the image.

## Architecture and decisions

`POST /chat` maintains a short in-memory session. A small HTML/CSS/JavaScript interface uses the same endpoint. The LLM uses the Responses API function-calling loop, with three allowlisted, read-only Python tools: `search_products`, `get_order`, and `get_policy`. It cannot execute arbitrary SQL or modify files. At startup, the CSV snapshot is validated and loaded into typed relational SQLite tables in memory. Only promotions flagged active are applied. A promotion price includes its original price and percentage. Order status requires both an order number and matching purchase email; the result omits customer contact details.

The policy PDF is split into pages and retrieved by a transparent keyword score. This avoids external embedding calls for a small eight-page manual and is easy to audit. It is not semantic/vector retrieval and can miss paraphrases. A vector or hybrid index becomes worthwhile if the corpus grows or a retrieval evaluation shows misses. The prototype supports a hosted OpenAI model for evaluation portability, while the local offline mode offers a reproducible fallback. Ollama/Qwen comparison remains an experiment, not a claimed tested feature.

The offline mode is deliberately narrow: it handles common catalog, order, address, return, and accessory requests with fixed templates. It is useful to exercise the data path without a provider; it is not equivalent to LLM reasoning. The LLM mode has not been end-to-end tested without an API key.

The manual has inconsistent phone and email details across sections, so the agent does not volunteer those details. Special holiday hours are unverified. The CSVs are static snapshots, not live inventory or carrier tracking. Sessions are memory-only and reset on restart; this prototype has no authentication or rate limiting and should not be exposed publicly as a production service. The purchase-email check is a demonstration guard, not strong identity verification. Keep customer data local and obtain proper consent and controls before any real deployment.

## Validation and delivery

Run `python -m unittest discover -s tests -v`. GitHub Actions checks Python compilation, tool behavior on synthetic records, and Docker build on pushes and pull requests. A production CD job would need a target environment and deployment credentials; this repository deliberately does not invent one or claim a deployment.

The case PDF requests a public GitHub link by replying to the email, while the recruitment email asks for a PDF through a Google Form by the end of 24 November 2026 (São Paulo time). Our delivery interpretation is to provide the repository link in the reply and a short English PDF with that link through the form, subject to recruiter clarification. Do not change the repository after submission.

See [examples.md](examples.md) for five reproducible offline interactions. AI assistance: Codex helped inspect the case, implement the prototype, and draft documentation; the candidate must review the behavior, decisions, and final submission. With more time: verify actual LLM responses, add semantic retrieval evaluation, test Ollama and a second hosted provider, improve identity verification, and add safe deployment controls.
