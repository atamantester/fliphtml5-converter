# FlipHTML5 EXE → PDF Dönüştürücü (Web)

FlipHTML5 offline EXE dosyalarını PDF'e dönüştüren web uygulaması.

## 🚀 Canlı Demo

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fliphtml5-converter.streamlit.app)

## Özellikler

- ✅ EXE dosyası yükleme (tarayıcıdan)
- ✅ 7-Zip ile otomatik extraction
- ✅ SWF → JPG dönüşümü (FFmpeg + FFDec)
- ✅ Kitap formatı (spread) veya tek sayfa PDF
- ✅ Canlı ilerleme ve log takibi
- ✅ PDF indirme

## Kurulum (Lokal)

```bash
# Repo'yu klonla
git clone https://github.com/atamantester/fliphtml5-converter.git
cd fliphtml5-converter

# Bağımlılıkları yükle
pip install -r requirements.txt

# Sistem araçları (macOS)
brew install p7zip ffmpeg

# Çalıştır
streamlit run streamlit_app.py
```

## Deploy (Streamlit Cloud)

1. [share.streamlit.io](https://share.streamlit.io) adresine git
2. GitHub repo'yu bağla
3. Main file: `streamlit_app.py`
4. Deploy!

`packages.txt` sistem paketlerini otomatik kurar.

## Lisans

MIT License
