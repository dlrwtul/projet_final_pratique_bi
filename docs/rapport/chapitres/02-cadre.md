# Notions et outils

## ELT et Modern Data Platform

Dans un entrepôt classique (ETL), les données sont transformées avant d'être chargées. Avec les entrepôts cloud comme Snowflake, le stockage coûte peu et la puissance de calcul se loue à la demande. On charge donc d'abord les données brutes, puis on les transforme directement dans l'entrepôt en SQL : c'est l'approche ELT. Une Modern Data Platform regroupe autour de l'entrepôt plusieurs outils spécialisés, un par étape, que l'on peut remplacer séparément.

## Architecture Médaillon

L'architecture Médaillon découpe l'entrepôt en trois couches. **Bronze** garde les données telles qu'elles arrivent de la source. **Silver** contient les données nettoyées : colonnes renommées, types corrigés, jointures techniques. **Gold** contient le modèle destiné à l'analyse. L'intérêt principal est de pouvoir corriger une transformation et la relancer sans avoir à réinterroger la source.

Pour la couche Gold, nous avons utilisé la modélisation en étoile de Kimball : des tables de faits qui enregistrent des événements chiffrés (une ligne de commande, une ligne de facture) et des dimensions qui les décrivent (client, produit, vendeur, date). Ce type de schéma, avec peu de tables et des noms explicites, est aussi plus facile à interroger pour un modèle de langage.

## Text-to-SQL

Le principe est d'envoyer à un modèle de langage une consigne qui contient la description des tables et la question de l'utilisateur, et de lui demander la requête SQL correspondante. Le modèle ne voit pas les données, seulement les noms des tables et des colonnes. Il peut se tromper sur le sens métier (prendre un montant TTC au lieu du HT, par exemple), ajouter du texte autour de la requête, ou même proposer une requête qui modifie les données. Il faut donc lui donner les définitions importantes et contrôler la requête avant de l'exécuter.

## Outils utilisés

::: {#tab:outils}
Étape               Outil               Utilisation dans le projet
------------------- ------------------- ----------------------------------------------
Source              SQL Server          base *WideWorldImporters*
Ingestion           DLT                 chargement de dix tables dans Bronze
Entrepôt            Snowflake           couches Bronze, Silver et Gold
Transformation      dbt                 modèles Silver et Gold, tests
Orchestration       Dagster             enchaînement, lignage, planification
Génération SQL      Cortex / Ollama     traduction question → SQL
Restitution         Streamlit           application WWI Insight

: Outils utilisés
:::
