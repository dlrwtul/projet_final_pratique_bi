---
lang: fr
---

# Résumé {.unnumbered}

Ce projet met en place une plateforme de données moderne à partir de la base transactionnelle *Wide World Importers* de Microsoft. Les données de SQL Server sont extraites avec DLT et chargées dans Snowflake, où elles sont organisées en trois couches : Bronze pour les données brutes, Silver pour les données nettoyées et Gold pour un modèle en étoile destiné à l'analyse. Les transformations sont écrites avec dbt et vérifiées par dix-huit tests de qualité ; l'ensemble est orchestré par Dagster, qui exécute la chaîne complète en sept minutes et demie et la planifie chaque nuit.

Une application Streamlit permet ensuite d'interroger la couche Gold en français. La question est traduite en SQL par un modèle de langage, la requête est contrôlée puis exécutée, et le résultat est présenté sous forme de graphique et de tableau. Le compte d'essai Snowflake ne donnant pas accès à la fonction Cortex `COMPLETE`, un modèle local servi par Ollama prend le relais, sans modification du reste de l'architecture.

**Mots-clés :** Modern Data Platform, architecture Médaillon, ELT, Snowflake, dbt, Dagster, Text-to-SQL.

# Abstract {.unnumbered}

This project builds a modern data platform on top of Microsoft's *Wide World Importers* transactional database. Data is extracted from SQL Server with DLT and loaded into Snowflake, where it is organised into three layers: Bronze for raw data, Silver for cleaned data and Gold for a star schema designed for analysis. Transformations are written with dbt and checked by eighteen data quality tests; Dagster orchestrates the whole chain, which runs in about seven and a half minutes and is scheduled every night.

A Streamlit application lets users query the Gold layer in French. Each question is translated into SQL by a language model, the query is checked and executed, and the result is shown as a chart and a table. Since the Snowflake trial account does not allow the Cortex `COMPLETE` function, a local model served by Ollama generates the SQL instead, with no change to the rest of the architecture.

**Keywords:** Modern Data Platform, Medallion architecture, ELT, Snowflake, dbt, Dagster, Text-to-SQL.

```{=latex}
\tableofcontents
\listoffigures
\lstlistoflistings
\clearpage
\pagenumbering{arabic}
```

```{=openxml}
<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr><w:r><w:t>Table des matières</w:t></w:r></w:p>
<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \o "1-2" \h \z \u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Ouvrez le document dans Word et acceptez la mise à jour des champs pour afficher la table des matières.</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
