# Introduction {.unnumbered}

Dans une entreprise commerciale, les données de vente sont stockées dans une base transactionnelle faite pour enregistrer des commandes, pas pour les analyser. Pour savoir quels clients rapportent le plus ou comment évoluent les ventes, il faut extraire ces données, les nettoyer et les réorganiser. Et même une fois l'entrepôt construit, un responsable commercial dépend souvent de quelqu'un qui sait écrire du SQL.

Le sujet du projet part de ce constat. Il demande de construire une *Modern Data Platform* sur la base *Wide World Importers* : ingestion avec DLT, stockage dans Snowflake en architecture Médaillon, transformations avec dbt, orchestration avec Dagster. Il demande aussi une application Streamlit qui traduit une question en langage naturel en requête SQL grâce à l'IA.

La question à laquelle nous avons essayé de répondre est donc la suivante : comment automatiser la chaîne qui va de la base source jusqu'à un modèle d'analyse, puis permettre d'interroger ce modèle en français sans connaître SQL ?

Toute la chaîne tourne sur Snowflake. Le chapitre 1 présente rapidement les notions et les outils utilisés. Le chapitre 2 décrit les données et l'architecture. Le chapitre 3 détaille la mise en œuvre avec quelques extraits de code, et le chapitre 4 présente les résultats, les problèmes rencontrés et les limites.
