import streamlit as st
import easyocr
import cv2
import numpy as np
import pandas as pd
import re
from PIL import Image
import os

# ------------------------------------------------------------
# 1. Конфигурация на страницата
# ------------------------------------------------------------
st.set_page_config(
    page_title="Анализатор на вредни съставки - EasyOCR",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Анализатор на вредни съставки")
st.markdown("**Автоматично разпознаване на текст от снимка с EasyOCR**")

# ------------------------------------------------------------
# 2. Кеширане на EasyOCR модела (зарежда се само веднъж)
# ------------------------------------------------------------
@st.cache_resource
def load_easyocr_reader():
    # Върни Reader само за български и английски (намалява зареждането)
    # gpu=False е задължително за Streamlit Cloud (няма GPU)
    return easyocr.Reader(['bg', 'en'], gpu=False)

# ------------------------------------------------------------
# 3. База данни с вредни съставки (български + английски + Е-номера)
# ------------------------------------------------------------
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
    "Глутамат натрий": {
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
    "Сончев залез (жълто)": {
        "bg": ["сончев залез"],
        "en": ["sunset yellow"],
        "e": ["E110"]
    },
    "Захарин": {
        "bg": ["захарин", "сахарин"],
        "en": ["saccharin"],
        "e": ["E954"]
    },
    "BHA / BHT": {
        "bg": ["бутилхидроксианизол", "бутилхидрокситолуен"],
        "en": ["bha", "bht", "butylated hydroxyanisole", "butylated hydroxytoluene"],
        "e": ["E320", "E321"]
    }
}

# Подготовка на сет за бързо търсене
search_set = set()
info_map = {}

for category, data in harmful_db.items():
    for name_bg in data["bg"]:
        key = name_bg.lower()
        search_set.add(key)
        info_map[key] = (category, "🇧🇬")
    for name_en in data["en"]:
        key = name_en.lower()
        search_set.add(key)
        info_map[key] = (category, "🇬🇧")
    for e_num in data["e"]:
        key = e_num.upper()
        search_set.add(key)
        info_map[key] = (category, "🔢")

# ------------------------------------------------------------
# 4. Функция за търсене на вредни съставки
# ------------------------------------------------------------
def find_harmful(text: str):
    if not text:
        return []
    text_lower = text.lower()
    found = []
    
    # Търсене на Е-номера (напр. E211)
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    for e in e_matches:
        e_upper = f"E{e[1:].upper()}"
        if e_upper in search_set:
            cat, icon = info_map[e_upper]
            found.append({"term": e_upper, "category": cat, "icon": icon})
    
    # Търсене на имена
    for keyword in search_set:
        if keyword in text_lower and not keyword.startswith('e'):
            if len(keyword) > 3:
                cat, icon = info_map[keyword]
                found.append({"term": keyword.title(), "category": cat, "icon": icon})
    
    # Премахване на дубликати (по термин и категория)
    unique = []
    seen = set()
    for item in found:
        key = (item["term"], item["category"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique

# ------------------------------------------------------------
# 5. Основна функция за разпознаване на текст от изображение
# ------------------------------------------------------------
def extract_text_from_image(image_file, reader):
    # Конвертиране на PIL Image към numpy масив
    img = Image.open(image_file)
    img_np = np.array(img)
    
    # OpenCV обработка за по-добро разпознаване
    if len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 1)
    gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # EasyOCR разпознаване (detail=0 връща само текста)
    result = reader.readtext(gray, detail=0, paragraph=True)
    full_text = " ".join(result)
    return full_text

# ------------------------------------------------------------
# 6. Интерфейс на Streamlit
# ------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📸 Анализ на снимка", "📋 Списък с вредни съставки", "ℹ️ Помощ"])

with tab1:
    st.subheader("📸 Качи снимка на етикет")
    uploaded_file = st.file_uploader("Избери файл (JPG, JPEG, PNG)", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Вашата снимка", use_column_width=True)
        
        with col2:
            if st.button("🔍 АНАЛИЗИРАЙ СНИМКАТА", type="primary", use_container_width=True):
                with st.spinner("📖 Зареждане на EasyOCR модел (само веднъж) и разпознаване..."):
                    reader = load_easyocr_reader()
                    recognized_text = extract_text_from_image(uploaded_file, reader)
                
                # Показване на разпознатия текст
                with st.expander("📝 Разпознат текст от снимката", expanded=False):
                    if recognized_text.strip():
                        st.text(recognized_text[:1000])
                        if len(recognized_text) > 1000:
                            st.caption("... текстът е съкратен")
                    else:
                        st.warning("⚠️ Не беше разпознат текст. Опитай с по-ясна снимка.")
                
                # Търсене на вредни съставки
                harmful_items = find_harmful(recognized_text)
                
                st.markdown("---")
                st.subheader("🔬 РЕЗУЛТАТИ ОТ АНАЛИЗА")
                
                if harmful_items:
                    st.error(f"⚠️ **Открити {len(harmful_items)} потенциално вредни съставки!**")
                    for item in harmful_items:
                        st.warning(f"{item['icon']} **{item['term'].upper()}** → {item['category']}")
                    
                    # Таблица за експорт
                    df = pd.DataFrame([{
                        "Съставка/Е-номер": i["term"].upper(),
                        "Категория": i["category"],
                        "Тип": i["icon"]
                    } for i in harmful_items])
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Изтегли резултатите (CSV)",
                        data=csv,
                        file_name="harmful_detected.csv",
                        mime="text/csv"
                    )
                else:
                    st.success("✅ **НЕ СА ОТКРИТИ ВРЕДНИ СЪСТАВКИ!**")
                    st.balloons()

with tab2:
    st.subheader("📋 Пълен списък на вредните съставки")
    rows = []
    for cat, data in harmful_db.items():
        all_names = data["bg"] + data["en"]
        e_nums = ", ".join(data["e"]) if data["e"] else "-"
        for name in all_names:
            rows.append({"Категория": cat, "Име": name.title(), "Е-номер(и)": e_nums})
    df_full = pd.DataFrame(rows)
    st.dataframe(df_full, use_container_width=True, height=400)
    
    st.download_button(
        label="📥 Изтегли пълния списък (CSV)",
        data=df_full.to_csv(index=False),
        file_name="all_harmful_ingredients.csv",
        mime="text/csv"
    )

with tab3:
    st.subheader("ℹ️ Инструкции и важна информация")
    st.markdown("""
    ### Как да използвам приложението?
    1. Качи снимка на етикет на продукт (храна, козметика и др.)
    2. Натисни „Анализирай снимката“
    3. Изчакай няколко секунди (първото стартиране може да е по-бавно, защото се теглят модели)
    4. Виж кои вредни съставки са открити
    
    ### Какво разпознава EasyOCR?
    - Български и английски текст
    - Главни и малки букви
    - Печатни букви (не ръкопис)
    
    ### Забележки:
    - Първото зареждане на модела може да отнеме ~30 секунди и да изтегли около 200MB данни.
    - Приложението работи **на CPU**, затова е по-бавно от локален вариант с GPU, но е напълно функционално.
    - Ако срещнеш грешка за липса на памет, опитай с по-малка снимка или ползвай Hugging Face Spaces (дава повече RAM).
    
    ### Важно:
    Това приложение е **информативно** и не е медицински или експертен съвет.
    """)

st.markdown("---")
st.caption("📌 Основано на EasyOCR + Streamlit | Версия 1.0")
