import base64
from datetime import datetime
import io
import os
import pandas as pd
import requests
import streamlit as st

FILE_PATH = "databaze_akci.csv"
DUMMY_ARTIKLY = [
   "00136365",
    "00136615",
    "00136616",
    "20277438",
    "20278622",
    "20279171",
    "20281496",
    "20281563",
    "20281565",
    "20817752",
    "20847344",
]

# Načtení klíčů ze Secrets (pokud chybí, běží v lokálním režimu)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")

st.set_page_config(
    page_title="Rezervace Dummy Artiklů", layout="wide", page_icon="📅"
)

# Úprava pozadí a stylování pro perfektní čitelnost
st.markdown(
    """
    <style>
    /* Hlavní pozadí s obrázkem */
    .stApp {
        background-image: url("https://images.t-online.de/2026/01/EFMxUbVUxzcI/0x638:1080x607/fit-in/1080x0/image.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    
    /* Celková ztmavovací vrstva pro potlačení rušivých prvků */
    .stApp::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(0, 0, 0, 0.45);
        z-index: -1;
    }

    /* Poloprůhledné tmavé karty pro formulář a přehled (Glassmorphism) */
    div[data-testid="stColumn"] {
        background: rgba(15, 20, 28, 0.88);
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(8px);
    }

    /* Zářivě bílá barva a stín pro všechny nadpisy i popisky polí */
    h1, h2, h3, label, p, span, .stMarkdown {
        color: #ffffff !important;
        text-shadow: 1px 1px 4px rgba(0, 0, 0, 0.9);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📌 Systém pro evidenci a rezervaci Dummy artiklů")


def get_headers():
  return {
      "Authorization": f"token {GITHUB_TOKEN}",
      "Accept": "application/vnd.github.v3+json",
  }


def nacti_databazi():
  # Lokální běh na PC bez GitHubu
  if not GITHUB_TOKEN or not GITHUB_REPO:
    if not os.path.exists(FILE_PATH):
      df_empty = pd.DataFrame(
          columns=[
              "ID",
              "Artikl",
              "Název akce",
              "Datum Od",
              "Datum Do",
              "Filiálka",
              "KW",
          ]
      )
      df_empty.to_csv(FILE_PATH, index=False)
    df = pd.read_csv(FILE_PATH, dtype={"Artikl": str})
    if "ID" not in df.columns and not df.empty:
      df.insert(0, "ID", range(1, len(df) + 1))
    return df, None

  # Načtení souboru z GitHubu přes API
  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
  res = requests.get(url, headers=get_headers())

  if res.status_code == 200:
    data = res.json()
    sha = data["sha"]
    content_str = base64.b64decode(data["content"]).decode("utf-8")
    df = pd.read_csv(io.StringIO(content_str), dtype={"Artikl": str})
    if "ID" not in df.columns and not df.empty:
      df.insert(0, "ID", range(1, len(df) + 1))
    return df, sha
  else:
    df_empty = pd.DataFrame(
        columns=[
            "ID",
            "Artikl",
            "Název akce",
            "Datum Od",
            "Datum Do",
            "Filiálka",
            "KW",
        ]
    )
    return df_empty, None


def uloz_databazi(df, sha=None):
  if not GITHUB_TOKEN or not GITHUB_REPO:
    df.to_csv(FILE_PATH, index=False)
    return True

  url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
  csv_buffer = io.StringIO()
  df.to_csv(csv_buffer, index=False)
  content_b64 = base64.b64encode(csv_buffer.getvalue().encode("utf-8")).decode(
      "utf-8"
  )

  payload = {
      "message": "Aktualizace rezervací přes webovou aplikaci",
      "content": content_b64,
  }
  if sha:
    payload["sha"] = sha

  res = requests.put(url, headers=get_headers(), json=payload)
  return res.status_code in [200, 201]


# Načtení dat při startu
df_db, current_sha = nacti_databazi()

col1, col2 = st.columns([1, 1.2])

with col1:
  st.header("📝 Nová rezervace")

  vybrany_artikl = st.selectbox("Číslo Dummy artiklu:", DUMMY_ARTIKLY)
  datum_od = st.date_input("Plánované datum OD:", value=datetime.today())
  datum_do = st.date_input("Plánované datum DO:", value=datetime.today())
  nazev = st.text_input("Nový název artiklu / akce:").strip()
  pobocka = st.text_input("Filiálka:").strip()

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

  if datum_do >= datum_od:
    if not kolize.empty:
      st.error(
          f"⛔ Artikl **{vybrany_artikl}** je v tomto termínu již OBSAZEN!"
      )
      st.dataframe(
          kolize[["Název akce", "Datum Od", "Datum Do", "Filiálka"]],
          use_container_width=True,
          hide_index=True,
      )
    else:
      st.success(f"✅ Artikl **{vybrany_artikl}** je v tomto termínu VOLNÝ.")

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

      df_novy = pd.concat([df_db, novy_zaznam], ignore_index=True)

      if uloz_databazi(df_novy, current_sha):
        st.balloons()
        st.success(f"🎉 Úspěšně zapsáno a trvale uloženo!")
        st.rerun()
      else:
        st.error(
            "❌ Chyba při zápisu na GitHub. Zkontrolujte nastavení Secrets."
        )

with col2:
  st.header("📊 Přehled databáze")

  filtr = st.multiselect(
      "Filtrovat podle artiklu:", options=DUMMY_ARTIKLY, default=[]
  )
  df_view = df_db.copy()
  if filtr:
    df_view = df_view[df_view["Artikl"].astype(str).isin(filtr)]

  st.dataframe(df_view, use_container_width=True, hide_index=True)

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
          df_upraveno = df_db[df_db["ID"] != id_smazat]
          if uloz_databazi(df_upraveno, current_sha):
            st.success(f"Rezervace ID {id_smazat} byla odstraněna.")
            st.rerun()
          else:
            st.error("❌ Chyba při mazání z GitHubu.")
        else:
          st.warning("Zadané ID v databázi neexistuje.")
