# Résultats et discussion

## Volumes et qualité des données

La chaîne complète s'exécute sans erreur sur Snowflake. Le tableau [@tab:gold] donne le contenu de la couche Gold après exécution.

::: {#tab:gold}
Table                     Lignes  Contenu
--------------------- ----------  ------------------------------------------
`fct_sales`              231 412  une ligne par ligne de commande
`fct_invoice_lines`      228 265  une ligne par ligne de facture
`dim_date`                 1 461  un jour par ligne, de 2013 à 2016
`dim_customers`              663  clients et ville de livraison
`dim_products`               227  articles en stock
`dim_salespeople`             10  personnes ayant le statut de vendeur

: Contenu de la couche Gold dans Snowflake
:::

Les volumes des tables de faits sont identiques à ceux des tables Bronze correspondantes : 231 412 lignes de commande et 228 265 lignes de facture. Les jointures de la couche Silver n'ont donc ni perdu ni dupliqué de lignes, ce que confirment aussi les tests `unique` sur les clés des faits. Les dix-huit tests de qualité réussissent tous lors de l'exécution de référence.

## Performances

Le tableau [@tab:perf] regroupe les durées mesurées. Celles de la chaîne proviennent de Dagster ; celles de l'application sont enregistrées avec chaque analyse.

::: {#tab:perf}
Opération                                                 Durée
-------------------------------------------------------- -----------
Ingestion DLT des dix tables (chargement initial)         4 min 33 s
Construction et tests dbt (31 nœuds)                      23,28 s
Exécution complète du job `pipeline_complet`              7 min 28 s
Génération du SQL par Ollama (questions libres)           29 à 37 s
Question déjà posée (SQL en cache)                        environ 0,3 s

: Durées mesurées sur la plateforme
:::

L'ingestion représente l'essentiel du temps. Les exécutions suivantes seront plus courtes, puisque les quatre tables de faits ne transfèrent alors que les lignes modifiées. Les transformations dbt sont rapides, même sur le plus petit warehouse Snowflake.

La latence de l'application est dominée par la génération du SQL. Ollama tourne ici sur le processeur d'un ordinateur portable, sans carte graphique : un modèle de sept milliards de paramètres y produit une requête en une trentaine de secondes.

## Réponses aux questions de la consigne

Les trois questions de la consigne ont été posées dans l'application. Les figures de cette section proviennent d'une exécution sur la base DuckDB locale, qui contient les mêmes données que Snowflake ; les montants ont été vérifiés sur les deux.

### Les dix meilleurs clients

Le meilleur client est *Tailspin Toys (Inguadona, MN)*, avec 384 393 \$ de chiffre d'affaires hors taxes sur la période (figure [@fig:q1]). L'écart entre les dix premiers clients est faible, et ils ne représentent ensemble que 3,71 M\$, soit 2,1 % du chiffre d'affaires total de 177,6 M\$. La clientèle de Wide World Importers est donc très dispersée : aucun client ne pèse assez pour mettre l'entreprise en difficulté s'il partait.

![Les dix meilleurs clients par chiffre d'affaires (exécution locale DuckDB)](figures/app_q1_top_clients_graphique.png){#fig:q1 width=95%}

Le tableau de résultat et le SQL exécuté sont accessibles dans deux autres onglets (figure [@fig:q1-sql]).

![Requête exécutée pour la première question](figures/app_q1_top_clients_sql.png){#fig:q1-sql width=95%}

### Les ventes par mois

Les ventes couvrent 41 mois, de janvier 2013 à mai 2016 (figure [@fig:q2]). Le chiffre d'affaires mensuel moyen est de 4,33 M\$. Le mois le plus faible est février 2013 (2,82 M\$) et le plus fort juillet 2015 (5,34 M\$). La tendance est à la hausse : le chiffre d'affaires annuel passe de 46,9 M\$ en 2013 à 51,5 M\$ en 2014 puis 55,8 M\$ en 2015, soit environ 9 % de croissance par an. L'année 2016 n'est couverte que sur cinq mois (23,4 M\$).

![Chiffre d'affaires par mois (exécution locale DuckDB)](figures/app_q2_ventes_mois_graphique.png){#fig:q2 width=95%}

### Les produits les plus rentables

Le bénéfice total s'élève à 85,7 M\$, soit environ 48 % du chiffre d'affaires hors taxes. Les produits les plus rentables sont des articles d'emballage : le papier bulle double face de 20 mm en rouleau de 50 m (5,29 M\$ de bénéfice) et la machine à coussins d'air bleue (4,44 M\$), comme le montre la figure [@fig:q3]. Cette réponse n'était possible qu'avec la seconde table de faits, puisque le bénéfice n'est connu qu'à la facturation.

![Les produits qui génèrent le plus de bénéfice (exécution locale DuckDB)](figures/app_q3_produits_benefice_graphique.png){#fig:q3 width=95%}

## Évaluation du Text-to-SQL

Les huit questions d'exemple ont un SQL écrit et vérifié à la main ; elles ne mesurent donc pas le modèle. Pour les questions libres, nous avons testé un petit nombre de formulations sur Snowflake avec Ollama, par exemple « Les 10 produits les plus vendus ? », présentée au chapitre 3. Sur ces essais, le SQL produit était correct : bonnes tables, bonnes jointures et bonne mesure, avec un résultat identique à celui d'une requête écrite à la main.

Ce constat doit rester prudent. Le nombre de questions testées est trop faible pour donner un taux de réussite, et elles portaient toutes sur des agrégations simples. Une évaluation sérieuse demanderait un jeu d'une cinquantaine de questions avec leur réponse attendue, comparées automatiquement au résultat de l'application. Elle permettrait aussi de mesurer l'effet des règles métier de la consigne (code [@code:prompt]), que nous avons ajoutées par précaution sans en mesurer l'apport.

## Difficultés rencontrées

Le tableau [@tab:difficultes] reprend les principaux problèmes rencontrés et la solution retenue pour chacun.

::: {#tab:difficultes}
---------------------------------------------------------------------------
Problème                           Solution
---------------------------------- ----------------------------------------
Modèles dbt en échec : noms de     Sources dbt avec `identifier` (noms
tables introuvables                normalisés par DLT)

Étape dbt absente de Dagster       Fichier renommé de `defs.yml` en
                                   `defs.yaml`

Dossier nommé `$HOME` créé par     `expandvars` dans le code, `replace`
DuckDB                             dans le profil dbt

*Insufficient privileges* sur les  Schémas créés par `PFPB_ROLE`, ou
schémas Snowflake                  propriété transférée

Avertissements DLT sur les         Colonnes exclues de l'ingestion
colonnes `geography`

Cortex `COMPLETE` refusé sur le    Repli automatique sur Ollama
compte d'essai

Déconnexion à chaque rechargement  Jeton de session dans l'adresse, stocké
de la page                         dans SQLite

Génération lente lors de la        Préchargement du modèle, cache du SQL
première question                  généré
---------------------------------------------------------------------------

Table: Difficultés rencontrées et solutions retenues
:::

## Limites

La solution présente plusieurs limites, dont certaines tiennent aux conditions du projet.

- **Cortex n'a pas pu être utilisé.** Le compte d'essai Snowflake ne donne pas accès à `CORTEX.COMPLETE`. Le code d'appel existe et le rôle dispose du droit `CORTEX_USER`, mais il n'a pas été testé sur un compte payant.
- **La génération locale est lente.** Une trentaine de secondes par question reste acceptable pour une démonstration, pas pour un usage quotidien. Une carte graphique ou un modèle hébergé réduirait ce délai à quelques secondes.
- **L'application utilise un rôle trop large.** Elle se connecte avec `PFPB_ROLE`, qui peut écrire dans les trois schémas. Le filtre `clean_sql` bloque les requêtes d'écriture, mais une protection applicative ne vaut pas un droit refusé par la base. Un rôle dédié, limité à `SELECT` sur `GOLD`, serait nécessaire en production.
- **Le jeton de session apparaît dans l'adresse.** Il peut se retrouver dans l'historique du navigateur ou être partagé par erreur avec un lien. Un cookie sécurisé serait préférable, mais Streamlit ne permet pas d'en poser simplement.
- **L'évaluation du Text-to-SQL est réduite**, comme indiqué plus haut.
- **Le modèle Gold ne garde pas l'historique des dimensions.** Si un client change de ville, l'ancienne valeur est écrasée. Une dimension à variation lente (*snapshot* dbt) corrigerait ce point.
