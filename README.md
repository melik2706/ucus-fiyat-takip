# Gaziantep ⇄ Ankara uçuş fiyat takibi

İki bağımsız kaynaktan, **Google Flights** (`fast-flights`) ve **Kiwi.com** (herkese açık GraphQL), 30 dakikada bir direkt uçuş fiyatlarını çeker, çapraz kontrol yapar ve Telegram'a bildirim gönderir. Tamamen ücretsizdir, API anahtarı gerekmez.

## Takip edilenler (`config.json`)
- 2 Kasım GZT→ESB, 3 Kasım GZT→ESB ve 3 Kasım ESB→GZT yönlerindeki tüm direkt uçuşlar
- ⭐ Sabitlenmiş uçuşlar: gidişte 2 Kas 21:20 ve 3 Kas 04:50 (GZT→ESB), dönüşte 3 Kas 19:25 ve 23:50 (ESB→GZT). Sonuçlarda görünmezlerse ayrıca uyarı gelir.
- Plana uyan uçuşlar: gidişte 2 Kas 17:00 sonrası kalkış ve 3 Kas 07:45'ten önce varış; dönüşte 3 Kas 15:30 ile 4 Kas 03:00 arası kalkış

## Çapraz kontrol
- Aynı uçuşun her iki kaynaktaki fiyatı yan yana gösterilir; uyarılar en düşük fiyata göre verilir.
- ✅ İki kaynakta da düştüyse gerçek indirimdir. ⚠️ Sadece birinde düştüyse o siteden kontrol ederek al.
- Kiwi fiyatı kendi hizmet bedelini içerdiği için genelde ~500 TL yüksektir. Google fiyatı havayolunun kendi fiyatına yakındır.

## Bildirimler
- 📉 Plana uyan bir uçuş şimdiye kadar görülen en düşük fiyatının altına inerse
- 🎯 Fiyat hedefin (`target_price`, varsayılan 2.000 TL) altına inerse
- 🆕 Plana uyan yeni bir uçuş eklenirse
- 📋 06:00–00:00 arası her saat başı özet: fiyatlar, en ucuz gidiş+dönüş ve son özetten beri yapılan kontrol sayısı (botun çalıştığının kanıtı). 01:00–06:00 arası özet gönderilmez; gece gelen fiyat uyarıları sessiz bildirimle gider.
- ⚠️ Arka arkaya 3 kontrolde veri alınamazsa
- 3 Kasım geçince takip kendiliğinden durur

## Nerede çalışır
Oracle Cloud Always Free sunucusunda (130.61.173.188, takvim asistanıyla aynı sunucu) `ucus-takip.timer` ile her saatin :11 ve :41'inde çalışır.
- Kod: `~/ucus-fiyat-takip` (her çalıştırmada `git pull` ile güncellenir; config değişikliği için push yeterli)
- Veri ve gizli ayarlar: `~/ucus-data` (`state.json`, `price_history.csv`, `.env`)
- Kaynak sınırı: CPUQuota=50%, MemoryMax=400M. Bir kontrol ~0,4 sn CPU kullanır.
- Log: `ssh -i ~/.ssh/oracle_asistan ubuntu@130.61.173.188 "journalctl -u ucus-takip -n 50"`
- Kurulum/güncelleme: `./deploy/sunucuya_kur.sh`. Takibi kapatma: `sudo systemctl disable --now ucus-takip.timer`
- GitHub Actions iş akışı sadece elle yedek çalıştırma içindir; GitHub'ın zamanlayıcısı güvenilir tetiklenmediği için taşındı.

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
- Robot izi yok: Başlangıç saati 0–3 dk, sorgular arası bekleme 3–12 sn rastgele; kaynak ve sorgu sırası her seferinde karışık.
- Bileti alırken havayolu/acente sitesine gizli sekmeden (incognito) gir.
