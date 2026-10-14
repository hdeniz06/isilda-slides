# isilda-slides

Işılda / Glowtrack için TikTok slideshow fabrikası (ABD kitlesi, İngilizce).

**Akış:** `content/<id>.json` eklenir → GitHub Actions Pexels'ten fotoğrafları, App Store'dan uygulama ekranlarını çeker → 1080x1920 slaytları render eder → `hdeniz06.github.io/isilda-slides` sayfasına yayınlar. TikTok telefonunda sayfayı aç → "Hepsini Fotoğraflara kaydet" → TikTok'ta photo mode ile paylaş.

## Slideshow formatı (`content/<id>.json`)

```json
{
  "id": "2026-10-15-spf-myths",          // benzersiz, tarihle başlar
  "title": "SPF myths",                   // sayfada görünen kısa ad
  "date": "2026-10-15",
  "style": "photo",                       // "photo" (Pexels arka plan) | "clean" (düz renk)
  "mentions_app": false,                  // true ise sayfada "Your brand" beyanı uyarısı çıkar
  "caption": "TikTok açıklaması + hashtagler",
  "slides": [
    {"type": "hook",  "text": "...*vurgulu kelime*...", "sub": "...", "photo": "pexels arama sorgusu"},
    {"type": "point", "num": 1, "title": "...", "body": "...", "photo": "..."},
    {"type": "list",  "title": "...", "items": ["...", "..."], "photo": "..."},
    {"type": "cta",   "text": "...", "sub": "..."},
    {"type": "app",   "title": "...", "screenshot": 0}
  ]
}
```

## İçerik kuralları

- Dil İngilizce, kitle ABD. Slayt başına az kelime: başlık ≤ 8 kelime, gövde ≤ 25 kelime.
- 5–7 slayt. İlk slayt kanca: merak veya hata korkusu ("You might be doing X wrong").
- Sağlık iddiası yok (tedavi eder / iyileştirir gibi). Genel bakım bilgisi, doğrulanabilir tavsiyeler.
- Uygulamadan bahseden slideshow'lar haftada en fazla ~2/7. Geliştirici ağzından dürüst konuşur ("I built Glowtrack…"), sahte kullanıcı yorumu yok.
- Uygulama slaytında yüz fotoğrafı yok, gerçek App Store ekranı kullanılır (`type: app`).
- Kanca ve konu tekrarı yok: `content/` altındaki önceki slideshow'ları kontrol et.

## Yerelde render

```
pip install pillow
PEXELS_API_KEY=... python3 scripts/build.py           # yeni olanları render eder, site/ üretir
python3 scripts/build.py --force <id>                 # birini yeniden render eder
```

Kullanılan Pexels fotoğrafları `history/photos_used.json` içinde, tekrar kullanılmaz.
