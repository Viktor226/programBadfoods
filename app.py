import streamlit as st
import pytesseract
import cv2
import numpy as np
import pandas as pd
import re
from PIL import Image
import os

# Конфигурация за Windows (промени пътя ако е нужно)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.set_page_config(page_title="Вредни съставки - Tesseract", page_icon="🛡️", layout="wide")

st.title("🛡️ Анализатор на вредни съставки")
st.markdown("**Автоматично разпознаване на текст от снимка с Tesseract OCR**")

# --- (същата база данни като във Версия 1) ---
harmful_db = {
    "Парабени": {
        "bg": ["метилпарабен", "етилпарабен", "пропилпарабен", "бутилпарабен"],
        "en": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben"],
        "e": []
    },
    "Сулфати": {
        "bg": ["натриев лаурил сулфат", "натриев лаурет сулфат"],
        "en": ["sodium lauryl sulfate", "sodium laureth sulfate", "sls", "sles"],
        "e": []
    },
    "Формалдехид": {
        "bg": ["формалдехид"],
        "en": ["formaldehyde"],
        "e": ["E240"]
    },
    "Аспартам": {
        "bg": ["аспартам"],
        "en": ["aspartame"],
        "e": ["E951"]
    },
    "Глутамат": {
        "bg": ["мононатриев глутамат"],
        "en": ["monosodium glutamate", "msg"],
        "e": ["E621"]
    },
    "Бензоат натрий": {
        "bg": ["натриев бензоат"],
        "en": ["sodium benzoate"],
        "e": ["E211"]
    },
    "Тартразин": {
        "bg": ["тартразин"],
        "en": ["tartrazine"],
        "e": ["E102"]
    }
}

# Подготовка за търсене
search_set = set()
ingredient_info = {}

for cat, data in harmful_db.items():
    for name in data["bg"]:
        search_set.add(name.lower())
        ingredient_info[name.lower()] = {"category": cat, "type": "🇧🇬"}
    for name in data["en"]:
        search_set.add(name.lower())
        ingredient_info[name.lower()] = {"category": cat, "type": "🇬🇧"}
    for e_num in data["e"]:
        search_set.add(e_num.upper())
        ingredient_info[e_num.upper()] = {"category": cat, "type": "🔢"}

def find_harmful(text):
    text_lower = text.lower()
    detected = []
    
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    for e in e_matches:
        e_upper = f"E{e[1:].upper()}"
        if e_upper in search_set:
            detected.append({"term": e_upper, "info": ingredient_info[e_upper]})
    
    for item in search_set:
        if item in text_lower and not item.startswith('E') and not item.startswith('e'):
            if len(item) > 3:
                detected.append({"term": item, "info": ingredient_info[item]})
    
    unique = []
    seen = set()
    for d in detected:
        if d["term"] not in seen:
            seen.add(d["term"])
            unique.append(d)
    return unique

def extract_text_from_image(image_path):
    """Разпознава текст от изображение с Tesseract"""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Подобряване на качеството
    gray = cv2.medianBlur(gray, 1)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    text = pytesseract.image_to_string(gray, lang='bul+eng')
    return text

# Интерфейс
uploaded_file = st.file_uploader("📸 Избери снимка на етикет", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        image = Image.open(uploaded_file)
        st.image(image, caption="Качена снимка", use_column_width=True)
    
    with col2:
        if st.button("🔍 АНАЛИЗИРАЙ", type="primary", use_container_width=True):
            with st.spinner("📖 Разпознаване на текст от изображение..."):
                temp_path = "temp_image.jpg"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                recognized_text = extract_text_from_image(temp_path)
                os.remove(temp_path)
            
            with st.expander("📝 Разпознат текст", expanded=True):
                st.text(recognized_text[:800] + ("..." if len(recognized_text) > 800 else ""))
            
            harmful_found = find_harmful(recognized_text)
            
            st.markdown("---")
            st.subheader("🔬 РЕЗУЛТАТИ")
            
            if harmful_found:
                st.error(f"⚠️ **Открити {len(harmful_found)} вредни съставки!**")
                for item in harmful_found:
                    st.warning(f"{item['info']['type']} **{item['term'].upper()}** → {item['info']['category']}")
            else:
                st.success("✅ **НЕ СА ОТКРИТИ ВРЕДНИ СЪСТАВКИ!**")
                st.balloons()
