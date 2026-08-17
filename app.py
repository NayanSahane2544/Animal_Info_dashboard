import streamlit as st
import pandas as pd
import os
import re
from PIL import Image
import math
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF
import tempfile
import requests
import urllib.parse
import streamlit.components.v1 as components
from pyvis.network import Network
import logging

# ================= 1. ARCHITECTURE & LOGGING =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
st.set_page_config(page_title="Planet Zoo Database", page_icon="🌍", layout="wide")

HEADERS = {
    "User-Agent": "PlanetZooDashboard/1.0 (https://streamlit.io; your_email@example.com)"
}

# ================= 2. DATA LOADING & CONVERSIONS =================
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('dataset.csv')
        
        def extract_avg_num(val):
            try:
                nums = [float(n) for n in re.findall(r'\d+\.?\d*', str(val).replace(',', ''))]
                return sum(nums) / len(nums) if len(nums) > 1 else (nums[0] if len(nums) == 1 else 0.0)
            except: return 0.0
                
        df['Clean_Speed'] = df['Top Speed (km/h)'].apply(extract_avg_num)
        df['Clean_Weight'] = df['Weight (kg)'].apply(extract_avg_num)
        df['Clean_Lifespan'] = df['Lifespan (years)'].apply(extract_avg_num)
        df['Clean_Height'] = df['Height (cm)'].apply(extract_avg_num)
        return df
    except FileNotFoundError:
        st.error("❌ Data file missing! Please ensure 'dataset.csv' is in the folder.")
        return pd.DataFrame()

df = load_data()

def convert_stats(val, metric, to_imperial):
    if not to_imperial: return val
    if metric == 'kg': return val * 2.20462
    if metric == 'cm': return val / 2.54
    if metric == 'km/h': return val / 1.60934
    return val

# ================= 3. EXTERNAL APIs (WIKIPEDIA & AUDIO) =================
@st.cache_data
def fetch_wiki_summary(animal_name, scientific_name=""):
    def get_extract(title):
        safe_title = urllib.parse.quote(title.replace(' ', '_'))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{safe_title}"
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200:
                extract = res.json().get('extract', '')
                sentences = extract.split('. ')
                return '. '.join(sentences[:2]) + '.' if len(sentences) >= 2 else extract
        except: pass
        return None

    def search_title(query):
        safe_query = urllib.parse.quote(query)
        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={safe_query}&limit=1&format=json"
        try:
            res = requests.get(url, headers=HEADERS, timeout=5)
            if res.status_code == 200 and len(res.json()) > 1 and len(res.json()[1]) > 0:
                return res.json()[1][0]
        except: pass
        return None

    for query in [animal_name, scientific_name]:
        if query and query != "Unknown":
            summary = get_extract(query)
            if summary: return summary
            title = search_title(query)
            if title:
                summary = get_extract(title)
                if summary: return summary
    return "Wikipedia summary currently unavailable."

@st.cache_data
def fetch_animal_audio(animal_name, scientific_name=""):
    try:
        search_term = scientific_name if scientific_name and scientific_name != "Unknown" else animal_name
        xc_url = f"https://xeno-canto.org/api/2/recordings?query={urllib.parse.quote(search_term)}"
        res = requests.get(xc_url, timeout=5).json()
        
        if res.get('recordings') and len(res['recordings']) > 0:
            return res['recordings'][0]['file']
    except Exception as e:
        logging.error(f"Xeno-canto fetch failed: {e}")

    try:
        search_url = "https://commons.wikimedia.org/w/api.php"
        queries = [f'"{animal_name}" sound', f'{scientific_name} sound' if scientific_name else ""]
        
        for query in queries:
            if not query.strip() or "Unknown" in query: continue
            
            search_params = {"action": "query", "list": "search", "srsearch": f"{query} filetype:audio", "format": "json"}
            res = requests.get(search_url, params=search_params, headers=HEADERS, timeout=5).json()
            
            if res.get('query', {}).get('search'):
                for item in res['query']['search']:
                    title = item['title']
                    if title.lower().endswith(('.ogg', '.wav', '.mp3')):
                        file_params = {"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url", "format": "json"}
                        file_res = requests.get(search_url, params=file_params, headers=HEADERS).json()
                        pages = file_res['query']['pages']
                        for page_id in pages:
                            return pages[page_id]['imageinfo'][0]['url']
    except Exception as e:
        logging.error(f"Wikimedia audio fetch failed: {e}")
        
    return None

# ================= 4. UI HELPER FUNCTIONS =================
def get_animal_hex_color(color_text):
    for key, hx in {'black':'#444','white':'#F5F5F5','grey':'#808080','brown':'#8B4513','red':'#CD5C5C','yellow':'#DAA520','green':'#2E8B57','blue':'#4682B4'}.items():
        if key in str(color_text).lower(): return hx
    return '#2b5876' 

def get_exact_countries(region_str):
    region_str = str(region_str).lower()
    codes = set()
    
    country_map = {
        'afghanistan': 'AFG', 'albania': 'ALB', 'algeria': 'DZA', 'angola': 'AGO', 'argentina': 'ARG',
        'australia': 'AUS', 'austria': 'AUT', 'bangladesh': 'BGD', 'belarus': 'BLR', 'belgium': 'BEL',
        'belize': 'BLZ', 'bhutan': 'BTN', 'bolivia': 'BOL', 'botswana': 'BWA', 'brazil': 'BRA',
        'bulgaria': 'BGR', 'cambodia': 'KHM', 'cameroon': 'CMR', 'canada': 'CAN', 'chad': 'TCD',
        'chile': 'CHL', 'china': 'CHN', 'colombia': 'COL', 'congo': 'COD', 'costa rica': 'CRI',
        'croatia': 'HRV', 'cuba': 'CUB', 'czech': 'CZE', 'denmark': 'DNK', 'ecuador': 'ECU',
        'egypt': 'EGY', 'ethiopia': 'ETH', 'fiji': 'FJI', 'finland': 'FIN', 'france': 'FRA',
        'gabon': 'GAB', 'germany': 'DEU', 'ghana': 'GHA', 'greece': 'GRC', 'greenland': 'GRL',
        'guatemala': 'GTM', 'guinea': 'GIN', 'guyana': 'GUY', 'honduras': 'HND', 'hungary': 'HUN',
        'iceland': 'ISL', 'india': 'IND', 'indonesia': 'IDN', 'iran': 'IRN', 'iraq': 'IRQ',
        'ireland': 'IRL', 'israel': 'ISR', 'italy': 'ITA', 'jamaica': 'JAM', 'japan': 'JPN',
        'jordan': 'JOR', 'kazakhstan': 'KAZ', 'kenya': 'KEN', 'laos': 'LAO', 'lebanon': 'LBN',
        'liberia': 'LBR', 'libya': 'LBY', 'madagascar': 'MDG', 'malaysia': 'MYS', 'mali': 'MLI',
        'mexico': 'MEX', 'mongolia': 'MNG', 'morocco': 'MAR', 'mozambique': 'MOZ', 'myanmar': 'MMR',
        'namibia': 'NAM', 'nepal': 'NPL', 'netherlands': 'NLD', 'new zealand': 'NZL', 'nicaragua': 'NIC',
        'nigeria': 'NGA', 'north korea': 'PRK', 'norway': 'NOR', 'oman': 'OMN', 'pakistan': 'PAK',
        'panama': 'PAN', 'papua new guinea': 'PNG', 'paraguay': 'PRY', 'peru': 'PER', 'philippines': 'PHL',
        'poland': 'POL', 'portugal': 'PRT', 'romania': 'ROU', 'russia': 'RUS', 'rwanda': 'RWA',
        'saudi arabia': 'SAU', 'senegal': 'SEN', 'serbia': 'SRB', 'somalia': 'SOM', 'south africa': 'ZAF',
        'south korea': 'KOR', 'spain': 'ESP', 'sri lanka': 'LKA', 'sudan': 'SDN', 'suriname': 'SUR',
        'sweden': 'SWE', 'switzerland': 'CHE', 'syria': 'SYR', 'taiwan': 'TWN', 'tanzania': 'TZA',
        'thailand': 'THA', 'tunisia': 'TUN', 'turkey': 'TUR', 'uganda': 'UGA', 'ukraine': 'UKR',
        'united arab emirates': 'ARE', 'united kingdom': 'GBR', 'united states': 'USA', 'uruguay': 'URY',
        'uzbekistan': 'UZB', 'venezuela': 'VEN', 'vietnam': 'VNM', 'yemen': 'YEM', 'zambia': 'ZMB',
        'zimbabwe': 'ZWE'
    }
    
    regions = {
        'sub-saharan africa': ['ZAF','KEN','TZA','NGA','COD','AGO','NAM','BWA','ZWE','UGA','ETH','SDN','ZMB','GHA','MLI','SEN','CMR','RWA','MDG','MOZ'],
        'north africa': ['EGY', 'DZA', 'LBY', 'SDN', 'MAR', 'TUN'],
        'africa': ['ZAF','KEN','TZA','NGA','EGY','COD','AGO','NAM','BWA','ZWE','MAR','DZA','LBY','SDN','ETH','SOM','UGA','ZMB','GHA','MLI','SEN','CMR','MDG','MOZ'],
        'south america': ['BRA','ARG','PER','COL','VEN','CHL','ECU','BOL','PRY','URY','GUY','SUR'],
        'central america': ['MEX','GTM','CRI','PAN','NIC','HND','BLZ','SLV'],
        'north america': ['USA','CAN','MEX'],
        'americas': ['USA','CAN','MEX','BRA','ARG','PER','COL','VEN','CHL','ECU','BOL','GTM','CRI','PAN','HND'],
        'europe': ['FRA','DEU','ITA','ESP','GBR','SWE','NOR','POL','ROU','FIN','UKR','BLR','GRC','CHE','AUT','NLD','BEL','CZE','PRT'],
        'eurasia': ['FRA','DEU','ITA','ESP','GBR','SWE','NOR','POL','ROU','RUS','CHN','KAZ','MNG','UKR','TUR','IRN'],
        'southeast asia': ['IDN','THA','MYS','VNM','PHL','KHM','MMR','LAO','SGP','BRN'],
        'asia': ['CHN','IND','IDN','THA','MYS','VNM','JPN','KAZ','MNG','IRN','PAK','BGD','SAU','KOR','PRK','NPL','LKA','MMR','KHM','LAO','PHL'],
        'middle east': ['SAU','IRN','IRQ','OMN','YEM','ARE','SYR','JOR','ISR','LBN','KWT','QAT'],
        'oceania': ['AUS','NZL','PNG','FJI','SLB','VUT'],
        'arctic': ['CAN','RUS','GRL','NOR','USA','ISL','SWE','FIN'],
        'himalayas': ['NPL','IND','BTN','CHN','PAK'],
        'amazon basin': ['BRA','PER','COL','VEN','ECU','BOL','GUY','SUR'],
        'sahara': ['DZA','TCD','EGY','LBY','MLI','MRT','MAR','NER','SDN','TUN'],
        'western africa': ['NGA','GHA','SEN','MLI','CIV','BFA','NER','BEN','TGO','GMB'],
        'eastern africa': ['KEN','TZA','ETH','UGA','SDN','RWA','BDI','MDV'],
        'amazon rainforest': ['BRA','PER','COL','VEN','ECU','BOL','GUY','SUR'],
        'galapagos islands': ['ECU'],
        'andaman islands': ['IND'],
        'borneo': ['IDN','MYS','BRN'],
        'sumatra': ['IDN'],
    }

    for key, iso in country_map.items():
        if key in region_str: codes.add(iso)
    for key, isos in regions.items():
        if re.search(r'\b' + re.escape(key) + r'\b', region_str): codes.update(isos)
            
    if not codes or 'worldwide' in region_str or 'ocean' in region_str or 'coastal' in region_str:
        codes.update(['USA', 'CHN', 'IND', 'BRA', 'ZAF', 'AUS', 'RUS', 'CAN', 'IDN', 'MEX', 'JPN', 'GRL', 'NOR', 'CHL', 'ARG', 'ZWE', 'KEN', 'FRA'])
        
    return list(codes)

# ================= 5. PDF GENERATOR ENGINE =================
def create_pdf_report(animal_name, data_row, img_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_fill_color(43, 88, 118)
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("Arial", 'B', 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, f"{animal_name} Report", ln=True, align='C')
    
    pdf.set_font("Arial", 'I', 14)
    pdf.cell(0, 10, f"Scientific Name: {data_row.get('Scientific Name', 'Unknown')}", ln=True, align='C')
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)
    
    if img_path and os.path.exists(img_path):
        pdf.image(img_path, x=65, y=55, w=80)
        pdf.ln(85)
    else: pdf.ln(10)
        
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Biological Statistics", ln=True)
    pdf.ln(2)
    
    stats_to_print = {
        'Family': data_row.get('Family', 'N/A'),
        'Diet': data_row.get('Diet', 'N/A'),
        'Status': data_row.get('Conservation Status', 'N/A'),
        'Habitat': data_row.get('Habitat', 'N/A'),
        'Height/Length': f"{data_row.get('Height (cm)', 'N/A')} cm",
        'Weight': f"{data_row.get('Weight (kg)', 'N/A')} kg",
        'Top Speed': f"{data_row.get('Top Speed (km/h)', 'N/A')} km/h",
        'Lifespan': f"{data_row.get('Lifespan (years)', 'N/A')} years"
    }
    
    for key, val in stats_to_print.items():
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(50, 10, f"{key}:", border=1)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"{str(val).encode('ascii', 'ignore').decode('ascii')}", border=1, ln=True)
        
    return pdf.output(dest="S").encode("latin1")

# ================= MAIN APP =================
if not df.empty:
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Planet_Zoo_logo.png/640px-Planet_Zoo_logo.png", use_container_width=True)
        st.header("🔍 Zoo Filters")
        
        selected_diet = st.selectbox("🍽️ Filter by Diet", ["All"] + list(df['Diet'].dropna().unique()))
        selected_status = st.selectbox("🛡️ Filter by Status", ["All"] + list(df['Conservation Status'].dropna().unique()))

    filtered_df = df.copy()
    if selected_diet != "All": filtered_df = filtered_df[filtered_df['Diet'] == selected_diet]
    if selected_status != "All": filtered_df = filtered_df[filtered_df['Conservation Status'] == selected_status]
    animal_list = filtered_df['Animal'].sort_values().unique()

    st.markdown("<h1 style='text-align: center; color: white; text-shadow: 2px 2px 4px #000000;'>🌍 Planet Zoo Interactive Database</h1>", unsafe_allow_html=True)
    
    # ADDED: The 3 Tabs including the new Compare Mode
    tab1, tab2, tab3 = st.tabs(["🦁 Animal Profile", "⚖️ Compare Mode", "📈 Global Analytics"])

    # ================= TAB 1: ANIMAL PROFILE =================
    with tab1:
        if len(animal_list) == 0:
            st.warning("No animals match the selected filters.")
        else:
            selected_animal = st.selectbox("Select an Animal to view its profile:", animal_list)
            animal_data = filtered_df[filtered_df['Animal'] == selected_animal].iloc[0]
            
            # --- DYNAMIC BACKGROUND COLOR ---
            theme_color = get_animal_hex_color(animal_data['Color'])
            bg_color = f"{theme_color}15" 
            
            st.markdown(f"""
            <style>
                .stApp {{ background-color: {bg_color}; transition: background-color 0.5s ease; }}
                .stat-card {{
                    background-color: rgba(20, 20, 20, 0.85); color: white; padding: 20px;
                    border-radius: 12px; border-left: 8px solid {theme_color}; margin-bottom: 15px;
                    box-shadow: 0 8px 16px rgba(0,0,0,0.4);
                }}
                .stat-card b {{ color: {theme_color}; filter: brightness(1.3); }}
                .stProgress > div > div > div > div {{ background-color: {theme_color}; }}
            </style>
            """, unsafe_allow_html=True)

            st.markdown("---")
            col1, col2 = st.columns([1, 1.2])
            
            # --- IMAGE HANDLING ---
            with col1:
                st.header(selected_animal)
                st.caption(f"**Family:** {animal_data['Family']} | **Diet:** {animal_data['Diet']} | **Color:** {animal_data['Color']}")
                
                clean_name = str(selected_animal).replace('/', '-').replace(':', '')
                image_found = False
                possible_dirs = ["images", "./images", "../images", os.path.join(os.getcwd(), "images")]
                
                for img_dir in possible_dirs:
                    if os.path.exists(img_dir):
                        for ext in ['.jpg', '.jpeg', '.png']:
                            img_path = os.path.join(img_dir, clean_name + ext)
                            if os.path.exists(img_path):
                                try:
                                    img = Image.open(img_path)
                                    width, height = img.size
                                    target_ratio = 16/9
                                    if width / height > target_ratio:
                                        new_width = int(target_ratio * height)
                                        img = img.crop(((width - new_width) / 2, 0, (width + new_width) / 2, height))
                                    else:
                                        new_height = int(width / target_ratio)
                                        img = img.crop((0, (height - new_height) / 2, width, (height + new_height) / 2))
                                    img = img.resize((800, 450), Image.Resampling.LANCZOS)
                                    st.image(img, use_container_width=True, style={"border-radius": "15px"})
                                except Exception:
                                    st.image(img_path, use_container_width=True) # Fallback to raw image
                                image_found = True
                                break
                    if image_found: break
                
                if not image_found:
                    st.error(f"🖼️ Could not find `{clean_name}.jpg`. Ensure your 'images' folder is in the same directory as app.py.")

                # ================= 🚨 ULTIMATE MAP FIX 🚨 =================
                st.subheader("📍 Habitat Region")
                iso_codes = get_exact_countries(animal_data['Countries Found'])
                
                if not iso_codes:
                    iso_codes = ['USA'] 

                # Plotly Graph Objects solves the invisible map bug permanently
                fig = go.Figure(data=go.Choropleth(
                    locations=iso_codes,
                    z=[1] * len(iso_codes), 
                    locationmode='ISO-3',
                    colorscale=[[0, theme_color], [1, theme_color]], 
                    showscale=False, 
                    marker_line_color='rgba(255,255,255,0.8)', 
                    marker_line_width=1.5
                ))
                
                fig.update_layout(
                    height=400, # Forces a physical height to prevent collapse
                    margin=dict(l=0, r=0, t=0, b=0), 
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)',
                    geo=dict(
                        showframe=False, 
                        showcoastlines=True, coastlinecolor="rgba(255,255,255,0.3)",
                        showcountries=True, countrycolor="rgba(255,255,255,0.1)",
                        showland=True, landcolor="#2b2b2b",  # Solid dark land
                        showocean=True, oceancolor="#0e1117", # Solid dark ocean 
                        projection_type='equirectangular',
                        bgcolor='rgba(0,0,0,0)'
                    )
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # --- STATS ---
            with col2:
                st.subheader("🧬 Biological Statistics")
                
                st.markdown(f"**Height / Length:** {animal_data['Height (cm)']} cm")
                st.progress(min(animal_data['Clean_Height'] / 500.0, 1.0))

                st.markdown(f"**Weight:** {animal_data['Weight (kg)']} kg")
                st.progress(min(math.log10(max(animal_data['Clean_Weight'], 1)) / 5.0, 1.0) if animal_data['Clean_Weight'] > 0 else 0)

                st.markdown(f"**Top Speed:** {animal_data['Top Speed (km/h)']} km/h")
                st.progress(min(animal_data['Clean_Speed'] / 120.0, 1.0))
                
                st.write("---")
                st.markdown(f'<div class="stat-card"><b>🛡️ Status:</b><br>{animal_data["Conservation Status"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-card"><b>🌳 Environment:</b><br>{animal_data["Habitat"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-card"><b>🦅 Predators:</b><br>{animal_data["Predators"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="stat-card"><b>👨‍👩‍👧‍👦 Social Structure:</b><br>{animal_data["Social Structure"]}</div>', unsafe_allow_html=True)

    # ================= TAB 2: COMPARE MODE =================
    with tab2:
        st.header("⚖️ Head-to-Head Comparison")
        comp1, comp2 = st.columns(2)
        
        # User selects two animals to compare
        with comp1: 
            a1 = st.selectbox("Select First Animal", df['Animal'].sort_values().unique(), index=0)
        with comp2: 
            # Default to second index if available
            default_index = 1 if len(df['Animal'].unique()) > 1 else 0
            a2 = st.selectbox("Select Second Animal", df['Animal'].sort_values().unique(), index=default_index)
        
        if a1 and a2:
            d1 = df[df['Animal'] == a1].iloc[0]
            d2 = df[df['Animal'] == a2].iloc[0]
            categories = ['Speed', 'Weight (Log)', 'Lifespan', 'Height (Log)']
            
            # Normalize stats so they can be plotted neatly on the same scale (0.0 to 1.0)
            r1 = [
                d1['Clean_Speed'] / 120.0, 
                math.log10(max(d1['Clean_Weight'], 1)) / 5.0, 
                d1['Clean_Lifespan'] / 100.0, 
                math.log10(max(d1['Clean_Height'], 1)) / 3.0
            ]
            r2 = [
                d2['Clean_Speed'] / 120.0, 
                math.log10(max(d2['Clean_Weight'], 1)) / 5.0, 
                d2['Clean_Lifespan'] / 100.0, 
                math.log10(max(d2['Clean_Height'], 1)) / 3.0
            ]
            
            # Build the interactive Radar Chart
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=r1, theta=categories, fill='toself', name=a1))
            fig.add_trace(go.Scatterpolar(r=r2, theta=categories, fill='toself', name=a2))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=False)), 
                showlegend=True, 
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    # ================= TAB 3: GLOBAL ANALYTICS =================
    with tab3:
        st.header("🏆 Global Analytics & Relationships")
        
        # Core Analytics Scatter Plots
        c_scatter1, c_scatter2 = st.columns(2)
        with c_scatter1:
            st.subheader("Height vs. Weight Analysis")
            scatter1 = px.scatter(df, x="Clean_Weight", y="Clean_Height", color="Diet", hover_name="Animal", 
                                  log_x=True, log_y=True, labels={"Clean_Weight": "Weight (kg) [Log]", "Clean_Height": "Height (cm) [Log]"})
            scatter1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(scatter1, use_container_width=True)
            
        with c_scatter2:
            st.subheader("Speed vs. Weight Analysis")
            scatter2 = px.scatter(df, x="Clean_Weight", y="Clean_Speed", color="Diet", hover_name="Animal", 
                                  log_x=True, labels={"Clean_Weight": "Weight (kg) [Log]", "Clean_Speed": "Top Speed (km/h)"})
            scatter2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(scatter2, use_container_width=True)

        st.markdown("---")
        st.header("📊 Top 10 Leaderboards")

        def create_top_10_chart(data_col, title, color_scale, label_x):
            top10 = df.nlargest(10, data_col).sort_values(by=data_col, ascending=True)
            chart = px.bar(top10, x=data_col, y="Animal", orientation='h', color=data_col, 
                           color_continuous_scale=color_scale, title=title, text_auto='.1f', labels={data_col: label_x})
            chart.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False)
            return chart

        c1, c2 = st.columns(2)
        with c1: st.plotly_chart(create_top_10_chart('Clean_Speed', 'Fastest Animals', 'Reds', 'Speed (km/h)'), use_container_width=True)
        with c2: st.plotly_chart(create_top_10_chart('Clean_Lifespan', 'Longest Lifespans', 'Greens', 'Lifespan (years)'), use_container_width=True)

        c3, c4 = st.columns(2)
        with c3: st.plotly_chart(create_top_10_chart('Clean_Weight', 'Heaviest Animals', 'Blues', 'Weight (kg)'), use_container_width=True)
        with c4: st.plotly_chart(create_top_10_chart('Clean_Height', 'Tallest/Longest Animals', 'Purples', 'Height (cm)'), use_container_width=True)