import streamlit as st
import os
import fitz  # PyMuPDF
from dotenv import load_dotenv, find_dotenv
from openai import OpenAI
import tempfile
import re

# =========================
# CONFIGURATION PAGE
# =========================
st.set_page_config(
    page_title="Analyse de Documents Financiers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse Automatique de Documents Financiers")
st.markdown("Transformez vos rapports financiers en résumés structurés grâce à l'IA générative")

# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.header("⚙️ Configuration")
    load_dotenv(find_dotenv(".env", usecwd=True))

    api_key = st.text_input(
        "🔑 Clé API OpenAI",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password"
    )

    if not api_key:
        st.error("Veuillez entrer une clé API valide")
        st.stop()

    st.session_state.openai_api_key = api_key
    model = st.selectbox("Modèle", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"], index=0)
    max_length = st.slider("Longueur max texte", 50_000, 200_000, 120_000, 10_000)

# =========================
# EXTRACTION TEXTE PDF
# =========================
def extract_pdf_text(pdf_file, max_length):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.read())
        path = tmp.name

    pdf = fitz.open(path)
    text = ""
    for i, page in enumerate(pdf, start=1):
        text += f"\n\n=== [PAGE {i}] ===\n{page.get_text()}"

    os.unlink(path)
    text = text[:max_length]
    return text, len(text)

# =========================
# EXTRACTION DES CHIFFRES
# =========================
def extract_numbers(text):
    keys = ["CA", "Résultat net", "Marge", "Dette", "Trésorerie"]
    numbers = {k: [] for k in keys}

    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.S)
    for p, content in pages:
        for k in keys:
            for m in re.findall(rf"{k}[:\s]*([\d\s,.]+)", content, re.I):
                numbers[k].append((m.replace(",", "."), p))
    return numbers

# =========================
# RATIOS FINANCIERS
# =========================
def calculate_ratios(numbers):
    ratios = {}

    try:
        ca = float(numbers["CA"][-1][0])
        rn = float(numbers["Résultat net"][-1][0])
        ratios["Marge nette (%)"] = round((rn / ca) * 100, 2)
    except:
        ratios["Marge nette (%)"] = "🔴 données manquantes"

    try:
        dette = float(numbers["Dette"][-1][0])
        treso = float(numbers["Trésorerie"][-1][0])
        ratios["Dette nette"] = round(dette - treso, 2)
    except:
        ratios["Dette nette"] = "🔴 données manquantes"

    return ratios

# =========================
# AUDIT FINANCIER
# =========================
def audit_financier(numbers, ratios):
    alerts = []

    if isinstance(ratios.get("Marge nette (%)"), float) and ratios["Marge nette (%)"] < 5:
        alerts.append("⚠️ Marge nette faible (<5%)")

    if not alerts:
        return "🔎 **Audit & Alertes**\n\n✅ Cohérence globale satisfaisante"

    return "🔎 **Audit & Alertes**\n\n" + "\n".join(alerts)

# =========================
# FORMAT STRUCTURÉ
# =========================
def format_output(facts, analysis, recommendations):
    return f"""
## 🟢 Données factuelles (PDF)
{facts}

## 🔵 Analyse & interprétation IA
{analysis}

## 🟣 Recommandations
{recommendations}
"""

# =========================
# MODE CONSULTANT
# =========================
def consultant_block():
    return """
## 🧠 Mode Consultant Business

### Leviers clés
- Rentabilité
- Structure de coûts
- Endettement

### Plan 30 / 60 / 90 jours
**30j** : audit interne  
**60j** : optimisation coûts  
**90j** : croissance structurée

### KPI
- Marge nette
- Cash-flow
- Dette nette
"""

# =========================
# GÉNÉRATION RÉSUMÉ
# =========================
def generate_summary(text, model):
    client = OpenAI(api_key=st.session_state.openai_api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Extrais uniquement les faits financiers du document."},
            {"role": "user", "content": text}
        ],
        temperature=0
    )

    facts = response.choices[0].message.content
    numbers = extract_numbers(text)
    ratios = calculate_ratios(numbers)
    audit = audit_financier(numbers, ratios)

    analysis = "Analyse basée sur tendances financières observées."
    recommendations = "Améliorer la rentabilité et maîtriser l’endettement."

    ratios_md = "\n".join([f"- **{k}** : {v}" for k, v in ratios.items()])

    return f"""
{format_output(facts, analysis, recommendations)}

## 📐 Ratios financiers automatiques
{ratios_md}

{audit}

{consultant_block()}
"""

# =========================
# QUESTIONS
# =========================
def answer_question(text, question, model):
    client = OpenAI(api_key=st.session_state.openai_api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Réponds comme un consultant financier senior."},
            {"role": "user", "content": question + "\n\n" + text}
        ],
        temperature=0.1
    )

    numbers = extract_numbers(text)
    ratios = calculate_ratios(numbers)
    audit = audit_financier(numbers, ratios)

    ratios_md = "\n".join([f"- {k} : {v}" for k, v in ratios.items()])

    return f"""
{response.choices[0].message.content}

## 📐 Ratios financiers
{ratios_md}

{audit}
"""

# =========================
# INTERFACE
# =========================
def main():
    tab1, tab2 = st.tabs(["📄 Analyse PDF", "❓ Questions"])

    with tab1:
        pdf = st.file_uploader("Uploader un PDF", type="pdf")
        if pdf and st.button("🚀 Analyser"):
            text, _ = extract_pdf_text(pdf, max_length)
            summary = generate_summary(text, model)
            st.session_state.text = text
            st.markdown(summary)

    with tab2:
        if "text" not in st.session_state:
            st.info("Analyse d'abord un document")
        else:
            q = st.text_input("Question")
            if q and st.button("🔍 Répondre"):
                st.markdown(answer_question(st.session_state.text, q, model))

if __name__ == "__main__":
    main()
