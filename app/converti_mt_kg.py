#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convertitore MT ↔ KG (Barre) – Streamlit
Sorgente: "PESO SPECIFICO + EXTRA COMPLETO.ods"

- Login con password (APP_PASSWORD in Secrets)
- Ricerca ODS: upload dalla sidebar oppure auto in ./data/ o ./
- Schede supportate: Barra Tonda, Barra Esagonale, Barra Quadra, Barra Tondo forata
- Diametro (e Foro per il forato) a tendina (solo valori reali, niente NaN)
- Kg e Metri si aggiornano automaticamente (last_changed)
- Slider decimali separati per Kg e Metri (0..3; default 0)
"""

from typing import Dict, Tuple, Optional
from pathlib import Path
import math
import pandas as pd
import streamlit as st

# ------------------------- Login -------------------------
st.set_page_config(page_title="Convertitore MT ↔ KG", page_icon="🔁", layout="centered")
st.title("🔁 Convertitore MT ↔ KG (Barre)")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("Accesso")
    pwd = st.text_input("Inserisci password", type="password")
    if st.button("Entra"):
        secret = None
        try:
            secret = st.secrets["APP_PASSWORD"]
        except Exception:
            pass
        if secret and pwd == secret:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Password errata o non configurata nei Secrets.")
    st.stop()

# ------------------------- Utility -------------------------
def to_float(x) -> Optional[float]:
    """Converte stringhe con virgola/spazi in float; ritorna None se non numerico."""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(" ", "")
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def is_number(x) -> bool:
    """True se x è un numero reale (non None e non NaN)."""
    if x is None:
        return False
    try:
        xf = float(x)
        return not math.isnan(xf)
    except Exception:
        return False

def norm(s: str) -> str:
    return (s or "").strip().lower()

def find_sheet_name(all_sheets, keywords):
    """Trova la prima sheet che contiene una keyword (case-insensitive)."""
    normed = {name: norm(name) for name in all_sheets}
    for name, n in normed.items():
        for kw in keywords:
            if kw in n:
                return name
    for name, n in normed.items():
        for kw in keywords:
            if any(tok in n for tok in kw.split()):
                return name
    return None

@st.cache_data(show_spinner=False)
def read_ods_all_sheets(path: str) -> Dict[str, pd.DataFrame]:
    return pd.read_excel(path, sheet_name=None, engine="odf", header=None)

def build_lookup_normale(df: pd.DataFrame) -> Dict[float, float]:
    """Legge col A (misura) e D (kg/m) scartando None/NaN."""
    out = {}
    for _, row in df.iterrows():
        misura = to_float(row.iloc[0])
        kg_m   = to_float(row.iloc[3])
        if is_number(misura) and is_number(kg_m):
            out[float(misura)] = float(kg_m)
    return out

def build_lookup_forata(df: pd.DataFrame) -> Dict[Tuple[float, float], float]:
    """Legge col A (diametro), B (foro), E (kg/m) scartando None/NaN."""
    out = {}
    for _, row in df.iterrows():
        diam = to_float(row.iloc[0])
        foro = to_float(row.iloc[1])
        kg_m = to_float(row.iloc[4])
        if is_number(diam) and is_number(foro) and is_number(kg_m):
            out[(float(diam), float(foro))] = float(kg_m)
    return out

def prepare_maps(dfs: Dict[str, pd.DataFrame]):
    """Mappa: {tipo: lookup} con robustezza sui nomi fogli."""
    SHEET_KEYS = {
        "tonda": ["barra tonda", "tonda", "tondo", "tondo pieno"],
        "esagonale": ["barra esagonale", "esagonale", "esagono"],
        "quadra": ["barra quadra", "quadra", "quadrato"],
        "tondo_forata": ["barra tondo forata", "tondo forato", "barra tonda forata"],
    }
    names = list(dfs.keys())
    m = {"tonda": {}, "esagonale": {}, "quadra": {}, "tondo_forata": {}}
    s = find_sheet_name(names, SHEET_KEYS["tonda"])
    if s: m["tonda"] = build_lookup_normale(dfs[s])
    s = find_sheet_name(names, SHEET_KEYS["esagonale"])
    if s: m["esagonale"] = build_lookup_normale(dfs[s])
    s = find_sheet_name(names, SHEET_KEYS["quadra"])
    if s: m["quadra"] = build_lookup_normale(dfs[s])
    s = find_sheet_name(names, SHEET_KEYS["tondo_forata"])
    if s: m["tondo_forata"] = build_lookup_forata(dfs[s])
    return m

def kg_da_mt(kg_per_m: float, m: float) -> float:
    return (to_float(kg_per_m) or 0.0) * (to_float(m) or 0.0)

def mt_da_kg(kg_per_m: float, kg: float) -> float:
    k = to_float(kg_per_m) or 0.0
    if k == 0:
        return 0.0
    return (to_float(kg) or 0.0) / k

# ------------------------- Sorgente dati (ODS) -------------------------
DEFAULT_ODS_BASENAME = "PESO SPECIFICO + EXTRA COMPLETO.ods"

with st.sidebar:
    st.header("📄 Sorgente dati")
    up = st.file_uploader("Carica l'ODS", type=["ods"])
    ods_path = None
    if up:
        ods_path = "tmp_input.ods"
        with open(ods_path, "wb") as f:
            f.write(up.read())
        st.success("File caricato.")
    else:
        for cand in [Path("data") / DEFAULT_ODS_BASENAME, Path(DEFAULT_ODS_BASENAME)]:
            if cand.exists():
                ods_path = str(cand)
                break
        if ods_path:
            st.caption(f"Uso file: **{ods_path}**")
        else:
            st.error(
                "File ODS non trovato. Caricalo dalla sidebar **oppure** aggiungilo al repo in `data/` "
                f"con nome esatto: `{DEFAULT_ODS_BASENAME}`."
            )
            st.stop()

# Carica tabelle e prepara le mappe
try:
    dfs = read_ods_all_sheets(ods_path)
    maps = prepare_maps(dfs)
except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")
    st.stop()

# ------------------------- Scelta tipo barra + misure -------------------------
tipo_vis = st.selectbox("Tipo di barra", ["Tonda", "Esagonale", "Quadra", "Tondo forato"])
key = {"Tonda": "tonda", "Esagonale": "esagonale", "Quadra": "quadra", "Tondo forato": "tondo_forata"}[tipo_vis]

kg_per_m = None
if key == "tondo_forata":
    if maps["tondo_forata"]:
        # Solo valori reali (niente NaN), unici e ordinati
        diametri = sorted({d for (d, _) in maps["tondo_forata"].keys() if is_number(d)})
        d_sel = st.selectbox("Diametro", options=diametri, index=0)
        fori = sorted({f for (d, f) in maps["tondo_forata"].keys()
                       if is_number(f) and abs(d - float(d_sel)) < 1e-9})
        f_sel = st.selectbox("Foro", options=fori, index=0)
        kg_per_m = maps["tondo_forata"].get((float(d_sel), float(f_sel)))
    else:
        st.warning("Nessun dato disponibile per Tondo forato nel file.")
else:
    misure = sorted([m for m in maps[key].keys() if is_number(m)])
    if misure:
        d_sel = st.selectbox("Diametro", options=misure, index=0)
        kg_per_m = maps[key].get(float(d_sel))
    else:
        st.warning(f"Nessun dato disponibile per {tipo_vis}.")

if kg_per_m is None:
    st.stop()

st.caption(f"Peso specifico scelto: **{kg_per_m} kg/m**")

# ------------------------- Slider decimali separati -------------------------
with st.sidebar:
    st.markdown("---")
    dec_kg = st.slider("Decimali (Kg)", 0, 3, value=0)
    dec_mt = st.slider("Decimali (Metri)", 0, 3, value=0)
    fmt_kg = f"%.{dec_kg}f"
    fmt_mt = f"%.{dec_mt}f"
    step_kg = float(10 ** (-dec_kg)) if dec_kg > 0 else 1.0
    step_mt = float(10 ** (-dec_mt)) if dec_mt > 0 else 1.0

# ------------------------- Campi con aggiornamento automatico -------------------------
if "mt_val" not in st.session_state: st.session_state.mt_val = 0.0
if "kg_val" not in st.session_state: st.session_state.kg_val = 0.0
if "last_changed" not in st.session_state: st.session_state.last_changed = None
if st.session_state.get("do_reset"):
    st.session_state.mt_val = 0.0
    st.session_state.kg_val = 0.0
    st.session_state.last_changed = None
    st.session_state.do_reset = False

# Calcolo PRIMA dei widget
if kg_per_m and kg_per_m > 0:
    if st.session_state.last_changed == "mt":
        st.session_state.kg_val = kg_da_mt(kg_per_m, st.session_state.mt_val)
    elif st.session_state.last_changed == "kg":
        st.session_state.mt_val = mt_da_kg(kg_per_m, st.session_state.kg_val)

def on_change_mt():
    st.session_state.last_changed = "mt"
def on_change_kg():
    st.session_state.last_changed = "kg"

c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    st.number_input("Metri", min_value=0.0, step=step_mt, format=fmt_mt,
                    key="mt_val", on_change=on_change_mt)
with c2:
    st.number_input("Kg", min_value=0.0, step=step_kg, format=fmt_kg,
                    key="kg_val", on_change=on_change_kg)
with c3:
    if st.button("RESET"):
        st.session_state.do_reset = True
        st.rerun()
