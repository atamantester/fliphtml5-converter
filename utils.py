"""
Yardımcı fonksiyonlar.
Natural sort, dosya keşfi ve diğer utility fonksiyonlar.
"""

import re
import os
import shutil
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import uuid

logger = logging.getLogger(__name__)


def generate_job_id() -> str:
    """Benzersiz iş ID'si oluşturur."""
    return str(uuid.uuid4())[:8]


def natural_sort_key(path: Path) -> Tuple:
    """
    Doğal sıralama için anahtar fonksiyonu.
    Sayısal bölümleri sayı olarak, diğerlerini string olarak sıralar.
    """
    filename = path.stem
    parts = re.split(r'(\d+)', filename)
    result = []
    for part in parts:
        if part.isdigit():
            result.append((0, int(part)))
        else:
            result.append((1, part.lower()))
    return tuple(result)


def sort_images_naturally(image_paths: List[Path]) -> List[Path]:
    """Görüntü dosyalarını doğal sıralama ile sıralar."""
    return sorted(image_paths, key=natural_sort_key)


def find_images_in_directory(directory: Path, recursive: bool = True) -> List[Path]:
    """Belirtilen dizinde görüntü dosyalarını bulur."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif'}
    images = []

    if not directory.exists():
        return images

    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if Path(file).suffix.lower() in image_extensions:
                    images.append(Path(root) / file)
    else:
        for file in directory.iterdir():
            if file.is_file() and file.suffix.lower() in image_extensions:
                images.append(file)

    return images


def find_swf_files(directory: Path) -> List[Path]:
    """Belirtilen dizinde sayfa SWF dosyalarını bulur (recursive).
    UI/skin SWF'lerini atlar (assets, skins, buttons dizinleri)."""
    SKIP_DIRS = {'assets', 'skins', 'buttons', 'preloader', 'css', 'js'}
    swf_files = []
    if not directory.exists():
        return swf_files
    for root, dirs, files in os.walk(directory):
        # UI dizinlerini atla
        root_parts = set(Path(root).parts)
        if root_parts & SKIP_DIRS:
            continue
        for file in files:
            if file.lower().endswith('.swf'):
                swf_files.append(Path(root) / file)
    return swf_files


def find_swf_folder(extracted_dir: Path) -> Optional[Path]:
    """Çıkarılmış dizinde SWF klasörünü tespit eder."""
    swf_folder_patterns = [
        'files/pages/swf',
        'files/page/swf',
        'offline/files/pages/swf',
        'offline/files/page/swf',
        'pages/swf',
        'swf',
    ]

    for pattern in swf_folder_patterns:
        check_path = extracted_dir / pattern
        if check_path.exists() and check_path.is_dir():
            swf_files = list(check_path.glob('*.swf'))
            if swf_files:
                return check_path

    for root, dirs, files in os.walk(extracted_dir):
        root_path = Path(root)
        if root_path.name.lower() == 'swf':
            swf_files = list(root_path.glob('*.swf'))
            if swf_files:
                return root_path

    return None


def find_page_images_folder(extracted_dir: Path) -> Optional[Path]:
    """Çıkarılmış dizinde sayfa görüntülerinin bulunduğu klasörü tespit eder."""
    possible_folders = [
        # offline/ prefix (FlipHTML5 standart yapısı)
        'offline/files/pages/svg',
        'offline/files/pages/thumbs',
        'offline/files/pages/jpg',
        'offline/files/pages/large',
        'offline/files/mobile',
        'offline/files/page',
        'offline/files/pages',
        # prefix'siz
        'files/pages/svg',
        'files/pages/thumbs',
        'files/pages/jpg',
        'files/pages/large',
        'files/mobile',
        'files/page',
        'files/pages',
        'pages/thumbs',
        'pages/jpg',
        'pages/svg',
        'mobile',
        'pages',
        'page',
        'images',
        'pics',
    ]

    for folder in possible_folders:
        check_path = extracted_dir / folder
        if check_path.exists() and check_path.is_dir():
            images = find_images_in_directory(check_path, recursive=False)
            if len(images) >= 2:
                return check_path

    best_folder = None
    max_images = 0

    for root, dirs, files in os.walk(extracted_dir):
        root_path = Path(root)
        image_count = sum(1 for f in files if Path(f).suffix.lower() in {'.jpg', '.jpeg', '.png'})
        if image_count > max_images:
            max_images = image_count
            best_folder = root_path

    if max_images >= 2:
        return best_folder

    return None


def _are_swfs_real_pages(swf_files: List[Path], min_size: int = 10000) -> bool:
    """SWF dosyalarının gerçek sayfa içeriği mi yoksa placeholder mı olduğunu kontrol eder.
    Gerçek sayfa SWF'leri genellikle 100KB+ olur, placeholder'lar 1-5KB olur."""
    if not swf_files:
        return False
    sizes = [f.stat().st_size for f in swf_files]
    avg_size = sum(sizes) / len(sizes)
    # Ortalama boyut 10KB'dan küçükse, bunlar placeholder SWF'lerdir
    return avg_size >= min_size


def discover_content(extracted_dir: Path) -> Tuple[List[Path], List[Path], str, Optional[Path]]:
    """
    Çıkarılmış dizinde içeriği keşfeder.
    Mantık: SWF dosyaları varsa boyutlarını kontrol et — gerçek sayfa mı placeholder mı?
    Placeholder SWF'lerse (küçük boyut), JPG'leri kullan.
    Returns: Tuple (görüntü_listesi, swf_listesi, kaynak_türü, swf_klasörü)
    """
    # 1. Sayfa SWF klasörünü ara (pages/swf/ vb.)
    swf_folder = find_swf_folder(extracted_dir)
    if swf_folder:
        swf_files = list(swf_folder.glob('*.swf'))
        if swf_files and _are_swfs_real_pages(swf_files):
            sorted_swf = sort_images_naturally(swf_files)
            return ([], sorted_swf, "swf", swf_folder)
        # SWF'ler placeholder — aynı dizin yapısında JPG ara
        # (pages/ altında jpg/ veya mobile/ olabilir)

    # 2. Genel SWF taraması (assets/skins hariç)
    swf_files = find_swf_files(extracted_dir)
    if len(swf_files) >= 2 and _are_swfs_real_pages(swf_files):
        sorted_swf = sort_images_naturally(swf_files)
        return ([], sorted_swf, "swf", None)

    # 3. Görüntüleri ara (SWF yok veya placeholder SWF'ler)
    page_folder = find_page_images_folder(extracted_dir)
    if page_folder:
        images = find_images_in_directory(page_folder, recursive=False)
        if images:
            sorted_images = sort_images_naturally(images)
            return (sorted_images, [], "images", None)

    all_images = find_images_in_directory(extracted_dir, recursive=True)
    if len(all_images) >= 2:
        sorted_images = sort_images_naturally(all_images)
        return (sorted_images, [], "images", None)

    # 4. SVG dosyalarını ara (JPG de yoksa son çare)
    svg_files = find_svg_files(extracted_dir)
    if len(svg_files) >= 2:
        sorted_svgs = sort_images_naturally(svg_files)
        return ([], sorted_svgs, "svg", None)

    return ([], [], "none", None)


def find_svg_files(directory: Path) -> List[Path]:
    """Sayfa SVG dosyalarını bulur (recursive). UI dizinlerini atlar."""
    SKIP_DIRS = {'assets', 'skins', 'buttons', 'preloader', 'css', 'js'}
    svg_files = []
    if not directory.exists():
        return svg_files
    for root, dirs, files in os.walk(directory):
        root_parts = set(Path(root).parts)
        if root_parts & SKIP_DIRS:
            continue
        for file in files:
            if file.lower().endswith('.svg'):
                svg_files.append(Path(root) / file)
    return svg_files


def convert_svgs_to_jpgs(
    svg_files: List[Path],
    output_dir: Path,
    progress_callback=None,
    log_callback=None
) -> Tuple[bool, List[Path], str]:
    """SVG dosyalarını JPG'ye dönüştürür. cairosvg kullanır."""

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    try:
        import cairosvg
    except ImportError:
        return False, [], "cairosvg kütüphanesi bulunamadı. pip install cairosvg"

    output_dir.mkdir(parents=True, exist_ok=True)
    jpg_files = []
    errors = []
    total = len(svg_files)

    log(f"SVG→JPG dönüştürme: {total} dosya")

    for i, svg_path in enumerate(svg_files):
        if progress_callback:
            progress_callback(i, total)

        page_num = i + 1
        jpg_filename = f"page_{page_num:04d}.jpg"
        jpg_path = output_dir / jpg_filename

        try:
            # SVG → PNG (cairosvg)
            png_bytes = cairosvg.svg2png(
                url=str(svg_path),
                output_width=1600
            )

            # PNG → JPG (Pillow)
            from PIL import Image
            import io
            png_img = Image.open(io.BytesIO(png_bytes))
            png_img.convert('RGB').save(jpg_path, 'JPEG', quality=98)
            png_img.close()

            jpg_files.append(jpg_path)
            log(f"✓ Sayfa {page_num}: {svg_path.name} → {jpg_filename}")

        except Exception as e:
            error_msg = f"Sayfa {page_num} ({svg_path.name}): {str(e)}"
            errors.append(error_msg)
            log(f"⚠ {error_msg}")

    if progress_callback:
        progress_callback(total, total)

    if jpg_files:
        log(f"✓ Toplam {len(jpg_files)}/{total} SVG dönüştürüldü")
        if errors:
            log(f"⚠ {len(errors)} dosya dönüştürülemedi")
        return True, jpg_files, ""
    else:
        return False, [], "Hiçbir SVG dönüştürülemedi.\n" + "\n".join(errors[:5])


def ensure_directory(path: Path) -> Path:
    """Dizinin var olduğundan emin olur, yoksa oluşturur."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(filename: str) -> str:
    """Dosya adını güvenli hale getirir."""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def format_file_size(size_bytes: int) -> str:
    """Bayt cinsinden boyutu okunabilir formata çevirir."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
