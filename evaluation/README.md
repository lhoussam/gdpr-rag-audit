# Evaluation data

79 questions in French, each with a reference answer written by experts and the passages of the corpus that state it, split into a development set and a test set. Also here: the human judgments used to check the LLM judge.

| File | Content |
|---|---|
| `questions.jsonl` | one question per line: `id`, `origin`, `category`, `question`, `reference_answer`, `passages` |
| `split.json` | the development and test sets, produced by `gdpr_rag_audit/split.py` |
| `annotation-rules.md` | the rules used to annotate passages and categories (in French) |
| `judgments/` | the rules used to judge answers (in French) and the human judgments |

## Questions

| Origin | Questions | Source |
|---|---|---|
| `edpb_faq` | 48 | FAQ of the EDPB data protection guide for small business, in French |
| `commission_qa` | 25 | European Commission's questions and answers on the standard contractual clauses, translated from English with a language model |
| `trap` | 6 | written for this project |

The two sources were chosen because their answers are written by data protection experts: annotating then means checking whether a passage states the expert's answer, which does not require being a lawyer. The traps are questions close to the topics of the corpus but outside it, added to test refusals.

Each question has a category, judged on the reference answer:

| Category | Meaning | Questions |
|---|---|---|
| `complete` | the corpus states every substantive claim of the reference answer | 49 |
| `partial` | at least one substantive claim is missing from the corpus | 14 |
| `out_of_corpus` | the corpus does not answer the question | 16 |

A substantive claim is an obligation, a condition (time limits and exceptions included) or a right. A missing detail, such as a name or a date, leaves a question complete. The system is expected to answer complete and partial questions, saying for partial ones what its sources do not cover, and to decline out-of-corpus questions.

## Annotation

For each complete or partial question, the annotation lists every passage that states a claim of the reference answer, including equivalent wordings (an article and the recital that restates it, for example). Sharing a keyword or a topic is not enough. The rules are in `annotation-rules.md`.

I made all the annotations, with the help of a language model:

1. **Pre-annotation.** A language model proposed a category and passages for each question. Proposals were not limited to the passages the system retrieves, so that the reference does not depend on the retriever under evaluation.
2. **Blind control.** I annotated 10 questions, drawn at random with a fixed seed, without seeing the proposals. I then compared the two annotations and settled each disagreement.
3. **Annotation of the other questions.** The proposals for the other questions were revised to target the defects found in the blind control. I then checked each of them against the text of the passages, keeping, removing and adding passages. I could consult the model in case of doubt; the decision remained mine.
4. **Final review.** I reread my first annotations, a script listed inconsistencies between similar questions, and the model reread the passages I had added. I settled each case.

On the 10 blind questions, compared with the final annotation:

| | Category right | Final passages found | Own passages kept in the final annotation |
|---|---|---|---|
| Mine, blind | 7/10 | 31 of 55 | 31 of 42 |
| Pre-annotation | 10/10 | 31 of 55 | 31 of 34 |

Each pass found about half of the final passages, and each found passages the other missed: 18 were found by both, 13 by me only, 13 by the pre-annotation only, and 11 by neither, added when settling disagreements or at the final review. A single annotation pass therefore misses many equivalent passages, which is why the reference combines both. It may still be incomplete, which would lower recall without the system being at fault.

On the other 68 questions, I kept 209 of the 212 proposed passages, removed 3 and added 67, so that 24% of their final passages come from me; 27 questions were modified, 2 of them changing category.

## Development and test sets

The questions are split in half: 39 for development, 40 for test. Questions whose reference answers largely overlap stay on the same side, so that the test does not repeat what was tuned on development. Categories and origins are balanced between the two sets:

| | complete | partial | out of corpus (of which traps) |
|---|---|---|---|
| dev | 24 | 7 | 8 (3) |
| test | 25 | 7 | 8 (3) |

The split was drawn once, with a fixed seed, and is never redrawn. The development set is used to build and adjust the system, and its failures are analysed one by one. The test set is used only to produce the published figures: its answers are not examined individually.

## Human judgments

To check the LLM judge, I judged the 32 answers given by the system in one development run (`results/dev-20261030-151711.json`): faithfulness for all 32, and accuracy (contradiction, coverage, limit signalled) for the 27 complete or partial questions. I wrote the rules, in `judgments/rules.md`, before judging, and the judge's instructions were derived from them.

- I judged faithfulness first, without the reference answer, then accuracy, with it.
- I judged without any language model and without knowing the judge's verdicts.
- I marked a case the rules do not settle as doubtful (`douteux`), with a note; it is left out of the agreement measure.
- I froze the judgments once complete, even where a disagreement with the judge later suggested an error: correcting only the disagreements would inflate agreement.

The judge's instructions were then revised once, after studying the disagreements, with general corrections only; the figures of both passes are in the [main README](../README.md#judge-reliability). A second judge model, `openai/gpt-oss-120b`, was also tried and set aside, its faithfulness verdicts changing between runs for 10 of 32 answers. On 5 answers, both judges accepted as supported what I had judged unsupported. I left my judgments unchanged, but they may be stricter than the judges on such cases.
