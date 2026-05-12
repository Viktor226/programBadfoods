import streamlit as st
import pytesseract
import cv2
import numpy as np
import pandas as pd
import re
from PIL import Image
import io
import os

# --- 1. Конфигурация на страницата ---
st.set_page_config(
    page_title="Анализатор на вредни съставки",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Анализатор на вредни съставки")
st.markdown("**Автоматично разпознаване на текст от снимка**")

# --- 2. База данни с вредни съставки ---
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
    }
        "Емулгатори и стабилизатори": {
        "bg": ["моно и диглицериди на мастни киселини", "полиглицерилови етери на мастни киселини", "соев лецитин", "лецитин"],
        "en": ["mono- and diglycerides of fatty acids", "polyglycerol esters of fatty acids", "soy lecithin", "lecithin"],
        "e": ["E471", "E475", "E322"]
    },
    "Консерванти (пропионати и сорбати)": {
        "bg": ["калциев пропионат", "калиев сорбат"],
        "en": ["calcium propionate", "potassium sorbate"],
        "e": ["E282", "E202"]
    },
    "Хелиращи агенти (алгинати)": {
        "bg": ["натриев алгинат"],
        "en": ["sodium alginate"],
        "e": ["E401"]
    },
    "Агенти за обработка на брашно": {
        "bg": ["l-цистеин", "аскорбинова киселина"],
        "en": ["l-cysteine", "ascorbic acid"],
        "e": ["E920", "E300"]
    },
    "Набухватели (карбонати)": {
        "bg": ["амониев карбонат", "калиев карбонат", "натриев карбонат"],
        "en": ["ammonium carbonate", "potassium carbonate", "sodium carbonate"],
        "e": ["E503", "E501", "E500"]
    },
    "Изкуствени подсладители (цикламат, ацесулфам)": {
        "bg": ["цикламат", "ацесулфам"],
        "en": ["cyclamate", "acesulfame k"],
        "e": ["E952", "E950"]
    },
    "Оцветители (карамел E150d)": {
        "bg": ["карамел"],
        "en": ["caramel colour", "ammonia caramel"],
        "e": ["E150d"]
    },
    "Киселини и регулатори (фосфорна киселина, натриев хидроксид)": {
        "bg": ["фосфорна киселина", "натриев хидроксид", "натриеви цитрати"],
        "en": ["phosphoric acid", "sodium hydroxide", "sodium citrates"],
        "e": ["E338", "E524", "E331"]
    },
    "Алергени (предупреждение)": {
        "bg": ["яйца", "фъстъци", "ядки", "целина", "сусам", "соя"],
        "en": ["eggs", "peanuts", "nuts", "celery", "sesame", "soy"],
        "e": []
    }
    
}

# Подготовка на сета за търсене
search_set = set()
info_dict = {}

for category, data in harmful_db.items():
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
    if not text:
        return []
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
        if keyword in text_lower and not keyword.startswith('e'):
            if len(keyword) > 3:
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

# --- 3. Интерфейс на Streamlit ---
tab1, tab2, tab3 = st.tabs(["📸 Анализ на снимка", "📋 Списък с вредни съставки", "ℹ️ Помощ"])

with tab1:
    st.subheader("📸 Качи снимка на етикет")
    uploaded_file = st.file_uploader(
        "Избери снимка (JPG, JPEG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        help="Снимката трябва да е ясна и добре осветена"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            image = Image.open(uploaded_file)
            st.image(image, caption="Вашата снимка", use_column_width=True)
        
        with col2:
            if st.button("🔍 АНАЛИЗИРАЙ СНИМКАТА", type="primary", use_container_width=True):
                with st.spinner("📖 Разпознаване на текст от изображение..."):
                    try:
                        recognized_text = process_image(uploaded_file)
                        harmful_found = detect_harmful(recognized_text)
                        
                        with st.expander("📝 Разпознат текст от снимката", expanded=False):
                            if recognized_text.strip():
                                st.text(recognized_text[:1000])
                                if len(recognized_text) > 1000:
                                    st.caption("... текстът е съкратен")
                            else:
                                st.warning("⚠️ Не беше разпознат текст. Опитай с по-ясна снимка или използвай полето по-долу за ръчно въвеждане.")
                        
                        # Ръчно въвеждане като резерв
                        manual_text = st.text_area("✏️ Или въведи списъка със съставки ръчно (алтернатива):", key="manual_input")
                        if manual_text:
                            harmful_found = detect_harmful(manual_text)
                        
                        st.markdown("---")
                        st.subheader("🔬 РЕЗУЛТАТИ ОТ АНАЛИЗА")
                        
                        if harmful_found:
                            st.error(f"⚠️ **Открити {len(harmful_found)} потенциално вредни съставки!**")
                            for item in harmful_found:
                                st.warning(f"**{item['name'].upper()}** → {item['category']} ({item['type']})")
                            
                            results_data = []
                            for item in harmful_found:
                                results_data.append({
                                    "Съставка / Е-номер": item["name"].upper(),
                                    "Категория": item["category"],
                                    "Тип": item["type"]
                                })
                            df_results = pd.DataFrame(results_data)
                            st.dataframe(df_results, use_container_width=True)
                            
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
                        st.info("Моля, опитай с друга снимка или използвай полето за ръчно въвеждане на текст.")

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
    st.download_button(label="📥 Изтегли пълния списък (CSV)", data=df_full.to_csv(index=False), file_name="all_harmful_ingredients.csv", mime="text/csv")

with tab3:
    st.subheader("ℹ️ Инструкции и важна информация")
    st.markdown("""
    ### Как да използвам приложението?
    1. Качи снимка на етикет на продукт (храна, козметика и др.)
    2. Натисни „Анализирай снимката“
    3. Изчакай няколко секунди (първото стартиране може да е по-бавно)
    4. Виж кои вредни съставки са открити
    
    ### Какво разпознава приложението?
    - Български и английски текст
    - Е-номера (E100-E999)
    
    ### Забележки:
    - Приложението използва **Tesseract OCR**, който е инсталиран на сървъра.
    - Първото стартиране може да отнеме повече време, защото се инсталират системните зависимости.
    - Ако OCR не разпознае добре текста, имаш възможност да въведеш съставките **ръчно** в полето отдолу.
    
    ### Важно:
    Това приложение е **информативно** и не е медицински или експертен съвет.
    """)

st.markdown("---")
st.caption("📌 Версия 2.0 | Базирано на Tesseract OCR | За въпроси и предложения: ...")
