"""
FlipHTML5 EXE → PDF Dönüştürücü
Streamlit Web Uygulaması — Çoklu Dosya Desteği
"""

import streamlit as st
import tempfile
import shutil
import logging
import zipfile
import io
import hashlib
from pathlib import Path
from datetime import datetime

from extract_utils import extract_exe, check_7zip_available, get_extracted_dir, cleanup_temp_dir
from swf_utils import convert_multiple_swf_to_jpg, check_ffmpeg_available
from pdf_utils import create_pdf_from_images
from utils import discover_content, sort_images_naturally, ensure_directory, format_file_size

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_password():
    """Kullanıcı kimlik doğrulaması. True dönerse giriş başarılı."""

    if st.session_state.get("authenticated"):
        return True

    # Login sayfası
    st.markdown("""
    <style>
        .login-container {
            max-width: 420px;
            margin: 5rem auto;
            padding: 2.5rem;
            background: linear-gradient(135deg, #1a1f2e 0%, #252b3b 100%);
            border: 1px solid #333;
            border-radius: 16px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .login-title {
            background: linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FFD700 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 1.8rem;
            font-weight: 800;
            text-align: center;
            margin-bottom: 0.3rem;
        }
        .login-subtitle {
            text-align: center;
            color: #666;
            font-size: 0.9rem;
            margin-bottom: 1.5rem;
        }
        .login-icon {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="login-icon">🔐</div>', unsafe_allow_html=True)
        st.markdown('<h2 class="login-title">FlipHTML5 Converter</h2>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Devam etmek için giriş yapın</p>', unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("👤 Kullanıcı Adı", placeholder="Kullanıcı adınız")
            password = st.text_input("🔑 Şifre", type="password", placeholder="Şifreniz")
            submit = st.form_submit_button("🚀 Giriş Yap", use_container_width=True, type="primary")

            if submit:
                if not username or not password:
                    st.error("❌ Kullanıcı adı ve şifre gerekli")
                    return False

                expected_user = st.secrets["auth"]["username"]
                expected_hash = st.secrets["auth"]["password_hash"]
                input_hash = hashlib.sha256(password.encode()).hexdigest()

                if username == expected_user and input_hash == expected_hash:
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı")
                    return False

    return False

# ─── Sayfa Ayarları ───
st.set_page_config(
    page_title="FlipHTML5 EXE → PDF Dönüştürücü",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ───
st.markdown("""
<style>
    .main-title {
        background: linear-gradient(135deg, #FF6B35 0%, #F7931E 50%, #FFD700 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        text-align: center;
        color: #888;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .status-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #252b3b 100%);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 1.2rem;
        margin: 0.5rem 0;
    }
    .status-card.success {
        border-color: #4CAF50;
        background: linear-gradient(135deg, #1a2e1a 0%, #1f3b1f 100%);
    }
    .status-card.error {
        border-color: #f44336;
        background: linear-gradient(135deg, #2e1a1a 0%, #3b1f1f 100%);
    }
    .stat-box {
        background: #1a1f2e;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #FF6B35;
    }
    .stat-label {
        color: #888;
        font-size: 0.85rem;
        margin-top: 0.3rem;
    }
    .stFileUploader > div > div {
        border: 2px dashed #FF6B35 !important;
        border-radius: 12px !important;
        background: rgba(255, 107, 53, 0.05) !important;
    }
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
    }
    .log-container {
        background: #0a0e17;
        border: 1px solid #1e2430;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.8rem;
        max-height: 400px;
        overflow-y: auto;
        color: #a0aec0;
    }
    .log-success { color: #4CAF50; }
    .log-warning { color: #FFC107; }
    .log-error { color: #f44336; }
    .log-info { color: #64B5F6; }
    .footer {
        text-align: center;
        color: #555;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding: 1rem;
        border-top: 1px solid #222;
    }
    .queue-item {
        background: #1a1f2e;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        margin: 0.3rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .queue-item.done { border-color: #4CAF50; }
    .queue-item.active { border-color: #FF6B35; background: #252b3b; }
    .queue-item.error { border-color: #f44336; }
</style>
""", unsafe_allow_html=True)


def check_system_tools():
    """Sistem araçlarının durumunu kontrol eder."""
    tools = {}
    available, msg = check_7zip_available("7z")
    tools["7-Zip"] = {"available": available, "message": msg}
    available, msg = check_ffmpeg_available("ffmpeg")
    tools["FFmpeg"] = {"available": available, "message": msg}
    import subprocess
    try:
        result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
        tools["Java"] = {"available": result.returncode == 0, "message": "Java kurulu"}
    except:
        tools["Java"] = {"available": False, "message": "Java bulunamadı"}
    return tools


def process_exe_file(uploaded_file, book_format: bool, progress_bar, status_text, log_container):
    """Yüklenen EXE dosyasını işler."""
    logs = []

    def log(msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {msg}")
        log_html = ""
        for line in logs[-50:]:
            css_class = "log-info"
            if "✓" in line or "başarı" in line.lower():
                css_class = "log-success"
            elif "⚠" in line or "uyarı" in line.lower():
                css_class = "log-warning"
            elif "HATA" in line or "✗" in line:
                css_class = "log-error"
            log_html += f'<div class="{css_class}">{line}</div>'
        log_container.markdown(f'<div class="log-container">{log_html}</div>', unsafe_allow_html=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="fliphtml5_"))

    try:
        status_text.text(f"📥 Dosya kaydediliyor: {uploaded_file.name}")
        progress_bar.progress(5)

        exe_path = temp_dir / uploaded_file.name
        with open(exe_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        file_size = exe_path.stat().st_size
        log(f"Dosya kaydedildi: {uploaded_file.name} ({format_file_size(file_size)})")

        status_text.text("🔧 Araçlar kontrol ediliyor...")
        progress_bar.progress(8)

        seven_zip_path = "7z"
        available, msg = check_7zip_available(seven_zip_path)
        if not available:
            raise Exception(f"7-Zip bulunamadı: {msg}")
        log(f"7-Zip: Kullanılabilir")

        ffmpeg_path = "ffmpeg"
        ffmpeg_available, ffmpeg_msg = check_ffmpeg_available(ffmpeg_path)
        log(f"FFmpeg: {ffmpeg_msg}")

        status_text.text(f"📦 EXE çıkarılıyor: {uploaded_file.name}")
        progress_bar.progress(15)
        log("EXE dosyası çıkarılıyor...")

        work_dir = temp_dir / "work"
        work_dir.mkdir(exist_ok=True)

        success, stdout, stderr = extract_exe(exe_path, work_dir, seven_zip_path, log)
        progress_bar.progress(25)

        status_text.text("🔍 İçerik analiz ediliyor...")
        progress_bar.progress(30)

        extracted_dir = get_extracted_dir(work_dir)
        images, swf_files, content_type, swf_folder = discover_content(extracted_dir)

        log(f"İçerik türü: {content_type}")
        log(f"Bulunan görüntüler: {len(images)}")
        log(f"Bulunan SWF dosyaları: {len(swf_files)}")

        if content_type == "none":
            raise Exception("Çıkarılan dosyalarda görüntü veya SWF bulunamadı")

        if content_type == "swf":
            status_text.text(f"🎨 SWF dönüştürülüyor: {uploaded_file.name}")
            log("SWF dosyaları JPG'ye dönüştürülüyor...")

            def swf_progress(current, total):
                if total > 0:
                    prog = 30 + int((current / total) * 50)
                    progress_bar.progress(min(prog, 80))

            jpg_output_dir = work_dir / "pages"
            success, images, error = convert_multiple_swf_to_jpg(
                swf_files, jpg_output_dir, ffmpeg_path,
                progress_callback=swf_progress, log_callback=log
            )

            if not success or not images:
                if images:
                    log(f"⚠ Bazı sayfalar dönüştürülemedi, devam ediliyor...")
                else:
                    raise Exception(f"SWF→JPG dönüştürme hatası: {error}")

        progress_bar.progress(80)
        total_pages = len(images)
        log(f"Toplam sayfa: {total_pages}")

        format_text = "kitap (spread)" if book_format else "tek sayfa"
        status_text.text(f"📄 PDF oluşturuluyor: {uploaded_file.name}")
        log(f"PDF oluşturuluyor: {format_text} formatı")

        output_filename = Path(uploaded_file.name).stem + ".pdf"
        output_path = temp_dir / output_filename

        def pdf_progress(current, total):
            if total > 0:
                prog = 80 + int((current / total) * 18)
                progress_bar.progress(min(prog, 98))

        success, error = create_pdf_from_images(
            images, output_path,
            log_callback=log,
            progress_callback=pdf_progress,
            book_format=book_format
        )

        if not success:
            raise Exception(f"PDF oluşturma hatası: {error}")

        progress_bar.progress(100)

        pdf_size = output_path.stat().st_size
        log(f"✓ PDF başarıyla oluşturuldu!")
        log(f"✓ Boyut: {format_file_size(pdf_size)}")
        log(f"✓ Sayfalar: {total_pages}")

        status_text.text(f"✅ Tamamlandı: {uploaded_file.name}")

        with open(output_path, "rb") as f:
            pdf_bytes = f.read()

        return pdf_bytes, output_filename, total_pages, pdf_size

    except Exception as e:
        log(f"HATA: {str(e)}")
        status_text.text(f"❌ Hata: {uploaded_file.name}")
        raise

    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ANA UYGULAMA
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Auth kontrolü — giriş yapılmadıysa login formu göster
if not check_password():
    st.stop()

st.markdown('<h1 class="main-title">📄 FlipHTML5 EXE → PDF</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">FlipHTML5 offline EXE dosyalarınızı PDF\'e dönüştürün</p>', unsafe_allow_html=True)

# ─── Sidebar ───
with st.sidebar:
    st.markdown(f"👤 **{st.session_state.get('username', '')}**")
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

    st.divider()
    st.markdown("### ⚙️ Ayarlar")

    book_format = st.toggle(
        "📖 Kitap Formatı (Spread)",
        value=True,
        help="Açık: Kapak tek, iç sayfalar yan yana. Kapalı: Her sayfa ayrı."
    )

    if book_format:
        st.info("📖 **Kitap formatı** aktif\n\nKapak tek sayfa, iç sayfalar yan yana birleştirilecek (InDesign spread)")
    else:
        st.info("📄 **Tek sayfa formatı** aktif\n\nHer sayfa bağımsız olarak PDF'e eklenecek")

    st.divider()

    st.markdown("### 🔧 Sistem Araçları")
    if st.button("🔄 Kontrol Et", use_container_width=True):
        tools = check_system_tools()
        for name, info in tools.items():
            if info["available"]:
                st.success(f"✅ {name}")
            else:
                st.error(f"❌ {name}: {info['message']}")

    st.divider()

    st.markdown("### 📋 Nasıl Çalışır?")
    st.markdown("""
    1. **EXE dosyaları yükle** — birden fazla seçebilirsin
    2. **Dönüştür** butonuna bas
    3. **PDF'leri indir** — tek tek veya toplu ZIP

    ---

    **Desteklenen formatlar:**
    - FlipHTML5 EXE (SWF içeren)
    - FlipHTML5 EXE (görüntü içeren)
    """)

    st.divider()
    st.markdown('<div class="footer">FlipHTML5 EXE→PDF Converter v2.1<br/>Streamlit Web Edition — Çoklu Dosya</div>', unsafe_allow_html=True)

# ─── Ana İçerik ───
uploaded_files = st.file_uploader(
    "📁 FlipHTML5 EXE dosyalarını sürükleyin veya seçin",
    type=["exe"],
    accept_multiple_files=True,
    help="Birden fazla FlipHTML5 .exe dosyası yükleyebilirsiniz (maks. 500 MB / dosya)"
)

if uploaded_files:
    file_count = len(uploaded_files)
    total_size = sum(len(f.getbuffer()) for f in uploaded_files)

    # Dosya bilgisi
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{file_count}</div>
            <div class="stat-label">Dosya</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{format_file_size(total_size)}</div>
            <div class="stat-label">Toplam Boyut</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="stat-box">
            <div class="stat-number">{'📖' if book_format else '📄'}</div>
            <div class="stat-label">{'Kitap Formatı' if book_format else 'Tek Sayfa'}</div>
        </div>
        """, unsafe_allow_html=True)

    # Dosya listesi
    if file_count > 1:
        with st.expander(f"📋 Yüklenen Dosyalar ({file_count})", expanded=False):
            for i, f in enumerate(uploaded_files):
                st.text(f"  {i+1}. {f.name} ({format_file_size(len(f.getbuffer()))})")

    st.markdown("")

    # Dönüştür butonu
    convert_col1, convert_col2, convert_col3 = st.columns([1, 2, 1])
    with convert_col2:
        btn_label = f"🚀 {file_count} Dosyayı Dönüştür" if file_count > 1 else "🚀 Dönüştürmeyi Başlat"
        convert_button = st.button(btn_label, use_container_width=True, type="primary")

    if convert_button:
        st.divider()

        results = []  # (pdf_bytes, filename, pages, size, success)

        # Genel ilerleme
        if file_count > 1:
            overall_status = st.empty()
            overall_progress = st.progress(0)

        for file_idx, uploaded_file in enumerate(uploaded_files):
            if file_count > 1:
                overall_status.text(f"📂 Dosya {file_idx + 1}/{file_count}: {uploaded_file.name}")
                overall_progress.progress(int((file_idx / file_count) * 100))

            # Her dosya için ayrı bölüm
            st.markdown(f"### {'📄' if file_count == 1 else f'📄 [{file_idx+1}/{file_count}]'} {uploaded_file.name}")

            status_text = st.empty()
            progress_bar = st.progress(0)

            with st.expander("📋 İşlem Logları", expanded=(file_count == 1)):
                log_container = st.empty()

            try:
                pdf_bytes, output_filename, total_pages, pdf_size = process_exe_file(
                    uploaded_file, book_format, progress_bar, status_text, log_container
                )

                results.append({
                    "success": True,
                    "pdf_bytes": pdf_bytes,
                    "filename": output_filename,
                    "pages": total_pages,
                    "size": pdf_size,
                    "original_name": uploaded_file.name
                })

                st.markdown(f"""
                <div class="status-card success">
                    <h4>✅ {output_filename}</h4>
                    <p>📊 {total_pages} sayfa • {format_file_size(pdf_size)}</p>
                </div>
                """, unsafe_allow_html=True)

                # Tek dosya indirme butonu
                st.download_button(
                    label=f"⬇️ {output_filename} ({format_file_size(pdf_size)})",
                    data=pdf_bytes,
                    file_name=output_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_{file_idx}"
                )

            except Exception as e:
                results.append({
                    "success": False,
                    "filename": uploaded_file.name,
                    "error": str(e),
                    "original_name": uploaded_file.name
                })

                st.markdown(f"""
                <div class="status-card error">
                    <h4>❌ {uploaded_file.name}</h4>
                    <p>{str(e)}</p>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

        # Genel ilerleme tamamla
        if file_count > 1:
            overall_progress.progress(100)

        # ─── Özet ───
        successful = [r for r in results if r["success"]]
        failed = [r for r in results if not r["success"]]

        total_pages_all = sum(r["pages"] for r in successful)
        total_size_all = sum(r["size"] for r in successful)

        st.markdown(f"""
        <div class="status-card {'success' if not failed else ''}">
            <h3>📊 Dönüştürme Özeti</h3>
            <p>✅ Başarılı: <strong>{len(successful)}/{file_count}</strong> dosya</p>
            <p>📄 Toplam: <strong>{total_pages_all}</strong> sayfa • <strong>{format_file_size(total_size_all)}</strong></p>
            {'<p>❌ Başarısız: <strong>' + str(len(failed)) + '</strong> dosya</p>' if failed else ''}
        </div>
        """, unsafe_allow_html=True)

        # Toplu ZIP indirme (2+ başarılı dosya varsa)
        if len(successful) >= 2:
            st.markdown("")
            zip_col1, zip_col2, zip_col3 = st.columns([1, 2, 1])
            with zip_col2:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_STORED) as zf:
                    for r in successful:
                        zf.writestr(r["filename"], r["pdf_bytes"])
                zip_buffer.seek(0)

                st.download_button(
                    label=f"📦 Tümünü ZIP İndir ({len(successful)} PDF • {format_file_size(zip_buffer.getbuffer().nbytes)})",
                    data=zip_buffer,
                    file_name="fliphtml5_pdfs.zip",
                    mime="application/zip",
                    use_container_width=True,
                    type="primary"
                )

else:
    st.markdown("")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; padding: 3rem 2rem; border: 2px dashed #333; border-radius: 16px; background: rgba(255,107,53,0.02);">
            <div style="font-size: 4rem; margin-bottom: 1rem;">📄</div>
            <h3 style="color: #ccc; margin-bottom: 0.5rem;">EXE dosyalarını yükleyin</h3>
            <p style="color: #666;">Birden fazla FlipHTML5 .exe dosyasını sürükleyin<br/>veya <strong>Browse files</strong> butonuna tıklayın</p>
        </div>
        """, unsafe_allow_html=True)
