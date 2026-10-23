# Cadre et choix techniques

Ce chapitre présente les notions sur lesquelles repose le projet, puis les outils retenus pour chaque étape de la chaîne.

## De l'entrepôt de données à la Modern Data Platform

L'entrepôt de données classique repose sur une chaîne ETL : les données sont extraites des systèmes sources, transformées sur un serveur intermédiaire, puis chargées dans l'entrepôt sous leur forme finale. Les transformations sont écrites dans un outil dédié et s'exécutent avant le chargement, ce qui rend toute correction coûteuse : il faut relancer l'extraction pour reconstruire une table.

Les entrepôts en nuage ont inversé cet ordre. Le stockage y est bon marché et la puissance de calcul se loue à la demande ; il devient donc raisonnable de charger d'abord les données brutes, puis de les transformer dans l'entrepôt lui-même, en SQL. On parle alors d'ELT. Une *Modern Data Platform* assemble autour de cet entrepôt des outils spécialisés, chacun responsable d'une étape : un outil d'ingestion, un outil de transformation, un orchestrateur et des applications de restitution. Chaque brique peut être remplacée sans reconstruire les autres, ce que nous avons d'ailleurs exploité en passant de DuckDB à Snowflake.

## L'architecture Médaillon

L'architecture Médaillon organise l'entrepôt en trois couches successives, chacune lisant la précédente.

- **Bronze** contient les données telles qu'elles arrivent de la source, sans règle métier. Elle sert de point de reprise : si une transformation est erronée, on la corrige et on la rejoue sans solliciter à nouveau SQL Server.
- **Silver** contient des données nettoyées et typées : colonnes renommées, dates converties, lignes invalides écartées, jointures techniques effectuées.
- **Gold** contient des tables conçues pour l'analyse, ici un schéma en étoile. C'est la seule couche exposée aux utilisateurs et à l'application.

Cette séparation rend chaque étape lisible et testable isolément. Elle permet aussi de limiter les droits : l'application n'a besoin que de lire la couche Gold.

## La modélisation dimensionnelle

La couche Gold suit la modélisation dimensionnelle de Ralph Kimball. Une **table de faits** enregistre des événements mesurables, par exemple une ligne de commande avec sa quantité et son montant. Les **tables de dimensions** décrivent le contexte de ces événements : le client, le produit, le vendeur, la date. Chaque table de faits a un **grain**, c'est-à-dire ce que représente exactement une ligne ; le fixer dès la conception évite les doubles comptes lors des agrégations.

Ce modèle convient particulièrement au Text-to-SQL : un schéma en étoile comporte peu de tables, des noms de colonnes explicites et des jointures simples, ce qui réduit les erreurs du modèle de langage.

## Le Text-to-SQL avec un modèle de langage

Un système Text-to-SQL traduit une question en langage naturel en requête SQL. Avec un grand modèle de langage, la traduction repose sur une consigne (*prompt*) qui contient la description du schéma, quelques règles métier et la question de l'utilisateur. Le modèle n'a pas accès aux données : il ne voit que les noms des tables et des colonnes.

Cette approche comporte trois limites, que l'application doit prendre en compte :

- le modèle peut produire une requête syntaxiquement correcte mais fausse sur le plan métier, par exemple en sommant un montant TTC au lieu du montant hors taxes ;
- il peut produire une requête qui modifie les données si la question s'y prête ;
- sa réponse n'est pas toujours limitée au SQL : il ajoute parfois une explication ou un bloc de code Markdown.

La première limite se réduit en donnant au modèle les définitions métier attendues ; les deux autres imposent de contrôler chaque requête avant de l'exécuter.

## Outils retenus

Le tableau [@tab:outils] résume le rôle de chaque outil dans le projet.

::: {#tab:outils}
Brique              Outil                  Rôle dans le projet
------------------- ---------------------- -------------------------------------------------------------
Source              SQL Server             Héberge la base transactionnelle *WideWorldImporters*
Ingestion           DLT                    Extrait dix tables et les charge dans la couche Bronze
Entrepôt            Snowflake              Stocke les trois couches ; DuckDB en local pendant le développement
Transformation      dbt                    Construit les couches Silver et Gold, exécute les tests
Orchestration       Dagster                Enchaîne DLT et dbt, affiche le lignage, planifie l'exécution
Génération du SQL   Cortex, Ollama         Traduit une question en SQL (Cortex sur Snowflake, sinon modèle local)
Restitution         Streamlit              Application WWI Insight : questions, résultats, dossiers

: Outils de la plateforme et rôle de chacun
:::

Ces outils ont un point commun : leur configuration est du code (Python, SQL ou YAML) versionné avec Git. L'ensemble du projet tient dans un seul dépôt et se reconstruit avec quelques commandes, rappelées en annexe.
