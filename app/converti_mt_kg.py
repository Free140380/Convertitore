#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit: Convertitore MT <-> KG per barre (Tonda, Esagonale, Quadra, Tondo forato)
Fonte: "PESO SPECIFICO + EXTRA COMPLETO.ods"

- Login con password tramite Streamlit Secrets (APP_PASSWORD) o variabile d'ambiente.
- Campo misura sempre "Diametro" (tendina). Per Tondo forato: Diametro -> Foro.
- Metri e Kg si aggiornano automaticamente (niente tasto Calcola).
- RESET sicuro (nessuna StreamlitAPIException).
- Slider decimali separati per Kg e Metri (0..3, default 0).
- Fix: tutti i numerici dei number_input sono float; filtra NaN dalle misure.
"""

from typing import Dict, Tuple, Optional
import os
import pandas as pd
import streamlit as st

DEFAULT_ODS = "PESO SPECIFICO + EXTRA COMPLETO.ods"

SHEET_KEYWORDS = {
    "tonda": ["barra tonda", "tonda", "tondo", "tondo pieno", "barra tondo"],
    "esagonale": ["barra esagonale", "esagonale", "esagono"],
    "quadra": ["barra quadra", "quadra", "quadrato"],
    "tondo_forata": ["barra tondo forata", "tondo forato", "barra tondo forato", "barra tonda forata", "tonda forata"],
}

# ------------------------- Utility -------------------------
def to_float(x) -> Optional[float]:
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

def _normalize_name(name: str) -> str:
    return (name or "").strip().lower()

def _find_sheet_name(all_sheets, keywords):
    norm = {s: _normalize_name(s) for s in all_sheets}
    # match pieno
    for s, s_norm in norm.items():
        for kw in keywords:
            if kw in s_norm:
                return s
    # fallback su token
    for s, s_norm in norm.items():
        for kw in keywords:
            if any(tok in s_norm for tok in kw.split()):
                return s
    return None

@st.cache_data(show_spinner=False)
def read_ods_all_sheets(path: str) -> Dict[str, pd.DataFrame]:
    return pd.read_excel(path, sheet_name=None, engine="odf", header=None)

def build_lookup_normale(df: pd.DataFrame) -> Dict[float, float]:
    lookup = {}
    for _, row in df.iterrows():
        misura = to_float(row.iloc[0])   # col A
        kg_per_m = to_float(row.iloc[3]) # col D
        if misura is not None and kg_per_m is not None:
            lookup[float(misura)] = float(kg_per_m)
    return lookup

def build_lookup_forata(df: pd.DataFrame) -> Dict[Tuple[float, float], float]:
    lookup = {}
    for _, row in df.iterrows():
        diam = to_float(row.iloc[0])     # col A
        foro = to_float(row.iloc[1])     # col B
        kg_per_m = to_float(row.iloc[4]) # col E
        if diam is not None and foro is not None and kg_per_m is not None:
            lookup[(float(diam), float(foro))] = float(kg_per_m)
    return lookup

def prepare_maps(dfs: Dict[str, pd.DataFrame]):
    all_sheet_names = list(dfs.keys())
    def sheet_for(key): return _find_sheet_name(all_sheet_names, SHEET_KEYWORDS[key])

    maps = {"tonda": {}, "esagonale": {}, "quadra": {}, "tondo_forata": {}}
    s = sheet_for("tonda")
    if s: maps["tonda"] = build_lookup_normale(dfs[s])
    s = sheet_for("esagonale")
    if s: maps["esagonale"] = build_lookup_normale(dfs[s])
    s = sheet_for("quadra")
    if s: maps["quadra"] = build_lookup_normale(dfs[s])
    s = sheet_for("tondo_forata")
    if s: maps["tondo_forata"] = build_lookup_forata(dfs[s])
    return maps

def kg_da_mt(kg_per_m: float, metri: float) -> float:
    return kg_per_m * (metri or 0.0)

def mt_da_kg(kg_per_m: float, kg: float) -> float:
    if not kg_per_m:
        return float("nan")
    return (kg or 0.0) / kg_per_m

# ------------------------- App -------------------------
st.set_page_config(page_title="Convertitore MT ↔ KG", page_icon="🔁", layout="centered")
st.title("🔁 Convertitore MT ↔ KG (Barre)")

# ------------------------- Login / Password -------------------------
# Password letta da Secrets (Streamlit Cloud) o, in locale, da variabile d'ambiente APP_PASSWORD
def _get_password() -> Optional[str]:
    try:
        return st.secrets["APP_PASSWORD"]   # preferito su Cloud
    except Exception:
        return os.getenv("APP_PASSWORD")     # fallback locale

APP_PASSWORD = _get_password()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("Accesso")
    pwd = st.text_input("Inserisci password", type="password")
    col_a, col_b = st.columns([1,3])
    with col_a:
        if st.button("Entra"):
            if APP_PASSWORD and pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.experimental_rerun()
            else:
                st.error("Password errata.")
    st.stop()

# ------------------------- RESET (prima dei widget) -------------------------
if st.session_state.get("do_reset", False):
    st.session_state["mt_val"] = 0.0
    st.session_state["kg_val"] = 0.0
    st.session_state["last_changed"] = None
    st.session_state["do_reset"] = False

# ------------------------- Sidebar -------------------------
with st.sidebar:
    st.header("📄 Sorgente dati")
    uploaded = st.file_uploader("Carica l'ODS", type=["ods"])
    if uploaded:
        ods_path = "tmp_input.ods"
        with open(ods_path, "wb") as f:
            f.write(uploaded.read())
        st.success("File caricato.")
    else:
        ods_path = DEFAULT_ODS
        st.caption(f'Uso: **{DEFAULT_ODS}** (stessa cartella dello script)')

    st.markdown("---")
    # Slider decimali separati (0..3) con default 0
    decimali_kg = st.slider("Decimali visualizzati (Kg)", 0, 3, value=0)
    decimali_mt = st.slider("Decimali visualizzati (Metri)", 0, 3, value=0)
    fmt_kg = f"%.{decimali_kg}f"
    fmt_mt = f"%.{decimali_mt}f"
    step_kg = float(10 ** (-decimali_kg)) if decimali_kg > 0 else 1.0
    step_mt = float(10 ** (-decimali_mt)) if decimali_mt > 0 else 1.0

    st.markdown("---")
    if st.button("Esci (Logout)"):
        st.session_state.authenticated = False
        st.experimental_rerun()

# ------------------------- Carica mappe -------------------------
try:
    dfs = read_ods_all_sheets(ods_path)
    maps = prepare_maps(dfs)
except Exception as e:
    st.error(f"Errore nella lettura del file: {e}")
    st.stop()

tipo = st.selectbox("Tipo di barra", ["Tonda", "Esagonale", "Quadra", "Tondo forato"])
tipo_key = {"Tonda": "tonda", "Esagonale": "esagonale", "Quadra": "quadra", "Tondo forato": "tondo_forata"}[tipo]

# ------------------------- Selettori misura a tendina -------------------------
kg_per_m = None
if tipo_key == "tondo_forata":
    if maps["tondo_forata"]:
        diametri_all = sorted({d for (d, _) in maps["tondo_forata"].keys()})
        diametri = [d for d in diametri_all if d == d]  # filtra NaN
        diametro = st.selectbox("Diametro", options=diametri, index=0 if diametri else None)
        if diametro is not None:
            fori_all = sorted({f for (d, f) in maps["tondo_forata"].keys() if abs(d - float(diametro)) < 1e-9})
            fori = [f for f in fori_all if f == f]      # filtra NaN
            foro = st.selectbox("Foro", options=fori, index=0 if fori else None)
            if foro is not None:
                kg_per_m = maps["tondo_forata"].get((float(diametro), float(foro)))
    else:
        st.warning("Nessun dato disponibile per Tondo forato nel file.")
else:
    misure_all = sorted(maps[tipo_key].keys())
    misure = [m for m in misure_all if m == m]          # filtra NaN
    if misure:
        diametro = st.selectbox("Diametro", options=misure, index=0)
        kg_per_m = maps[tipo_key].get(float(diametro))
    else:
        st.warning(f"Nessun dato disponibile per {tipo}.")

# ------------------------- Calcolo automatico + widget -------------------------
# Stato iniziale (parte sempre da 0)
if "mt_val" not in st.session_state or isinstance(st.session_state.get("mt_val"), str):
    st.session_state.mt_val = to_float(st.session_state.get("mt_val")) or 0.0
if "kg_val" not in st.session_state or isinstance(st.session_state.get("kg_val"), str):
    st.session_state.kg_val = to_float(st.session_state.get("kg_val")) or 0.0
if "last_changed" not in st.session_state:
    st.session_state.last_changed = None

# Calcola PRIMA dei widget (evita StreamlitAPIException)
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
        st.session_state["do_reset"] = True
        st.experimental_rerun()

# Info supporto
if kg_per_m is not None:
    st.caption(f"kg/m: **{kg_per_m}**")
else:
    st.caption("Seleziona una misura per ottenere il kg/m.")

st.markdown("---")
st.caption("Inserisci **Kg** oppure **Metri**: l'altro campo si aggiorna automaticamente. Usa **RESET** per una nuova conversione. L’accesso è protetto da password tramite Secrets.")
