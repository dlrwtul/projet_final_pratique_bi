---
lang: fr
---

# Résumé {.unnumbered}

Ce projet consiste à monter une plateforme de données à partir de la base *Wide World Importers* de Microsoft. Les données sont extraites de SQL Server avec DLT, chargées dans Snowflake, puis transformées avec dbt selon une architecture Médaillon (Bronze, Silver, Gold). Dagster orchestre le tout et lance la chaîne chaque nuit. Une application Streamlit permet ensuite de poser des questions en français sur la couche Gold : un modèle de langage écrit la requête SQL et l'application affiche le résultat. Comme Cortex n'est pas disponible sur un compte d'essai Snowflake, c'est un modèle local (Ollama) qui génère le SQL.

**Mots-clés :** Modern Data Platform, Médaillon, Snowflake, dbt, Dagster, Text-to-SQL.

**Abstract.** This project builds a data platform on Microsoft's *Wide World Importers* database. Data is extracted from SQL Server with DLT, loaded into Snowflake and transformed with dbt into Bronze, Silver and Gold layers, with Dagster running the whole chain every night. A Streamlit application lets users ask questions in French; a language model writes the SQL query, which is checked and run on the Gold layer. Since Cortex is not available on a Snowflake trial account, a local model served by Ollama generates the SQL.

```{=latex}
\tableofcontents
\clearpage
\pagenumbering{arabic}
```

```{=openxml}
<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr><w:r><w:t>Table des matières</w:t></w:r></w:p>
<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \o "1-2" \h \z \u </w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Ouvrez le document dans Word et acceptez la mise à jour des champs pour afficher la table des matières.</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
