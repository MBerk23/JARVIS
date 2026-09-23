# =========================================================
# JARVIS
# BERK'İN KİŞİSEL YAPAY ZEKA ASİSTANI
#
# Özellikler:
# - Ollama AI (qwen2.5)
# - Kalıcı hafıza (eksik alanları otomatik tamamlayan güvenli yükleme)
# - Türkçe sesli cevap
# - Mikrofon butonu
# - Thread ile donmayan GUI
# - Oyun modu, Kod modu
# - PDF okuma / Sesli kitap
# - Hızlı komutlar (Steam, LoL, VSCode, ChatGPT)
# - YENİ: Enter ile mesaj gönderme (Shift+Enter -> yeni satır)
# - YENİ: Kod blokları düzgün, satır satır ve kopyalanabilir gösteriliyor
# - YENİ: "Son Kodu Kopyala" butonu (panoya tek tıkla kopyalar)
# - YENİ: Ses durdurma butonu, eş zamanlı ses dosyası çakışma düzeltmesi
# =========================================================

import os
import sys
import re
import html
import time
import json
import subprocess
import shutil
import webbrowser
import asyncio
import threading

import pygame  # Ses çalmak için
import ollama
import speech_recognition as sr
import edge_tts

from PyPDF2 import PdfReader

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame,
    QFileDialog, QProgressBar
)

# =========================================================
# AYARLAR
# =========================================================

ASISTAN_ADI = "JARVIS"
MODEL_ADI = "qwen3:8b"
VOICE = "tr-TR-AhmetNeural"
SESLI_CEVAP = True
HAFIZA_DOSYASI = "hafiza.json"
PDF_KLASORU = "pdf_kitaplar"
SES_KLASORU = "jarvis_audio"

os.makedirs(PDF_KLASORU, exist_ok=True)
os.makedirs(SES_KLASORU, exist_ok=True)

# =========================================================
# KULLANICI PROFİLİ
# =========================================================

VARSAYILAN_KULLANICI_BILGILERI = {
    "genel": {
        "isim": "Mehmet Berk Güler",
        "hitap": "Berk",
        "ülke": "Türkiye"
    },
    "egitim": {
        "universite": "Marmara Üniversitesi",
        "bolum": "Elektrik-Elektronik Mühendisliği",
        "durum": "Mezun",
        "ikinci_egitim": "Anadolu Üniversitesi Açıköğretim Yönetim Bilişim Sistemleri",
        "dersler": ["Güç Sistemleri", "Elektromanyetik Alan Teorisi", "Sinyaller ve Sistemler", "Per-Unit", "MATLAB", "Simulink"]
    },
    "programlama": {
        "diller": ["Python", "C", "C++", "C#", "MicroC", "MATLAB"],
        "python": ["OpenCV", "MediaPipe", "TensorFlow", "TensorFlow Lite", "PyQt5", "Tkinter", "Kivy", "Pandas", "PyGame", "PyWhatKit", "Selenium"]
    },
    "arduino_embedded": {
        "platformlar": ["Arduino", "Raspberry Pi 4", "Raspberry Pi Pico", "Raspberry Pi Pico W", "ESP32", "Jetson Nano"],
        "konular": ["GPIO", "PWM", "ADC", "UART", "I2C", "SPI", "sensörler", "motor kontrolü", "servo", "gömülü sistemler", "kamera sistemleri", "IoT"],
        # NOT: "MicroC" -> mikroC PRO (MikroElektronika) olarak biliniyor, PIC/AVR/ARM için kullanılır.
        # PlatformIO eklendi: Arduino IDE'ye alternatif, VSCode içinde profesyonel gömülü geliştirme ortamı.
        "yazilim": ["Arduino IDE", "PlatformIO", "MicroC (mikroC PRO)", "Python", "Proteus"]
    },
    "modelleme_elektronik": {
        # Fritzing eklendi: breadboard/şematik tasarımı için yaygın kullanılan basit bir araç.
        "yazilim": ["Proteus", "MATLAB", "Simulink", "AutoCAD", "Fritzing"],
        "konular": ["Devre tasarımı", "Elektronik devreler", "NTC", "Sensörler", "Kontrol sistemleri", "Sinyal işleme", "Güç sistemleri", "Per-Unit", "Elektromanyetik alan"]
    },
    "3d": {
        "yazici": "Creality Ender-3 V3 KE",
        "konular": ["3D printing", "3D modelleme", "STL", "PLA", "G-code", "dilimleme", "mekanik tasarım"]
    },
    "yapay_zeka": {
        "konular": ["Python", "OpenCV", "MediaPipe", "TensorFlow", "TensorFlow Lite", "Computer Vision", "Machine Learning", "gerçek zamanlı görüntü işleme"]
    },
    "bitirme_projesi": {
        "isim": "Sürücü Risk ve Uygunluk Tespit Sistemi",
        "teknolojiler": ["Raspberry Pi 4", "Kamera", "OpenCV", "MediaPipe", "TensorFlow Lite", "Python", "IR termal sensör", "İvmeölçer", "Jiroskop", "I2C"],
        "hedef": "Gerçek zamanlı sürücü izleme ve Driving Fitness Score oluşturmak."
    },
    "asistan": {
        "dil": "Türkçe",
        "hitap": "Berk",
        "samimi": True
    }
}

# =========================================================
# HAFIZA İŞLEMLERİ
# =========================================================

def yeni_hafiza():
    return {
        "kullanici_bilgileri": json.loads(json.dumps(VARSAYILAN_KULLANICI_BILGILERI)),
        "mesaj_gecmisi": []
    }

def varsayilanlarla_birlestir(hedef, varsayilan):
    """
    Kayıtlı hafızadaki (hafiza.json) eksik alanları varsayılan profil ile
    (iç içe sözlükler dahil) otomatik tamamlar. Bu sayede eski/eksik bir
    hafiza dosyası KeyError ile çökme yaratmaz.
    """
    for anahtar, deger in varsayilan.items():
        if anahtar not in hedef:
            hedef[anahtar] = json.loads(json.dumps(deger))
        elif isinstance(deger, dict) and isinstance(hedef.get(anahtar), dict):
            varsayilanlarla_birlestir(hedef[anahtar], deger)
    return hedef

def hafizayi_kaydet():
    global hafiza
    try:
        with open(HAFIZA_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(hafiza, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Hafıza kayıt hatası:", e)

def hafizayi_yukle():
    if not os.path.exists(HAFIZA_DOSYASI):
        return yeni_hafiza()
    try:
        with open(HAFIZA_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
        if "kullanici_bilgileri" not in veri:
            veri["kullanici_bilgileri"] = json.loads(json.dumps(VARSAYILAN_KULLANICI_BILGILERI))
        else:
            veri["kullanici_bilgileri"] = varsayilanlarla_birlestir(
                veri["kullanici_bilgileri"], VARSAYILAN_KULLANICI_BILGILERI
            )
        if "mesaj_gecmisi" not in veri:
            veri["mesaj_gecmisi"] = []
        return veri
    except Exception as e:
        print("Hafıza okuma hatası, yeni hafıza oluşturuluyor:", e)
        return yeni_hafiza()

hafiza = hafizayi_yukle()
kullanici_bilgileri = hafiza["kullanici_bilgileri"]
mesaj_gecmisi = hafiza["mesaj_gecmisi"]

# =========================================================
# SYSTEM PROMPT
# =========================================================

def sistem_promptu():
    profil = json.dumps(kullanici_bilgileri, ensure_ascii=False, indent=2)

    return f"""
Sen JARVIS adında Berk'in kişisel yapay zeka asistanısın.
Türkçe konuş. Direkt cevap ver. Teknik konularda (Arduino, Python vb.) detaylı çalışır kod yaz.
Kod verirken MUTLAKA ```dil_adi ve ``` ile başlayan/biten markdown kod bloğu kullan
(örnek: ```python ... ```). Dil etiketini kodun GERÇEK diline göre seç:
Arduino/C/C++ kodu için ```cpp, Python için ```python, MATLAB için ```matlab
kullan - Arduino kodunu ASLA ```python etiketiyle verme.

Samimi ama saygılı bir üslup kullan. Robotik ve aşırı resmi cevaplardan kaçın.

==============================
KULLANICI PROFİLİ
==============================
{profil}
"""

# =========================================================
# PDF OKUMA
# =========================================================

def pdf_metni_oku(dosya):
    reader = PdfReader(dosya)
    sayfalar = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text:
                sayfalar.append(f"\n\n--- SAYFA {i + 1} ---\n\n" + text)
        except Exception as e:
            print(f"PDF sayfa {i+1} okunamadı:", e)
    return "".join(sayfalar)

def pdf_parcalara_ayir(metin, karakter=5000):
    return [metin[i:i + karakter] for i in range(0, len(metin), karakter)]

# =========================================================
# MESAJ BİÇİMLENDİRME (KOD BLOKLARI DÜZELTİLDİ)
# =========================================================
# ASIL BUG BURADAYDI:
# self.chat.append(...) HTML olarak yorumlanıyor. HTML'de düz "\n"
# karakterleri satır sonu OLUŞTURMAZ, bu yüzden birden çok satırlı
# kod tek satıra yapışık şekilde görünüyordu. Aşağıdaki fonksiyon
# kod bloklarını tespit edip <br> ile satır satır, sabit genişlikli
# fontla ve fare ile seçilip kopyalanabilir şekilde render ediyor.

KOD_BLOGU_DESENI = re.compile(r"```(\w+)?\n?(.*?)```", re.DOTALL)

def kod_bloklarini_bul(metin):
    return [eslesme.group(2).rstrip("\n") for eslesme in KOD_BLOGU_DESENI.finditer(metin)]

def mesaji_html_bicimlendir(metin):
    parcalar = re.split(r"(```\w*\n?.*?```)", metin, flags=re.DOTALL)
    sonuc = ""
    for parca in parcalar:
        eslesme = KOD_BLOGU_DESENI.match(parca)
        if eslesme:
            dil = (eslesme.group(1) or "").upper()
            kod = eslesme.group(2).rstrip("\n")
            kod_escaped = html.escape(kod).replace("\n", "<br>")
            sonuc += (
                '<div style="background:#03151d;border:1px solid #15536b;'
                'border-radius:8px;padding:10px;margin:6px 0;">'
                f'<div style="color:#5deaff;font-size:11px;margin-bottom:6px;">'
                f'📋 {dil or "KOD"} — fareyle seçip Ctrl+C ile kopyalayabilirsin</div>'
                f'<div style="font-family:Consolas,\'Courier New\',monospace;'
                f'color:#c9f7ff;font-size:13px;white-space:pre;">{kod_escaped}</div>'
                '</div>'
            )
        elif parca:
            sonuc += html.escape(parca).replace("\n", "<br>")
    return sonuc

# =========================================================
# SES MOTORU
# =========================================================

class SesMotoru:
    def __init__(self):
        self.durduruldu = False
        self.duraklatildi = False
        self.thread = None

    def durdur(self):
        self.durduruldu = True
        try:
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass

    def devam(self):
        self.duraklatildi = False

    def duraklat(self):
        self.duraklatildi = True

    async def ses_uret(self, metin, dosya):
        communicate = edge_tts.Communicate(metin, VOICE)
        await communicate.save(dosya)

    def oku(self, metin):
        # Önceki sesi kesip yeni dosya adıyla çakışmayı önlüyoruz
        # (aynı jarvis_temp.mp3 dosyası hâlâ çalarken tekrar yazılmaya
        # çalışılırsa Windows'ta dosya kilitli olabiliyordu).
        self.durdur()
        self.duraklatildi = False
        self.durduruldu = False

        def worker():
            try:
                dosya = os.path.join(SES_KLASORU, f"jarvis_{int(time.time() * 1000)}.mp3")
                asyncio.run(self.ses_uret(metin, dosya))

                if self.durduruldu:
                    return

                if not pygame.mixer.get_init():
                    pygame.mixer.init()

                pygame.mixer.music.load(dosya)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    if self.durduruldu:
                        pygame.mixer.music.stop()
                        break
                    while self.duraklatildi:
                        pygame.time.Clock().tick(10)
                        if self.durduruldu:
                            pygame.mixer.music.stop()
                            return
                    pygame.time.Clock().tick(20)

                try:
                    os.remove(dosya)
                except Exception:
                    pass
            except Exception as e:
                print("TTS hatası:", e)

        self.thread = threading.Thread(target=worker, daemon=True)
        self.thread.start()

ses_motoru = SesMotoru()

# =========================================================
# MİKROFON THREAD
# =========================================================

class MikrofonThread(QThread):
    sonuc = pyqtSignal(str)
    hata = pyqtSignal(str)

    def run(self):
        try:
            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            with sr.Microphone() as source:
                self.sonuc.emit("Dinliyorum...")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=8, phrase_time_limit=20)
            text = recognizer.recognize_google(audio, language="tr-TR")
            self.sonuc.emit(text)
        except Exception as e:
            self.hata.emit(str(e))

# =========================================================
# AI THREAD
# =========================================================

class AIThread(QThread):
    cevap = pyqtSignal(str)
    hata = pyqtSignal(str)

    def __init__(self, komut):
        super().__init__()
        self.komut = komut

    def run(self):
        try:
            cevap = jarvis_yanit(self.komut)
            self.cevap.emit(cevap)
        except Exception as e:
            self.hata.emit(str(e))

# =========================================================
# AI SORGUSU
# =========================================================

def jarvis_yanit(komut):
    global mesaj_gecmisi, hafiza

    mesaj_gecmisi.append({"role": "user", "content": komut})

    messages = [{"role": "system", "content": sistem_promptu()}]
    messages.extend(mesaj_gecmisi[-30:])

    response = ollama.chat(model=MODEL_ADI, messages=messages)
    cevap = response["message"]["content"]

    mesaj_gecmisi.append({"role": "assistant", "content": cevap})

    hafiza["mesaj_gecmisi"] = mesaj_gecmisi
    hafiza["kullanici_bilgileri"] = kullanici_bilgileri
    hafizayi_kaydet()

    return cevap

# =========================================================
# UYGULAMA AÇMA FONKSİYONLARI
# =========================================================

def steam_ac():
    try:
        os.startfile("steam://open/main")
        return True
    except Exception:
        return False

def lol_ac():
    yollar = [
        r"C:\Riot Games\Riot Client\RiotClientServices.exe",
        r"C:\Program Files\Riot Games\Riot Client\RiotClientServices.exe",
        r"D:\Riot Games\Riot Client\RiotClientServices.exe",
        r"E:\Riot Games\Riot Client\RiotClientServices.exe"
    ]
    for yol in yollar:
        if os.path.exists(yol):
            try:
                subprocess.Popen([yol])
                return True
            except Exception:
                pass
    return False

def vscode_ac():
    yollar = [
        shutil.which("code"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe")
    ]
    for yol in yollar:
        if yol and os.path.exists(yol):
            try:
                subprocess.Popen([yol])
                return True
            except Exception:
                pass
    return False

def whatsapp_ac():
    # Masaüstü WhatsApp uygulaması yaygın olarak bu klasörlerden birinde kurulu olur.
    # Bulunamazsa (ör. Microsoft Store sürümü farklı yollarda saklanıyor), web
    # sürümünü (web.whatsapp.com) açarak yine de işlevsel bir sonuç veriyoruz.
    yollar = [
        os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\WhatsApp\WhatsApp.exe"),
    ]
    for yol in yollar:
        if os.path.exists(yol):
            try:
                subprocess.Popen([yol])
                return True
            except Exception:
                pass
    webbrowser.open("https://web.whatsapp.com")
    return True

def spotify_ac():
    # Spotify masaüstü uygulaması genelde AppData\Roaming altına kurulur.
    # Bulunamazsa tarayıcıda open.spotify.com'u açıyoruz.
    yollar = [
        os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
        r"C:\Program Files\Spotify\Spotify.exe",
        r"C:\Program Files (x86)\Spotify\Spotify.exe",
    ]
    for yol in yollar:
        if os.path.exists(yol):
            try:
                subprocess.Popen([yol])
                return True
            except Exception:
                pass
    webbrowser.open("https://open.spotify.com")
    return True

def hizli_ac(uygulama):
    uygulama = uygulama.lower()
    if uygulama == "steam":
        return steam_ac()
    if uygulama == "lol":
        return lol_ac()
    if uygulama == "vscode":
        return vscode_ac()
    if uygulama == "whatsapp":
        return whatsapp_ac()
    if uygulama == "spotify":
        return spotify_ac()

    siteler = {
        "youtube": "https://youtube.com",
        "chatgpt": "https://chatgpt.com",
        "gemini": "https://gemini.google.com",
        "github": "https://github.com",
        "linkedin": "https://www.linkedin.com",
        "gmail": "https://mail.google.com"
    }
    if uygulama in siteler:
        webbrowser.open(siteler[uygulama])
        return True
    return False

# =========================================================
# JARVIS CORE (ANİMASYON)
# =========================================================

class JarvisCore(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.active = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.animasyon)
        self.timer.start(30)
        self.setMinimumSize(300, 300)

    def animasyon(self):
        self.angle += (5 if self.active else 2)
        self.update()

    def set_active(self, active):
        self.active = active

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#03060b"))

        cx, cy = self.width() // 2, self.height() // 2

        for radius in [130, 110, 85, 60]:
            pen = QPen(QColor("#00cfff"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle)
        pen = QPen(QColor("#62efff"))
        pen.setWidth(4)
        painter.setPen(pen)
        for i in range(4):
            painter.drawLine(0, -130, 0, -150)
            painter.rotate(90)
        painter.restore()

        painter.setPen(QPen(QColor("#74f5ff"), 3))
        painter.setBrush(QColor("#071722"))
        radius = 48
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(QColor("#74f5ff"))
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(cx - 45, cy - 10, 90, 25, Qt.AlignCenter, "JARVIS")

# =========================================================
# ENTER İLE GÖNDER (YENİ)
# =========================================================
# ASIL BUG BURADAYDI: Sıradan QTextEdit'te Enter tuşu her zaman
# yeni satır ekler, gönderme tetiklemez. Bu alt sınıf Enter'ı
# yakalayıp gonder_sinyali sinyalini yayınlıyor; Shift+Enter ise
# normal şekilde yeni satır ekliyor.

class GonderKutusu(QTextEdit):
    gonder_sinyali = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.gonder_sinyali.emit()
            return
        super().keyPressEvent(event)

# =========================================================
# ANA GUI SİSTEMİ
# =========================================================

class JarvisGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.mod = "ANA"
        self.ai_thread = None
        self.mic_thread = None
        self.son_kodlar = []  # Son AI cevabındaki kod blokları (kopyala butonu için)
        self.sesli_cevap = SESLI_CEVAP  # artık sabit değil, buton ile açılıp kapanabiliyor

        self.setWindowTitle("JARVIS - YAPAY ZEKA ASİSTANI")
        self.resize(1400, 850)

        self.setStyleSheet("""
        QWidget { background: #03060b; color: #d9faff; font-family: Segoe UI; }
        QFrame { background: #070d15; border: 1px solid #123c50; border-radius: 12px; }
        QLabel#title { color: #72efff; font-size: 32px; font-weight: bold; }
        QLabel#mode { color: #5deaff; font-size: 17px; font-weight: bold; }
        QPushButton { background: #091924; color: #c9f7ff; border: 1px solid #15536b; border-radius: 8px; padding: 12px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background: #103044; border: 1px solid #55ebff; }
        QPushButton#active { background: #0d3548; border: 2px solid #55ebff; }
        QPushButton#mic { background: #07394b; font-size: 15px; }
        QPushButton#send { background: #075b75; border: 1px solid #61efff; }
        QTextEdit { background: #020509; border: 1px solid #123c50; border-radius: 10px; color: #d9faff; padding: 12px; font-size: 14px; }
        QProgressBar { border: 1px solid #123c50; border-radius: 6px; background: #03060b; height: 12px; }
        """)

        self.arayuz()
        self.ana_modu()

    # =====================================================
    # ARAYÜZ OLUŞTURMA
    # =====================================================
    def arayuz(self):
        ana = QVBoxLayout(self)
        ana.setContentsMargins(18, 18, 18, 18)

        # ÜST BAŞLIK
        ust = QHBoxLayout()
        baslik = QVBoxLayout()
        title = QLabel("JARVIS")
        title.setObjectName("title")
        alt = QLabel("BERK'İN KİŞİSEL YAPAY ZEKA SİSTEMİ")
        alt.setStyleSheet("color:#4e6874;")
        baslik.addWidget(title)
        baslik.addWidget(alt)

        self.mode_label = QLabel("ANA MOD")
        self.mode_label.setObjectName("mode")

        ust.addLayout(baslik)
        ust.addStretch()
        ust.addWidget(self.mode_label)
        ana.addLayout(ust)

        # MOD SEÇİM BUTONLARI
        modlar = QHBoxLayout()
        self.ana_btn = QPushButton("◉ ANA MOD")
        self.oyun_btn = QPushButton("🎮 OYUN MODU")
        self.kod_btn = QPushButton("⌨ KOD MODU")
        self.is_btn = QPushButton("💼 İŞ MODU")

        self.ana_btn.clicked.connect(self.ana_modu)
        self.oyun_btn.clicked.connect(self.oyun_modu)
        self.kod_btn.clicked.connect(self.kod_modu)
        self.is_btn.clicked.connect(self.is_modu)

        modlar.addWidget(self.ana_btn)
        modlar.addWidget(self.oyun_btn)
        modlar.addWidget(self.kod_btn)
        modlar.addWidget(self.is_btn)
        ana.addLayout(modlar)

        # İÇERİK BÖLÜMÜ (SOL-MERKEZ-SAĞ)
        icerik = QHBoxLayout()

        # SOL: Hızlı Komutlar
        self.sol = QFrame()
        sol_layout = QVBoxLayout(self.sol)
        self.quick_title = QLabel("HIZLI KOMUTLAR")
        self.quick_title.setStyleSheet("color:#72efff; font-size:17px; font-weight:bold;")
        sol_layout.addWidget(self.quick_title)

        self.quick_layout = QVBoxLayout()
        sol_layout.addLayout(self.quick_layout)
        sol_layout.addStretch()
        icerik.addWidget(self.sol, 1)

        # MERKEZ: Çekirdek Animasyonu
        merkez = QFrame()
        merkez_layout = QVBoxLayout(merkez)
        self.core = JarvisCore()
        merkez_layout.addWidget(self.core)

        self.status = QLabel("SİSTEM HAZIR")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color:#55b8c8;")
        merkez_layout.addWidget(self.status)

        self.pdf_progress = QProgressBar()
        self.pdf_progress.setVisible(False)
        merkez_layout.addWidget(self.pdf_progress)
        icerik.addWidget(merkez, 2)

        # SAĞ: Sohbet Konsolu
        sag = QFrame()
        sag_layout = QVBoxLayout(sag)
        chat_title = QLabel("JARVIS KONSOLU")
        chat_title.setStyleSheet("color:#72efff; font-size:17px; font-weight:bold;")
        sag_layout.addWidget(chat_title)

        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        sag_layout.addWidget(self.chat)

        # İNPUT VE MİKROFON
        input_row = QHBoxLayout()
        self.input = GonderKutusu()
        self.input.setPlaceholderText("Jarvis'e komut ver... (Enter: gönder, Shift+Enter: yeni satır)")
        self.input.setFixedHeight(65)
        self.input.gonder_sinyali.connect(self.mesaj_gonder)

        self.mic_btn = QPushButton("🎙 MİKROFON")
        self.mic_btn.setObjectName("mic")
        self.mic_btn.setFixedWidth(130)
        self.mic_btn.clicked.connect(self.mikrofon)

        send = QPushButton("GÖNDER")
        send.setObjectName("send")
        send.setFixedWidth(100)
        send.clicked.connect(self.mesaj_gonder)

        input_row.addWidget(self.input)
        input_row.addWidget(self.mic_btn)
        input_row.addWidget(send)
        sag_layout.addLayout(input_row)
        icerik.addWidget(sag, 2)

        ana.addLayout(icerik, 1)

        # ALT BİLGİ
        footer = QLabel(f"MODEL: {MODEL_ADI}   |   HAFIZA: AKTİF   |   SES DURUMU: ANA MODDAKİ 🔊 BUTONUNDAN AYARLANIR")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color:#38515c;")
        ana.addWidget(footer)

    # =====================================================
    # YARDIMCI GÖRSEL FONKSİYONLAR
    # =====================================================
    def temizle_butonlar(self):
        while self.quick_layout.count():
            item = self.quick_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def hizli_buton(self, text, function):
        button = QPushButton(text)
        button.clicked.connect(function)
        self.quick_layout.addWidget(button)

    def mod_guncelle(self):
        self.ana_btn.setObjectName("")
        self.oyun_btn.setObjectName("")
        self.kod_btn.setObjectName("")
        self.is_btn.setObjectName("")

        if self.mod == "ANA": self.ana_btn.setObjectName("active")
        elif self.mod == "OYUN": self.oyun_btn.setObjectName("active")
        elif self.mod == "KOD": self.kod_btn.setObjectName("active")
        elif self.mod == "IS": self.is_btn.setObjectName("active")

        self.setStyleSheet(self.styleSheet())

    def chat_ekle(self, gonderen, mesaj):
        renk = "#55ebff" if gonderen == "JARVIS" else ("#a3f76f" if gonderen == "BERK" else "#ff5555")
        icerik_html = mesaji_html_bicimlendir(mesaj)
        self.chat.append(f"<b style='color:{renk}'>{gonderen}:</b><br>{icerik_html}<br>")
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    # =====================================================
    # MODLAR VE BUTON İŞLEMLERİ
    # =====================================================
    def ana_modu(self):
        self.mod = "ANA"
        self.mode_label.setText("ANA MOD")
        self.mod_guncelle()
        self.temizle_butonlar()

        self.hizli_buton("🎮 OYUN MODU", self.oyun_modu)
        self.hizli_buton("⌨ KOD MODU", self.kod_modu)
        self.hizli_buton("📖 PDF / SESLİ KİTAP", self.pdf_ac)
        self.hizli_buton("📋 SON KODU KOPYALA", self.kodu_kopyala)
        self.hizli_buton("🔇 SESİ DURDUR (şu anki)", lambda: ses_motoru.durdur())
        self.hizli_buton(f"🔊 SESLİ CEVAP: {'AÇIK ✅' if self.sesli_cevap else 'KAPALI'}", self.ses_ac_kapa)
        self.hizli_buton("♻ HAFIZAYI TEMİZLE", self.hafiza_temizle)

    def oyun_modu(self):
        self.mod = "OYUN"
        self.mode_label.setText("🎮 OYUN MODU")
        self.mod_guncelle()
        self.temizle_butonlar()
        self.hizli_buton("🎮 LEAGUE OF LEGENDS", lambda: self.hizli_ac("lol"))
        self.hizli_buton("♨ STEAM", lambda: self.hizli_ac("steam"))
        self.hizli_buton("▶ YOUTUBE", lambda: self.hizli_ac("youtube"))
        self.hizli_buton("← ANA MOD", self.ana_modu)

    def kod_modu(self):
        self.mod = "KOD"
        self.mode_label.setText("⌨ KOD MODU")
        self.mod_guncelle()
        self.temizle_butonlar()
        self.hizli_buton("🤖 CHATGPT", lambda: self.hizli_ac("chatgpt"))
        self.hizli_buton("✨ GEMINI", lambda: self.hizli_ac("gemini"))
        self.hizli_buton("🧑‍💻 VISUAL STUDIO CODE", lambda: self.hizli_ac("vscode"))
        self.hizli_buton("🐙 GITHUB", lambda: self.hizli_ac("github"))
        self.hizli_buton("📋 SON KODU KOPYALA", self.kodu_kopyala)
        self.hizli_buton("← ANA MOD", self.ana_modu)

    def is_modu(self):
        self.mod = "IS"
        self.mode_label.setText("💼 İŞ MODU")
        self.mod_guncelle()
        self.temizle_butonlar()
        self.hizli_buton("🐙 GITHUB", lambda: self.hizli_ac("github"))
        self.hizli_buton("💼 LINKEDIN", lambda: self.hizli_ac("linkedin"))
        self.hizli_buton("💬 WHATSAPP", lambda: self.hizli_ac("whatsapp"))
        self.hizli_buton("🎵 SPOTIFY", lambda: self.hizli_ac("spotify"))
        self.hizli_buton("📧 GMAIL", lambda: self.hizli_ac("gmail"))
        self.hizli_buton("← ANA MOD", self.ana_modu)

    # =====================================================
    # FONKSİYONLAR
    # =====================================================
    def hizli_ac(self, uygulama):
        sonuc = hizli_ac(uygulama)
        if sonuc:
            self.chat_ekle("SİSTEM", f"{uygulama.upper()} başarıyla başlatıldı.")
        else:
            self.chat_ekle("SİSTEM", f"{uygulama.upper()} açılamadı. Yol bulunamıyor.")

    def ses_ac_kapa(self):
        self.sesli_cevap = not self.sesli_cevap
        if not self.sesli_cevap:
            ses_motoru.durdur()  # kapatınca o an çalan sesi de kes
        durum = "AÇIK 🔊" if self.sesli_cevap else "KAPALI 🔇"
        self.chat_ekle("SİSTEM", f"Sesli cevap {durum} olarak ayarlandı.")
        if self.mod == "ANA":
            self.ana_modu()

    def kodu_kopyala(self):
        if self.son_kodlar:
            QApplication.clipboard().setText(self.son_kodlar[-1])
            self.chat_ekle("SİSTEM", "Son kod bloğu panoya kopyalandı. ✅ (Ctrl+V ile yapıştırabilirsin)")
        else:
            self.chat_ekle("SİSTEM", "Kopyalanacak bir kod bloğu bulunamadı.")

    def hafiza_temizle(self):
        global mesaj_gecmisi, hafiza
        mesaj_gecmisi.clear()
        hafiza["mesaj_gecmisi"] = []
        hafizayi_kaydet()
        self.chat.clear()
        self.son_kodlar = []
        self.chat_ekle("SİSTEM", "Hafıza ve mesaj geçmişi başarıyla temizlendi.")

    def mesaj_gonder(self):
        komut = self.input.toPlainText().strip()
        if not komut: return
        self.input.clear()
        self.chat_ekle("BERK", komut)

        self.core.set_active(True)
        self.status.setText("JARVIS DÜŞÜNÜYOR...")

        self.ai_thread = AIThread(komut)
        self.ai_thread.cevap.connect(self.ai_cevap_geldi)
        self.ai_thread.hata.connect(self.ai_hata_geldi)
        self.ai_thread.start()

    def ai_cevap_geldi(self, cevap):
        self.core.set_active(False)
        self.status.setText("SİSTEM HAZIR")
        self.chat_ekle("JARVIS", cevap)

        kodlar = kod_bloklarini_bul(cevap)
        if kodlar:
            self.son_kodlar = kodlar

        if self.sesli_cevap:
            ses_motoru.oku(cevap)

    def ai_hata_geldi(self, hata):
        self.core.set_active(False)
        self.status.setText("BAĞLANTI HATASI")
        hata_mesaji = (
            f"Ollama AI Hatası: {hata}<br>"
            "<b>ÇÖZÜM:</b> Lütfen CMD/Terminal açıp <code>ollama run qwen2.5</code> yazarak "
            "modeli arka planda başlat."
        )
        self.chat.append(f"<b style='color:#ff5555'>SİSTEM:</b><br>{hata_mesaji}<br>")
        self.chat.verticalScrollBar().setValue(self.chat.verticalScrollBar().maximum())

    def mikrofon(self):
        self.mic_btn.setEnabled(False)
        self.mic_btn.setText("🎙 DİNLİYOR...")
        self.core.set_active(True)

        self.mic_thread = MikrofonThread()
        self.mic_thread.sonuc.connect(self.mikrofon_sonuc)
        self.mic_thread.hata.connect(self.mikrofon_hata)
        self.mic_thread.start()

    def mikrofon_sonuc(self, text):
        if text == "Dinliyorum...":
            self.status.setText("JARVIS DİNLİYOR...")
            return
        self.mic_btn.setEnabled(True)
        self.mic_btn.setText("🎙 MİKROFON")
        self.core.set_active(False)
        self.input.setText(text)
        self.mesaj_gonder()

    def mikrofon_hata(self, hata):
        self.mic_btn.setEnabled(True)
        self.mic_btn.setText("🎙 MİKROFON")
        self.core.set_active(False)
        self.status.setText("SİSTEM HAZIR")
        self.chat_ekle("SİSTEM", f"Mikrofon Hatası: {hata}")

    def pdf_ac(self):
        dosya, _ = QFileDialog.getOpenFileName(self, "PDF Seç", "", "PDF Dosyaları (*.pdf)")
        if dosya:
            self.chat_ekle("SİSTEM", f"PDF Okunuyor: {dosya.split('/')[-1]}")
            metin = pdf_metni_oku(dosya)
            if metin:
                self.chat_ekle("JARVIS", "PDF başarıyla sisteme yüklendi. Sesi başlatıyorum (ilk 3000 karakter).")
                if self.sesli_cevap:
                    ses_motoru.oku(metin[:3000])
            else:
                self.chat_ekle("SİSTEM", "PDF okunamadı veya içi boş.")

# =========================================================
# PROGRAMI BAŞLATMA
# =========================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    jarvis_app = JarvisGUI()
    jarvis_app.show()

    sys.exit(app.exec_())