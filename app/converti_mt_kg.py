#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit: Convertitore MT ↔ KG per barre (Tonda, Esagonale, Quadra, Tondo forato)
Fonte: "PESO SPECIFICO + EXTRA COMPLETO.ods"
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# =========================
# LOGIN con password
# =========================
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 Convertitore MT ↔ KG (Barre)")
    pwd = st.text_input("Inserisci password", type="password")
    if pwd == st.secrets.get("APP_PASSWORD"):
        st.session_state.authenticated = True
        st.rerun()
    elif pwd:
        st.error("Password errata")
    st.stop()

# =========================
# FUNZIONI LETTURA ODS
# =========================
def read_ods_all_sheets(path):
    return pd.read_excel(path, sheet_name=None, engine="odf")

# =========================
# SELEZIONE FILE ODS
# =========================
DEFAULT_ODS_BASENAME = "PESO SPECIFICO + EXTRA COMPLETO.ods"

with st.sidebar:
    st.header("📄 Sorgente dati")
    uploaded = st.file_uploader("Carica l'ODS", type=["ods"])
    ods_path = None

    if uploaded:
        ods_path = "tmp_input.ods"
        with open(ods_path, "wb") as f:
            f.write(uploaded.read())
        st.success("File caricato.")
    else:
        # cerca in /data e in root
        candidates = [
            Path("data") / DEFAULT_ODS_BASENAME,
            Path(DEFAULT_ODS_BASENAME),
        ]
        for p in candidates:
            if p.exists():
                ods_path = str(p)
                break

        if ods_path:
            st.caption(f"Uso file: **{ods_path}**")
        else:
            st.error(
                "❌ File ODS non trovato.\n\n"
                "➡️ Caricalo dalla sidebar **oppure** aggiungilo al repo in `data/` "
                f"con nome esatto: `{DEFAULT_ODS_BASENAME}`"
            )
            st.stop()

# =========================
# CARICA I DATI
# =========================
dfs = read_ods_all_sheets(ods_path)

# =========================
# UI PRINCIPALE
# =========================
st.title("🔄 Convertitore MT ↔ KG (Barre)")

tipo = st.selectbox("Tipo di barra", list(dfs.keys()))

df = dfs[tipo]

if tipo == "Barra Tondo forata":
    diametro = st.selectbox("Diametro", sorted(df.iloc[:,0].dropna().unique()))
    foro = st.selectbox("Foro", sorted(df.iloc[:,1].dropna().unique()))
    peso_spec = df[
        (df.iloc[:,0]==diametro) & (df.iloc[:,1]==foro)
    ].iloc[0,4]
else:
    diametro = st.selectbox("Diametro", sorted(df.iloc[:,0].dropna().unique()))
    peso_spec = df[df.iloc[:,0]==diametro].iloc[0,3]

st.markdown(f"**Peso specifico scelto:** {peso_spec} kg/m")

# =========================
# CONVERTITORE MT ↔ KG
# =========================
col1, col2 = st.columns(2)

with col1:
    mt_val = st.number_input("Metri", min_value=0.0, step=0.01, format="%.2f", key="mt_val")
with col2:
    kg_val = st.number_input("Kg", min_value=0.0, step=0.01, format="%.2f", key="kg_val")

# logica: aggiorna il campo opposto
if st.session_state.mt_val and not st.session_state.kg_val:
    st.session_state.kg_val = round(st.session_state.mt_val * peso_spec, 2)
elif st.session_state.kg_val and not st.session_state.mt_val:
    st.session_state.mt_val = round(st.session_state.kg_val / peso_spec, 2)

if st.button("RESET"):
    st.session_state.mt_val = 0.0
    st.session_state.kg_val = 0.0
    st.rerun()
