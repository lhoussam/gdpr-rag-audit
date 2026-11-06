# Project vision

> This document describes what the project aims to build and why. What is built so far, and how it performs, is in the [README](README.md).

## The problem

A consultant or a DPO regularly has to check that their clients' data processing agreements comply with Article 28 of the GDPR. This work raises three difficulties:

- **It requires cross-checking several sources.** The text of the GDPR is not enough: knowing whether a clause is sufficient requires knowing the EDPB guidelines and the recommendations of the CNIL.
- **The documents under review cannot be trusted.** The agreement is often drafted by the processor itself, the party that has an interest in it being found compliant.
- **The documents contain personal data.** Sending them as they are to a language model provider goes against the data minimisation principle the consultant is there to enforce.

## What the project builds

An assistant that helps analyse GDPR documents, and that:

1. **Answers questions on the regulation** (GDPR, CNIL, EDPB) from its sources only, citing them precisely, at the level of the article or paragraph.
2. **Will analyse a data processing agreement clause by clause** against Article 28. Each finding will rest on an excerpt of the agreement, quoted word for word and checked.
3. **Will mask the personal data in client documents** before they are sent to a language model provider. The originals stay on the server, so that quotes can still be checked.
4. **Will keep each client's documents apart** in isolated workspaces.
5. **Says when its sources do not answer**, in whole or in part.

## What sets the project apart

### Every choice is measured
The project does not stop at working: it measures how well it works. Retrieval quality, citation accuracy, the ability to decline to answer and, later, the reliability of the agreement analysis are evaluated on dedicated datasets. A technique is added only if it improves a measure.

### Retrieval will be compared with long context
Current models accept very long contexts. The project will therefore compare retrieval-augmented generation with placing the whole corpus in the context, in quality, cost and latency. The comparison will be made at several corpus sizes, to find the point from which retrieval becomes necessary.

### Security will be attacked, defended and measured
The project starts from an explicit threat model, summarised below. Defences will be evaluated before and after they are put in place, and so will their cost, since a defence that degrades answer quality too much is not a good defence.

### The project will be deployed
A containerised API will be deployed on Azure. Continuous integration will run part of the evaluation on each change, and a drop in quality will block the merge.

## Threat model, in brief

| What is protected | Against what |
|---|---|
| The integrity of an agreement analysis | Instructions hidden in the document by its author |
| Confidentiality between clients | An answer drawing on another client's documents |
| Confidentiality of the conversation | Data exfiltration triggered by the content of a document |
| The personal data in the documents | Sending it to external providers when not needed |

The chosen principle is to **favour architectural defences**, which a simple rephrasing cannot get around: citation checks, client isolation at the database level, output sanitisation. Probabilistic detectors come as a complement.

## Sources

The corpus is made of public texts, added in stages:

1. The GDPR, the European Commission's standard contractual clauses for Article 28, and the EDPB guidelines on the concepts of controller and processor.
2. The main EDPB guidelines, the French Data Protection Act and the CNIL guides.
3. Possibly, the CNIL's sanction decisions.

The evaluation questions come from published question-and-answer documents of the EDPB and the European Commission, whose answers, written by experts, serve as references. The agreements analysed during evaluation will be **fictitious** and built for the purpose. No real client document is used.

## Engineering principles

- **Complexity must be justified.** A component enters the project only if it meets an identified need or improves a measure. Simple solutions are preferred as long as they are enough.
- **Deterministic first.** When a check can be done by code rather than by a model, it is done by code.
- **Results can be checked.** Each evaluation records its configuration and its raw outputs, and published figures are generated from these records.
- **Limits are stated.** What the project cannot do or has not tested is written down explicitly.

## Out of scope

- Giving an overall compliance opinion on a document.
- Providing legal advice. The tool supports analysis; it does not replace a lawyer's expertise.
- Letting the assistant act (send messages, call external services).
- Training or fine-tuning a model.
- Processing scanned documents.
- Offering an elaborate interface: a simple demonstration interface is enough.

## Accepted limits

- The evaluation data is annotated by a single person, an engineer, not a lawyer. The questions therefore favour answers that can be checked in the texts.
- Defences will be evaluated against a known set of attacks. An attacker who knew the defences could do better.
