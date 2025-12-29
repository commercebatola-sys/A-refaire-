import streamlit as st
import os
import fitz  # PyMuPDF
import tempfile
import re
from dotenv import load_dotenv, find_dotenv
import requests  # pour appeler Grok API

# --- Configuration page ---
st.set_page_config(
    page_title="Analyse de Documents Financiers",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Analyse Automatique de Documents Financiers avec Grok")
st.markdown("Transformez vos rapports financiers en résumés structurés grâce à l'IA Grok")

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Configuration")
    env_path = find_dotenv(filename=".env", usecwd=True)
    load_dotenv(dotenv_path=env_path, override=True)
    
    st.subheader("🔑 Clé API Grok")
    default_api_key = os.getenv("GROK_API_KEY", "")
    if 'grok_api_key' not in st.session_state:
        st.session_state.grok_api_key = default_api_key
    
    api_key = st.text_input(
        "Clé API Grok",
        value=st.session_state.grok_api_key,
        type="password",
        placeholder="grok-...",
        help="Entrez votre clé API Grok"
    )
    
    if api_key != st.session_state.grok_api_key:
        st.session_state.grok_api_key = api_key
        st.success("✅ Clé API mise à jour !")
    
    if not api_key:
        st.error("❌ Veuillez entrer votre clé API Grok")
        st.stop()
    else:
        st.success(f"✅ API Key configurée: {api_key[:8]}...")
    
    max_length = st.slider("Longueur maximale du texte (caractères)", 50000, 200000, 120000, step=10000)
    
    st.markdown("---")
    st.markdown("**Instructions :**")
    st.markdown("1. Uploadez votre PDF financier")
    st.markdown("2. Obtenez un résumé structuré avec audit")
    st.markdown("3. Posez des questions spécifiques")

# --- Extraction PDF ---
def extract_pdf_text(pdf_file, max_length=120000):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name
        
        pdf = fitz.open(tmp_path)
        text = ""
        for i, page in enumerate(pdf, start=1):
            text += f"\n\n=== [PAGE {i}] ===\n" + page.get_text().strip()
        
        text = "\n".join(line.strip() for line in text.splitlines())
        if len(text) > max_length:
            text = text[:max_length]
            st.warning(f"⚠️ Le texte a été tronqué à {max_length} caractères")
        
        os.unlink(tmp_path)
        return text, len(text)
    except Exception as e:
        st.error(f"❌ Erreur lors de la lecture du PDF: {str(e)}")
        return None, 0

# --- Extraction chiffres ---
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

# --- Audit financier ---
def audit_financier(numbers):
    audit_text = "🔎 Audit & Alertes de cohérence\n\n"
    issues = []

    ca_list = [float(re.sub(r"[^\d.]", "", val)) for val, _ in numbers["CA"] if re.sub(r"[^\d.]", "", val)]
    rn_list = [float(re.sub(r"[^\d.]", "", val)) for val, _ in numbers["Résultat net"] if re.sub(r"[^\d.]", "", val)]
    
    if ca_list and rn_list and ca_list[-1] > ca_list[0] and rn_list[-1] < rn_list[0]:
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

# --- Fonction pour appeler Grok ---
def grok_generate(text, instruction, max_tokens=2000):
    api_key = st.session_state.get('grok_api_key')
    if not api_key:
        st.error("❌ Clé API Grok non configurée")
        return None
    
    url = "https://api.grok.com/v1/generate"  # exemple URL Grok
    headers = {"Authorization": f"Bearer {api_key}"}
    payload = {
        "prompt": instruction + "\n\n" + text,
        "max_tokens": max_tokens,
        "temperature": 0.1
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json().get("text", "")
    except Exception as e:
        st.error(f"❌ Erreur API Grok : {str(e)}")
        return None

# --- Génération résumé avec audit ---
def generate_summary(text):
    instruction = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Lis ce document et fournis : résumé exécutif, tableau chiffres clés, analyse performances, structure financière, risques et recommandations. "
        "Sépare en Markdown : 🟢 Données factuelles, 🔵 Analyse IA, 🟣 Recommandations."
    )
    summary = grok_generate(text, instruction)
    if summary:
        numbers = extract_numbers(text)
        audit = audit_financier(numbers)
        return summary + "\n\n" + audit
    return None

# --- Réponse à questions ---
def answer_question(text, question):
    instruction = (
        "Tu es un assistant IA hybride : analyste financier, consultant business et auditeur senior. "
        "Réponds à la question en citant les chiffres clés et pages si possible. "
        "Si question concerne performance, rentabilité, évolution ou solidité, applique Mode Audit."
        "Sépare en Markdown : 🟢 Faits PDF, 🔵 Analyse IA, 🟣 Recommandations."
    )
    answer = grok_generate(f"Question : {question}\n\nTexte PDF :\n{text}", instruction)
    if any(word in question.lower() for word in ["performance", "rentabilité", "évolution", "risques", "solidité"]):
        numbers = extract_numbers(text)
        audit = audit_financier(numbers)
        return answer + "\n\n" + audit
    return answer

# --- Interface principale ---
def main():
    tab1, tab2 = st.tabs(["📄 Upload & Analyse", "❓ Questions"])
    
    with tab1:
        st.header("📄 Upload et Analyse du PDF")
        uploaded_file = st.file_uploader("Choisissez votre PDF", type=['pdf'])
        
        if uploaded_file:
            file_details = {"Nom": uploaded_file.name, "Taille": f"{uploaded_file.size/1024:.1f} KB"}
            st.json(file_details)
            
            if st.button("🚀 Analyser le document"):
                with st.spinner("📖 Extraction du texte..."):
                    text, text_length = extract_pdf_text(uploaded_file, max_length)
                
                if text:
                    st.success(f"✅ Texte extrait : {text_length} caractères")
                    with st.expander("👁️ Aperçu du texte extrait"):
                        st.text(text[:1000] + "..." if len(text) > 1000 else text)
                    
                    with st.spinner("🤖 Génération du résumé et audit..."):
                        summary = generate_summary(text)
                    
                    if summary:
                        st.success("✅ Résumé et audit générés !")
                        st.subheader("📊 Résumé Financier avec Audit")
                        st.markdown(summary)
                        st.session_state['pdf_text'] = text
                        st.session_state['summary'] = summary
                        st.download_button("💾 Télécharger le résumé", data=summary, file_name=f"resume_{uploaded_file.name.replace('.pdf','')}.md", mime="text/markdown")
                    else:
                        st.error("❌ Échec de la génération du résumé")

    with tab2:
        st.header("❓ Questions sur le Document")
        if 'pdf_text' not in st.session_state:
            st.info("ℹ️ Analysez d'abord un document")
        else:
            question = st.text_input("Posez votre question :", placeholder="Ex: Quel est le chiffre d'affaires ?")
            if question and st.button("🔍 Rechercher la réponse"):
                with st.spinner("🤖 Recherche en cours..."):
                    answer = answer_question(st.session_state['pdf_text'], question)
                if answer:
                    st.success("✅ Réponse trouvée !")
                    st.markdown("**Question :** " + question)
                    st.markdown("**Réponse :**")
                    st.markdown(answer)
                else:
                    st.error("❌ Échec de la recherche de réponse")

st.markdown("---")
st.markdown("**Note :** Vérifiez toujours les chiffres et pages d'origine.")

if __name__ == "__main__":
    main()
