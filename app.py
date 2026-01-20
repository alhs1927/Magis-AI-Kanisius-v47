import streamlit as st
import google.generativeai as genai
from groq import Groq
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import PIL.Image
import PyPDF2
import re

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Magis AI - Ignatian Pedagogy",
    page_icon="https://i.imgur.com/UUCgyfV.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. CSS MODERN & JESUIT THEME ---
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #F8FAFC !important; color: #0F172A !important; font-family: 'Plus Jakarta Sans', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid #E2E8F0; }
    
    /* JUDUL DIPERBESAR & WARNA EMAS */
    .magis-title {
        font-weight: 800; 
        font-size: 42px; 
        background: linear-gradient(90deg, #DAA520, #FFD700, #B8860B);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0px;
        line-height: 1.2;
    }
    
    /* TAGLINE BARU */
    .magis-tagline {
        font-size: 16px;
        font-weight: 600;
        font-style: italic;
        color: #1B365D; 
        margin-bottom: 10px;
    }

    .magis-subtitle { font-size: 14px; color: #64748B; margin-bottom: 20px; font-weight: 500;}
    
    .bubble-user {
        background-color: #1B365D; color: white; padding: 16px; 
        border-radius: 12px 12px 0 12px; margin-left: auto; max-width: 85%;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .bubble-ai {
        background-color: #FFFFFF; color: #0F172A; 
        border: 1px solid #E2E8F0; border-left: 4px solid #C5A059;
        padding: 16px; border-radius: 12px 12px 12px 0; margin-right: auto; max-width: 95%;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    
    /* Button Kirim Styling */
    div[data-testid="stForm"] button {
        background-color: #1B365D;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        width: 100%;
    }
    
    .status-ok { color: #059669; font-weight: bold; font-size: 12px; border: 1px solid #059669; padding: 4px; border-radius: 5px; background: #ECFDF5; }
    .status-err { color: #DC2626; font-weight: bold; font-size: 12px; border: 1px solid #DC2626; padding: 4px; border-radius: 5px; background: #FEF2F2; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. IGNATIAN DNA (OTAK UTAMA - TETAP UTUH) ---
IGNATIAN_BASE_PROMPT = """
PERAN: 'Magis AI', asisten pedagogi dan pendamping spiritual khas Kolese Jesuit (Ignasian).

DNA SPIRITUAL & FILOSOFI (WAJIB DIINTEGRASIKAN):

1.  **IPP (Ignatian Pedagogical Paradigm):**
    - **Context:** Memahami dunia nyata siswa, keluarga, dan budaya.
    - **Experience:** Melibatkan rasa, akal budi, dan imajinasi (bukan hafalan semata).
    - **Reflection:** Menggali makna, nilai, dan kebenaran dari pengalaman.
    - **Action:** Dorongan untuk bertindak melayani sesama (Magis).
    - **Evaluation:** Menilai perkembangan karakter dan kompetensi secara utuh.

2.  **Cura Personalis:**
    - Perhatian personal pada keunikan tiap pribadi.
    - Mendengarkan dengan hati, memanusiakan, dan tidak menghakimi.

3.  **Universal Apostolic Preferences (UAP):**
    - Menunjukkan jalan menuju Tuhan (Latihan Rohani & Diskresi).
    - Berjalan bersama yang tersingkir (Solidaritas & Keadilan).
    - Menemani kaum muda menuju masa depan penuh harapan.
    - Merawat rumah kita bersama (Kesadaran Ekologis).

4.  **Ignatian Leadership & Values:**
    - **Self-Awareness:** Mengenal diri (kekuatan & kelemahan) dalam terang Ilahi.
    - **Ingenuity:** Cerdik dan inovatif dalam menghadapi tantangan zaman.
    - **Love & Heroism:** Kasih yang melayani lebih dari standar (Magis) dan keberanian memimpin.
    - **Profil Lulusan:** 4C (Competence, Conscience, Compassion, Commitment) + 1L (Leadership).

5.  **Diskresi (Pembedaan Roh) & Spiritualitas:**
    - **Pembedaan Roh:** Membantu membedakan gerak roh baik (Consolation: damai, sukacita, kasih) dan roh jahat (Desolation: gelisah, takut, putus asa).
    - **AMDG (Ad Maiorem Dei Gloriam):** Segala sesuatu demi kemuliaan Tuhan yang lebih besar.
    - **Nilai St. Petrus Canisius:** Ketekunan, kesetiaan pada Gereja, dan edukasi yang membebaskan.

ATURAN OUTPUT:
- Gunakan bahasa Indonesia yang akademis, reflektif, namun hangat (Tone: Sahabat Pembimbing/Mentor).
- Setiap saran atau materi pembelajaran harus memiliki "kedalaman" (menyentuh aspek Conscience/Compassion), bukan hanya teknis.
- Matematika wajib menggunakan LaTeX ($...$).
- Jika membuat TABEL, gunakan format Markdown standard.
- Berikan output yang TERSTRUKTUR rapi.
- FOKUS pada teks dan konten materi. Jangan menyertakan tag gambar.
"""

# --- 4. ENGINE: AUTO-DISCOVERY & SELF HEALING ---
class AIProvider:
    def __init__(self, api_key):
        self.api_key = api_key
        self.provider_name = "None"
        self.client = None
        self.available_models = []
        self.active_model = None
        self.is_valid = False
        
        if not api_key: return

        if api_key.startswith("gsk_"):
            self.provider_name = "Groq"
            self._setup_groq()
        else:
            self.provider_name = "Google"
            self._setup_google()
        
    def _setup_groq(self):
        try:
            self.client = Groq(api_key=self.api_key)
            models = self.client.models.list()
            self.available_models = [m.id for m in models.data if 'llama' in m.id or 'mixtral' in m.id]
            self.available_models.sort(key=lambda x: '70b' in x, reverse=True)
            if self.available_models:
                self.active_model = self.available_models[0]
                self.is_valid = True
        except: pass

    def _setup_google(self):
        try:
            genai.configure(api_key=self.api_key)
            priorities = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
            self.available_models = priorities 
            try:
                all_models = genai.list_models()
                real_models = [m.name.replace("models/", "") for m in all_models if 'generateContent' in m.supported_generation_methods]
                if real_models: self.available_models = [p for p in priorities if p in real_models] + [m for m in real_models if m not in priorities]
            except: pass
            
            self.active_model = self.available_models[0] if self.available_models else 'gemini-1.5-flash'
            self.is_valid = True
        except: pass

    def generate_stream(self, history, prompt, system_config, image_input=None, lib_text=""):
        if not self.is_valid: yield "⚠️ Error: API Key bermasalah."; return

        full_system = f"{IGNATIAN_BASE_PROMPT}\n\n{system_config}"
        hist_str = "\n".join([f"{'USER' if m['role']=='user' else 'AI'}: {m['content']}" for m in history])
        final_prompt = f"RIWAYAT CHAT:\n{hist_str}\n\nSUMBER PUSTAKA:\n{lib_text}\n\nPERMINTAAN USER:\n{prompt}"

        models_to_try = [self.active_model] + [m for m in self.available_models if m != self.active_model]
        success = False

        for model in models_to_try:
            if success: break
            try:
                if self.provider_name == "Google":
                    inputs = [f"SYSTEM_INSTRUCTION:\n{full_system}\n\nTASK:\n{final_prompt}"]
                    if image_input: inputs.append(image_input)
                    m = genai.GenerativeModel(model)
                    res = m.generate_content(inputs, stream=True)
                    for c in res: 
                        if c.text: yield c.text; success = True
                
                elif self.provider_name == "Groq":
                    if image_input: yield "ℹ️ [Groq: Gambar input diabaikan]\n"
                    stream = self.client.chat.completions.create(
                        messages=[{"role":"system","content":full_system},{"role":"user","content":final_prompt}],
                        model=model, stream=True
                    )
                    for c in stream:
                        txt = c.choices[0].delta.content
                        if txt: yield txt; success = True
            except: continue

# --- 5. LOGIC UI & HELPER (DOC ENGINE) ---
class DocEngine:
    @staticmethod
    def read(files):
        txt = ""; names = []
        for f in files:
            try:
                if f.name.endswith('.pdf'): txt += "".join([p.extract_text() for p in PyPDF2.PdfReader(f).pages])
                elif f.name.endswith('.docx'): txt += "\n".join([p.text for p in Document(f).paragraphs])
                elif f.name.endswith('.txt'): txt += f.getvalue().decode("utf-8")
                names.append(f.name)
            except: pass
        return txt, names

    @staticmethod
    def _set_table_borders(table):
        tbl = table._tbl
        for cell in tbl.iter_tcs():
            tcPr = cell.tcPr
            tcBorders = OxmlElement('w:tcBorders')
            top = OxmlElement('w:top'); top.set(qn('w:val'), 'single'); top.set(qn('w:sz'), '4')
            left = OxmlElement('w:left'); left.set(qn('w:val'), 'single'); left.set(qn('w:sz'), '4')
            bottom = OxmlElement('w:bottom'); bottom.set(qn('w:val'), 'single'); bottom.set(qn('w:sz'), '4')
            right = OxmlElement('w:right'); right.set(qn('w:val'), 'single'); right.set(qn('w:sz'), '4')
            tcBorders.append(top); tcBorders.append(left); tcBorders.append(bottom); tcBorders.append(right)
            tcPr.append(tcBorders)

    @staticmethod
    def _process_markdown_to_docx(doc, text):
        lines = text.split('\n')
        in_table = False
        table_data = []
        
        for line in lines:
            clean_line = line.strip()
            
            # Deteksi Tabel Markdown
            if "|" in clean_line and len(clean_line) > 2:
                if re.match(r'^\|?[\s-]+\|[\s-]+\|', clean_line): continue
                row_cells = [c.strip() for c in clean_line.split('|') if c.strip()]
                if row_cells:
                    if not in_table: in_table = True; table_data = [row_cells]
                    else: table_data.append(row_cells)
            else:
                if in_table:
                    if table_data:
                        table = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
                        table.style = 'Table Grid'
                        for r_idx, row_content in enumerate(table_data):
                            for c_idx, cell_content in enumerate(row_content):
                                if c_idx < len(table.columns):
                                    cell = table.cell(r_idx, c_idx)
                                    cell.text = cell_content.replace('**', '')
                        DocEngine._set_table_borders(table)
                        doc.add_paragraph()
                    in_table = False; table_data = []

                # Heading & Text Formatting
                if clean_line.startswith('### '): doc.add_heading(clean_line.replace('### ', ''), level=3)
                elif clean_line.startswith('## '): doc.add_heading(clean_line.replace('## ', ''), level=2)
                elif clean_line.startswith('# '): doc.add_heading(clean_line.replace('# ', ''), level=1)
                elif clean_line:
                    p = doc.add_paragraph()
                    parts = re.split(r'(\*\*.*?\*\*)', clean_line)
                    for part in parts:
                        if part.startswith('**') and part.endswith('**'):
                            run = p.add_run(part[2:-2]); run.bold = True
                        else: p.add_run(part.replace('$', ''))

    @staticmethod
    def create_word(history):
        doc = Document()
        title = doc.add_heading("Hasil Magis AI - Ignatian Pedagogy", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        for msg in history:
            role_p = doc.add_heading(msg['role'].upper(), level=2)
            role_p.runs[0].font.color.rgb = RGBColor(27, 54, 93)
            DocEngine._process_markdown_to_docx(doc, msg['content'])
            doc.add_paragraph("-" * 20)

        bio = BytesIO(); doc.save(bio); return bio

# --- 6. APLIKASI UTAMA ---
if 'history' not in st.session_state: st.session_state.history = []
if 'library' not in st.session_state: st.session_state.library = {"text":"", "files":[]}

inject_css()

# API Handling
api_key = None
try:
    if "GOOGLE_API_KEY" in st.secrets: api_key = st.secrets["GOOGLE_API_KEY"]
    elif "GROQ_API_KEY" in st.secrets: api_key = st.secrets["GROQ_API_KEY"]
except: pass 

# --- SIDEBAR & SMART INPUT LOGIC ---
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 10px;">
            <img src="https://i.imgur.com/UUCgyfV.png" width="100">
        </div>
    """, unsafe_allow_html=True)
    
    # MODIFIKASI: Versi dipindahkan ke bawah, tombol Reset juga dipindah.
    # Disini hanya Input API Key di bagian atas
    
    if not api_key: api_key = st.text_input("🔑 API Key", type="password")
    provider = AIProvider(api_key)
    if provider.is_valid: st.markdown(f"<div class='status-ok'>✅ {provider.provider_name} Aktif</div>", unsafe_allow_html=True)
    else: st.markdown("<div class='status-err'>⚠️ Menunggu Kunci</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    mode = st.selectbox("1. Divisi Pelayanan", ["Akademik (Pedagogi)", "Pastoral & Diskresi", "Manajemen Sekolah"])
    config_details = ""
    auto_prompt_template = "" # Variabel untuk text input otomatis
    
    if mode == "Akademik (Pedagogi)":
        st.markdown("#### ⚙️ Detail Akademik")
        with st.expander("Konfigurasi Kelas & Materi", expanded=True):
            input_kelas = st.selectbox("Jenjang Kelas", ["7 SMP", "8 SMP", "9 SMP", "10 SMA (Fase E)", "11 SMA (Fase F)", "12 SMA (Fase F)"])
            input_mapel = st.text_input("Mata Pelajaran", placeholder="Misal: Sejarah Indonesia")
            input_kd = st.text_area("Kompetensi Dasar (KD) / CP", placeholder="Paste CP/Tujuan Pembelajaran...", height=80)
            
        with st.expander("Parameter Soal / Tugas"):
            input_bloom = st.multiselect("Level Kognitif (Bloom)", 
                                         ["C1 (Mengingat)", "C2 (Memahami)", "C3 (Menerapkan)", "C4 (Menganalisis)", "C5 (Mengevaluasi)", "C6 (Mencipta)"],
                                         default=["C4 (Menganalisis)", "C5 (Mengevaluasi)"])
            input_difficulty = st.select_slider("Tingkat Kesulitan", options=["Mudah", "Sedang", "HOTS (Sulit)", "Olimpiade"])
            
        with st.expander("Gaya & Pendekatan"):
            input_gaya = st.selectbox("Gaya Bahasa", ["Formal Akademis", "Sokratik (Bertanya Balik)", "Storytelling (Naratif)", "Simpel & Lugas"])
            input_ipp_focus = st.multiselect("Fokus IPP", ["Context", "Experience", "Reflection", "Action", "Evaluation"], default=["Reflection"])

        # String untuk System Instruction
        config_details = f"KONFIGURASI: Kelas {input_kelas}, Mapel {input_mapel}, Gaya {input_gaya}, IPP {','.join(input_ipp_focus)}"
        
        # String untuk Auto-Input User
        auto_prompt_template = (
            f"Saya guru {input_mapel} untuk kelas {input_kelas}. \n"
            f"Topik: {input_kd if input_kd else '[Isi Topik]'}. \n\n"
            f"Tolong buatkan [Rencana Pembelajaran / 5 Soal PG / Studi Kasus] "
            f"dengan level kognitif {', '.join(input_bloom)} dan tingkat kesulitan {input_difficulty}. "
            f"Tekankan pada aspek {', '.join(input_ipp_focus)}."
        )

    elif mode == "Pastoral & Diskresi":
        st.markdown("#### 🕊️ Detail Pastoral")
        with st.expander("Konteks Bimbingan", expanded=True):
            pas_subjek = st.selectbox("Subjek", ["Siswa", "Guru/Karyawan", "Orang Tua", "Alumni"])
            pas_masalah = st.selectbox("Jenis Masalah", ["Akademik", "Keluarga", "Pecarian Jati Diri", "Keputusan Besar (Diskresi)", "Kejenuhan/Burnout"])
            pas_metode = st.radio("Metode Pendampingan", ["Mendengarkan (Listening)", "Diskresi (Pembedaan Roh)", "Examen (Refleksi Harian)"])
        
        config_details = f"KONFIGURASI PASTORAL: Subjek {pas_subjek}, Masalah {pas_masalah}, Metode {pas_metode}"
        
        auto_prompt_template = (
            f"Saya sedang mendampingi seorang {pas_subjek} yang mengalami pergumulan tentang {pas_masalah}. \n\n"
            f"Mohon berikan panduan percakapan atau refleksi menggunakan pendekatan {pas_metode}. "
            f"Tujuannya adalah membantu subjek menemukan kedamaian (konsolasi) dan mengambil keputusan yang tepat."
        )
        
    else: 
        st.markdown("#### 💼 Detail Manajemen")
        man_jenis = st.selectbox("Jenis Dokumen", ["Surat Resmi", "Proposal Kegiatan", "Pidato/Sambutan", "Email Internal"])
        man_tone = st.select_slider("Nada Bicara", options=["Tegas & Formal", "Persuasif", "Apresiatif", "Instruktif"])
        man_topik = st.text_input("Topik/Acara", placeholder="Misal: Hari Guru")
        
        config_details = f"KONFIGURASI MANAJEMEN: Dokumen {man_jenis}, Tone {man_tone}"
        
        auto_prompt_template = (
            f"Buatkan draf {man_jenis} bertema '{man_topik if man_topik else '[Isi Topik]'}'. \n\n"
            f"Gunakan nada bicara yang {man_tone}. "
            f"Pastikan struktur dokumen rapi dan sesuai standar institusi pendidikan Jesuit."
        )

    # MODIFIKASI: Tombol Reset & Footer dipindah ke sini (Bawah)
    st.markdown("---")
    
    if st.button("🗑️ Reset Sesi", use_container_width=True): 
        st.session_state.history = []
        st.rerun()
        
    st.markdown("""
        <div style="text-align: center; margin-top: 20px; color: #64748B; font-size: 12px;">
            <strong>Magis AI v47.0</strong><br>
            Design by: Albertus Henny Setyawan<br>
            Kolese Kanisius Jakarta | 2026
        </div>
    """, unsafe_allow_html=True)

# --- MAIN UI ---
c1,c2 = st.columns([3,1])
with c1: 
    st.markdown(f'''
    <div class="magis-title">MAGIS AI</div>
    <div class="magis-tagline">Mitra Diskresi Guru Ignasian</div>
    <div class="magis-subtitle">Mode: {mode}</div>
    ''', unsafe_allow_html=True)

with st.expander("📂 Pustaka & Dokumen Pendukung", expanded=False):
    files = st.file_uploader("Upload RPP/Buku/Materi", accept_multiple_files=True)
    img_up = st.file_uploader("Analisis Gambar/Soal Visual", type=['png','jpg'])
    if files:
        t, n = DocEngine.read(files)
        st.session_state.library = {"text": t, "files": n}
        st.success(f"Masuk Memori: {len(n)} file.")

# --- CHAT DISPLAY ---
for m in st.session_state.history:
    st.markdown(f"<div class='{'bubble-user' if m['role']=='user' else 'bubble-ai'}'>{m['content'].replace('[DOC_CONTEXT]','')}</div>", unsafe_allow_html=True)

# --- SMART INPUT AREA (MENGGANTIKAN CHAT INPUT BIASA) ---
st.markdown("---")
with st.container():
    # Menggunakan FORM agar lebih terkontrol
    with st.form(key='smart_input_form', clear_on_submit=True):
        col_in1, col_in2 = st.columns([6, 1])
        
        # KEY TRICK: Menggunakan hash dari template sebagai key
        # Ini memaksa text_area untuk merefresh value-nya saat sidebar berubah
        prompt_key = f"input_{hash(auto_prompt_template)}" 
        
        with col_in1:
            user_in = st.text_area(
                "Instruksi (Otomatis menyesuaikan konfigurasi):", 
                value=auto_prompt_template, 
                height=100,
                key=prompt_key
            )
        with col_in2:
            st.markdown("<br><br>", unsafe_allow_html=True) # Spacer
            submitted = st.form_submit_button("🚀 KIRIM")

# LOGIC PEMROSESAN
if submitted and user_in and provider.is_valid:
    final_msg = user_in
    if st.session_state.library["text"]: final_msg += " [DOC_CONTEXT]"
    st.session_state.history.append({"role":"user", "content":final_msg})
    st.rerun()

if st.session_state.history and st.session_state.history[-1]['role'] == 'user':
    with st.spinner("Sedang meracik materi Ignatian..."):
        full_res = ""
        box = st.empty()
        last_usr = st.session_state.history[-1]['content']
        img_data = PIL.Image.open(img_up) if img_up else None
        
        for chk in provider.generate_stream(st.session_state.history[:-1], last_usr, config_details, img_data, st.session_state.library["text"]):
            full_res += chk
            box.markdown(f"<div class='bubble-ai'>{full_res}</div>", unsafe_allow_html=True)
            
        st.session_state.history.append({"role":"assistant", "content":full_res})
        st.rerun()

if st.session_state.history:
    docx = DocEngine.create_word(st.session_state.history)
    st.download_button("📥 Download Docx", docx, "Hasil-MagisAI.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")