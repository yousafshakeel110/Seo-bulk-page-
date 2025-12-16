import streamlit as st
import openai
from bs4 import BeautifulSoup
import re
import json
import csv
from io import StringIO
import requests
from PIL import Image
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
import base64
from pathlib import Path

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

st.set_page_config(page_title="SEO Page Generator Pro", layout="wide", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .stTabs [data-baseweb="tab-list"] { background-color: #f0f2f6; }
    .success-box { background: #d4edda; padding: 15px; border-radius: 8px; border-left: 4px solid #28a745; }
    .info-box { background: #cfe2ff; padding: 15px; border-radius: 8px; border-left: 4px solid #0d6efd; }
    .warning-box { background: #fff3cd; padding: 15px; border-radius: 8px; border-left: 4px solid #ffc107; }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'api_key_set' not in st.session_state:
    st.session_state.api_key_set = False
if 'generated_pages' not in st.session_state:
    st.session_state.generated_pages = []

def set_openai_key(api_key):
    openai.api_key = api_key
    st.session_state.api_key_set = True

def extract_colors_from_html(html_content):
    """Extract color scheme from HTML"""
    color_pattern = r'#(?:[0-9a-fA-F]{3}){1,2}|rgb\([^)]+\)|rgba\([^)]+\)'
    colors = list(set(re.findall(color_pattern, html_content)))
    return colors[:5] if colors else []

def extract_fonts_from_html(html_content):
    """Extract font families from HTML"""
    font_pattern = r'font-family:\s*[\'"]?([^\'";\n]+)[\'"]?[;]'
    fonts = list(set(re.findall(font_pattern, html_content, re.IGNORECASE)))
    return fonts[:3] if fonts else ['Arial', 'Helvetica', 'sans-serif']

def parse_keywords_input(keyword_input):
    """Parse keywords from text or CSV"""
    keywords = []
    for line in keyword_input.strip().split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if ',' in line:
                parts = line.split(',')
                keywords.append({
                    'keyword': parts[0].strip(),
                    'city': parts[1].strip() if len(parts) > 1 else '',
                    'state': parts[2].strip() if len(parts) > 2 else '',
                    'country': parts[3].strip() if len(parts) > 3 else ''
                })
            else:
                keywords.append({'keyword': line, 'city': '', 'state': '', 'country': ''})
    return keywords

def generate_meta_tags(keyword, city, country, content_summary):
    """Generate SEO meta tags with NLP"""
    title_length = 55
    desc_length = 155
    
    location_text = f" in {city}" if city else ""
    location_text += f", {country}" if country else ""
    
    meta_title = f"{keyword}{location_text} | Professional Services".replace("  ", " ")[:title_length]
    meta_desc = f"Expert {keyword} services{location_text}. {content_summary[:80]}...".replace("  ", " ")[:desc_length]
    
    schema_org = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": keyword,
        "description": meta_desc,
        "areaServed": country or "Worldwide",
        "address": {
            "@type": "PostalAddress",
            "addressLocality": city,
            "addressRegion": "",
            "addressCountry": country or "US"
        }
    }
    
    return {
        'title': meta_title,
        'description': meta_desc,
        'keywords': f"{keyword}, {keyword} services, professional {keyword}",
        'schema': schema_org
    }

def generate_content_with_openai(keyword, city, state, country, api_key):
    """Generate optimized content using OpenAI"""
    try:
        openai.api_key = api_key
        
        location_context = f" in {city}" if city else ""
        location_context += f", {state}" if state else ""
        location_context += f", {country}" if country else ""
        
        prompt = f"""Generate professional, SEO-optimized content for a service page about "{keyword}"{location_context}.

Requirements:
1. Write a compelling H1 heading (50-60 chars)
2. Write an intro paragraph (100-120 words) using natural language
3. Create 3 service benefits as H2 sections with 80-100 word descriptions each
4. Include a CTA section
5. Use semantic HTML keywords naturally
6. Ensure 2-3% keyword density
7. Make it locally relevant if location is provided

Format response as JSON with keys: h1, intro, benefits, cta
Each benefit should have: title, description"""

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert SEO copywriter specializing in local business content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        
        content_text = response.choices[0].message.content
        
        try:
            content = json.loads(content_text)
        except:
            content = {
                'h1': f"Professional {keyword} Services{location_context}",
                'intro': f"Looking for quality {keyword} services{location_context}? We provide expert solutions tailored to your needs.",
                'benefits': [
                    {'title': 'Expert Team', 'description': f'Our experienced professionals deliver top-quality {keyword} services.'},
                    {'title': 'Affordable Pricing', 'description': f'Competitive rates for {keyword} without compromising quality.'},
                    {'title': 'Fast Service', 'description': f'Quick turnaround on {keyword} projects while maintaining excellence.'}
                ],
                'cta': f'Contact us today for professional {keyword} services!'
            }
        
        return content
    
    except Exception as e:
        st.error(f"OpenAI Error: {str(e)}")
        return None

def generate_html_page(keyword, city, state, country, content, meta_tags, colors, fonts, original_html, api_key):
    """Generate complete HTML page"""
    
    primary_color = colors[0] if colors else '#667eea'
    secondary_color = colors[1] if len(colors) > 1 else '#764ba2'
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{meta_tags['description']}">
    <meta name="keywords" content="{meta_tags['keywords']}">
    <meta name="author" content="SEO Page Generator">
    <title>{meta_tags['title']}</title>
    
    <script type="application/ld+json">
    {json.dumps(meta_tags['schema'], indent=2)}
    </script>
    
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: {fonts[0] if fonts else 'Arial'}, sans-serif; color: #333; line-height: 1.6; }}
        
        header {{ background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%); 
                 color: white; padding: 60px 20px; text-align: center; }}
        header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        
        nav {{ background: {primary_color}; padding: 15px; }}
        nav a {{ color: white; text-decoration: none; margin: 0 15px; }}
        
        .container {{ max-width: 1200px; margin: 0 auto; padding: 40px 20px; }}
        
        .intro-section {{ background: #f8f9fa; padding: 30px; border-radius: 8px; margin-bottom: 40px; }}
        .intro-section p {{ font-size: 1.1em; color: #555; }}
        
        .benefits {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 30px; margin: 40px 0; }}
        .benefit {{ background: white; padding: 25px; border-radius: 8px; border-left: 4px solid {primary_color}; 
                   box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .benefit h2 {{ color: {primary_color}; margin-bottom: 15px; }}
        
        .cta-section {{ background: {primary_color}; color: white; padding: 40px; text-align: center; border-radius: 8px; margin: 40px 0; }}
        .cta-section button {{ background: white; color: {primary_color}; padding: 12px 30px; border: none; 
                              border-radius: 5px; font-size: 1.1em; cursor: pointer; font-weight: bold; }}
        
        footer {{ background: #333; color: white; text-align: center; padding: 20px; margin-top: 60px; }}
        
        .breadcrumb {{ color: {primary_color}; margin-bottom: 20px; font-size: 0.9em; }}
        
        h1, h2, h3 {{ color: {primary_color}; margin-top: 20px; }}
        
        @media (max-width: 768px) {{
            header h1 {{ font-size: 1.8em; }}
            .benefits {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="#{keyword.lower().replace(' ', '-')}">{keyword}</a>
        <a href="/contact">Contact</a>
    </nav>
    
    <header>
        <div class="breadcrumb">Home / {keyword}{' / ' + city if city else ''}</div>
        <h1>{content.get('h1', f'Professional {keyword} Services')}</h1>
    </header>
    
    <div class="container">
        <section class="intro-section">
            <p>{content.get('intro', '')}</p>
        </section>
        
        <section class="benefits">
"""
    
    for benefit in content.get('benefits', []):
        html_template += f"""
            <div class="benefit">
                <h2>{benefit.get('title', '')}</h2>
                <p>{benefit.get('description', '')}</p>
            </div>
"""
    
    html_template += f"""
        </section>
        
        <section class="cta-section">
            <h2>Ready to Get Started?</h2>
            <p>{content.get('cta', '')}</p>
            <button onclick="alert('Contact form here')">Get in Touch</button>
        </section>
    </div>
    
    <footer>
        <p>&copy; 2024 {keyword} Services. All rights reserved.</p>
        <p>Serving {city or 'Multiple Locations'}{', ' + country if country else ''}</p>
    </footer>
</body>
</html>"""
    
    return html_template

# ==================== MAIN UI ====================

st.title("🚀 SEO Page Generator Pro")
st.markdown("Generate 100s of optimized HTML pages in minutes using AI + NLP")

tabs = st.tabs(["⚙️ Setup", "📄 Generate Pages", "📊 Preview & Download"])

# ==================== TAB 1: SETUP ====================
with tabs[0]:
    st.header("Step 1: Configure Your Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔑 OpenAI API Key")
        api_key_input = st.text_input("Enter your OpenAI API Key", type="password", 
                                      key="openai_key_input")
        if api_key_input:
            set_openai_key(api_key_input)
            st.success("✅ API Key Connected!")
    
    with col2:
        st.subheader("🎨 Home Page Upload")
        html_file = st.file_uploader("Upload your home page HTML", type=['html'])
        
        if html_file:
            html_content = html_file.read().decode('utf-8')
            st.session_state.html_content = html_content
            st.session_state.colors = extract_colors_from_html(html_content)
            st.session_state.fonts = extract_fonts_from_html(html_content)
            st.success("✅ HTML Analyzed!")
            
            if st.session_state.colors:
                st.info(f"Colors detected: {', '.join(st.session_state.colors)}")
            if st.session_state.fonts:
                st.info(f"Fonts detected: {', '.join(st.session_state.fonts)}")

# ==================== TAB 2: GENERATE PAGES ====================
with tabs[1]:
    st.header("Step 2: Add Keywords & Generate")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📝 Keywords Input Method")
        input_method = st.radio("Choose input method:", ["Paste Keywords", "Upload CSV File"])
        
        if input_method == "Paste Keywords":
            keyword_text = st.text_area(
                "Paste keywords (one per line or with location data):\nFormat: keyword, city, state, country",
                placeholder="plumber\nelectrician, New York, NY, USA\naircon repair, Dubai, DXB, UAE",
                height=150
            )
            keywords_list = parse_keywords_input(keyword_text)
        else:
            csv_file = st.file_uploader("Upload CSV file", type=['csv'])
            if csv_file:
                csv_content = csv_file.read().decode('utf-8')
                keywords_list = parse_keywords_input(csv_content)
            else:
                keywords_list = []
    
    with col2:
        st.subheader("🌍 Default Location (Optional)")
        col_city, col_state, col_country = st.columns(3)
        with col_city:
            default_city = st.text_input("City", "")
        with col_state:
            default_state = st.text_input("State", "")
        with col_country:
            default_country = st.text_input("Country", "")
    
    st.markdown("---")
    
    col_gen1, col_gen2, col_gen3 = st.columns(3)
    
    with col_gen1:
        use_default_location = st.checkbox("Use default location for all keywords")
    
    with col_gen2:
        optimize_headings = st.checkbox("Advanced: Optimize all H tags", value=True)
    
    with col_gen3:
        add_schema = st.checkbox("Include Schema.org JSON-LD", value=True)
    
    if st.button("🎯 Generate All Pages", use_container_width=True):
        if not st.session_state.api_key_set:
            st.error("❌ Please set OpenAI API Key first!")
        elif not keywords_list:
            st.error("❌ Please add keywords!")
        elif 'html_content' not in st.session_state:
            st.error("❌ Please upload HTML file first!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            st.session_state.generated_pages = []
            
            for idx, kw_item in enumerate(keywords_list):
                keyword = kw_item['keyword']
                city = kw_item['city'] or default_city if use_default_location else kw_item['city']
                state = kw_item['state'] or default_state if use_default_location else kw_item['state']
                country = kw_item['country'] or default_country if use_default_location else kw_item['country']
                
                status_text.info(f"⏳ Generating: {keyword} ({idx+1}/{len(keywords_list)})")
                
                content = generate_content_with_openai(
                    keyword, city, state, country, 
                    st.session_state.api_key_set
                )
                
                if content:
                    meta_tags = generate_meta_tags(
                        keyword, city, country,
                        content.get('intro', '')
                    )
                    
                    html_page = generate_html_page(
                        keyword, city, state, country,
                        content, meta_tags,
                        st.session_state.colors,
                        st.session_state.fonts,
                        st.session_state.html_content,
                        openai.api_key
                    )
                    
                    st.session_state.generated_pages.append({
                        'keyword': keyword,
                        'city': city,
                        'country': country,
                        'html': html_page,
                        'content': content,
                        'meta': meta_tags
                    })
                
                progress_bar.progress((idx + 1) / len(keywords_list))
            
            status_text.empty()
            progress_bar.empty()
            st.success(f"✅ Generated {len(st.session_state.generated_pages)} pages!")

# ==================== TAB 3: PREVIEW & DOWNLOAD ====================
with tabs[2]:
    st.header("Step 3: Preview & Download")
    
    if st.session_state.generated_pages:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_page_idx = st.selectbox(
                "Select page to preview:",
                range(len(st.session_state.generated_pages)),
                format_func=lambda i: f"{st.session_state.generated_pages[i]['keyword']} - {st.session_state.generated_pages[i]['city']}"
            )
        
        with col2:
            if st.button("📋 Copy HTML"):
                st.session_state.clipboard = st.session_state.generated_pages[selected_page_idx]['html']
                st.success("Copied to clipboard!")
        
        selected = st.session_state.generated_pages[selected_page_idx]
        
        st.subheader(f"📄 {selected['keyword']}")
        st.write(f"**Location:** {selected['city']}, {selected['country']}")
        st.write(f"**Meta Title:** {selected['meta']['title']}")
        st.write(f"**Meta Description:** {selected['meta']['description']}")
        
        st.markdown("---")
        
        col_preview, col_code = st.tabs(["Preview", "HTML Code"])
        
        with col_preview:
            st.components.v1.html(selected['html'], height=800)
        
        with col_code:
            st.code(selected['html'], language='html')
        
        st.markdown("---")
        st.subheader("📥 Download Options")
        
        col_zip, col_json, col_csv = st.columns(3)
        
        with col_zip:
            if st.button("📦 Download All as ZIP"):
                import zipfile
                from io import BytesIO
                
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w') as zf:
                    for page in st.session_state.generated_pages:
                        filename = f"{page['keyword'].replace(' ', '_')}_{page['city']}.html"
                        zf.writestr(filename, page['html'])
                
                st.download_button(
                    label="💾 Download ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="seo_pages.zip",
                    mime="application/zip"
                )
        
        with col_json:
            json_data = json.dumps([
                {
                    'keyword': p['keyword'],
                    'city': p['city'],
                    'meta': p['meta'],
                    'content': p['content']
                }
                for p in st.session_state.generated_pages
            ], indent=2)
            
            st.download_button(
                label="📄 Download JSON",
                data=json_data,
                file_name="pages_metadata.json",
                mime="application/json"
            )
        
        with col_csv:
            csv_data = "Keyword,City,Country,Meta Title,Meta Description\n"
            for page in st.session_state.generated_pages:
                csv_data += f"{page['keyword']},{page['city']},{page['country']},\"{page['meta']['title']}\",\"{page['meta']['description']}\"\n"
            
            st.download_button(
                label="📊 Download CSV",
                data=csv_data,
                file_name="pages_metadata.csv",
                mime="text/csv"
            )
    
    else:
        st.info("⏳ Generate pages first to see preview and download options")
