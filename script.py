import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import random
import logging
import sys
import argparse

# ==========================================
# ARGUMENT PARSING
# ==========================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Vize randevu takip botu — seçilen siteyi periyodik olarak\n"
            "kontrol eder ve müsait slot bulunca Telegram bildirimi gönderir.\n\n"
            "Örnek kullanım:\n"
            "  python monitor.py \\\n"
            "    --url https://example.com/appointments \\\n"
            "    --bot-token 123456:ABC-DEF \\\n"
            "    --chat-id 987654321 \\\n"
            "    --selector \"//div[@class='available-slot']\" \\\n"
            "    --proxy 1.2.3.4:8000 \\\n"
            "    --headless"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # ── Zorunlu parametreler ──────────────────────────────────────────────
    required = parser.add_argument_group("Zorunlu parametreler")

    required.add_argument(
        "--url", "-u",
        required=True,
        metavar="URL",
        help="Randevu sayfasının tam adresi  (ör. https://example.com/appointment)",
    )
    required.add_argument(
        "--bot-token", "-t",
        required=True,
        metavar="TOKEN",
        help="@BotFather'dan alınan Telegram bot token'ı",
    )
    required.add_argument(
        "--chat-id", "-c",
        required=True,
        metavar="CHAT_ID",
        help="Bildirimlerin gönderileceği Telegram chat ID'si",
    )

    # ── Slot tespit parametreleri ─────────────────────────────────────────
    detect = parser.add_argument_group(
        "Slot tespit parametreleri",
        "En az biri kullanılmalıdır: --selector, --keyword veya --page-keyword"
    )

    detect.add_argument(
        "--selector",
        metavar="SELECTOR",
        default=None,
        help=(
            "Müsait slotları bulmak için XPath veya CSS seçicisi\n"
            "  XPath örneği: \"//div[@class='slot available']\"\n"
            "  CSS  örneği:  \".slot.available\""
        ),
    )
    detect.add_argument(
        "--selector-type",
        choices=["xpath", "css"],
        default="xpath",
        metavar="TYPE",
        help="Seçici türü: 'xpath' (varsayılan) veya 'css'",
    )
    detect.add_argument(
        "--keyword",
        metavar="KELIME",
        default=None,
        help=(
            "Sayfanın görünür metninde aranacak anahtar kelime\n"
            "  Ör: 'Available'  veya  'Müsait'"
        ),
    )
    detect.add_argument(
        "--page-keyword",
        metavar="KELIME",
        default=None,
        help=(
            "Sayfanın ham HTML kaynağında aranacak anahtar kelime\n"
            "  Ör: 'isAvailable:true'  veya  'slot_count\":1'"
        ),
    )

    # ── İsteğe bağlı parametreler ─────────────────────────────────────────
    optional = parser.add_argument_group("İsteğe bağlı parametreler")

    optional.add_argument(
        "--proxy", "-p",
        metavar="PROXY",
        default=None,
        help=(
            "Konut proxy adresi  (opsiyonel)\n"
            "  Format: IP:PORT  veya  IP:PORT:KULLANICI:ŞIFRE"
        ),
    )
    optional.add_argument(
        "--min-interval",
        type=int,
        default=600,
        metavar="SANİYE",
        help="Kontroller arası minimum bekleme süresi (varsayılan: 600)",
    )
    optional.add_argument(
        "--max-interval",
        type=int,
        default=900,
        metavar="SANİYE",
        help="Kontroller arası maksimum bekleme süresi (varsayılan: 900)",
    )
    optional.add_argument(
        "--wait-timeout",
        type=int,
        default=15,
        metavar="SANİYE",
        help="Sayfa yüklenmesi için maksimum bekleme süresi (varsayılan: 15)",
    )
    optional.add_argument(
        "--headless",
        action="store_true",
        help="Tarayıcıyı arka planda (headless) çalıştır — sunucu/Raspberry Pi için önerilir",
    )
    optional.add_argument(
        "--notify-message",
        metavar="METİN",
        default=None,
        help=(
            "Telegram bildirimi için özel mesaj metni\n"
            "  Ör: \"Schengen randevusu açıldı!\"\n"
            "  Belirtilmezse varsayılan İngilizce mesaj kullanılır."
        ),
    )

    args = parser.parse_args()

    # ── Mantıksal doğrulama ───────────────────────────────────────────────
    if not any([args.selector, args.keyword, args.page_keyword]):
        parser.error(
            "Slot tespiti için en az bir parametre gerekli:\n"
            "  --selector  |  --keyword  |  --page-keyword"
        )
    if args.min_interval > args.max_interval:
        parser.error("--min-interval, --max-interval değerinden büyük olamaz.")

    return args


# ==========================================
# LOGGING SETUP
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ==========================================
# TELEGRAM NOTIFICATION
# ==========================================

def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Telegram Bot API üzerinden Markdown formatlı bir mesaj gönderir.

    Args:
        bot_token : BotFather'dan alınan token.
        chat_id   : Hedef chat ID'si.
        message   : Gönderilecek metin (Telegram Markdown destekler).

    Returns:
        Başarılıysa True, hata durumunda False.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info("Telegram bildirimi başarıyla gönderildi.")
            return True
        logger.error("Telegram API hatası: %s", response.text)
        return False
    except requests.RequestException as exc:
        logger.error("Telegram API'ye ulaşılamadı: %s", exc)
        return False


# ==========================================
# SLOT DETECTION STRATEGIES
# ==========================================

def _detect_by_selector(driver, selector: str, selector_type: str, timeout: int) -> bool:
    """
    Verilen XPath veya CSS seçicisine uyan en az bir öğenin
    DOM'da bulunup bulunmadığını kontrol eder.
    """
    try:
        by = By.XPATH if selector_type == "xpath" else By.CSS_SELECTOR
        elements = WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, selector))
        )
        found = len(elements) > 0
        if found:
            logger.info(
                "Seçici ile %d öğe bulundu (%s: %s)",
                len(elements), selector_type.upper(), selector,
            )
        return found
    except Exception:
        return False


def _detect_by_visible_keyword(driver, keyword: str) -> bool:
    """
    Sayfanın görünür body metninde anahtar kelimeyi arar (büyük/küçük harf duyarsız).
    """
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        found = keyword.lower() in body_text.lower()
        if found:
            logger.info("Görünür metinde anahtar kelime bulundu: '%s'", keyword)
        return found
    except Exception:
        return False


def _detect_by_page_source_keyword(driver, keyword: str) -> bool:
    """
    Ham HTML kaynağında anahtar kelimeyi arar (büyük/küçük harf duyarsız).
    JSON flag'leri veya gizli HTML öznitelikleri için kullanışlıdır.
    """
    found = keyword.lower() in driver.page_source.lower()
    if found:
        logger.info("Sayfa kaynağında anahtar kelime bulundu: '%s'", keyword)
    return found


# ==========================================
# BROWSER AUTOMATION
# ==========================================

def check_appointments(args) -> bool:
    """
    Tarayıcı oturumu açar, hedef URL'ye gider ve CLI parametrelerine
    göre müsait randevu slotu olup olmadığını kontrol eder.

    Returns:
        Slot bulunup bildirim gönderildiyse True, aksi hâlde False.
    """
    logger.info("Tarayıcı oturumu başlatılıyor...")

    options = uc.ChromeOptions()

    if args.headless:
        options.add_argument("--headless")
        logger.info("Headless mod etkin.")

    if args.proxy:
        options.add_argument(f"--proxy-server={args.proxy}")
        logger.info("Proxy kullanılıyor: %s", args.proxy)

    driver = uc.Chrome(options=options)

    try:
        logger.info("Sayfa yükleniyor: %s", args.url)
        driver.get(args.url)

        # İnsan benzeri rastgele gecikme
        human_delay = random.uniform(3.5, 6.2)
        logger.info("Sayfa yüklendi. %.1f s bekleniyor...", human_delay)
        time.sleep(human_delay)

        # ------------------------------------------------------------------
        # İPUCU: Eğer site CAPTCHA sunuyorsa, burada 2captcha gibi bir
        # çözüm servisi entegre edip dönen token'ı sayfanın gizli
        # textarea alanına inject edebilirsiniz.
        # ------------------------------------------------------------------

        # ── Tespit stratejilerini sırayla uygula ──────────────────────────
        appointment_found = False

        if args.selector:
            appointment_found = _detect_by_selector(
                driver, args.selector, args.selector_type, args.wait_timeout
            )

        if not appointment_found and args.keyword:
            appointment_found = _detect_by_visible_keyword(driver, args.keyword)

        if not appointment_found and args.page_keyword:
            appointment_found = _detect_by_page_source_keyword(driver, args.page_keyword)

        # ── Sonuç ─────────────────────────────────────────────────────────
        if appointment_found:
            if args.notify_message:
                message = (
                    f"*UYARI:* {args.notify_message}\n\n"
                    f"Hemen rezervasyon yapın: [Randevu sayfasına git]({args.url})"
                )
            else:
                message = (
                    "*ALERT:* An appointment slot has just opened!\n\n"
                    f"Book now: [Go to the booking page]({args.url})"
                )

            send_telegram_message(args.bot_token, args.chat_id, message)
            logger.info("Müsait slot tespit edildi — bildirim gönderildi.")
            return True

        logger.info("Şu an müsait slot yok. Sonraki kontrolde tekrar denenecek.")
        return False

    except Exception as exc:
        logger.error("Randevu kontrolü sırasında beklenmeyen hata: %s", exc)
        return False

    finally:
        driver.quit()
        logger.debug("Tarayıcı oturumu kapatıldı.")


# ==========================================
# MAIN LOOP
# ==========================================

if __name__ == "__main__":
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Randevu monitörü başlatıldı.  Durdurmak için Ctrl+C.")
    logger.info("Hedef URL     : %s", args.url)
    logger.info(
        "Kontrol aralığı: %d – %d saniye",
        args.min_interval, args.max_interval,
    )
    logger.info("=" * 60)

    while True:
        found = check_appointments(args)

        if found:
            logger.info("Randevu slotu bulundu — monitör kapatılıyor.")
            sys.exit(0)

        wait_seconds = random.randint(args.min_interval, args.max_interval)
        logger.info(
            "Sonraki kontrol %d saniye sonra (%d dakika %d saniye)...",
            wait_seconds,
            wait_seconds // 60,
            wait_seconds % 60,
        )
        time.sleep(wait_seconds)
