import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from fpdf import FPDF

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="GMAO & Compétences", layout="wide")

# --- INITIALISATION DES VARIABLES (Anti-crash) ---
# On les crée AVANT pour qu'elles existent partout dans le code
df_agents = pd.DataFrame(columns=['Nom', 'Statut'])
df_hab = pd.DataFrame(columns=['Agent', 'Type', 'Date_Peremption'])
df_outils = pd.DataFrame(columns=['ID_Outil', 'Nom', 'Statut', 'Dernier_Controle', 'Periodicite_Mois'])
connexion_ok = False

# --- CONNEXION GOOGLE SHEETS ---
st.title("⚙️ Système Intégré : Compétences & Outillage")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONNEXION DIRECTE (PLAN C) ---
def charger_data(id_onglet):
    # On récupère l'URL de base et on ajoute l'ID de l'onglet (gid)
    # GID : Agents=0, Habilitations=413247074, Outillage=1710929285
    base_url = st.secrets["url_fiche"]
    return pd.read_csv(f"{base_url}{id_onglet}")

try:
    # On utilise les GID (identifiants d'onglets) que j'ai trouvé dans ton fichier
    df_agents = charger_data("0") 
    df_hab = charger_data("413247074")
    df_outils = charger_data("1710929285")
    
    st.success("✅ Connexion directe établie ! Les données sont synchronisées.")
    connexion_ok = True
except Exception as e:
    st.error(f"❌ Erreur de lecture directe : {e}")
    connexion_ok = False
    
# --- FONCTIONS UTILES ---
def calculer_statut_outil(row):
    if pd.isna(row['Dernier_Controle']): return "⚪ Inconnu"
    try:
        dernier = pd.to_datetime(row['Dernier_Controle']).date()
        echeance = dernier + pd.DateOffset(months=int(row['Periodicite_Mois']))
        echeance = echeance.date()
        aujourdhui = date.today()
        jours_restants = (echeance - aujourdhui).days
        
        if row['Statut'] == "NC": return "🔴 NON CONFORME"
        if jours_restants <= 0: return "🔴 EXPIRE"
        
        seuil_alerte = 30 if int(row['Periodicite_Mois']) <= 6 else 90
        if jours_restants <= seuil_alerte:
            return f"🟠 ALERTE ({jours_restants} j)"
        return "🟢 CONFORME"
    except:
        return "❌ Erreur format date"

# Application de la logique outillage si les données existent
if not df_outils.empty and 'Dernier_Controle' in df_outils.columns:
    df_outils['Etat_Alerte'] = df_outils.apply(calculer_statut_outil, axis=1)

# --- INTERFACE MENU ---
menu = ["Tableau de Bord", "Évaluations", "Parc Machine", "Outillage", "Bilan PDF", "Admin"]
choix = st.sidebar.selectbox("Menu", menu)

# --- MODULE 1 : TABLEAU DE BORD ---
if choix == "Tableau de Bord":
    st.header("📊 Cockpit de Pilotage")
    recherche = st.text_input("🔍 Recherche rapide (Agent, Outil, Installation...)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚨 Alertes Habilitations")
        if not df_hab.empty:
            st.dataframe(df_hab, use_container_width=True)
        else:
            st.info("Aucune donnée d'habilitation à afficher.")
        
    with col2:
        st.subheader("⚖️ Comparateur d'Agents")
        if not df_agents.empty:
            liste_agents = df_agents['Nom'].dropna().unique()
            agents_sel = st.multiselect("Sélectionner agents", liste_agents)
            if agents_sel:
                st.write(f"Comparaison de : {', '.join(agents_sel)}")
        else:
            st.write("En attente de la liste des agents...")

# --- MODULE 2 : OUTILLAGE ---
elif choix == "Outillage":
    st.header("🔧 Suivi Réglementaire")
    if not df_outils.empty:
        st.dataframe(df_outils, use_container_width=True)
    else:
        st.info("L'inventaire d'outillage est vide ou inaccessible.")

# --- MODULE 3 : BILAN PDF ---
elif choix == "Bilan PDF":
    st.header("📄 Génération du Rapport")
    if not df_agents.empty:
        agent_pdf = st.selectbox("Choisir l'agent", df_agents['Nom'].unique())
        if st.button("Générer PDF"):
            st.info(f"Préparation du rapport pour {agent_pdf}...")
    else:
        st.error("Impossible de générer un rapport sans données.")
