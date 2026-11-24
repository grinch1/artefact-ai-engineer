# Artefact case checklist

Updated: 24 November 2026. `[x]` means verified, `[ ]` means open. Items marked **partial** have code or documentation but still need an end-to-end check.

## Agent and data (case PDF, page 1)

- [x] Python is the primary language (`agent.py`, `api.py`, `store.py`).
- [x] Text message interface through the web chat and `POST /chat`; CLI also available.
- [x] Store persona and tone specified in the agent instructions and shown in the UI.
- [x] Product, price, stock, active promotion, and order lookup from the supplied CSV snapshot loaded into SQLite.
- [x] A live "all discounted products" question exposed a partial catalog page being treated as a complete promotion list. `search_products` now filters active promotions before pagination, and a response check requires every returned product. The local model listed all 4/4 active discounts in a fresh retest.
- [x] `policies.json` separates PDF-derived `company_policies`, candidate-designed `agent_policies`, and actual `application_rules`; startup checks the PDF hash when the original is present.
- [x] A real-model accessory example redirects without claiming that accessories are sold.
- [x] Compared Qwen 2.5 7B, Qwen3 14B and gpt-oss 20B on the Mainframe. gpt-oss 20B is the selected local model; the hosted model still needs an API-key test.
- [x] The application retrieves structured policy evidence before every model response; section and page are recorded. No fixed policy response replaces model output.
- [x] The independent retrieval evaluator found the expected company section in the top three for 31/31 customer phrasings; unseen wording can still miss.
- [x] A live broad-policy conversation exposed a retrieval gap: generic policy requests returned only the ambiguity section, and an affirmative follow-up returned no section. Broad requests now include the reviewed policy set, follow-ups retain that scope, and the output allowance covers the longer answer. The local model answered the repeated follow-up with policy details; wording still needs review.
- [x] Order lookup requires both order number and matching purchase email; tests cover a mismatch.
- [x] The gpt-oss 20B evaluator has 26 scenarios and repeated fresh runs. Expanded runs scored 51/52 and then 52/52, but manual review found a missed legal-warranty omission in the latter. The stronger check passed 3/3 targeted retests. Broader testing remains open; no production reliability claim is made.
- [x] Static-data and no-live-tracking limits are stated in the UI and README.

## Technical choices and README (case PDF, page 2)

- [x] Explain approach: four allowlisted functions across catalog, orders, and policy domains; SQLite for CSVs and structured retrieval from the versioned policy object (`README.md`).
- [x] Explain provider/model choice and how to configure the API; hosted mode defaults to `gpt-5.4-mini`.
- [x] Explain interface choice (FastAPI plus small HTML/CSS/JavaScript chat) and CLI alternative.
- [x] Explain in-memory conversation history and its reset on restart.
- [x] Explain data preparation, active-promotion filtering, and private data handling.
- [x] Document environment setup and commands for API, CLI, tests, and Docker.
- [x] Document known limitations and what to improve with more time.
- [x] Disclose use of Codex as a coding assistant and the candidate's review responsibility.
- [x] Fresh public clone: installed requirements in a new virtual environment, passed all unit tests, loaded case data, and verified `/health`, `/mode` and `/chat` against the Mainframe model.
- [ ] **Optional production check:** Run the Docker container locally with mounted data; CI already builds the image, but the local Docker daemon was unavailable.

## Demonstration examples (case PDF, page 2)

- [x] Replaced the previous guard transcripts with six genuine gpt-oss 20B responses in `examples.md`, including the corrected full-promotion listing.
- [x] Include a nontrivial case combining an active product promotion and the PIX non-stacking rule, plus an online-return policy case.
- [x] Included model name, prefetched policy sections, model tool calls, and observed limitations.
- [ ] Repeat a representative subset with the paid hosted model before claiming its behavior.

## Repository and quality (case PDF, page 2)

- [x] Public GitHub repository: https://github.com/grinch1/artefact-ai-engineer
- [x] More than one genuine progress commit on `main`; no force push used.
- [x] Twenty-nine unit tests pass locally, including policy provenance, fact-driven numerical guards, broad-policy follow-up routing, promotion listing, retrieval, installments, rounding, and strict tool routing. Previous commits passed GitHub Actions compilation, tests, and Docker build; the current commit needs its own CI check.
- [x] Private case CSVs, internal PDF, ZIP, and API keys are excluded from version control; the reviewed customer-facing `policies.json` is public.
- [ ] Review the final repository contents and README as the candidate before submission.
- [ ] Freeze the repository after the submission date and time; the case explicitly forbids later changes.

## Submission (case PDF, page 3; recruitment email)

- [x] Prepared and visually reviewed a two-page English PDF in Downloads with the repository link, architecture, evidence, and limitations: `Vitor Hugo Moraes da Costa - Senior AI Engineer.pdf`.
- [ ] Submit the PDF through the Google Form from the recruitment email while signed into a Gmail-enabled account.
- [ ] Reply to the original Artefact email with the public repository link, as requested by the case PDF.
- [ ] Verify receipt/submission before **24 November 2026, 23:59, São Paulo time** (second business day after the Saturday email).
- [ ] Record the final commit and submission time; make no subsequent changes to the repository.

The PDF and email give different delivery channels. The planned interpretation is to satisfy both: reply with the repository link and submit the English PDF through the form. If the recruiter clarifies otherwise, update this checklist before submission.

## Next work, in order

1. Candidate reviews the final README, six examples, public repository, and English PDF in Downloads.
2. Submit the English PDF through the Google Form and reply to the original Artefact email with the public repository link by the deadline.
3. Record the submission time and final commit, then freeze the repository. A hosted paid-model comparison is optional future work; do not commit an API key or change this repository after the deadline.
