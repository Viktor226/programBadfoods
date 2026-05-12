import streamlit as st
import pytesseract
import cv2
import numpy as np
import pandas as pd
import re
from PIL import Image
import io
import os
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Users \Viktor'

# Конфигурация на страницата
st.set_page_config(
    page_title="Анализатор на вредни съставки",
    page_icon="🛡️",
    layout="wide"
)

# Заглавие
st.title("🛡️ Анализатор на вредни съставки")
st.markdown("**Автоматично разпознаване на текст от снимка**")

# --- БАЗА ДАННИ С ВРЕДНИ СЪСТАВКИ ---
harmful_ingredients = {
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
    "Мононатриев глутамат": {
        "bg": ["мононатриев глутамат"],
        "en": ["monosodium glutamate", "msg"],
        "e": ["E621"]
    },
    "Натриев бензоат": {
        "bg": ["натриев бензоат"],
        "en": ["sodium benzoate"],
        "e": ["E211"]
    },
    "Тартразин": {
        "bg": ["тартразин"],
        "en": ["tartrazine"],
        "e": ["E102"]
    },
    "Сончев залез": {
        "bg": ["сончев залез"],
        "en": ["sunset yellow"],
        "e": ["E110"]
    },
    "Сакхарин": {
        "bg": ["захарин", "сахарин"],
        "en": ["saccharin"],
        "e": ["E954"]
    },
    "BHA/BHT": {
        "bg": ["бутилхидроксианизол", "бутилхидрокситолуен"],
        "en": ["bha", "bht", "butylated hydroxyanisole", "butylated hydroxytoluene"],
        "e": ["E320", "E321"]
    }
}

# Подготовка на сета за търсене
search_set = set()
info_dict = {}

for category, data in harmful_ingredients.items():
    # Български имена
    for name in data["bg"]:
        name_low = name.lower()
        search_set.add(name_low)
        info_dict[name_low] = {"category": category, "lang": "🇧🇬 Българско"}
    # Английски имена
    for name in data["en"]:
        name_low = name.lower()
        search_set.add(name_low)
        info_dict[name_low] = {"category": category, "lang": "🇬🇧 Английско"}
    # Е-номера
    for e_num in data["e"]:
        search_set.add(e_num.upper())
        info_dict[e_num.upper()] = {"category": category, "lang": "🔢 Е-номер"}

def detect_harmful(text):
    """Търси вредни съставки в текста"""
    text_lower = text.lower()
    found = []
    
    # Търсене на Е-номера
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    for e_code in e_matches:
        e_upper = f"E{e_code[1:].upper()}"
        if e_upper in search_set:
            found.append({
                "name": e_upper,
                "category": info_dict[e_upper]["category"],
                "type": info_dict[e_upper]["lang"]
            })
    
    # Търсене на имена
    for keyword in search_set:
        if keyword in text_lower and not keyword.startswith('E'):
            if len(keyword) > 3:  # Игнорираме твърде кратки думи
                found.append({
                    "name": keyword.title(),
                    "category": info_dict[keyword]["category"],
                    "type": info_dict[keyword]["lang"]
                })
    
    # Премахване на дубликати
    unique = []
    seen = set()
    for item in found:
        key = (item["name"], item["category"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    
    return unique

def process_image(image_file):
    """Обработва изображението и разпознава текст с Tesseract"""
    # Четене на изображението
    image = Image.open(image_file)
    
    # Конвертиране към numpy array за OpenCV
    img_array = np.array(image)
    
    # Конвертиране към RGB (ако е необходимо)
    if len(img_array.shape) == 3:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # Преобразуване в сива скала
    gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    
    # Подобряване на качеството за по-добро OCR
    gray = cv2.medianBlur(gray, 1)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # Разпознаване на текст (български и английски)
    text = pytesseract.image_to_string(gray, lang='bul+eng')
    
    return text

# --- ИНТЕРФЕЙС ---
tab1, tab2, tab3 = st.tabs(["📸 Анализ на снимка", "📋 Списък с вредни съставки", "ℹ️ Помощ"])

with tab1:
    st.subheader("📸 Качи снимка на етикет")
    
    uploaded_file = st.file_uploader(
        "Избери снимка (JPG, JPEG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        help="Снимката трябва да е ясна и добре осветена"
    )
    
    if uploaded_file:
        # Показване на снимката
        col1, col2 = st.columns([1, 1])
        
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Вашата снимка", use_column_width=True)
        
        with col2:
            if st.button("🔍 АНАЛИЗИРАЙ СНИМКАТА", type="primary", use_container_width=True):
                with st.spinner("📖 Разпознаване на текст от изображение..."):
                    try:
                        # Разпознаване на текст
                        recognized_text = process_image(uploaded_file)
                        
                        # Търсене на вредни съставки
                        harmful_found = detect_harmful(recognized_text)
                        
                        # Показване на разпознатия текст
                        with st.expander("📝 Разпознат текст от снимката", expanded=False):
                            if recognized_text.strip():
                                st.text(recognized_text[:1000])
                                if len(recognized_text) > 1000:
                                    st.caption("... текстът е съкратен")
                            else:
                                st.warning("⚠️ Не беше разпознат текст. Опитай с по-ясна снимка.")
                        
                        # Резултати
                        st.markdown("---")
                        st.subheader("🔬 РЕЗУЛТАТИ ОТ АНАЛИЗА")
                        
                        if harmful_found:
                            st.error(f"⚠️ **Открити {len(harmful_found)} потенциално вредни съставки!**")
                            
                            # Показване на резултатите в таблица
                            results_data = []
                            for item in harmful_found:
                                results_data.append({
                                    "Съставка / Е-номер": item["name"].upper(),
                                    "Категория": item["category"],
                                    "Тип": item["type"]
                                })
                            
                            df_results = pd.DataFrame(results_data)
                            st.dataframe(df_results, use_container_width=True)
                            
                            # Детайлен списък
                            for item in harmful_found:
                                st.warning(f"**{item['name'].upper()}** → {item['category']} ({item['type']})")
                            
                            # Бутон за изтегляне на резултатите
                            csv = df_results.to_csv(index=False)
                            st.download_button(
                                label="📥 Изтегли резултатите като CSV",
                                data=csv,
                                file_name="harmful_detections.csv",
                                mime="text/csv"
                            )
                        else:
                            st.success("✅ **НЕ СА ОТКРИТИ ВРЕДНИ СЪСТАВКИ!**")
                            st.balloons()
                            
                    except Exception as e:
                        st.error(f"❌ Грешка при обработката: {str(e)}")
                        st.info("Моля, опитай с друга снимка или провери дали Tesseract е инсталиран правилно.")

with tab2:
    st.subheader("📋 Пълен списък на вредните съставки")
    
    # Създаване на таблица
    table_data = []
    for category, data in harmful_ingredients.items():
        all_names = data["bg"] + data["en"]
        e_nums = ", ".join(data["e"]) if data["e"] else "-"
        
        for name in all_names:
            table_data.append({
                "Категория": category,
                "Име": name.title(),
                "Е-номер(и)": e_nums
            })
    
    df_full = pd.DataFrame(table_data)
    st.dataframe(df_full, use_container_width=True, height=400)
    
    # Филтър по категория
    categories = list(harmful_ingredients.keys())
    selected_cat = st.selectbox("🔍 Филтрирай по категория", ["Всички"] + categories)
    
    if selected_cat != "Всички":
        filtered_df = df_full[df_full["Категория"] == selected_cat]
        st.dataframe(filtered_df, use_container_width=True)
    
    # Експорт
    st.download_button(
        label="📥 Изтегли пълния списък (CSV)",
        data=df_full.to_csv(index=False),
        file_name="all_harmful_ingredients.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("ℹ️ Как да използваш приложението")
    
    st.markdown("""
    ### 📸 Стъпки за употреба:
    
    1. **Качи снимка** на етикета на продукта
    2. Натисни **"Анализирай снимката"**
    3. Изчакай няколко секунди
    4. Виж резултатите - кои вредни съставки са открити
    
    ### 🔍 Какво търси приложението?
    
    - 🇧🇬 **Български имена** на вредни съставки
    - 🇬🇧 **Английски имена** на вредни съставки
    - 🔢 **Е-номера** (E100 - E999)
    
    ### 📋 Какви категории вредни съставки се откриват?
    
    - Парабени (консерванти)
    - Сулфати (пянообразуватели)
    - Формалдехид
    - Изкуствени подсладители
    - Глутамат натрий
    - Натриев бензоат
    - Вредни оцветители (тартразин, сончев залез)
    - BHA/BHT антиоксиданти
    
    ### 💡 Съвети за по-добри резултати:
    
    - Използвай **добре осветена** снимка
    - Снимай **отгоре**, без сянка
    - Текстът трябва да е **четим и фокусиран**
    - Ако снимката не работи, опитай с по-близък кадър
    
    ### ⚠️ Важно предупреждение:
    
    Това приложение е **информативно** и не е медицински или експертен съвет.
    Винаги проверявай етикетите сами и се консултирай със специалист при съмнения.
    """)

# Долен колонтитул
st.markdown("---")
st.markdown("📌 **Версия:** 1.0 | **База данни:** 10+ категории вредни съставки")
