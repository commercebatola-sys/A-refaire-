import streamlit as st
import os
import fitz  # PyMuPDF
from openai import OpenAI
import tempfile
import re

# -----------------------------
# CONFIGURATION PAGE
# -----------------------------
st.set_page_config(
    page_title="Analyse de Documents Financiers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse Automatique de Documents Financiers")
st.markdown("Transformez vos rapports financiers en résumés structurés grâce à l'IA générative")

# -----------------------------
# API KEY & Configuration Sidebar
# -----------------------------
OPENAI_API_KEY = "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"
st.session_state['openai_api_key'] = OPENAI_API_KEY

with st.sidebar:
    st.header("⚙️ Configuration")
    st.markdown("🔑 **Clé API configurée automatiquement**")
    st.success(f"✅ API Key active : {OPENAI_API_KEY[:8]}...")

    model = st.selectbox(
        "Choisissez le modèle OpenAI",
        ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
        index=2
    )

    max_length = st.slider(
        "Longueur maximale du texte (caractères)",
        50000, 200000, 120000, step=10000
    )

    st.markdown("---")
    st.markdown("**Instructions :**")
    st.markdown("1. Uploadez votre PDF financier")
    st.markdown("2. Obtenez un résumé structuré avec audit")
    st.markdown("3. Posez des questions spécifiques")

# -----------------------------
# FONCTIONS
# -----------------------------
def extract_pdf_text(pdf_file, max_length=120000):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name

        pdf = fitz.open(tmp_path)
        text = ""
        for i, page in enumerate(pdf, start=1):
            page_text = page.get_text()
            text += f"\n\n=== [PAGE {i}] ===\n" + page_text.strip()

        text = "\n".join(line.strip() for line in text.splitlines())
        if len(text) > max_length:
            text = text[:max_length]
            st.warning(f"⚠️ Le texte a été tronqué à {max_length} caractères pour éviter les dépassements d'API")

        os.unlink(tmp_path)
        return text, len(text)
    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture du PDF: {str(e)}")
        return None, 0


def extract_numbers(text):
    numbers = {"CA": [], "Résultat net": [], "Marge": [], "Dette": [], "Trésorerie": []}
    pages = re.findall(r"=== \[PAGE (\d+)\] ===\n(.*?)(?=== \[PAGE|\Z)", text, re.DOTALL)
    for page_num, page_text in pages:
        for key in numbers.keys():
            pattern = rf"{key}[:\s]*([\d\s,.]+(?:M|k|K)?)"
            for match in re.findall(pattern, page_text, re.IGNORECASE):
                value = match.replace(" ", "").replace(",", ".")
                numbers[key].append((value, page_num))
    return numbers


def audit_financier(numbers):
    audit_text = "🔎 Audit & Alertes de cohérence\n\n"
    issues = []

    ca_list = [float(re.sub(r"[^\d.]", "", val)) for val, _ in numbers["CA"] if re.sub(r"[^\d.]", "", val)]
    rn_list = [float(re.sub(r"[^\d.]", "", val)) for val, _ in numbers["Résultat net"] if re.sub(r"[^\d.]", "", val)]

    if ca_list and rn_list:
        if ca_list[-1] > ca_list[0] and rn_list[-1] < rn_list[0]:
            issues.append(f"⚠️ Incohérence : CA ↑ mais Résultat net ↓ (pages {numbers['CA'][-1][1]} & {numbers['Résultat net'][-1][1]})")

    if numbers["Marge"]:
        issues.append(f"🔵 Marge identifiée : {numbers['Marge'][-1][0]}% (page {numbers['Marge'][-1][1]})")
    if numbers["Dette"] and numbers["Trésorerie"]:
        issues.append(f"⚠️ Dette vs Trésorerie : Dette = {numbers['Dette'][-1][0]}, Trésorerie = {numbers['Trésorerie'][-1][0]} (pages {numbers['Dette'][-1][1]} & {numbers['Trésorerie'][-1][1]})")

    if not issues:
        audit_text += "✅ Cohérence globale : satisfaisante"
    else:
        audit_text += "\n".join(issues)
        audit_text += "\n\n✅ Cohérence globale : moyenne"

    return audit_text


def generate_summary(text, model="gpt-3.5-turbo"):
    api_key = st.session_state.get('openai_api_key')
    instructions = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Lis ce document financier et fournis : résumé exécutif, tableau des chiffres clés, analyse des performances, structure financière, risques et guidance. "
        "Si l'information est absente, indique 'non précisé'. "
        "Sépare les sections Markdown : 🟢 Données factuelles, 🔵 Analyse & interprétation IA, 🟣 Recommandations."
    )
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": text[:30000]}  # tronque si trop long
            ],
            max_tokens=2000,
            temperature=0.1
        )
        summary = response.choices[0].message.content
        numbers = extract_numbers(text)
        audit = audit_financier(numbers)
        return summary + "\n\n" + audit
    except Exception as e:
        st.error(f"❌ Erreur lors de la génération du résumé: {str(e)}")
        return None


def answer_question(text, question, model="gpt-3.5-turbo"):
    api_key = st.session_state.get('openai_api_key')
    instructions = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Lis le texte, extrais les chiffres clés, identifie risques et stratégie, cite les pages si possible. "
        "Ne jamais inventer de données. "
        "Si la question concerne performance, rentabilité, évolution ou solidité financière, applique automatiquement le Mode Audit. "
        "Réponds clairement et distingue : 🟢 Faits PDF, 🔵 Analyse IA, 🟣 Recommandations."
    )
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": f"Question : {question}\n\nTexte PDF :\n{text[:30000]}"}
            ],
            max_tokens=1000,
            temperature=0.1
        )
        answer = response.choices[0].message.content
        if any(word in question.lower() for word in ["performance", "rentabilité", "évolution", "risques", "solidité"]):
            numbers = extract_numbers(text)
            audit = audit_financier(numbers)
            return answer + "\n\n" + audit
        return answer
    except Exception as e:
        st.error(f"❌ Erreur lors de la réponse à la question: {str(e)}")
        return None

# -----------------------------
# INTERFACE PRINCIPALE
# -----------------------------
def main():
    tab1, tab2 = st.tabs(["📄 Upload & Analyse", "❓ Questions"])
    
    with tab1:
        st.header("📄 Upload et Analyse du PDF")
        uploaded_file = st.file_uploader("Choisissez votre document financier (PDF)", type=['pdf'])
        
        if uploaded_file:
            file_details = {"Nom": uploaded_file.name, "Taille": f"{uploaded_file.size/1024:.1f} KB", "Type": uploaded_file.type}
            st.json(file_details)
            
            if st.button("🚀 Analyser le document"):
                with st.spinner("📖 Extraction du texte en cours..."):
                    text, text_length = extract_pdf_text(uploaded_file, max_length)
                
                if text:
                    st.success(f"✅ Texte extrait : {text_length} caractères")
                    with st.expander("👁️ Aperçu du texte extrait"):
                        st.text(text[:1000] + "..." if len(text) > 1000 else text)
                    
                    with st.spinner("🤖 Génération du résumé et audit..."):
                        summary = generate_summary(text, model)
                    
                    if summary:
                        st.success("✅ Résumé et audit générés !")
                        st.subheader("📊 Résumé Financier avec Audit")
                        st.markdown(summary)
                        st.session_state['pdf_text'] = text
                        st.session_state['summary'] = summary
                        st.download_button(
                            "💾 Télécharger le résumé",
                            data=summary,
                            file_name=f"resume_{uploaded_file.name.replace('.pdf','')}.md",
                            mime="text/markdown"
                        )
                    else:
                        st.error("❌ Échec de la génération du résumé")
                else:
                    st.error("❌ Échec de l'extraction du texte")
    
    with tab2:
        st.header("❓ Questions sur le Document")
        if 'pdf_text' not in st.session_state:
            st.info("ℹ️ Analysez d'abord un document dans l'onglet 'Upload & Analyse'")
        else:
            question = st.text_input("Posez votre question sur le document :", placeholder="Ex: Quel est le chiffre d'affaires ?")
            if question:
                if st.button("🔍 Rechercher la réponse"):
                    with st.spinner("🤖 Recherche en cours..."):
                        answer = answer_question(st.session_state['pdf_text'], question, model)
                    if answer:
                        st.success("✅ Réponse trouvée !")
                        st.markdown("**Question :** " + question)
                        st.markdown("**Réponse :**")
                        st.markdown(answer)
                    else:
                        st.error("❌ Échec de la recherche de réponse")
            
            st.subheader("💡 Questions suggérées")
            suggested_questions = [
                "Quel est le chiffre d'affaires ?",
                "Quelle est la marge nette ?",
                "Quels sont les principaux risques identifiés ?",
                "Quelle est la dette nette ?",
                "Quel est le cash flow opérationnel ?"
            ]
            for i, q in enumerate(suggested_questions):
                if st.button(f"❓ {q}", key=f"suggested_{i}"):
                    with st.spinner("🤖 Recherche en cours..."):
                        answer = answer_question(st.session_state['pdf_text'], q, model)
                    if answer:
                        st.success("✅ Réponse trouvée !")
                        st.markdown("**Question :** " + q)
                        st.markdown("**Réponse :**")
                        st.markdown(answer)
                    else:
                        st.error("❌ Échec de la recherche de réponse")


st.markdown("---")
st.markdown("**Note :** Vérifiez toujours les chiffres et pages d'origine. En cas d'ambiguïté, utilisez 'non précisé'.")

if __name__ == "__main__":
    main()
