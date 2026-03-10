"""
PDF oluşturma işlemleri.
Kitap formatında (spread layout) PDF oluşturur.
"""

import img2pdf
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


class PDFCreationError(Exception):
    """PDF oluşturma sırasında oluşan hatalar için özel exception."""
    pass


def validate_images(image_paths: List[Path], log_callback=None) -> List[Path]:
    """Görüntülerin geçerli olduğunu doğrular."""
    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    valid_images = []
    for path in image_paths:
        try:
            if not path.exists():
                log(f"Dosya bulunamadı: {path}")
                continue
            if path.stat().st_size == 0:
                log(f"Boş dosya: {path}")
                continue
            with Image.open(path) as img:
                valid_images.append(path)
        except Exception as e:
            log(f"Geçersiz görüntü {path}: {e}")
            continue
    return valid_images


def get_image_size(image_path: Path) -> Tuple[int, int]:
    """Görüntü boyutunu döndürür (width, height)."""
    with Image.open(image_path) as img:
        return img.size


def create_spread_image(
    left_image: Optional[Path],
    right_image: Optional[Path],
    output_path: Path,
    log_callback=None
) -> bool:
    """İki görüntüyü yan yana birleştirerek spread oluşturur."""
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    try:
        if left_image is None and right_image is None:
            return False

        left_img = Image.open(left_image) if left_image else None
        right_img = Image.open(right_image) if right_image else None

        if left_img and right_img:
            left_w, left_h = left_img.size
            right_w, right_h = right_img.size
            target_height = max(left_h, right_h)

            if left_h != target_height:
                ratio = target_height / left_h
                new_width = int(left_w * ratio)
                left_img = left_img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                left_w = new_width

            if right_h != target_height:
                ratio = target_height / right_h
                new_width = int(right_w * ratio)
                right_img = right_img.resize((new_width, target_height), Image.Resampling.LANCZOS)
                right_w = new_width

            spread_width = left_w + right_w
            spread_height = target_height

        elif left_img:
            spread_width, spread_height = left_img.size
        else:
            spread_width, spread_height = right_img.size

        spread = Image.new('RGB', (spread_width, spread_height), (255, 255, 255))

        if left_img and right_img:
            if left_img.mode != 'RGB':
                left_img = left_img.convert('RGB')
            if right_img.mode != 'RGB':
                right_img = right_img.convert('RGB')
            spread.paste(left_img, (0, 0))
            spread.paste(right_img, (left_img.size[0], 0))
        elif left_img:
            if left_img.mode != 'RGB':
                left_img = left_img.convert('RGB')
            spread.paste(left_img, (0, 0))
        else:
            if right_img.mode != 'RGB':
                right_img = right_img.convert('RGB')
            spread.paste(right_img, (0, 0))

        output_path.parent.mkdir(parents=True, exist_ok=True)
        spread.save(output_path, 'JPEG', quality=98, optimize=False)

        if left_img:
            left_img.close()
        if right_img:
            right_img.close()
        spread.close()

        return True

    except Exception as e:
        log(f"Spread oluşturma hatası: {e}")
        return False


def create_book_spreads(
    image_paths: List[Path],
    output_dir: Path,
    log_callback=None,
    progress_callback=None
) -> Tuple[List[Path], str]:
    """Sayfa görüntülerinden kitap spread'leri oluşturur."""
    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    if not image_paths:
        return [], "Görüntü listesi boş"

    output_dir.mkdir(parents=True, exist_ok=True)

    spreads = []
    total_pages = len(image_paths)
    log(f"Kitap spread'leri oluşturuluyor: {total_pages} sayfa")

    if total_pages == 1:
        num_spreads = 1
    else:
        remaining = total_pages - 1
        num_spreads = 1 + (remaining + 1) // 2

    spread_index = 0
    page_index = 0

    while page_index < total_pages:
        if progress_callback:
            progress_callback(spread_index, num_spreads)

        spread_path = output_dir / f"spread_{spread_index + 1:04d}.jpg"

        if page_index == 0:
            success = create_spread_image(
                image_paths[0], None, spread_path, log_callback
            )
            if success:
                spreads.append(spread_path)
                log(f"Spread {spread_index + 1}: Kapak (Sayfa 1)")
            page_index = 1
        else:
            left_page = image_paths[page_index] if page_index < total_pages else None
            right_page = image_paths[page_index + 1] if page_index + 1 < total_pages else None

            success = create_spread_image(
                left_page, right_page, spread_path, log_callback
            )

            if success:
                spreads.append(spread_path)
                if left_page and right_page:
                    log(f"Spread {spread_index + 1}: Sayfa {page_index + 1}-{page_index + 2}")
                elif left_page:
                    log(f"Spread {spread_index + 1}: Sayfa {page_index + 1} (arka kapak)")

            page_index += 2

        spread_index += 1

    if progress_callback:
        progress_callback(num_spreads, num_spreads)

    log(f"Toplam {len(spreads)} spread oluşturuldu")

    if not spreads:
        return [], "Spread oluşturulamadı"

    return spreads, ""


def create_pdf_from_images(
    image_paths: List[Path],
    output_path: Path,
    log_callback=None,
    progress_callback=None,
    book_format: bool = True
) -> Tuple[bool, str]:
    """Görüntü listesinden PDF oluşturur."""

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    if not image_paths:
        return False, "Görüntü listesi boş"

    log(f"PDF oluşturma başlatılıyor: {len(image_paths)} sayfa")
    log(f"Format: {'Kitap (spread)' if book_format else 'Tek sayfa'}")

    try:
        valid_images = validate_images(image_paths, log_callback)

        if not valid_images:
            return False, "Geçerli görüntü bulunamadı"

        log(f"Geçerli görüntü sayısı: {len(valid_images)}")

        temp_dir = output_path.parent / "_temp_pdf_spreads"

        if book_format:
            log("Kitap spread'leri oluşturuluyor...")

            def spread_progress(current, total):
                if progress_callback and total > 0:
                    prog = int((current / total) * 70)
                    progress_callback(prog, 100)

            spreads, error = create_book_spreads(
                valid_images, temp_dir / "spreads", log_callback, spread_progress
            )

            if not spreads:
                return False, f"Spread oluşturma hatası: {error}"

            pdf_images = spreads
        else:
            pdf_images = []
            total = len(valid_images)

            for i, img_path in enumerate(valid_images):
                if progress_callback:
                    progress_callback(int((i / total) * 70), 100)

                processed = process_image_for_pdf(img_path, temp_dir / "processed", log)
                if processed:
                    pdf_images.append(processed)

            if not pdf_images:
                return False, "İşlenebilir görüntü bulunamadı"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        log(f"PDF yazılıyor: {len(pdf_images)} sayfa/spread")

        if progress_callback:
            progress_callback(75, 100)

        try:
            image_bytes_list = []
            for img_path in pdf_images:
                with open(img_path, 'rb') as f:
                    image_bytes_list.append(f.read())

            pdf_bytes = img2pdf.convert(image_bytes_list)

            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)

        except Exception as pdf_error:
            log(f"PDF yazma hatası: {pdf_error}")
            raise

        if progress_callback:
            progress_callback(95, 100)

        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        if progress_callback:
            progress_callback(100, 100)

        file_size_mb = output_path.stat().st_size / 1024 / 1024
        log(f"PDF başarıyla oluşturuldu: {output_path}")
        log(f"Dosya boyutu: {file_size_mb:.2f} MB")

        return True, ""

    except Exception as e:
        error_msg = f"PDF oluşturma hatası: {str(e)}"
        log(f"HATA: {error_msg}")
        return False, error_msg


def process_image_for_pdf(
    image_path: Path,
    temp_dir: Path,
    log_callback=None
) -> Optional[Path]:
    """Tek bir görüntüyü PDF için işler."""

    def log(msg: str):
        if log_callback:
            log_callback(msg)

    suffix = image_path.suffix.lower()

    try:
        with Image.open(image_path) as img:
            mode = img.mode

            if suffix in ['.jpg', '.jpeg'] and mode == 'RGB':
                return image_path

            if suffix == '.png' and mode in ['RGB', 'RGBA', 'L', 'P']:
                return image_path

            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_path = temp_dir / f"{image_path.stem}.jpg"

            if mode == 'RGBA':
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                background.save(temp_path, 'JPEG', quality=98)
            else:
                img.convert('RGB').save(temp_path, 'JPEG', quality=98)

            return temp_path

    except Exception as e:
        log(f"Görüntü işleme hatası {image_path}: {e}")
        return None
