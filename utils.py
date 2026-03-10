"""
Yardımcı fonksiyonlar.
Natural sort, dosya keşfi ve diğer utility fonksiyonlar.
"""

import re
import os
from pathlib import Path
from typing import List, Tuple, Optional
import uuid


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
    """Belirtilen dizinde SWF dosyalarını bulur (recursive)."""
    swf_files = []
    if not directory.exists():
        return swf_files
    for root, dirs, files in os.walk(directory):
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
        'files/mobile',
        'files/page',
        'files/pages',
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


def discover_content(extracted_dir: Path) -> Tuple[List[Path], List[Path], str, Optional[Path]]:
    """
    Çıkarılmış dizinde içeriği keşfeder.
    Öncelik: SWF > Görüntüler (SWF yüksek kaliteli sayfa, JPG sadece thumbnail)
    Returns: Tuple (görüntü_listesi, swf_listesi, kaynak_türü, swf_klasörü)
    """
    # 1. Önce SWF dosyalarını ara (yüksek kaliteli sayfa içeriği)
    swf_folder = find_swf_folder(extracted_dir)
    if swf_folder:
        swf_files = list(swf_folder.glob('*.swf'))
        if swf_files:
            sorted_swf = sort_images_naturally(swf_files)
            return ([], sorted_swf, "swf", swf_folder)

    swf_files = find_swf_files(extracted_dir)
    if swf_files:
        sorted_swf = sort_images_naturally(swf_files)
        return ([], sorted_swf, "swf", None)

    # 2. SWF yoksa görüntüleri ara (fallback)
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

    return ([], [], "none", None)


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
