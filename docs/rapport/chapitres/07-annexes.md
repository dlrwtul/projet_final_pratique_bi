# Annexe : commandes principales {.unnumbered}

```bash
uv sync && source .venv/bin/activate

# Pipeline sur Snowflake
export DLT_DESTINATION=snowflake DBT_TARGET=prod
export SF_ACCOUNT=<compte> SF_USER=<utilisateur> SF_PASSWORD='<mot_de_passe>'
dg list defs          # vérifier les actifs chargés
dg dev                # http://localhost:3000, puis « Materialize all »

# Application
ollama pull qwen2.5-coder:7b
streamlit run presentation_app/app.py      # http://localhost:8501
```
