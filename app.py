import streamlit as st
import easyocr
import cv2
import re
from PIL import Image
import numpy as np

# База данни с вредни съставки (същата като преди)
harmful_ingredients_db = {
    "parabens": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben"],
    "sulfates": ["sodium lauryl sulfate", "sodium laureth sulfate"],
    "phthalates": ["dep", "dbp", "bbp", "dehp"],
    "formaldehyde releasers": ["formaldehyde", "dmdm hydantoin"],
    "silicones": ["dimethicone", "cyclomethicone"],
    "mineral oil": ["mineral oil", "paraffinum liquidum"]
}

harmful_set = set()
for ingredients in harmful_ingredients_db.values():
    for ing in ingredients:
        harmful_set.add(ing.lower())

# Заглавие
st.set_page_config(page_title="Анализатор на вредни съставки", page_icon="🛡️")
st.title("🛡️ Анализатор на вредни съставки")
st.markdown("Качи снимка на етикет и ще ти кажа дали съдържа вредни вещества")

# Качване на снимка
uploaded_file = st.file_uploader("📸 Избери снимка", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    # Показване на снимката
    image = Image.open(uploaded_file)
    st.image(image, caption="Качена снимка", use_column_width=True)
    
    # OCR разпознаване
    with st.spinner("🔍 Разпознаване на текст от изображение..."):
        # Запазване временно
        with open("temp.jpg", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # EasyOCR
        reader = easyocr.Reader(['en', 'bg'])
        result = reader.readtext("temp.jpg", detail=0, paragraph=True)
        text = " ".join(result)
    
    st.subheader("📝 Разпознат текст:")
    st.text(text[:500] + "..." if len(text) > 500 else text)
    
    # Търсене на вредни съставки
    text_lower = text.lower()
    detected = []
    
    for harmful in harmful_set:
        if harmful in text_lower:
            detected.append(harmful)
    
    # Показване на резултатите
    st.subheader("🔬 Резултати:")
    
    if detected:
        st.error(f"⚠️ Открити {len(detected)} вредни съставки!")
        
        for bad in set(detected):
            # Намери категорията
            category = None
            for cat, items in harmful_ingredients_db.items():
                if bad in items:
                    category = cat
                    break
            if category:
                st.warning(f"**{bad.upper()}** → Категория: {category}")
            else:
                st.warning(f"**{bad.upper()}**")
    else:
        st.success("✅ Не са открити вредни съставки!")
    
    # Изтриване на временния файл
    import os
    os.remove("temp.jpg")
