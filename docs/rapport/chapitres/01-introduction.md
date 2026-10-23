# Introduction générale {.unnumbered}

Une entreprise de distribution enregistre chaque jour des commandes, des factures, des mouvements de stock et des paiements. Ces données sont stockées dans des bases transactionnelles conçues pour enregistrer rapidement des opérations, et non pour répondre à des questions d'analyse. Savoir quels clients rapportent le plus, comment évoluent les ventes d'un mois à l'autre ou quels produits dégagent la meilleure marge suppose de rassembler les données, de les nettoyer et de les réorganiser. En pratique, ce travail repose souvent sur une équipe technique, et un responsable commercial doit attendre qu'un analyste écrive la requête SQL dont il a besoin.

Deux évolutions récentes changent cette situation. D'une part, les plateformes de données en nuage comme Snowflake séparent le stockage du calcul et permettent de charger les données brutes avant de les transformer sur place ; c'est l'approche ELT (*Extract, Load, Transform*). Des outils spécialisés couvrent chaque étape : DLT pour l'ingestion, dbt pour les transformations, Dagster pour l'orchestration. D'autre part, les grands modèles de langage savent désormais produire une requête SQL à partir d'une question formulée en langage naturel, ce qui ouvre l'accès aux données à des utilisateurs qui ne connaissent pas SQL.

## Problématique {.unnumbered}

Le projet répond à la question suivante : comment concevoir une plateforme qui automatise l'ingestion, la transformation et la modélisation des données d'une base transactionnelle, puis qui permet de les interroger en français, de façon fiable et sans connaissance de SQL ?

## Objectifs {.unnumbered}

L'objectif est de construire une chaîne complète sur la base *Wide World Importers* de Microsoft. Concrètement, il s'agit :

- d'extraire automatiquement les données de SQL Server et de les charger dans Snowflake avec DLT ;
- d'organiser l'entrepôt selon une architecture Médaillon, en trois couches Bronze, Silver et Gold ;
- d'écrire les transformations avec dbt, en les documentant et en les testant ;
- d'orchestrer et de planifier l'ensemble avec Dagster ;
- de développer une application Streamlit qui traduit une question en SQL avec un modèle de langage et affiche le résultat.

## Démarche et organisation du rapport {.unnumbered}

Nous avons d'abord développé toute la chaîne sur une base DuckDB locale, gratuite et sans configuration, avant de basculer vers Snowflake en changeant uniquement des variables d'environnement. Ce choix a permis de corriger rapidement les modèles dbt et l'application sans consommer de crédits.

Le chapitre 1 présente les notions et les outils sur lesquels repose le projet. Le chapitre 2 décrit le jeu de données, les besoins d'analyse et l'architecture retenue. Le chapitre 3 détaille la mise en œuvre de chaque brique, en s'appuyant sur des extraits du code du projet. Le chapitre 4 présente les résultats obtenus, les difficultés rencontrées et les limites de la solution. La conclusion dresse le bilan du projet et propose des suites possibles.
