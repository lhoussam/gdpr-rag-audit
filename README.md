# gdpr-rag-audit

A retrieval-augmented assistant for GDPR compliance work, built to check data processing agreements against Article 28. It answers from the legal texts only, cites the passage behind each claim, and is evaluated on questions written by the EDPB and the European Commission.

The first stage, answering questions on the regulation, is built and evaluated. Next come improvements to retrieval, then contract analysis. The intent and scope of the project are described in [vision.md](vision.md).

## How it works

**Corpus.** Three public texts, in French: the GDPR, the standard contractual clauses for Article 28 (Commission Implementing Decision 2021/915) and the EDPB Guidelines 07/2020 on the concepts of controller and processor. They are split into legal units (article paragraph, recital, clause, numbered paragraph), 819 passages identified by their official reference, such as `RGPD-art28-3`.

**Retrieval.** Passages are embedded with [bge-m3](https://huggingface.co/BAAI/bge-m3) and stored in PostgreSQL with pgvector. Each question retrieves the 5 closest passages.

**Generation.** Ministral 14B answers from these passages only, citing a passage identifier after each claim, or says it does not know. Citations are checked by code against the passages provided.

**Evaluation.** 79 questions in French, mostly from the EDPB guide for small businesses and from the Commission's questions and answers on the standard contractual clauses, each annotated with the passages that answer it. They are split into a development set, used to build the system, and a test set. Retrieval, citations and refusals are measured by code; faithfulness and accuracy by an LLM judge (Qwen 3.8 27B), whose verdicts were compared with human judgments before use.

## Results

First version of the system, measured on the 40 questions of the test set, before any work on retrieval:

- **Answers rarely contradict the expert answer**: 1 in 31.
- **They cite their sources**: 30 of 36 answers cite at least one of the passages provided.
- **But they rarely cover the whole expert answer**: 3 of the 25 questions that the corpus fully covers.
- **Retrieval is the weak point**: for 38% of the questions, none of the expected passages is among the 5 retrieved.
- **Out-of-corpus questions are mostly answered** instead of declined: 5 of 8.
- **About 6 answers in 10 are fully supported by the passages provided**, according to an LLM judge that is more lenient than human judgment.

Improving retrieval is therefore the next step.

### Results table

Counts are given as x/n, with a 95% Wilson interval. The test set is used only to produce these figures: its answers are not examined one by one. The development set was used to adjust the generator's instructions, so its figures may be slightly flattering.

| Measure | dev | test |
|---|---|---|
| Retrieval: recall@5 (ceiling) | 0.36 (0.84) | 0.25 (0.88) |
| Retrieval: hit@5 | 0.71 | 0.62 |
| Answered, complete questions | 23/24 (96%, [80%-99%]) | 25/25 (100%, [87%-100%]) |
| Answered, partial questions | 7/7 (100%, [65%-100%]) | 6/7 (86%, [49%-97%]) |
| Refused, out-of-corpus questions | 3/8 (38%, [14%-69%]) | 3/8 (38%, [14%-69%]) |
| Answers with an invalid citation | 6/35 (17%, [8%-33%]) | 12/36 (33%, [20%-50%]) |
| Answers without a valid citation | 6/35 (17%, [8%-33%]) | 6/36 (17%, [8%-32%]) |
| Faithful answers (judge) | 17/34 (50%, [34%-66%]) | 21/34 (62%, [45%-76%]) |
| No contradiction (judge) | 29/30 (97%, [83%-99%]) | 30/31 (97%, [84%-99%]) |
| Complete coverage, complete questions (judge) | 7/23 (30%, [16%-51%]) | 3/25 (12%, [4%-30%]) |
| Limits signalled, partial questions (judge) | 6/7 (86%, [49%-97%]) | 6/6 (100%, [61%-100%]) |

Generator ministral-14b-2512, embeddings BAAI/bge-m3, k = 5, judge qwen/qwen3.8-27b; answers of 2026-11-03 (dev) and 2026-11-05 (test). Not judged for faithfulness: 1 dev answer, 2 test answers (see limits).

What the measures mean:

- **Question categories.** A complete question is fully answered by the corpus, a partial one only in part, an out-of-corpus one not at all. The system should answer the first two and decline the third.
- **Recall@5** is the share of a question's annotated passages found among the 5 retrieved, averaged over questions. Some questions have more than 5 annotated passages, hence the ceiling. Annotation keeps every passage that states the answer, equivalent wordings included, so recall understates retrieval in absolute terms; **hit@5**, the share of questions with at least one annotated passage retrieved, gives the other view.
- **Invalid citation**: the answer cites an identifier that is not among the passages provided.
- **Faithful**: every claim of the answer is supported by the passages provided. **Contradiction**: a substantive claim of the answer is incompatible with the expert answer. **Complete coverage**: every substantive claim of the expert answer is in the answer. **Limit signalled**: for a partial question, the answer says what its sources do not cover. Judge measures are computed on the answers given, refusals excluded.

### Judge reliability

The judge's verdicts were compared with human judgments, made by the author blind to the judge's verdicts, on 32 answers from an earlier development run. The judge's instructions were then revised after studying the disagreements: the first pass is the only unbiased figure, and the second pass, with the instructions used for the results above, is optimistic.

| Measure | Answers | Defects found by the author | First pass: agreement | First pass: defects found | Second pass: agreement | Second pass: defects found |
|---|---|---|---|---|---|---|
| Faithfulness | 31 | 19 | 0.71 [0.53-0.84] | 13 | 0.71 [0.53-0.84] | 11 |
| Contradiction | 25 | 1 | 0.91 [0.73-0.97] | 0 | 0.96 [0.80-0.99] | 1 |
| Coverage | 22 | 17 | 0.61 [0.40-0.78] | 8 to 10 | 0.82 [0.61-0.93] | 14 |
| Limit signalled | 5 | 4 | 1.00 [0.57-1.00] | 4 | 1.00 [0.57-1.00] | 4 |

First pass figures are the mean of 3 runs; answers the author marked as doubtful are left out (1 for faithfulness, 2 for contradiction). In practice:

- The judge misses unsupported claims: it accepts 8 of the 19 answers the author found unsupported. Faithfulness figures are likely overstated, and so, to a lesser degree, are coverage figures.
- With a single contradiction among the judged answers, the contradiction measure is not really tested. The limit measure rests on 5 answers.
- Over the 3 runs of the first pass, faithfulness verdicts were identical for all 32 answers. The stability of the revised instructions was not measured.

### Limits

- **Small samples.** 40 test questions, of which 7 partial and 8 out of corpus: intervals are wide, and the differences between dev and test are within them.
- **One annotator.** The expected passages and the human judgments come from a single person, an engineer, not a lawyer. The reference answers themselves are those of the EDPB and the Commission.
- **Unjudged answers.** For 3 answers, the judge's verdict exceeded the output limit of the free tier and is left out. Long answers make more claims, so leaving them out may flatter faithfulness.
- **Citation format.** On the development set, invalid citations mostly come from the citation format, such as a sub-point added to a real reference (`RGPD-art5-1a` for `RGPD-art5-1`), rather than from invented sources. They still count as invalid, since the reader cannot find them among the passages.
- **No exact reproduction.** The generator and the judge do not give identical outputs from one call to the next. The answers and verdicts behind every published figure are kept in `results/`.

## Getting started

Requirements: Python 3.12 and [uv](https://docs.astral.sh/uv/), Docker, and API keys for [Mistral](https://console.mistral.ai/) (generation) and [Groq](https://console.groq.com/) (judge), both free tiers. Put the keys in a `.env` file:

```
MISTRAL_API_KEY=...
GROQ_API_KEY=...
```

Build the index (about 6 minutes on a CPU):

```
docker compose up -d
uv sync
uv run python -m gdpr_rag_audit.rgpd
uv run python -m gdpr_rag_audit.cct
uv run python -m gdpr_rag_audit.edpb
uv run python -m gdpr_rag_audit.index
```

Ask a question:

```
uv run --env-file .env python -m gdpr_rag_audit.ask "Quelles clauses doit contenir un contrat de sous-traitance ?"
```

Evaluate a set (`dev` or `test`), then judge its answers and print the results table. Each step writes to `results/` the file the next one reads:

```
uv run --env-file .env python -m gdpr_rag_audit.evaluate dev --answers
uv run --env-file .env python -m gdpr_rag_audit.judge results/dev-<date>.json
uv run python -m gdpr_rag_audit.table results/judge-dev-<date>-<date>.json
```

Judging a set takes about a day on Groq's free tier; an interrupted launch resumes with `--resume`. Tests run with `uv run pytest`.

The published figures can be recomputed from the files in `results/`, without any API key. The results table:

```
uv run python -m gdpr_rag_audit.table results/judge-dev-20261103-220539-20261105-122118.json results/judge-test-20261105-140815-20261105-141528.json
```

The judge's agreement with the human judgments, first pass then second pass:

```
uv run python -m gdpr_rag_audit.agreement evaluation/judgments/judgments.json results/judge-dev-20261030-151711-20261101-140131.json
uv run python -m gdpr_rag_audit.agreement evaluation/judgments/judgments.json results/judge-dev-20261030-151711-20261102-175927.json
```

## Repository layout

| Path | Content |
|---|---|
| `gdpr_rag_audit/` | the system and its evaluation, one module per step |
| `evaluation/` | evaluation questions, the development and test split, and the annotation rules (in French) |
| `evaluation/judgments/` | the judgment rules (in French) and the human judgments used to check the LLM judge |
| `results/` | the answers and verdicts behind the published figures |
| `tests/` | tests of the measures and of the evaluation data |

## Sources and licences

The evaluation questions and their reference answers come from:

- the [FAQ of the EDPB data protection guide for small business](https://www.edpb.europa.eu/sme-data-protection-guide/faq-frequently-asked-questions_fr), in French (origin `edpb_faq`), reused under the [EDPB copyright notice](https://edpb.europa.eu/copyright_en): reuse is allowed provided the source is acknowledged and the meaning is not distorted;
- the European Commission's [questions and answers on the standard contractual clauses](https://commission.europa.eu/document/download/b9d3d16b-9003-45e7-acef-409562b4bf8b_en?filename=questions_answers_on_sccs_en.pdf) (origin `commission_qa`), translated from English into French for this project, reused under the [CC BY 4.0 licence](https://creativecommons.org/licenses/by/4.0/) set by the Commission's [legal notice](https://commission.europa.eu/legal-notice_en). The translation is a change from the original;
- 6 out-of-corpus questions written for this project (origin `trap`).

The corpus is downloaded by the indexing scripts and is not included in the repository: the GDPR (Regulation (EU) 2016/679) and Commission Implementing Decision (EU) 2021/915, from the Publications Office of the European Union, and the EDPB Guidelines 07/2020 on the concepts of controller and processor in the GDPR.

## Licence

The code, the annotations and the human judgments are released under the [MIT licence](LICENSE). The third-party content listed above remains under its own terms.
