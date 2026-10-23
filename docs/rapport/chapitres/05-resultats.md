# Résultats et limites

## Résultats

Le run complet passe sur Snowflake et les dix-huit tests réussissent. Les tables de faits ont le même nombre de lignes que les tables Bronze d'origine (231 412 lignes de commande et 228 265 lignes de facture), donc les jointures n'ont ni perdu ni dupliqué de lignes.

::: {#tab:volumes}
Couche     Table                          Lignes
---------- ------------------------- -----------
Bronze     `order_lines`                 231 412
Bronze     `invoice_lines`               228 265
Bronze     `orders`                       73 595
Gold       `fct_sales`                   231 412
Gold       `fct_invoice_lines`           228 265
Gold       `dim_date`                      1 461
Gold       `dim_customers`                   663
Gold       `dim_products`                    227
Gold       `dim_salespeople`                  10

: Principaux volumes dans Snowflake
:::

Pour les trois questions du sujet, l'application donne les résultats suivants :

- **Meilleurs clients.** Le premier est *Tailspin Toys (Inguadona, MN)* avec 384 393 \$ de CA HT. Les dix premiers ne font que 3,71 M\$ sur 177,6 M\$ au total (2,1 %) : la clientèle est très dispersée.
- **Ventes par mois.** En moyenne 4,33 M\$ par mois, avec un minimum en février 2013 (2,82 M\$) et un maximum en juillet 2015 (5,34 M\$). Le CA annuel progresse d'environ 9 % par an entre 2013 et 2015.
- **Produits les plus rentables.** Le papier bulle double face 20 mm (5,29 M\$ de bénéfice) puis la machine à coussins d'air bleue (4,44 M\$). Le bénéfice total est de 85,7 M\$.

Côté temps de réponse, le SQL d'une question libre met entre 29 et 37 s à être généré par Ollama, sur un ordinateur portable sans carte graphique. Une question déjà posée répond presque tout de suite (environ 0,3 s) parce que le SQL généré est mis en cache.

Nous n'avons testé qu'un petit nombre de questions libres. Celles que nous avons posées ont donné un SQL correct, mais c'est trop peu pour annoncer un taux de réussite.

## Difficultés rencontrées

::: {#tab:difficultes}
-------------------------------------------------------------------------
Problème                           Solution
---------------------------------- --------------------------------------
Tables introuvables dans dbt       `identifier` dans les sources dbt
(noms renommés par DLT)

Étape dbt absente de Dagster       renommer `defs.yml` en `defs.yaml`

*Insufficient privileges* sur      propriété des schémas donnée à
les schémas Snowflake              `PFPB_ROLE`

Cortex refusé (compte d'essai)     repli sur Ollama
-------------------------------------------------------------------------

: Principales difficultés
:::

## Limites

La solution a plusieurs limites. Cortex n'a pas pu être testé, faute de compte payant. La génération avec Ollama est trop lente pour un usage réel ; il faudrait une carte graphique ou un modèle hébergé. L'application se connecte avec `PFPB_ROLE`, qui a les droits d'écriture : `clean_sql` bloque les requêtes dangereuses, mais il faudrait surtout un rôle en lecture seule sur `GOLD`. Le jeton de session dans l'adresse n'est pas idéal non plus, car il peut être partagé par erreur avec un lien. Enfin, les dimensions ne gardent pas l'historique (si un client change de ville, l'ancienne valeur est perdue).
