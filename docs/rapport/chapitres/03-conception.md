# Données et conception

## Le jeu de données

*Wide World Importers* est une base d'exemple de Microsoft. Elle simule un grossiste qui vend des articles de nouveauté et d'emballage (adhésifs, papier bulle, figurines…) à des magasins aux États-Unis. Nous avons utilisé les schémas `Sales` (clients, commandes, factures), `Warehouse` (articles) et `Application` (personnes et villes). Les commandes vont de janvier 2013 à mai 2016, soit 41 mois, avec 73 595 commandes et 231 412 lignes de commande pour 663 clients et 227 articles.

Le sujet donne trois questions types : les dix meilleurs clients par chiffre d'affaires, le total des ventes par mois, et les produits qui génèrent le plus de bénéfice. Nous en avons ajouté quelques autres du même genre (CA par année, par vendeur, panier moyen…).

La troisième question pose un petit problème : le bénéfice n'existe pas dans les commandes. On ne le trouve que dans les lignes de facture (`Sales.InvoiceLines.LineProfit`). Le modèle a donc besoin de deux tables de faits.

## Architecture

![Architecture de la plateforme](figures/architecture.png){#fig:architecture width=100%}

La figure [@fig:architecture] résume l'architecture. DLT lit dix tables dans SQL Server et les écrit dans le schéma `BRONZE` de Snowflake. dbt construit ensuite les vues `SILVER` et les tables `GOLD`. Dagster lance les deux étapes l'une après l'autre. L'application ne lit que la couche Gold et passe par Cortex ou, à défaut, par Ollama pour générer le SQL.

## Modèle de la couche Gold

![Schéma en étoile de la couche Gold](figures/etoile.png){#fig:etoile width=85%}

Le modèle (figure [@fig:etoile]) a deux tables de faits :

- `fct_sales`, une ligne par ligne de commande, avec la quantité, le prix et le chiffre d'affaires HT et TTC ;
- `fct_invoice_lines`, une ligne par ligne de facture, avec le montant facturé et le bénéfice.

Elles partagent les dimensions `dim_customers`, `dim_products` et `dim_salespeople`, plus une dimension `dim_date` qui contient chaque jour de 2013 à 2016. Nous avons fixé le chiffre d'affaires comme `quantity × unit_price` hors taxes, et cette définition est reprise à la fois dans la documentation dbt et dans la consigne envoyée au modèle de langage.

Le choix entre DuckDB (développement) et Snowflake (production) se fait seulement par variables d'environnement : `DLT_DESTINATION` pour DLT et `DBT_TARGET` pour dbt.
