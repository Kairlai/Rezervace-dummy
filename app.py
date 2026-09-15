import os
from datetime import datetime
import pandas as pd
import streamlit as st

DB_FILE = "databaze_akci.csv"
DUMMY_ARTIKLY = [
    "00136365",
    "00136615",
    "00136616",
    "20277438",
    "20278622",
    "20279171",
    "20281496",
]

st.set_page_config(
    page_title="Rezervace Dummy Artiklů", layout="wide", page_icon="📅"
)
st.title("📌 Systém pro evidenci a rezervaci Dummy artiklů")


def nacti_databazi():
  if not os.path.exists(DB_FILE):
    df_empty = pd.DataFrame(
        columns=["ID", "Artikl", "Název akce", "Datum Od", "Datum Do", "Filiálka", "KW"]
    )
    df_empty.to_csv(DB_FILE, index=False)

  df = pd.read_csv(DB_FILE, dtype={"Artikl": str})
  if "ID" not in df.columns and not df.empty:
    df.insert(0, "ID", range(1, len(df) + 1))
  return df


def uloz_databazi(df):
  df.to_csv(DB_FILE, index=False)


df_db = nacti_databazi()

col1, col2 = st.columns([1, 1.2])

with col1:
  st.header("📝 Nová rezervace")

  vybrany_artikl = st.selectbox("Číslo Dummy artiklu:", DUMMY_ARTIKLY)
  datum_od = st.date_input("Plánované datum OD:", value=datetime.today())
  datum_do = st.date_input("Plánované datum DO:", value=datetime.today())
  nazev = st.text_input("Nový název artiklu / akce:").strip()
  pobocka = st.text_input("Filiálka:").strip()

  # Kontrola překryvu termínů (překrývají se, pokud StartA <= EndB a EndA >= StartB)
  kolize = pd.DataFrame()
  if not df_db.empty:
    df_temp = df_db.copy()
    df_temp["Datum Od"] = pd.to_datetime(df_temp["Datum Od"]).dt.date
    df_temp["Datum Do"] = pd.to_datetime(df_temp["Datum Do"]).dt.date

    kolize = df_temp[
        (df_temp["Artikl"].astype(str) == str(vybrany_artikl))
        & (df_temp["Datum Od"] <= datum_do)
        & (df_temp["Datum Do"] >= datum_od)
    ]

  # Zobrazení stavu termínu
  if datum_do >= datum_od:
    if not kolize.empty:
      st.error(
          f"⛔ Artikl **{vybrany_artikl}** je v tomto termínu již OBSAZEN!"
      )
      st.caption("Existující rezervace v tomto období:")
      st.dataframe(
          kolize[["Název akce", "Datum Od", "Datum Do", "Filiálka"]],
          use_container_width=True,
          hide_index=True,
      )
    else:
      st.success(f"✅ Artikl **{vybrany_artikl}** je v tomto termínu VOLNÝ.")

  # Tlačítko uložení s kompletní validací
  if st.button("Zapsat do databáze", type="primary"):
    if not nazev or not pobocka:
      st.warning("⚠️ Prosím, vyplňte Název akce i Filiálku.")
    elif datum_do < datum_od:
      st.error("❌ Datum DO nesmí být před datem OD.")
    elif not kolize.empty:
      st.error("❌ Akci nelze uložit! Termín je již obsazen.")
    else:
      kw = datum_od.isocalendar()[1]
      nove_id = 1 if df_db.empty else int(df_db["ID"].max()) + 1

      novy_zaznam = pd.DataFrame([{
          "ID": nove_id,
          "Artikl": str(vybrany_artikl),
          "Název akce": nazev,
          "Datum Od": datum_od.strftime("%Y-%m-%d"),
          "Datum Do": datum_do.strftime("%Y-%m-%d"),
          "Filiálka": pobocka,
          "KW": kw,
      }])

      df_db = pd.concat([df_db, novy_zaznam], ignore_index=True)
      uloz_databazi(df_db)
      st.balloons()
      st.success(f"🎉 Úspěšně zapsáno! Akce: '{nazev}' (KW: {kw})")
      st.rerun()

with col2:
  st.header("📊 Přehled databáze")

  # Filtr podle artiklu
  filtr = st.multiselect(
      "Filtrovat podle artiklu:", options=DUMMY_ARTIKLY, default=[]
  )
  df_view = df_db.copy()
  if filtr:
    df_view = df_view[df_view["Artikl"].astype(str).isin(filtr)]

  st.dataframe(df_view, use_container_width=True, hide_index=True)

  # Sekce pro smazání chybného záznamu
  with st.expander("🗑️ Storno / Smazání rezervace"):
    if not df_db.empty:
      id_smazat = st.number_input(
          "Zadejte ID rezervace ke smazání:",
          min_value=1,
          max_value=int(df_db["ID"].max()),
          step=1,
      )
      if st.button("Smazat záznam", type="secondary"):
        if id_smazat in df_db["ID"].values:
          df_db = df_db[df_db["ID"] != id_smazat]
          uloz_databazi(df_db)
          st.success(f"Rezervace ID {id_smazat} byla odstraněna.")
          st.rerun()
        else:
          st.warning("Zadané ID v databázi neexistuje.")