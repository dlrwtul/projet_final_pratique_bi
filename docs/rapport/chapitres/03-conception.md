# Analyse et conception

## Le jeu de données Wide World Importers

*Wide World Importers* est une base d'exemple publiée par Microsoft. Elle décrit un grossiste fictif qui importe et revend des articles de nouveauté et d'emballage (rubans adhésifs, papier bulle, cartons, figurines) à des magasins de jouets et à des particuliers aux États-Unis. La base transactionnelle *WideWorldImporters* est organisée en plusieurs schémas, dont trois nous intéressent :

- `Sales` : clients, commandes, lignes de commande, factures et lignes de facture ;
- `Warehouse` : articles en stock et leurs caractéristiques ;
- `Application` : personnes (dont les vendeurs) et référentiel géographique.

Les commandes couvrent la période de janvier 2013 à mai 2016, soit 41 mois. La base contient 73 595 commandes, 231 412 lignes de commande, 663 clients et 227 articles.

## Besoins d'analyse

La consigne cite trois questions types, que l'application doit traiter :

1. Quels sont les dix meilleurs clients par chiffre d'affaires ?
2. Quel est le montant total des ventes par mois ?
3. Quels produits génèrent le plus de bénéfices ?

Elles imposent trois mesures : le chiffre d'affaires hors taxes, le bénéfice et un découpage par mois. Nous y avons ajouté des questions voisines, utiles pour un responsable commercial : le chiffre d'affaires par année et par vendeur, les produits les plus vendus en quantité, le bénéfice par année et le panier moyen par commande.

Une difficulté apparaît dès la troisième question : le bénéfice n'existe pas dans les commandes. Il n'est calculé qu'au moment de la facturation, dans la colonne `LineProfit` de la table `Sales.InvoiceLines`. Le modèle Gold doit donc comporter deux tables de faits, l'une pour les commandes, l'autre pour les factures.

## Architecture générale

La figure [@fig:architecture] présente l'architecture retenue. DLT extrait les données de SQL Server et les charge dans le schéma `BRONZE` de Snowflake. dbt construit ensuite les vues du schéma `SILVER` et les tables du schéma `GOLD`. Dagster orchestre ces deux étapes et les planifie. L'application Streamlit lit uniquement la couche Gold ; elle délègue la génération du SQL à Snowflake Cortex ou, à défaut, à un modèle local servi par Ollama.

![Architecture de la plateforme](figures/architecture.png){#fig:architecture width=100%}

## Tables sources retenues

Nous n'avons chargé que les tables nécessaires aux analyses visées. Le tableau [@tab:sources] précise l'usage de chacune.

::: {#tab:sources}
Table SQL Server               Usage dans le modèle
------------------------------ -------------------------------------------------------
`Sales.Customers`              Dimension client et ville de livraison
`Sales.Orders`                 En-tête des commandes : date, client, vendeur
`Sales.OrderLines`             Lignes de commande : article, quantité, prix
`Sales.Invoices`               En-tête des factures : date de facturation
`Sales.InvoiceLines`           Lignes de facture : montant facturé et bénéfice
`Warehouse.StockItems`         Dimension produit
`Application.People`           Dimension vendeur (`IsSalesperson = 1`)
`Application.Cities`           Ville de livraison des clients
`Application.StateProvinces`   Référentiel géographique (chargé pour des analyses futures)
`Application.Countries`        Référentiel géographique (chargé pour des analyses futures)

: Tables extraites de *WideWorldImporters*
:::

## Modèle de la couche Gold

La couche Gold suit un schéma en étoile à deux tables de faits, représenté par la figure [@fig:etoile].

- `fct_sales` a pour grain la **ligne de commande**. Elle porte la quantité, le prix unitaire et le chiffre d'affaires hors taxes et toutes taxes comprises.
- `fct_invoice_lines` a pour grain la **ligne de facture**. Elle porte le montant facturé et le bénéfice.

Les deux tables partagent les dimensions `dim_customers`, `dim_products` et `dim_salespeople`. La dimension `dim_date` couvre chaque jour de 2013 à 2016 ; elle se joint aux faits sur la date de commande ou de facturation.

![Schéma en étoile de la couche Gold](figures/etoile.png){#fig:etoile width=95%}

Le chiffre d'affaires est défini comme la somme de `quantity × unit_price`, hors taxes. Nous avons écrit cette définition dans la documentation dbt et dans la consigne transmise au modèle de langage, pour que l'application et un analyste obtiennent le même chiffre.

## Environnements de développement et de production

Le même code s'exécute dans deux environnements. En développement, DLT et dbt écrivent dans un fichier DuckDB local ; en production, ils écrivent dans Snowflake. Le choix se fait uniquement par des variables d'environnement, regroupées dans le tableau [@tab:env].

::: {#tab:env}
Variable             Développement (DuckDB)      Production (Snowflake)
-------------------- --------------------------- ---------------------------
`DLT_DESTINATION`    `duckdb`                    `snowflake`
`DBT_TARGET`         `dev`                       `prod`
`DUCKDB_PATH`        chemin du fichier local     non utilisée
`SF_ACCOUNT`, …      non utilisées               identifiants Snowflake

: Variables d'environnement qui sélectionnent la destination
:::

Ce découplage a deux avantages : il évite de consommer des crédits Snowflake pendant la mise au point, et il permet de tester une modification en local avant de la déployer.
