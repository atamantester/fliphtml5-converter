"""
7-Zip extraction işlemleri.
EXE dosyalarından içerik çıkarma.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Extraction sırasında oluşan hatalar için özel exception."""
    pass


def check_7zip_available(seven_zip_path: str) -> Tuple[bool, str]:
    """7-Zip'in kullanılabilir olup olmadığını kontrol eder."""
    try:
        result = subprocess.run(
            [seven_zip_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        return True, "7-Zip kullanılabilir"
    except FileNotFoundError:
        return False, f"7-Zip bulunamadı: {seven_zip_path}"
    except subprocess.TimeoutExpired:
        return False, "7-Zip zaman aşımına uğradı"
    except Exception as e:
        return False, f"7-Zip kontrol hatası: {str(e)}"


def extract_exe(
    exe_path: Path,
    output_dir: Path,
    seven_zip_path: str,
    log_callback=None
) -> Tuple[bool, str, str]:
    """EXE dosyasını 7-Zip ile çıkarır."""

    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    extracted_dir = output_dir / "extracted"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        seven_zip_path,
        "x",
        "-y",
        f"-o{extracted_dir}",
        str(exe_path)
    ]

    log(f"Extraction başlatılıyor: {exe_path.name}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(exe_path.parent)
        )

        stdout = result.stdout
        stderr = result.stderr

        log(f"7-Zip çıkış kodu: {result.returncode}")

        if result.returncode != 0:
            error_msg = f"7-Zip hata kodu: {result.returncode}"
            if stderr:
                error_msg += f"\n{stderr}"
            raise ExtractionError(error_msg)

        if not any(extracted_dir.iterdir()):
            raise ExtractionError("Çıkarma başarılı görünüyor ama dosya bulunamadı")

        log(f"Extraction başarılı: {extracted_dir}")
        return True, stdout, stderr

    except subprocess.TimeoutExpired:
        error_msg = "Extraction zaman aşımına uğradı (5 dakika)"
        log(f"HATA: {error_msg}")
        raise ExtractionError(error_msg)
    except FileNotFoundError:
        error_msg = f"7-Zip bulunamadı: {seven_zip_path}"
        log(f"HATA: {error_msg}")
        raise ExtractionError(error_msg)
    except ExtractionError:
        raise
    except Exception as e:
        error_msg = f"Beklenmeyen hata: {str(e)}"
        log(f"HATA: {error_msg}")
        raise ExtractionError(error_msg)


def cleanup_temp_dir(temp_dir: Path, log_callback=None) -> bool:
    """Geçici dizini temizler."""
    def log(msg: str):
        logger.info(msg)
        if log_callback:
            log_callback(msg)

    try:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            log(f"Geçici dizin silindi: {temp_dir}")
            return True
        return True
    except Exception as e:
        log(f"Geçici dizin silinemedi: {e}")
        return False


def get_extracted_dir(temp_dir: Path) -> Path:
    """Çıkarılmış dosyaların bulunduğu dizini döndürür."""
    return temp_dir / "extracted"
