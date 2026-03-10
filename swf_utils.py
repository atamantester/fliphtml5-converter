"""
SWF dosyalarını görüntüye dönüştürme işlemleri.
FFmpeg kullanarak SWF → JPG dönüşümü yapar.
"""

import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
import logging
import shutil

logger = logging.getLogger(__name__)


class SWFConversionError(Exception):
    """SWF dönüştürme sırasında oluşan hatalar için özel exception."""
    pass


def check_ffmpeg_available(ffmpeg_path: str = "ffmpeg") -> Tuple[bool, str]:
    """FFmpeg'in kullanılabilir olup olmadığını kontrol eder."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        version_info = result.stdout.split('\n')[0] if result.stdout else "Bilinmeyen versiyon"
        return True, f"FFmpeg kullanılabilir: {version_info}"
    except FileNotFoundError:
        return False, f"FFmpeg bulunamadı: {ffmpeg_path}. Lütfen FFmpeg'i yükleyin."
    except subprocess.TimeoutExpired:
        return False, "FFmpeg zaman aşımına uğradı"
    except Exception as e:
        return False, f"FFmpeg kontrol hatası: {str(e)}"


def is_jpg_valid(jpg_path: Path, min_size: int = 5000) -> bool:
    """JPG dosyasının geçerli olup olmadığını kontrol eder."""
    if not jpg_path.exists():
        return False
    if jpg_path.stat().st_size < min_size:
        return False
    try:
        from PIL import Image
        with Image.open(jpg_path) as img:
            img.verify()
        return True
    except Exception:
        return False


def create_placeholder_jpg(output_path: Path, message: str = "Render Failed", color: tuple = (200, 100, 100)) -> bool:
    """Hata placeholder JPG oluşturur."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        width, height = 320, 450
        img = Image.new('RGB', (width, height), color=color)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.load_default(size=20)
        except:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2

        draw.text((text_x, text_y), message, font=font, fill=(255, 255, 255))
        img.save(output_path, 'JPEG', quality=85)
        img.close()
        return True
    except Exception as e:
        logger.warning(f"Placeholder JPG oluşturma başarısız: {e}")
        return False


def get_ffdec_path() -> Optional[Path]:
    """JPEXS FFDec (ffdec.jar) yolunu bulur."""
    possible_paths = [
        Path(__file__).parent / "tools" / "ffdec.jar",
        Path("/usr/bin/ffdec"),
        Path("/usr/local/bin/ffdec"),
    ]
    for path in possible_paths:
        if path.exists():
            return path
    return None


def check_java_available() -> bool:
    """Java'nın kurulu olup olmadığını kontrol eder."""
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def convert_swf_to_jpg_ffdec(
    swf_path: Path,
    output_path: Path,
    ffdec_path: Optional[Path] = None,
    scale: int = 1600,
    quality: int = 85,
    timeout: int = 120,
    log_callback=None
) -> Tuple[bool, Optional[Path], str]:
    """JPEXS FFDec kullanarak SWF'i JPG'ye dönüştürür."""

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    if not ffdec_path:
        ffdec_path = get_ffdec_path()

    if not ffdec_path or not ffdec_path.exists():
        return False, None, "FFDec bulunamadı"

    if not check_java_available():
        return False, None, "Java kurulu değil"

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    temp_export_dir = output_dir / f"ffdec_export_{swf_path.stem}"
    temp_export_dir.mkdir(exist_ok=True)

    try:
        cmd = [
            "java",
            "-jar", str(ffdec_path),
            "-export", "image",
            str(temp_export_dir),
            str(swf_path)
        ]

        log(f"FFDec çalıştırılıyor: {swf_path.name}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else f"FFDec çıkış kodu: {result.returncode}"
            return False, None, error_msg

        exported_images = list(temp_export_dir.glob("*.png")) + list(temp_export_dir.glob("*.jpg"))

        if not exported_images:
            return False, None, "FFDec resim export edemedi"

        first_image = sorted(exported_images)[0]

        try:
            from PIL import Image
            with Image.open(first_image) as img:
                if img.width > scale:
                    ratio = scale / img.width
                    new_size = (scale, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                img.convert('RGB').save(output_path, 'JPEG', quality=quality)
            return True, output_path, ""
        except Exception as e:
            return False, None, f"Görüntü dönüştürme hatası: {str(e)}"

    except subprocess.TimeoutExpired:
        return False, None, f"FFDec zaman aşımı ({timeout}s)"
    except Exception as e:
        return False, None, f"FFDec hatası: {str(e)}"
    finally:
        try:
            shutil.rmtree(temp_export_dir, ignore_errors=True)
        except:
            pass


def convert_swf_to_jpg_ffmpeg(
    swf_path: Path,
    output_path: Path,
    ffmpeg_path: str = "ffmpeg",
    scale: int = 1600,
    quality: int = 2,
    timeout: int = 60,
    log_callback=None,
    use_white_bg: bool = False
) -> Tuple[bool, Optional[Path], str]:
    """FFmpeg kullanarak tek bir SWF dosyasını JPG görüntüye dönüştürür."""

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    scale_filter = f"scale='min(iw,{scale})':-2"

    if use_white_bg:
        vf_filter = f"{scale_filter},format=rgba,split[a][b];[b]drawbox=c=white:t=fill[bg];[bg][a]overlay"
    else:
        vf_filter = scale_filter

    cmd = [
        ffmpeg_path,
        "-y",
        "-allowed_extensions", "ALL",
        "-i", str(swf_path),
        "-frames:v", "1",
        "-vf", vf_filter,
        "-c:v", "mjpeg",
        "-q:v", str(quality),
        "-f", "image2",
        str(output_path)
    ]

    log(f"SWF→JPG: {swf_path.name}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if output_path.exists():
            if is_jpg_valid(output_path):
                return True, output_path, ""
            else:
                if not use_white_bg:
                    log(f"Geçersiz JPG, beyaz arka plan ile tekrar deneniyor...")
                    output_path.unlink(missing_ok=True)
                    return convert_swf_to_jpg_ffmpeg(
                        swf_path, output_path, ffmpeg_path,
                        scale, quality, timeout, log_callback,
                        use_white_bg=True
                    )
                else:
                    return False, None, f"JPG dosyası geçersiz: {output_path}"
        else:
            error_msg = "FFmpeg çıktı dosyası oluşturamadı"
            if result.stderr:
                stderr_lines = result.stderr.strip().split('\n')
                for line in stderr_lines:
                    if 'error' in line.lower() or 'invalid' in line.lower():
                        error_msg = f"FFmpeg Hatası: {line.strip()[:100]}"
                        break
            return False, None, error_msg

    except subprocess.TimeoutExpired:
        return False, None, f"SWF dönüştürme zaman aşımına uğradı ({timeout}s)"
    except FileNotFoundError:
        return False, None, f"FFmpeg bulunamadı: {ffmpeg_path}"
    except Exception as e:
        return False, None, f"Beklenmeyen hata: {str(e)}"


def convert_multiple_swf_to_jpg(
    swf_files: List[Path],
    output_dir: Path,
    ffmpeg_path: str = "ffmpeg",
    scale: int = 1600,
    quality: int = 2,
    timeout: int = 60,
    progress_callback=None,
    log_callback=None
) -> Tuple[bool, List[Path], str]:
    """Birden fazla SWF dosyasını JPG görüntülere dönüştürür."""

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    output_dir.mkdir(parents=True, exist_ok=True)

    jpg_files = []
    errors = []
    total = len(swf_files)

    ffdec_path = get_ffdec_path()
    has_java = check_java_available()

    if ffdec_path and has_java:
        log(f"✓ FFDec bulundu, {total} SWF dosyasını dönüştürmek için kullanılacak")
    else:
        log(f"⚠ FFDec/Java bulunamadı, FFmpeg kullanılacak")

    for i, swf_path in enumerate(swf_files):
        if progress_callback:
            progress_callback(i, total)

        page_num = i + 1
        jpg_filename = f"page_{page_num:04d}.jpg"
        jpg_path = output_dir / jpg_filename

        success = False
        result_path = None

        if ffdec_path and has_java:
            success, result_path, error = convert_swf_to_jpg_ffdec(
                swf_path, jpg_path, ffdec_path, scale, quality, timeout, log_callback
            )
            if success:
                log(f"✓ Sayfa {page_num}: {swf_path.name} → {jpg_filename} (FFDec)")

        if not success:
            success, result_path, error = convert_swf_to_jpg_ffmpeg(
                swf_path, jpg_path, ffmpeg_path, scale, quality, timeout, log_callback
            )

        if success and result_path:
            jpg_files.append(result_path)
            if not (ffdec_path and has_java and success):
                log(f"✓ Sayfa {page_num}: {swf_path.name} → {jpg_filename}")
        else:
            error_detail = error or "Bilinmeyen hata"
            errors.append(f"Sayfa {page_num} ({swf_path.name}): {error_detail}")

            placeholder_msg = f"[Render Error]\n{swf_path.name}"
            if create_placeholder_jpg(jpg_path, message=placeholder_msg, color=(200, 100, 100)):
                jpg_files.append(jpg_path)
                log(f"⚠ Sayfa {page_num}: Placeholder oluşturuldu - {error_detail}")

    if progress_callback:
        progress_callback(total, total)

    if jpg_files:
        log(f"✓ Toplam {len(jpg_files)}/{total} sayfa dönüştürüldü")
        if errors:
            log(f"⚠ {len(errors)} sayfa dönüştürülemedi")
        return True, jpg_files, ""
    else:
        error_msg = "Hiçbir SWF dosyası dönüştürülemedi.\n" + "\n".join(errors[:5])
        return False, [], error_msg
