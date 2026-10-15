# Route Cost Watch

Route Cost Watch analyzes freight cost per tonne-kilometre by route and
Monday-start week. It flags unusual increases, checks structured operational
notes, and writes candidate rows to `outputs/output.csv`. Code decides the
verdict and matched note; the LLM can only word an explanation for a
deterministically matched note.

## Run

On Windows, install the requirements in the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set `GROQ_API_KEY` in a local `.env` file to use Groq for justified
explanations. `LLM_MODEL` is optional; the default is
`openai/gpt-oss-120b`. Never commit `.env`.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m output_pipeline
.\.venv\Scripts\python.exe .\check_format.py
.\.venv\Scripts\python.exe -m evaluate
.\.venv\Scripts\python.exe -m reproducibility
```

`data/` is not committed. Copy all three input CSVs into it:
`shipment_records.csv`, `context_notes.csv`, and
`sample_output_format_v2.csv`.

The first run may download the local embedding model
`sentence-transformers/all-MiniLM-L6-v2`. If `GROQ_API_KEY` is missing or a
Groq explanation call fails, the pipeline prints a warning and uses a
deterministic explanation for the already-decided justified row.

## Results

The current output contains **20 candidate rows**: **3 justified** and **17
unexplained**.

- **N002 — Ahmedabad-Mumbai**, week of 2025-01-20 (one row).
- **N001 — Chennai-Bangalore**, weeks of 2025-02-24 and 2025-03-03 (two rows).

The CSV header and column order are fixed by `CONTRACT.md`:

```text
route,week_of,cost_per_tonne_km,vs_own_history,vs_similar_routes,flagged,matched_note_id,reason
```

## Decisions

Weekly cost is `sum(freight_cost) / sum(tonnes × km)`. The own-history
baseline is the mean of up to eight preceding route-week rows, strictly before
the current week. The peer baseline is the mean cost of other routes with the
same `route_type` in that week.

A row is a candidate only when its own-history change is positive and either
`vs_own_history >= 10%` or `vs_similar_routes >= 20%`. This requires a
meaningful increase against the route's own past or a larger outlier versus
similar routes, rather than flagging every positive change. All three rows in
`data/sample_output_format_v2.csv` are candidates under this rule. Lowering
the own-history threshold to 5% produces **52 candidates** on the current data.

Verdicts are code-determined: a note must raise costs, apply to the route (or
all routes), and overlap the route-week. N004–N010 do not describe cost rises
and cannot justify a row.

- N003 has only a start date in the source notes. Its one-week default window
  is 2025-05-05 through 2025-05-11. It describes an expected 5–7% increase;
  no route-week beginning 2025-05-05 is a candidate at the default threshold,
  so it does not match an output row.
- N002 describes a “festival week” and has only a start date in the source
  notes. Its window is interpreted as the Monday–Sunday week 2025-01-20 to
  2025-01-26.

## Determinism and LLM cost

The Groq request uses temperature **0** (`config.LLM_TEMPERATURE`). The reproducibility check compares cost values, percentage values, verdicts, and matched note IDs; these were identical across runs. Explanation wording is not compared and can differ between fresh runs: three fresh runs used 823, 825 and 916 output tokens while the verdicts, matched note IDs, and numbers stayed identical.

Latest run (`outputs/p9_token_cost_log.csv`):

| Item                     |                  Value |
| ------------------------ | ---------------------: |
| Uncached LLM calls       |                      3 |
| Input tokens             |                    836 |
| Output tokens            |                    916 |
| Model                    |  `openai/gpt-oss-120b` |
| Input rate used in code  |      $0.15 / 1M tokens |
| Output rate used in code |      $0.60 / 1M tokens |
| Published-rate estimate  |              $0.000675 |
| Actual cost              | $0.00 (Groq free tier) |

Estimate = 836 × $0.15 / 1,000,000 + 916 × $0.60 / 1,000,000.
Confirm current rates on Groq's pricing page before estimating future cost.

## Evaluation

Run `python -m evaluate` in the project environment. The latest run printed:

```text
PASS: numeric checks (3/3)
PASS: hand labels verdict accuracy 20/20; note ID accuracy 3/3; false justified 0
PASS: trap checks (N004-N010, wrong route, wrong window)
PASS: grounding check on every justified output row
```

`eval_labels.csv` has one label for each of the 20 candidate rows. The first 7 were written from the notes' text and the expected cases in my build plan, with AI-assisted tooling. The other 13 were added afterwards and checked against the notes. It is a regression and trap-case set, not a blind independent test.

## Sample output rows

| Route             | Week of    | Cost / tonne-km | Vs own history | Vs peers | Result                                           |
| ----------------- | ---------- | --------------: | -------------: | -------: | ------------------------------------------------ |
| Ahmedabad-Mumbai  | 2025-01-20 |            3.29 |         +29.5% |   +22.5% | No (justified), N002                             |
| Delhi-Jaipur      | 2024-11-11 |            4.17 |         +35.5% |   +21.0% | Yes, unexplained                                 |
| Chennai-Bangalore | 2025-03-10 |            3.57 |         +22.1% |   +33.8% | Yes, unexplained; N001's window ended 2025-03-08 |

## Limitations

- The rolling history counts route-week rows, not calendar weeks. There are
  no calendar gaps in the current data.
- Short and Long route types each have only one peer, so their peer averages
  are based on a single route.
- Mumbai-Pune is above its sole Short-route peer in 102 of 104 shared weeks;
  peer-relative increases for it should be read in that structural context.
- Retrieval proposes the top three notes from a collection of only 10.
  Retrieval does not decide a verdict; route, date, and cost-effect gates do.
- **56 of 728 route-weeks** use fewer than eight prior weeks for their
  own-history baseline.

## File map

- `weekly_metrics.py`, `baselines.py`, `flagging.py`: metrics, baselines, and candidate rule.
- `notes_retrieval.py`, `verdicts.py`, `explanations.py`: note proposals, deterministic verdicts, and grounded explanation text.
- `llm_wrapper.py`: Groq-compatible client, prompt cache, and usage logging.
- `output_pipeline.py`, `CONTRACT.md`: CSV generation and output contract.
- `check_format.py`: output CSV contract validation.
- `evaluate.py`, `eval_labels.csv`: evaluation checks and labeled cases.
- `reproducibility.py`, `repro_check.md`: repeat-run comparison and latest report.
- `notes_structured.json`: structured notes used by the deterministic gate.
- `data/`: shipment records, source notes, and sample output rows.
- `outputs/output.csv`: current candidate output.
