"""Yazım için eğitilmiş model (Faz 3, K33): BERTurk üzerinde kelime kelime hata etiketleyici.

Modüller:
  etiketler : sınıflar ve GECTurk kurallarının sınıflara eşlenmesi
  vikipedi  : Türkçe Vikipedi değişiklik geçmişinden gerçek hata → düzeltme çiftleri
  sentetik  : kitap cümlelerine kitaplarda görülen türde yapay hata ekleme
  veri      : eğitim / geliştirme / test dosyalarının kurulması (sızıntı önlemleriyle)
  egit      : eğitim (kayıt noktası, bekçi, bellek yetmezse küçültme)
  olc       : K33'te önceden yazılan ölçümler
  gece      : hepsini sırayla çalıştıran gece betiği
"""
