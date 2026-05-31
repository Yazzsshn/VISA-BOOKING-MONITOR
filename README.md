# 🗓️ Vize Randevu Monitörü

Seçtiğiniz randevu sayfasını otomatik olarak takip eden, müsait slot bulunduğunda **Telegram** üzerinden anlık bildirim gönderen bir Python botu.

Herhangi bir vize veya resmi randevu sitesinde çalışacak şekilde tasarlanmıştır — URL, tespit yöntemi ve bildirim metni tamamen komut satırından yapılandırılır.

---

## ✅ Özellikler

- **Herhangi bir siteyle çalışır** — URL'yi ve tespit yöntemini siz belirlersiniz
- **3 farklı slot tespit stratejisi:** XPath/CSS seçici, görünür metin anahtar kelimesi, ham HTML kaynağı anahtar kelimesi
- **Telegram bildirimi** — slot açılır açılmaz mesaj alırsınız
- **Proxy desteği** — konut proxy ile IP engellenmesini önleme
- **Headless mod** — sunucu veya Raspberry Pi üzerinde arka planda çalışır
- **Rastgele bekleme aralığı** — tespit riskini azaltmak için

---

## 📋 Gereksinimler

```
Python 3.9+
Google Chrome (yüklü olması gerekir)
```

### Python paketleri

```bash
pip install undetected-chromedriver selenium requests
```

---

## 🚀 Kurulum

```bash
git clone https://github.com/kullanici/visa-monitor.git
cd visa-monitor
pip install undetected-chromedriver selenium requests
```

---

## ⚙️ Kullanım

```
python monitor.py --url URL --bot-token TOKEN --chat-id CHAT_ID [seçenekler]
```

### Zorunlu parametreler

| Parametre | Kısa | Açıklama |
|-----------|------|----------|
| `--url` | `-u` | Randevu sayfasının tam adresi |
| `--bot-token` | `-t` | @BotFather'dan alınan Telegram bot token'ı |
| `--chat-id` | `-c` | Bildirimlerin gönderileceği Telegram chat ID'si |

### Slot tespit parametreleri *(en az biri zorunlu)*

| Parametre | Açıklama |
|-----------|----------|
| `--selector "XPATH"` | Müsait slotları işaret eden XPath seçicisi |
| `--selector-type css` | Seçiciyi CSS olarak yorumla (varsayılan: `xpath`) |
| `--keyword "Müsait"` | Sayfanın görünür metninde aranacak kelime |
| `--page-keyword "true"` | Ham HTML kaynağında aranacak kelime/dize |

### İsteğe bağlı parametreler

| Parametre | Varsayılan | Açıklama |
|-----------|------------|----------|
| `--proxy IP:PORT` | — | Konut proxy adresi |
| `--min-interval` | `600` | Kontroller arası minimum bekleme (saniye) |
| `--max-interval` | `900` | Kontroller arası maksimum bekleme (saniye) |
| `--wait-timeout` | `15` | Sayfa yükleme zaman aşımı (saniye) |
| `--headless` | `False` | Tarayıcıyı arka planda çalıştır |
| `--notify-message "Metin"` | — | Telegram için özel bildirim metni |

---

## 💡 Kullanım Örnekleri

### 1 — XPath seçicisiyle temel kullanım

```bash
python monitor.py \
  --url "https://example-visa-site.com/appointments" \
  --bot-token "123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ" \
  --chat-id "987654321" \
  --selector "//div[contains(@class,'available-slot')]"
```

### 2 — Anahtar kelime araması + proxy + headless mod

```bash
python monitor.py \
  --url "https://example-visa-site.com/appointments" \
  --bot-token "123456789:ABCDefGhIJKlmNoPQRsTUVwxyZ" \
  --chat-id "987654321" \
  --keyword "Müsait" \
  --proxy "1.2.3.4:8000" \
  --headless \
  --notify-message "Schengen vizesi randevusu açıldı!"
```

### 3 — CSS seçicisi + özel aralık

```bash
python monitor.py \
  --url "https://example-visa-site.com/appointments" \
  --bot-token "TOKEN" \
  --chat-id "CHAT_ID" \
  --selector ".slot.open" \
  --selector-type css \
  --min-interval 300 \
  --max-interval 600
```

### 4 — Ham HTML kaynağında JSON flag aramak

```bash
python monitor.py \
  --url "https://example-visa-site.com/appointments" \
  --bot-token "TOKEN" \
  --chat-id "CHAT_ID" \
  --page-keyword "\"available\":true"
```

### 5 — Birden fazla stratejiyi birlikte kullanmak

Birden fazla tespit parametresi verilirse bot sırayla dener;
herhangi biri eşleşirse slot bulunmuş sayılır:

```bash
python monitor.py \
  --url "https://example-visa-site.com/appointments" \
  --bot-token "TOKEN" \
  --chat-id "CHAT_ID" \
  --selector "//td[@data-status='open']" \
  --keyword "Available" \
  --page-keyword "slotCount:1"
```

---

## 🔔 Telegram Bot Kurulumu

1. Telegram'da **@BotFather**'ı aratın ve başlatın.
2. `/newbot` komutunu gönderin ve adımları takip edin.
3. Size verilen **token**'ı `--bot-token` parametresi olarak kullanın.
4. Chat ID'nizi öğrenmek için **@userinfobot**'a bir mesaj atın;  
   ya da bota bir mesaj gönderdikten sonra şu adresi tarayıcıda açın:  
   `https://api.telegram.org/bot<TOKEN>/getUpdates`

---

## 🔍 Doğru Seçiciyi Nasıl Bulursunuz?

1. Hedef siteyi Chrome ile açın.
2. Sağ tıklayın → **İncele (Inspect)**.
3. Müsait randevu gösteren öğeyi bulun.
4. Öğeye sağ tıklayın → **Kopyala → XPath kopyala**.
5. Kopyalanan değeri `--selector` parametresi olarak kullanın.

**Alternatif:** Site tamamen JavaScript ile render ediliyorsa ve DOM üzerinden seçici bulmak zorsa, `--page-keyword` ile API yanıtındaki bir JSON anahtarını arayabilirsiniz.

---

## ⚠️ Önemli Notlar

- Bot, slot bulur bulmaz bildirim gönderir ve **otomatik olarak kapanır**.
- İstek sıklığını makul tutun; çok kısa aralıklar IP engeline yol açabilir.
- Headless mod sunucularda önerilir; yerel makinede headless olmadan test edebilirsiniz.
- Site CAPTCHA sunuyorsa manuel çözüm veya 2captcha gibi bir servis entegrasyonu gereklidir (`monitor.py` içinde ilgili yorum satırına bakın).

---

## 📄 Lisans

MIT
