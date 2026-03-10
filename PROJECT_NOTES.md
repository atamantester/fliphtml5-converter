# FlipHTML5 EXE → PDF Converter — Proje Notları

## 📌 Genel Bakış

FlipHTML5 offline EXE dosyalarını PDF'e dönüştüren Streamlit web uygulaması.

- **Platform:** Streamlit Community Cloud
- **Repo:** `atamantester/fliphtml5-converter`
- **URL:** https://fliphtml5.streamlit.app (custom subdomain)

---

## 🏗️ Dosya Yapısı

| Dosya | Açıklama |
|---|---|
| `streamlit_app.py` | Ana uygulama — UI, login, iş kuyruğu |
| `utils.py` | İçerik keşfi, SWF/SVG/JPG tespiti, sıralama |
| `swf_utils.py` | SWF → JPG dönüştürme (FFDec + FFmpeg) |
| `pdf_utils.py` | PDF oluşturma, kitap spread'leri |
| `extract_utils.py` | 7-Zip ile EXE çıkarma |
| `tools/ffdec.jar` | FFDec SWF decompiler (+ `tools/lib/` 54 JAR) |
| `.streamlit/config.toml` | Upload limiti 500MB, dark tema |
| `.streamlit/secrets.toml` | Auth şifresi (gitignore'da, GitHub'a push edilmez) |
| `packages.txt` | Sistem bağımlılıkları (7z, ffmpeg, java, libcairo2) |
| `requirements.txt` | Python bağımlılıkları |

---

## 🔐 Kimlik Doğrulama

- **Kullanıcı:** `admin`
- **Şifre:** `Fl1pH7ml5_2026!Px`
- Şifre **SHA-256 hash** olarak saklanır
- `secrets.toml` **gitignore'da** — GitHub'a push edilmez
- Streamlit Cloud'da: App Settings → Secrets → TOML yapıştır

```toml
[auth]
username = "admin"
password_hash = "572c2503e3edb097b34b7860bd3c7dde30f9e56611b27fab0f551e58dea80604"
```

---

## 🔄 Dönüştürme Akışı

```
EXE → 7-Zip → İçerik Keşfi → Dönüştürme → PDF
```

### İçerik Keşfi Öncelik Sırası (`discover_content`)

| Öncelik | Koşul | Davranış |
|---|---|---|
| 1 | `pages/swf/` klasöründe **büyük SWF** (ort. ≥10KB) | SWF → JPG (FFDec) |
| 2 | Genel taramada **büyük SWF** (≥2 adet, ort. ≥10KB) | SWF → JPG (FFDec) |
| 3 | JPG/PNG dosyaları bulunursa | Doğrudan kullan |
| 4 | Sadece SVG dosyaları varsa | SVG → JPG (cairosvg) |

### Önemli: Placeholder SWF'leri Atlama

Bazı EXE'lerde `pages/swf/` klasöründe 1KB'lık placeholder SWF'ler bulunur. `_are_swfs_real_pages()` fonksiyonu ortalama boyutu kontrol eder:
- Ortalama ≥ 10KB → Gerçek sayfa SWF'leri
- Ortalama < 10KB → Placeholder, JPG'lere geç

### UI/Skin SWF'leri Filtreleme

`find_swf_files()` şu dizinlerdeki SWF'leri **atlar**: `assets/`, `skins/`, `buttons/`, `preloader/`, `css/`, `js/`

---

## 📁 FlipHTML5 EXE İç Yapısı

EXE çıkarıldığında tipik yapı:

```
extracted/
└── offline/
    └── files/
        ├── assets/skins/    ← UI bileşenleri (SWF), ATLA
        ├── pages/
        │   ├── swf/         ← Sayfa SWF'leri (büyükse kullan)
        │   ├── svg/         ← JPG + SVG karışık (JPG'leri kullan)
        │   └── large/       ← Büyük JPG'ler
        └── data/
```

### Önemli: `offline/` Prefix

`get_extracted_dir()` → `temp/work/extracted/` döndürür. İçerik `extracted/offline/files/...` altında olur. Bu yüzden `find_page_images_folder` hem `files/pages/svg` hem `offline/files/pages/svg` yollarını arar.

---

## 🎨 Kalite Ayarları

| Seviye | JPEG | Maks Genişlik | Kullanım |
|---|---|---|---|
| **Orijinal** | %98 | Değişmez | En yüksek kalite |
| **Yüksek** | %95 | Değişmez | Çok az fark |
| **Orta** | %85 | 1600px | İyi kalite, küçük dosya |
| **Düşük** | %70 | 1200px | En küçük dosya |

---

## 🛠️ Sistem Bağımlılıkları (Streamlit Cloud)

`packages.txt` (apt-get ile kurulur):
- `p7zip-full` — EXE çıkarma
- `ffmpeg` — SWF → JPG fallback
- `default-jre` — Java (FFDec için)
- `libcairo2-dev` — SVG → JPG (cairosvg için)

`requirements.txt`:
- `streamlit` — Web framework
- `img2pdf` — Görüntülerden PDF
- `Pillow` — Görüntü işleme
- `cairosvg` — SVG render

---

## ⚠️ Bilinen Sorunlar ve Çözümler

| Sorun | Neden | Çözüm |
|---|---|---|
| Blank/beyaz PDF sayfaları | FFDec `frame` modu boş render | `image` modu öncelikli, min 50KB kontrol |
| Tek SWF bulunuyor (UI) | `VideoPlayerControls.swf` gibi skin dosyaları | `assets/skins/` filtreleme + tek SWF atlama |
| JPG'ler bulunamıyor | `offline/` prefix eksik | Tüm yollara `offline/` prefix eklendi |
| İndirme butonları kayboluyor | Streamlit sayfa yeniden çalıştırma | `session_state` ile sonuç saklama |
| Sürükle-bırak çalışmıyor | Tarayıcı .exe güvenlik kısıtı | Sadece Browse files kullanılıyor |
| 10-15 sn indirme gecikmesi | Streamlit rerun + büyük veri | Normal davranış, Streamlit sınırlaması |

---

## 📋 Özellikler

- ✅ Çoklu dosya yükleme ve sıralı işleme
- ✅ İş listesi ve ilerleme takibi
- ✅ Tekli indirme + toplu ZIP indirme
- ✅ Kitap formatı (spread) ve tek sayfa formatı
- ✅ 4 seviye kalite seçeneği
- ✅ SHA-256 güvenli giriş
- ✅ SWF, JPG ve SVG desteği
- ✅ Akıllı içerik keşfi (placeholder tespiti)
- ✅ Session state ile kalıcı sonuçlar
- ✅ İşleri temizle butonu

---

*Son güncelleme: 10 Mart 2026*
