# 🤖 JARVIS - Yapay Zeka Destekli Masaüstü Asistanı

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-brightgreen.svg)

**JARVIS**, sesli komutları algılayan, doğal konuşma sentezi ile yanıt veren, kalıcı hafıza desteği sunan ve PDF dokümanlarını analiz edebilen modüler bir masaüstü yapay zeka asistanıdır. Kullanıcı ile etkileşimlerini saklayarak kişiselleştirilmiş bir asistan deneyimi sağlar.

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [Proje Mimarisi ve Dizim Yapısı](#-proje-mimarisi-ve-dizim-yapısı)
- [Gereksinimler](#-gereksinimler)
- [Kurulum ve Çalıştırma](#-kurulum-ve-çalıştırma)
- [Kullanım ve Komut Örnekleri](#-kullanım-ve-komut-örnekleri)
- [Konfigürasyon ve Hafıza Yönetimi](#-konfigürasyon-ve-hafıza-yönetimi)
- [Yol Haritası (Roadmap)](#-yol-haritası-roadmap)
- [Katkıda Bulunma](#-katkıda-bulunma)
- [Lisans](#-lisans)

---

## 🚀 Özellikler

- 🎤 **Gelişmiş Sesli Etkileşim (STT / TTS):** Kullanıcı sesini anlık olarak metne çevirir ve yüksek kaliteli ses sentezi ile sesli yanıt verir.
- 🧠 **Kalıcı Hafıza Yönetimi (`hafiza.json`):** Kullanıcı tercihlerini, geçmiş konuşmaları ve önemli bilgileri hafızasında tutarak bağlama uygun yanıtlar üretir.
- 📚 **PDF & Doküman Analizi (`pdf_kitaplar/`):** Klasördeki PDF dosyalarını okur, özetler, içerik sorgulaması yapar ve metin tabanlı analizler sunar.
- 💻 **Masaüstü & Sistem Otomasyonu:** Bilgisayar içi uygulamaları başlatabilir, web aramaları yapabilir ve sistem görevlerini yerine getirebilir.
- ⚡ **Önbellek & Performans Optimazyonu (`jarvis_audio/`):** Üretilen ses yanıtlarını lokal olarak yönetir ve geçici dosyaları performanslı şekilde işler.

---

## 📁 Proje Mimarisi ve Dizim Yapısı

```text
jarvis/
│
├── app.py                # Ana uygulama, ses işleme ve asistan mantığı
├── hafiza.json           # Kullanıcı verileri, tercihler ve konuşma geçmişi
├── requirements.txt      # Gerekli Python kütüphaneleri ve bağımlılıklar
├── .gitignore            # Depoya eklenmeyecek geçici/özel dosyalar
├── README.md             # Proje dokümantasyonu
│
├── jarvis_audio/         # Sentezlenen geçici ses dosyalarının depolandığı dizin
└── pdf_kitaplar/         # Asistanın okuyup analiz edeceği PDF dokümanları
