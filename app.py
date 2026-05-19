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
    "Парабени (консерванти)": {
        "bg": ["метилпарабен", "етилпарабен", "пропилпарабен", "бутилпарабен"],
        "en": ["methylparaben", "ethylparaben", "propylparaben", "butylparaben"],
        "e": [],
        "description": "Използват се като консерванти в козметика и храни. Свързват се с хормонални нарушения, имитират естроген и могат да повлияят на репродуктивната система. Някои проучвания сочат връзка с рак на гърдата.",
        "used_for": "Консервант против мухъл, бактерии и дрожди"
    },
    "Сулфати (пянообразуватели)": {
        "bg": ["натриев лаурил сулфат", "натриев лаурет сулфат"],
        "en": ["sodium lauryl sulfate", "sodium laureth sulfate", "sls", "sles"],
        "e": [],
        "description": "Дразнят кожата, очите и скалпа. Могат да причинят дерматит, акне и да изсушават косата. При дългосрочна употреба могат да увредят кожната бариера.",
        "used_for": "Пянообразувател в шампоани, пасти за зъби, сапуни"
    },
    "Формалдехид": {
        "bg": ["формалдехид"],
        "en": ["formaldehyde"],
        "e": ["E240"],
        "description": "Канцероген от категория 1 (доказан при хора). Може да причини алергични реакции, дразнене на дихателните пътища, астма и главоболие. Свързва се с рак на носа и левкемия.",
        "used_for": "Консервант, дезинфектант, в козметиката като консервант"
    },
    "Аспартам": {
        "bg": ["аспартам"],
        "en": ["aspartame"],
        "e": ["E951"],
        "description": "Изкуствен подсладител. Проучвания сочат възможна връзка с главоболие, световъртеж, промени в настроението, депресия и дори тумори на мозъка при животни. Противопоказен за хора с фенилкетонурия.",
        "used_for": "Подсладител в безалкохолни напитки, дъвки, десерти"
    },
    "Глутамат натрий (MSG)": {
        "bg": ["мононатриев глутамат", "глутаминова киселина"],
        "en": ["monosodium glutamate", "msg"],
        "e": ["E621"],
        "description": "Усилвател на вкуса. Може да предизвика т.нар. 'синдром на китайския ресторант' - главоболие, гадене, слабост, сърцебиене. При чувствителни хора може да причини астматични пристъпи.",
        "used_for": "Усилвател на вкуса в готови храни, чипсове, супи"
    },
    "Натриев бензоат": {
        "bg": ["натриев бензоат", "бензоена киселина"],
        "en": ["sodium benzoate", "benzoic acid"],
        "e": ["E211", "E210"],
        "description": "Консервант. В комбинация с аскорбинова киселина (витамин С) може да образува бензен - доказан канцероген. Може да предизвика алергични реакции и да влоши симптомите на ADHD при деца.",
        "used_for": "Консервант в безалкохолни напитки, сосове, сладка"
    },
    "Тартразин (E102)": {
        "bg": ["тартразин"],
        "en": ["tartrazine"],
        "e": ["E102"],
        "description": "Изкуствен жълт оцветител. Може да предизвика алергични реакции, обриви, астма. Свързва се с хиперактивност при деца (ADHD). Забранен в някои държави.",
        "used_for": "Жълт оцветител в бонбони, напитки, десерти"
    },
    "Сончев залез (E110)": {
        "bg": ["сончев залез"],
        "en": ["sunset yellow"],
        "e": ["E110"],
        "description": "Изкуствен жълто-оранжев оцветител. Свързва се с алергични реакции, уртикария, стомашно разстройство и хиперактивност при деца.",
        "used_for": "Оцветител в сосове, супи, напитки, сладолед"
    },
    "Захарин": {
        "bg": ["захарин", "сахарин"],
        "en": ["saccharin"],
        "e": ["E954"],
        "description": "Изкуствен подсладител. В миналото е бил свързван с рак на пикочния мехур при животни. Въпреки че по-нови проучвания го оправдават, остава противоречив.",
        "used_for": "Подсладител в диетични напитки и нискокалорични храни"
    },
    "BHA / BHT": {
        "bg": ["бутилхидроксианизол", "бутилхидрокситолуен"],
        "en": ["bha", "bht"],
        "e": ["E320", "E321"],
        "description": "Антиоксиданти и консерванти. Класифицирани като 'възможни канцерогени за човека' (IARC категория 2B). Могат да повлияят на хормоналния баланс и функцията на черния дроб.",
        "used_for": "Консерванти в мазнини, масла, зърнени закуски, дъвки"
    },
    "Цикламат": {
        "bg": ["цикламат"],
        "en": ["cyclamate"],
        "e": ["E952"],
        "description": "Изкуствен подсладител. Забранен в САЩ поради съмнения за канцерогенност. Може да причини увреждане на тестисите и да повлияе на плодовитостта.",
        "used_for": "Подсладител в нискокалорични храни и напитки"
    },
    "Ацесулфам К": {
        "bg": ["ацесулфам"],
        "en": ["acesulfame k"],
        "e": ["E950"],
        "description": "Изкуствен подсладител. Проучвания сочат възможна връзка с тумори при лабораторни животни. Може да стимулира отделянето на инсулин (повишава апетита).",
        "used_for": "Подсладител в безалкохолни напитки, сладкиши"
    },
    "Калиев сорбат": {
        "bg": ["калиев сорбат"],
        "en": ["potassium sorbate"],
        "e": ["E202"],
        "description": "Консервант. Може да предизвика алергични реакции, дразнене на кожата и очите. В редки случаи - генотоксични ефекти.",
        "used_for": "Консервант в сирена, вина, сосове, козметика"
    },
    "Фосфорна киселина": {
        "bg": ["фосфорна киселина"],
        "en": ["phosphoric acid"],
        "e": ["E338"],
        "description": "Регулатор на киселинността. Може да увреди зъбния емайл, да намали костната плътност (остеопороза) и да натовари бъбреците.",
        "used_for": "Киселина в кола напитките"
    },
    "Пропилен гликол": {
        "bg": ["пропилен гликол"],
        "en": ["propylene glycol"],
        "e": ["E490"],
        "description": "Овлажнител и разтворител. Може да предизвика дразнене на кожата, контактен дерматит и алергични реакции. Във високи дози е токсичен за бъбреците и черния дроб.",
        "used_for": "В козметика, храни, фармацевтични продукти"
    }
}

# Подготовка на сета за търсене
search_set = set()
info_dict = {}
# Функция за търсене (модифицирана)
def find_harmful(text: str):
    if not text:
        return []
    text_lower = text.lower()
    found = []
    
    # Търсене на Е-номера
    e_matches = re.findall(r'e[0-9]{3}', text_lower)
    for e in e_matches:
        e_upper = f"E{e[1:].upper()}"
        # Търсене в базата данни
        for category, data in harmful_db.items():
            if e_upper in data["e"]:
                found.append({
                    "term": e_upper,
                    "category": category,
                    "type": "🔢 Е-номер",
                    "description": data["description"],
                    "used_for": data["used_for"]
                })
                break
    
    # Търсене на имена (български и английски)
    for category, data in harmful_db.items():
        all_names = data["bg"] + data["en"]
        for name in all_names:
            if name.lower() in text_lower:
                found.append({
                    "term": name.title(),
                    "category": category,
                    "type": "📝 Име",
                    "description": data["description"],
                    "used_for": data["used_for"]
                })
                break  # Спри след първото съвпадение в категорията
    
    # Премахване на дубликати
    unique = []
    seen = set()
    for item in found:
        if item["term"] not in seen:
            seen.add(item["term"])
            unique.append(item)
    return unique

# --- ПОКАЗВАНЕ НА РЕЗУЛТАТИ С ОПИСАНИЕ ---
if harmful_found:
    st.error(f"⚠️ **Открити {len(harmful_found)} потенциално вредни съставки!**")
    
    for item in harmful_found:
        with st.expander(f"{item['type']} **{item['term'].upper()}** → {item['category']}"):
            st.markdown(f"**🔬 За какво се използва:** {item['used_for']}")
            st.markdown(f"**⚠️ Защо е вредна:** {item['description']}")
else:
    st.success("✅ **НЕ СА ОТКРИТИ ВРЕДНИ СЪСТАВКИ!**")

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
