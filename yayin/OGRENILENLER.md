# Yayın robotu: öğrenilenler

1. **26 Kasım, mükerrer story ve reel.** Meta engeli kalkınca kaydı elle sıfırlayıp yeniden paylaştırdım. Aynı anda arka planda çalışan bekçi de sıfırlanan kaydı gördü ve aynı paylaşımı ikinci kez yaptı.
   - Düzeltme: Her paylaşımdan önce kayıt "isleniyor" diye depoya kilitleniyor (git push). Kilidi alamayan robot paylaşmıyor. İki robot aynı anda çalışsa da aynı paylaşım bir kez çıkar.
   - Hata olursa otomatik tekrar deneme yok (EN_FAZLA_DENEME = 1). Bunun yerine GitHub'da uyarı açılıyor.
   - Kural: Kayıt elle sıfırlanmaz. Yeniden paylaşım gerekiyorsa takvime yeni kimlikli bir satır eklenir.
2. **26 Kasım, 10:30 story kaçtı.** GitHub zamanlayıcısı saatlerce çalışmadı. Düzeltme: kendini yeniden başlatan bekçi.
3. **26 Kasım, 18:00 kaçtı.** Meta API erişimini engelledi. Düzeltme: paylaşım hatasında GitHub konusu açılıyor, sahibine bildirim gidiyor.
4. **Her paylaşımdan sonra** son paylaşımlar listelenip mükerrer olup olmadığına bakılır (temizlik.py).
