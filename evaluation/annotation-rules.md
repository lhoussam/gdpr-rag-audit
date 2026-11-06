# Règles d'annotation

## Passages

1. Un passage est retenu s'il énonce une affirmation de la réponse de référence, ou une partie essentielle de celle-ci. Partager un mot-clé ou un sujet ne suffit pas.
2. Test : si le système ne retrouvait que ce passage, pourrait-il donner la réponse ou une partie essentielle ?
3. Un passage peut contenir des informations qui dépassent la réponse. Il reste retenu s'il énonce une de ses affirmations.
4. Seuls comptent les passages qui répondent à la question. Un passage qui n'appuie qu'un exemple de la réponse n'est pas retenu.
5. Une affirmation qui ne s'obtient qu'en combinant plusieurs passages ou en raisonnant en plusieurs étapes ne compte pas. La définition d'un terme employé dans la réponse n'est retenue que si la question demande ce que désigne ce terme.
6. Toutes les formulations équivalentes d'une même affirmation sont retenues : article, considérant, paragraphe des lignes directrices. Pour une réponse en liste, chaque élément est cherché.
7. L'annotation est relative à la réponse de référence : un passage pertinent pour la question mais qui n'énonce aucune affirmation de la réponse n'est pas retenu.

## Catégories

- **Complète** : tout le fond de la réponse est couvert par le corpus.
- **Partielle** : au moins une affirmation de fond (obligation, condition, droit) est absente du corpus. Le système doit répondre sur ce qui est couvert et signaler les limites.
- **Hors corpus** : le corpus ne permet pas de répondre. Le système doit refuser.
- **À écarter** : la question est inutilisable.

Un détail absent du corpus (nom propre, date, constat pratique, motivation) ne rend pas la réponse partielle. La catégorie se juge sur la réponse à la question, sans tenir compte des exemples.

## Exemples

- Règle 3 (FAQ-03, déclaration de confidentialité) : l'art. 13(1) est retenu. Sa phrase d'ouverture énonce l'obligation d'informer lors de la collecte ; la liste détaillée qui suit, absente de la réponse, ne l'exclut pas.
- Règle 4 (FAQ-14, donnée personnelle) : l'art. 4(14) sur les données biométriques n'est pas retenu. La réponse les cite comme exemple, la question porte sur la définition.
- Règle 5 (FAQ-34, enregistrements papier) : l'art. 4(6), définition du « fichier », n'est pas retenu. Il faut le combiner avec l'art. 2(1) pour conclure que le RGPD s'applique au papier. À l'inverse, pour FAQ-40 (qu'est-ce qu'une analyse d'impact ?), les passages qui définissent l'analyse par son contenu sont retenus : la question porte sur ce terme.
- Règle 6 (FAQ-41, bases légales) : pour chaque base de la liste, l'article et le considérant correspondant sont retenus (art. 6(1) d) et considérant 46 pour l'intérêt vital, par exemple).
- Règle 7 (FAQ-30, violation de données) : la clause 9 des clauses types n'est pas retenue. Elle décrit les obligations du sous-traitant, dont la réponse ne parle pas.
- Catégories : FAQ-18 est partielle, car l'obligation d'informer des mesures de sécurité affirmée par la réponse est absente du corpus. FAQ-04 reste complète : seuls les noms des autorités qui ont publié des modèles de contrat manquent.
