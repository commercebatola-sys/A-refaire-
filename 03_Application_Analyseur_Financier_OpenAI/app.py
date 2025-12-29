import streamlit as st
import os
import fitz  # PyMuPDF
import tempfile
import re
from dotenv import load_dotenv, find_dotenv

# ======================================================
# CONFIGURATION PAGE
# ======================================================
st.set_page_config(
    page_title="Analyseur Financier IA",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Analyse Automatique de Documents Financiers")
st.markdown(
    "Prototype d’analyse financière assistée par IA — "
    "**résumé, audit de cohérence et réponses intelligentes**"
)

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    st.header("⚙️ Configuration")
    load_dotenv(find_dotenv(), override=True)

    st.markdown("### 🧠 Comportement de l’IA")
    st.markdown("""
- Analyste financier senior  
- Auditeur de cohérence  
- Consultant business  
- Réponses structurées en Markdown  
""")

    max_length = st.slider(
        "Longueur maximale du texte PDF (caractères)",
        50_000, 200_000, 120_000, step=10_000
    )

    st.markdown("---")
    st.markdown("### 📘 Mode Prototype")
    st.info(
        "L’IA est simulée. "
        "La logique métier est complète et remplaçable par une vraie API IA."
    )

# ======================================================
# EXTRACTION TEXTE PDF
# ======================================================
def extract_pdf_text(pdf_file, max_length):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_file.read())
            path = tmp.name

        doc = fitz.open(path)
        text = ""

        for i, page in enumerate(doc, start=1):
            text += f"\n\n=== [PAGE {i}] ===\n"
            text += page.get_text().strip()

        text = "\n".join(line.strip() for line in text.splitlines())

        if len(text) > max_length:
            text = text[:max_length]
            st.warning("⚠️ Texte tronqué pour rester exploitable par l’IA")

        os.remove(path)
        return text

    except Exception as e:
        st.error(f"Erreur PDF : {e}")
        return None

# ======================================================
# EXTRACTION DE DONNÉES NUMÉRIQUES SIMPLES
# ======================================================
def extract_numbers(text):
    keywords = ["chiffre d'affaires", "résultat net", "marge", "dette", "trésorerie"]
    data = {}

    for key in keywords:
        pattern = rf"{key}[^0-9]*([\d\s,.]+)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        data[key] = matches

    return data

# ======================================================
# AUDIT DE COHÉRENCE SIMPLE
# ======================================================
def audit_financier(data):
    alerts = []

    if data["chiffre d'affaires"] and data["résultat net"]:
        alerts.append("📈 CA et Résultat net identifiés — cohérence à vérifier manuellement")

    if data["dette"] and data["trésorerie"]:
        alerts.append("⚠️ Dette et Trésorerie présentes — analyser la solvabilité")

    if not alerts:
        return "✅ Aucune incohérence majeure détectée"

    return "\n".join(alerts)

# ======================================================
# MOTEUR IA — MODE PROTOTYPE (REMPLAÇABLE)
# ======================================================
def ia_engine(text, instruction):
    """
    IA simulée.
    Remplacer cette fonction par une vraie API IA plus tard.
    """

    return f"""
## 🟢 Données factuelles
- Document analysé avec succès
- Longueur du texte : {len(text)} caractères
- Analyse basée uniquement sur le contenu fourni

## 🔵 Analyse IA
Le document présente une structure financière classique.
Les indicateurs clés mentionnés suggèrent une activité économique structurée.
Certaines tendances méritent une analyse plus approfondie, notamment la rentabilité
et la gestion de la dette.

## 🟣 Recommandations
- Vérifier l’évolution du chiffre d’affaires sur plusieurs exercices
- Analyser la relation entre dette et trésorerie
- Compléter avec un audit humain si décision stratégique
"""

# ======================================================
# GÉNÉRATION DU RÉSUMÉ GLOBAL
# ======================================================
def generate_summary(text):
    instruction = """
    Tu es un analyste financier senior.
    Tu dois produire un résumé structuré avec :
    - faits
    - analyse
    - recommandations
    """

    summary = ia_engine(text, instruction)
    numbers = extract_numbers(text)
    audit = audit_financier(numbers)

    return summary + "\n\n---\n\n### 🔎 Audit de cohérence\n" + audit

# ======================================================
# RÉPONSE AUX QUESTIONS
# ======================================================
def answer_question(text, question):
    instruction = f"""
    Tu es un analyste financier.
    Réponds uniquement à partir du document.
    Question : {question}
    """

    response = ia_engine(text, instruction)
    numbers = extract_numbers(text)
    audit = audit_financier(numbers)

    return response + "\n\n---\n\n### 🔎 Audit lié à la question\n" + audit

# ======================================================
# INTERFACE PRINCIPALE
# ======================================================
def main():
    tab1, tab2 = st.tabs(["📄 Analyse du document", "❓ Questions"])

    with tab1:
        uploaded = st.file_uploader("Uploader un PDF financier", type=["pdf"])

        if uploaded and st.button("🚀 Analyser"):
            with st.spinner("Extraction du texte..."):
                text = extract_pdf_text(uploaded, max_length)

            if text:
                st.session_state["pdf_text"] = text
                st.success("✅ Texte extrait")

                with st.spinner("Analyse IA en cours..."):
                    summary = generate_summary(text)

                st.markdown("## 📊 Résumé & Audit")
                st.markdown(summary)

                st.download_button(
                    "💾 Télécharger le résumé",
                    summary,
                    file_name="resume_financier.md",
                    mime="text/markdown"
                )

    with tab2:
        if "pdf_text" not in st.session_state:
            st.info("Analysez d’abord un document")
        else:
            question = st.text_input("Votre question")
            if question and st.button("🔍 Répondre"):
                with st.spinner("Analyse IA..."):
                    answer = answer_question(
                        st.session_state["pdf_text"],
                        question
                    )
                st.markdown(answer)

# ======================================================
# LANCEMENT
# ======================================================
if __name__ == "__main__":
    main()
