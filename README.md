# gdpr-rag-audit

A retrieval-augmented assistant for GDPR compliance work, built to check data processing agreements against Article 28. It answers from the legal texts only, cites the passage behind each claim, and is evaluated on questions written by the EDPB and the European Commission.

The first stage, answering questions on the regulation, is built and evaluated. Next comes contract analysis, then work on the quality of answers. The intent and scope of the project are described in [vision.md](vision.md).

## Example

One example shows the format, not the quality: measured quality is in [Results](#results).

> **Dans quel délai le sous-traitant doit-il notifier une violation de données au responsable du traitement ?**
>
> D'après les extraits fournis, le sous-traitant doit notifier une violation de données à caractère personnel **dans les meilleurs délais après en avoir pris connaissance** :
>
> - [RGPD-art33-2] : *« Le sous-traitant notifie au responsable du traitement toute violation de données à caractère personnel dans les meilleurs délais après en avoir pris connaissance. »*
> - [CCT-clause9.2] : *« En cas de violation de données à caractère personnel en rapport avec des données traitées par le sous-traitant, celui-ci en informe le responsable du traitement **dans les meilleurs délais** après en avoir pris connaissance. »*
>
> Les extraits ne précisent pas de délai fixe (comme 72 heures), mais insistent sur la notion de **délai le plus court possible** pour minimiser les risques pour les droits et libertés des personnes concernées.
>
> **Ce que les extraits ne couvrent pas** :
> - Un délai précis (ex. : 24h, 48h) n'est pas mentionné, contrairement à l'obligation du responsable du traitement envers l'autorité de contrôle (72h max. selon [RGPD-art33-1]).
> - Les modalités pratiques (ex. : point de contact, format) ne sont pas détaillées, bien que [EDPB-07-2020-136] suggère d’inclure ces éléments dans le contrat.

<details>
<summary>Sources cited</summary>

- `CCT-clause9.2`: CCT 2021/915 › Section II (Obligations des parties) › Clause 9 (Notification de violations de données à caractère personnel) › 9.2 (Violation de données en rapport avec des données traitées par le sous-traitant)
- `EDPB-07-2020-136`: EDPB 07/2020 › Partie II (Conséquences de l’attribution des différents rôles) › 1 (Relation entre le responsable du traitement et le sous-traitant) › 1.3 (Forme du contrat ou de l’autre acte juridique) › 1.3.6 (Le sous-traitant doit aider le responsable du traitement à garantir le respect des obligations prévues aux articles 32 à 36 [article 28, paragraphe 3, point f), du RGPD]) › §136
- `RGPD-art33-1`: RGPD › Chapitre IV (Responsable du traitement et sous-traitant) › Section 2 (Sécurité des données à.caractère personnel) › Article 33 (Notification à l'autorité de contrôle d'une violation de données à caractère personnel) › §1
- `RGPD-art33-2`: RGPD › Chapitre IV (Responsable du traitement et sous-traitant) › Section 2 (Sécurité des données à.caractère personnel) › Article 33 (Notification à l'autorité de contrôle d'une violation de données à caractère personnel) › §2

</details>

## How it works

**Corpus.** Three public texts, in French: the GDPR, the standard contractual clauses for Article 28 (Commission Implementing Decision 2021/915) and the EDPB Guidelines 07/2020 on the concepts of controller and processor. They are split into legal units (article paragraph, recital, clause, numbered paragraph), 819 passages identified by their official reference, such as `RGPD-art28-3`.

**Retrieval.** Passages are embedded with [bge-m3](https://huggingface.co/BAAI/bge-m3) and stored in PostgreSQL with pgvector. For each question, the language model first writes a hypothetical passage that would answer it, in the style of the legal texts; the question followed by this text retrieves the 5 closest passages. The hypothetical text only serves the search and is never shown: answers are built from the retrieved passages alone.

**Generation.** Ministral 14B answers from these passages only, citing a passage identifier after each claim, or says it does not know. Citations are checked by code against the passages provided; a citation of a sub-point of a provided passage, such as `RGPD-art5-1a` for `RGPD-art5-1`, is brought back to that passage.

**Evaluation.** 79 questions in French, mostly from the EDPB guide for small businesses and from the Commission's questions and answers on the standard contractual clauses, each annotated with the passages that answer it. They are split into a development set, used to build the system, and a test set. Retrieval, citations and refusals are measured by code; faithfulness and accuracy by an LLM judge (Qwen 3.8 27B), whose verdicts were compared with human judgments before use. How the questions were annotated and split is described in [evaluation/README.md](evaluation/README.md).

## Results

Measured on the 40 questions of the test set:

- **Answers rarely contradict the expert answer**: 1 in 29.
- **They cite their sources**: 33 of 34 answers cite at least one of the passages provided, and 2 cite an identifier outside them.
- **But they rarely cover the whole expert answer**: 1 of the 23 answered questions that the corpus fully covers.
- **Retrieval often misses**: for 28% of the questions, none of the expected passages is among the 5 retrieved.
- **Out-of-corpus questions are mostly answered** instead of declined: 5 of 8.
- **About half of the answers are fully supported by the passages provided** (17 of 32), according to an LLM judge that is more lenient than human judgment.

Contract analysis comes next. Faithfulness is the first improvement planned after it.

### Results table

Counts are given as x/n, with a 95% Wilson interval. The test set is used only to produce these figures: its answers are not examined one by one. The development set was used to adjust the generator's instructions and to choose the retrieval technique, so its figures may be flattering.

| Measure | dev | test |
|---|---|---|
| Retrieval: recall@5 (ceiling) | 0.40 (0.84) | 0.33 (0.88) |
| Retrieval: hit@5 | 0.84 | 0.72 |
| Answered, complete questions | 22/24 (92%, [74%-98%]) | 23/25 (92%, [75%-98%]) |
| Answered, partial questions | 7/7 (100%, [65%-100%]) | 6/7 (86%, [49%-97%]) |
| Refused, out-of-corpus questions | 3/8 (38%, [14%-69%]) | 3/8 (38%, [14%-69%]) |
| Answers with an invalid citation | 0/34 (0%, [0%-10%]) | 2/34 (6%, [2%-19%]) |
| Answers without a valid citation | 1/34 (3%, [1%-15%]) | 1/34 (3%, [1%-15%]) |
| Faithful answers (judge) | 16/33 (48%, [33%-65%]) | 17/32 (53%, [36%-69%]) |
| No contradiction (judge) | 28/29 (97%, [83%-99%]) | 28/29 (97%, [83%-99%]) |
| Complete coverage, complete questions (judge) | 8/22 (36%, [20%-57%]) | 1/23 (4%, [1%-21%]) |
| Limits signalled, partial questions (judge) | 7/7 (100%, [65%-100%]) | 6/6 (100%, [61%-100%]) |

Generator ministral-14b-2512, embeddings BAAI/bge-m3, k = 5, judge qwen/qwen3.8-27b; answers of 2026-11-07 (dev) and 2026-11-08 (test). Not judged for faithfulness: 1 dev answer, 2 test answers (see limits).

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

- **Small samples.** 40 test questions, of which 7 partial and 8 out of corpus: intervals are wide, and most differences between dev and test are within them.
- **One annotator.** The expected passages and the human judgments come from a single person, an engineer, not a lawyer. The reference answers themselves are those of the EDPB and the Commission.
- **Unjudged answers.** For 3 answers, the judge's verdict exceeded the output limit of the free tier and is left out. Long answers make more claims, so leaving them out may flatter faithfulness.
- **Possible leakage.** The hypothetical answer is written by a model that may have read the public sources of the evaluation questions, which could flatter retrieval.
- **No exact reproduction.** The generator, the hypothetical answer and the judge vary from one call to the next, and so do the figures. The answers and verdicts behind every published figure are in `results/`.

## Design choices

- **Retrieval with a hypothetical answer.** Everyday questions and legal texts use different words. It was the only technique tried with a gain beyond run-to-run variation on the development set, where hit@5 rose from 0.74 to 0.84. On the test set, hit@5 went from 0.62 to 0.72 and recall@5 from 0.25 to 0.33, a gain too small to be established on 32 questions. Answer quality showed no measurable change.
- **No reranker.** A cross-encoder gave no gain beyond that variation, at about 15 seconds per question on a CPU.
- **No hybrid search.** Not tried: the diagnosis showed that many failures come from shared words that mislead, which keyword matching would reinforce.
- **Citations repaired by code.** A rule that code can guarantee should not depend on the model following instructions. On the test set, answers with an invalid citation went from 12 of 36 to 2 of 34.
- **k stays at 5.** Recall always rises with k. Only the judge can show whether answers benefit, and the input of the generator and of the judge would double.

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
uv run python -m gdpr_rag_audit.table results/judge-dev-20261107-142120-20261107-143204.json results/judge-test-20261108-115338-20261108-123836.json
```

The figures before the hypothetical answer and the citation repair:

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
