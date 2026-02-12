import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from fpdf import FPDF

# --- CONFIGURATION PAGE ---
st.set_page_config(page_title="GMAO & Compétences", layout="wide")

# --- CONNEXION GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- INITIALISATION DES VARIABLES (Anti-crash) ---
# On crée des tableaux vides pour que l'app affiche "0 résultats" au lieu de planter
df_agents = pd.DataFrame(columns=['Nom', 'Statut'])
df_hab = pd.DataFrame(columns=['Agent', 'Type', 'Date_Peremption'])
df_outils = pd.DataFrame(columns=['ID_Outil', 'Nom', 'Statut', 'Dernier_Controle', 'Periodicite_Mois'])
connexion_ok = False

# --- BLOC DE DIAGNOSTIC ET CHARGEMENT ---
st.title("⚙️ Système Intégré : Compétences & Outillage")

try:
    # 1. Test du Secret
    url_test = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    if len(url_test) < 80:
        st.error(f"⚠️ URL TRONQUÉE : Votre lien dans les Secrets ne fait que {len(url_test)} caractères. Il est probablement coupé par un retour à la ligne.")
    
    # 2. Tentative de lecture
    df_agents = conn.read(worksheet="Agents")
    df_hab = conn.read(worksheet="Habilitations")
    df_outils = conn.read(worksheet="Outillage")
    
    st.success("✅ Connexion réussie : Données chargées depuis Google Sheets.")
    connexion_ok = True

except Exception as e:
    st.error(f"❌ Erreur technique : {e}")
    st.warning("Mode Consultation Seule : L'application utilise des données vides. Vérifiez l'URL dans vos Secrets.")

# --- FONCTIONS UTILES ---
def alerte_habilitation(date_peremption):
    if pd.isna(date_peremption): return "⚪ Inconnu"
    aujourdhui = date.today()
    # Logique Septembre N pour expiration N+1
    if aujourdhui.month >= 9 and date_peremption.year == aujourdhui.year + 1:
        return "🟠 Planification N+1"
    if date_peremption <= aujourdhui:
        return "🔴 Périmé"
    return "🟢 Valide"

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

# Application de la logique outillage
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
            st.dataframe(df_hab)
        else:
            st.info("Aucune habilitation enregistrée.")
        
    with col2:
        st.subheader("⚖️ Comparateur d'Agents")
        if not df_agents.empty:
            agents_sel = st.multiselect("Sélectionner agents", df_agents['Nom'].unique())
        else:
            st.write("En attente de données...")

# --- MODULE 2 : OUTILLAGE ---
elif choix == "Outillage":
    st.header("🔧 Suivi Réglementaire")
    tab1, tab2 = st.tabs(["Inventaire", "Validation par Lot"])
    with tab1:
        if not df_outils.empty:
            st.dataframe(df_outils)
        else:
            st.info("L'inventaire est vide.")

# --- MODULE 3 : BILAN PDF ---
elif choix == "Bilan PDF":
    st.header("📄 Génération du Rapport")
    if not df_agents.empty:
        agent_pdf = st.selectbox("Choisir l'agent", df_agents['Nom'].unique())
        if st.button("Générer PDF"):
            st.success(f"PDF pour {agent_pdf} en cours de préparation...")
    else:
        st.error("Impossible de générer un PDF sans liste d'agents.")
