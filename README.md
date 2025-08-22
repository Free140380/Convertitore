# Convertitore MT ↔ KG (Barre) – Streamlit

App Streamlit per convertire **Metri ↔ Chilogrammi** usando i **kg/m** da un file ODS.

## Struttura
```
convertitore-mt-kg/
├─ app/                          # metti qui il tuo file converti_mt_kg_streamlit.py
├─ data/                         # opzionale: metti qui l'ODS se vuoi tenerlo nel repo
├─ .gitignore
├─ requirements.txt
└─ README.md
```

> NIENTE file ODS e NIENTE script forniti qui: **aggiungi tu** il tuo `converti_mt_kg_streamlit.py` dentro `app/` e, se vuoi, l'ODS dentro `data/`.

## Password (Secrets)
Su Streamlit Cloud → **Settings → Secrets**:
```toml
APP_PASSWORD = "LaTuaPasswordQui"
```

## Esecuzione locale
```bash
pip install -r requirements.txt
streamlit run app/converti_mt_kg_streamlit.py
```

## Deploy su Streamlit Cloud
- Entry point: `app/converti_mt_kg_streamlit.py`
- Aggiungi i **Secrets** (vedi sopra).
