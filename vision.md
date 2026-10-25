# Vision du projet

> Document de cadrage. Il décrit ce que le projet cherche à construire et pourquoi. Les choix techniques détaillés seront documentés au fil de l'avancement.

## Le problème

Un consultant ou un DPO doit régulièrement vérifier que les contrats de sous-traitance de ses clients respectent l'article 28 du RGPD. Ce travail pose trois difficultés :

- **Il demande de croiser plusieurs sources.** Le texte du RGPD ne suffit pas : savoir si une clause est suffisante suppose de connaître les lignes directrices de l'EDPB et les recommandations de la CNIL.
- **Les documents analysés ne sont pas fiables.** Le contrat est souvent rédigé par le sous-traitant lui-même, c'est-à-dire par la partie qui a intérêt à ce qu'il soit jugé conforme.
- **Les documents contiennent des données personnelles.** Les envoyer tels quels à un fournisseur de modèle de langage va à l'encontre du principe de minimisation que le consultant est justement chargé de faire respecter.

## Ce que le projet construit

Un assistant qui aide à analyser des documents RGPD, et qui en particulier :

1. **Répond aux questions sur la réglementation** (RGPD, CNIL, EDPB) en citant précisément ses sources, au niveau de l'article ou du paragraphe.
2. **Analyse un contrat de sous-traitance clause par clause** au regard de l'article 28. Chaque conclusion s'appuie sur un extrait du contrat cité mot pour mot et vérifié.
3. **Sépare les documents de chaque client** dans des espaces de travail isolés.
4. **Sait dire qu'il ne sait pas** quand la réponse n'est pas dans ses sources.

## Ce qui distingue le projet

### Chaque choix est mesuré
Le projet ne se contente pas de fonctionner : il mesure à quel point il fonctionne. La qualité de la recherche, l'exactitude des citations, la capacité à refuser de répondre et la fiabilité de l'analyse des contrats sont évaluées sur des jeux de données construits pour l'occasion. Une technique n'est ajoutée que si elle améliore une mesure.

### Le RAG n'est utilisé que là où il se justifie
Les modèles actuels acceptent des contextes très longs. Le projet compare donc systématiquement la recherche documentaire (RAG) à l'approche qui consiste à tout placer dans le contexte, en qualité, en coût et en latence. La comparaison est faite à plusieurs tailles de corpus pour déterminer à partir de quand le RAG devient nécessaire.

### La sécurité est attaquée, défendue et mesurée
Le projet part d'un modèle de menace explicite, détaillé plus bas. Les défenses sont évaluées avant et après leur mise en place à l'aide d'un outil de red teaming. Leur coût est aussi mesuré, car une défense qui dégrade trop la qualité des réponses n'est pas une bonne défense.

### Le projet est déployé
Une API conteneurisée est déployée sur Azure. L'intégration continue fait tourner une partie de l'évaluation à chaque modification, et une baisse de qualité bloque la fusion.

## Modèle de menace, en résumé

| Ce qu'on protège | Contre quoi |
|---|---|
| L'intégrité de l'analyse d'un contrat | Des instructions cachées dans le document par son rédacteur |
| La confidentialité entre clients | Une réponse qui exploiterait les documents d'un autre client |
| La confidentialité de la conversation | Une exfiltration de données provoquée par le contenu d'un document |
| Les données personnelles des documents | Leur envoi non nécessaire à des fournisseurs externes |

Le principe retenu est de **privilégier les défenses d'architecture**, qui ne se contournent pas par une simple reformulation : vérification des citations, isolation des clients au niveau de la base de données, nettoyage des sorties. Les détecteurs probabilistes viennent en complément.

## Les sources

Le corpus est constitué de textes publics, ajoutés par étapes :

1. Le RGPD, les clauses contractuelles types de la Commission européenne pour l'article 28, et les lignes directrices de l'EDPB sur les notions de responsable de traitement et de sous-traitant.
2. Les principales lignes directrices de l'EDPB, la loi Informatique et Libertés et les guides de la CNIL.
3. Éventuellement, les décisions de sanction de la CNIL.

Les contrats analysés pendant l'évaluation sont **fictifs** et construits pour l'occasion. Aucun document réel de client n'est utilisé.

## Principes d'ingénierie

- **La complexité doit se justifier.** Un composant n'entre dans le projet que s'il répond à un besoin identifié ou s'il améliore une mesure. Les solutions simples sont préférées tant qu'elles suffisent.
- **Le déterministe d'abord.** Quand une vérification peut être faite par du code plutôt que par un modèle, elle est faite par du code.
- **Les résultats sont reproductibles.** Chaque évaluation enregistre sa configuration, et les chiffres publiés sont générés à partir de ces enregistrements.
- **Les limites sont dites.** Ce que le projet ne sait pas faire ou n'a pas testé est écrit explicitement.

## Hors périmètre

- Rendre un avis global de conformité sur un document.
- Fournir un conseil juridique. L'outil est une aide à l'analyse, pas un substitut à l'expertise d'un juriste.
- Permettre à l'assistant d'agir (envoyer des messages, appeler des services externes).
- Entraîner ou ajuster un modèle.
- Traiter des documents scannés.
- Proposer une interface élaborée : une interface simple de démonstration suffit.

## Limites assumées

- Les jeux d'évaluation sont annotés par un ingénieur, pas par un juriste. Les questions privilégient donc les réponses vérifiables dans les textes.
- Les défenses sont évaluées contre un ensemble d'attaques connu. Un attaquant qui connaîtrait les défenses pourrait obtenir de meilleurs résultats.

## État d'avancement

Le projet est en phase de cadrage. Les résultats seront publiés ici au fur et à mesure.
