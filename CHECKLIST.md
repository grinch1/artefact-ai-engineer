# Artefact case checklist

Updated: 23 November 2026. `[x]` means verified, `[ ]` means open. Items marked **partial** have code or documentation but still need an end-to-end check.

## Agent and data (case PDF, page 1)

- [x] Python is the primary language (`agent.py`, `api.py`, `store.py`).
- [x] Text message interface through the web chat and `POST /chat`; CLI also available.
- [x] Store persona and tone specified in the agent instructions and shown in the UI.
- [x] Product, price, stock, active promotion, and order lookup from the supplied CSV snapshot loaded into SQLite.
- [x] Store policy lookup from the supplied PDF, separate from structured data tools.
- [x] A real-model accessory example redirects without claiming that accessories are sold.
- [x] Compared Qwen 2.5 7B and Qwen3 14B on the Mainframe. Qwen3 14B is the selected local model; the hosted model still needs an API-key test.
- [x] The application retrieves policy PDF evidence before every model response; section and page are recorded. No fixed policy response replaces model output.
- [ ] **Partial:** Evaluate section-level keyword retrieval across paraphrases and ambiguous questions; it can still miss relevant passages.
- [x] Order lookup requires both order number and matching purchase email; tests cover a mismatch.
- [ ] **Partial:** Qwen3 14B answered the selected policy cases in the recorded examples, but a repeated run misstated an alternative installment value. The nine-case suite and manual review do not establish general compliance.
- [x] Static-data and no-live-tracking limits are stated in the UI and README.

## Technical choices and README (case PDF, page 2)

- [x] Explain approach: allowlisted function calls, SQLite for CSVs, keyword retrieval for the eight-page policy manual (`README.md`).
- [x] Explain provider/model choice and how to configure the API; hosted mode defaults to `gpt-5.4-mini`.
- [x] Explain interface choice (FastAPI plus small HTML/CSS/JavaScript chat) and CLI alternative.
- [x] Explain in-memory conversation history and its reset on restart.
- [x] Explain data preparation, active-promotion filtering, and private data handling.
- [x] Document environment setup and commands for API, CLI, tests, and Docker.
- [x] Document known limitations and what to improve with more time.
- [x] Disclose use of Codex as a coding assistant and the candidate's review responsibility.
- [ ] **Partial:** Run the documented steps from a fresh clone with the case data mounted; CI builds the image, but local Docker daemon was unavailable for a container runtime check.

## Demonstration examples (case PDF, page 2)

- [x] Replaced the previous guard transcripts with five genuine Qwen3 14B responses in `examples.md`.
- [x] Include a nontrivial case combining an active product promotion and the PIX non-stacking rule, plus an online-return policy case.
- [x] Included model name, prefetched policy sections, model tool calls, and observed limitations.
- [ ] Repeat a representative subset with the paid hosted model before claiming its behavior.

## Repository and quality (case PDF, page 2)

- [x] Public GitHub repository: https://github.com/grinch1/artefact-ai-engineer
- [x] More than one genuine progress commit on `main`; no force push used.
- [x] The current branch has ten passing unit tests locally, including policy prefetch before both model adapters. Recheck CI after pushing the model change.
- [x] Private case CSVs, internal policy PDF, ZIP, and API keys are excluded from version control.
- [ ] Review the final repository contents and README as the candidate before submission.
- [ ] Freeze the repository after the submission date and time; the case explicitly forbids later changes.

## Submission (case PDF, page 3; recruitment email)

- [ ] Prepare a short English PDF containing the repository link, architecture, evidence, and limitations. Name it `Vitor Hugo Moraes da Costa - Senior AI Engineer.pdf`.
- [ ] Submit the PDF through the Google Form from the recruitment email while signed into a Gmail-enabled account.
- [ ] Reply to the original Artefact email with the public repository link, as requested by the case PDF.
- [ ] Verify receipt/submission before **24 November 2026, 23:59, São Paulo time** (second business day after the Saturday email).
- [ ] Record the final commit and submission time; make no subsequent changes to the repository.

The PDF and email give different delivery channels. The planned interpretation is to satisfy both: reply with the repository link and submit the English PDF through the form. If the recruiter clarifies otherwise, update this checklist before submission.

## Next work, in order

1. Review the Qwen3 14B examples and limits with the candidate; confirm CI for the model-change commit.
2. Configure a hosted paid-model API key later and repeat the scenarios. Do not commit the key.
3. Review from a fresh clone and, if available, run the container with the case data mounted read-only.
4. Draft and inspect the English PDF, then submit through both channels and freeze the repository.
