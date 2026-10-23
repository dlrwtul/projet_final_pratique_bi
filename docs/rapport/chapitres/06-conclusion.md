# Conclusion générale {.unnumbered}

Ce projet avait pour but de construire une plateforme de données complète, de la base transactionnelle jusqu'à une application interrogeable en français. La chaîne fonctionne de bout en bout sur Snowflake : DLT charge dix tables de *WideWorldImporters* dans la couche Bronze, dbt construit sept vues Silver et six tables Gold vérifiées par dix-huit tests, et Dagster enchaîne ces étapes en un peu plus de sept minutes, chaque nuit à 2 h. L'application WWI Insight répond aux trois questions de la consigne et à des questions libres, en contrôlant chaque requête avant de l'exécuter.

Trois choix ont particulièrement compté. Le développement sur DuckDB a permis de mettre au point les modèles et l'application sans dépenser de crédits, puis de passer à Snowflake en changeant seulement des variables d'environnement. Le modèle en étoile à deux tables de faits a résolu la question du bénéfice, qui n'existe qu'à la facturation, et il a donné au modèle de langage un schéma simple à interroger. Enfin, la sélection automatique du moteur de génération a permis de contourner l'absence de Cortex sur le compte d'essai sans toucher au reste de l'architecture.

Le projet nous a aussi appris que les difficultés se trouvent souvent entre les outils plutôt que dans chacun d'eux : noms de tables normalisés par DLT, extension de fichier ignorée par Dagster, propriété des schémas dans Snowflake, variables d'environnement non interprétées. Aucun de ces problèmes n'était complexe, mais chacun bloquait la chaîne entière.

## Perspectives {.unnumbered}

Plusieurs suites sont envisageables :

- utiliser Cortex sur un compte Snowflake payant et comparer ses requêtes à celles d'Ollama ;
- constituer un jeu d'évaluation d'une cinquantaine de questions avec leur réponse attendue, pour mesurer la qualité du Text-to-SQL ;
- créer un rôle Snowflake en lecture seule sur `GOLD` pour l'application ;
- historiser les dimensions clients et produits avec les *snapshots* de dbt ;
- étendre le modèle aux achats et aux stocks, présents dans la base source mais non chargés ;
- déployer l'application et Dagster sur un serveur, avec une authentification par cookie plutôt que par l'adresse.
