# Conclusion {.unnumbered}

La chaîne demandée fonctionne de bout en bout : DLT charge dix tables de SQL Server dans Snowflake, dbt construit les couches Silver et Gold et les teste, et Dagster lance le tout chaque nuit en un peu plus de sept minutes. L'application répond aux trois questions du sujet et à des questions libres, en vérifiant chaque requête avant de l'exécuter.

Ce qui nous a pris le plus de temps, ce n'est pas l'écriture des modèles mais les petits problèmes entre les outils : noms renommés par DLT, extension de fichier ignorée par Dagster, propriété des schémas dans Snowflake. Commencer en local avec DuckDB a beaucoup aidé, parce que nous avons pu corriger ces erreurs sans consommer de crédits.

Pour la suite, il faudrait tester Cortex sur un compte payant, préparer un vrai jeu de questions pour évaluer le Text-to-SQL, créer un rôle en lecture seule pour l'application et ajouter les achats et les stocks au modèle.
