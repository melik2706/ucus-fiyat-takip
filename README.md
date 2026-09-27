# Gaziantep ⇄ Ankara uçuş fiyat takibi

Google Flights'tan (ücretsiz `fast-flights` kütüphanesi, API anahtarı gerekmez) yaklaşık 3 saatte bir direkt uçuş fiyatlarını çeker ve Telegram'a bildirim gönderir.

## Takip edilenler (`config.json`)
- 2 Kasım GZT→ESB, 3 Kasım GZT→ESB ve 3 Kasım ESB→GZT yönlerindeki tüm direkt uçuşlar
- ⭐ Sabitlenmiş uçuşlar: gidişte 2 Kas 21:20 ve 3 Kas 04:50 (GZT→ESB), dönüşte 3 Kas 19:25 ve 23:50 (ESB→GZT). Sonuçlarda görünmezlerse ayrıca uyarı gelir.
- Plana uyan uçuşlar: gidişte 2 Kas 17:00 sonrası kalkış ve 3 Kas 07:45'ten önce varış; dönüşte 3 Kas 15:30 ile 4 Kas 03:00 arası kalkış

## Bildirimler
- 📉 Plana uyan bir uçuş şimdiye kadar görülen en düşük fiyatının altına inerse
- 🎯 Fiyat hedefin (`target_price`, varsayılan 2.000 TL) altına inerse
- 🆕 Plana uyan yeni bir uçuş eklenirse
- 📋 Her gün saat 09:00'dan sonraki ilk kontrolde günlük özet ve en ucuz gidiş+dönüş kombinasyonu
- ⚠️ Arka arkaya 3 kontrolde veri alınamazsa
- 3 Kasım geçince takip kendiliğinden durur

## Kurulum
1. Telegram'da @BotFather'a `/newbot` yazıp token'ı al, sonra bota bir mesaj gönder.
2. `python telegram_setup.py <TOKEN>` komutu chat ID'yi yazdırır ve test mesajı gönderir.
3. GitHub deposunda Settings → Secrets → Actions altına `TELEGRAM_BOT_TOKEN` ve `TELEGRAM_CHAT_ID` ekle.
4. Actions sekmesinden "Uçuş fiyat takibi" → Run workflow ile ilk kontrolü başlat.

Yerelde deneme: `python main.py --dry-run` (mesaj göndermez). Testler: `python -m pytest`.
Fiyat geçmişi `data/price_history.csv` dosyasında tutulur.

## Gizlilik
- Kimlik yok: Giriş yapılmaz, e-posta veya telefon gönderilmez. Her sorgu çerezsiz, sıfırdan açılan bir oturumla yapılır.
- IP bağı yok: Sorgular GitHub'ın bulut sunucularından gider. Senin ev/telefon IP'n kullanılmaz ve sunucu her çalıştırmada değişir.
- Havayolu sitesine gidilmez: Sadece Google Flights (fiyat karşılaştırma) sorgulanır. AJet/THY sitelerine hiç istek atılmaz.
- Robot izi yok: Başlangıç saati 0–15 dk, sorgular arası bekleme 6–25 sn rastgele ve sorgu sırası her seferinde karışık. Günde yalnızca yaklaşık 8 kontrol yapılır.
- Bileti alırken havayolu/acente sitesine gizli sekmeden (incognito) gir.
