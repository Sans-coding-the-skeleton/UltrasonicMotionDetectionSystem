# Ultrazvukový systém detekce pohybu

Nízkonákladový systém pro detekci pohybu pomocí ultrazvukového senzoru **HC-SR04** a **Raspberry Pi**. Cílem je vytvořit přesnější alternativu k PIR senzorům pro aplikace jako zabezpečení domácnosti nebo monitorování prostoru. Projekt kombinuje hardware (Raspberry Pi, HC-SR04) s Python kódem pro zpracování dat v reálném čase.

---

## Průběh vývoje
- **Počáteční koncept**: Systém využíval kamerový modul Raspberry Pi a detekci pohybu na principu analýzy snímků (tzv. "radarový" přístup). Tato metoda však generovala příliš mnoho falešných poplachů.
- **Vylepšení**: Byl přidán ultrazvukový senzor **HC-SR04** pro přesnější měření vzdálenosti a detekci pohybu.
- **Hardware**: Pro správnou funkci senzoru bylo nutné vytvořit **odporový dělič** (5V → 3.3V), aby nedošlo k poškození GPIO pinů Raspberry Pi.

---

## Instalace OS na Raspberry Pi
1. **Stáhněte Raspberry Pi Imager** z [oficiální stránky](https://www.raspberrypi.com/software/).
2. **Připravte SD kartu**:
   - Vložte SD kartu do čtečky a připojte k počítači.
3. **Napište OS na SD kartu**:
   - V programu vyberte **Raspberry Pi OS (64-bit)**.
   - Zvolte cílové úložiště (SD kartu).
   - Klikněte na **Write** a počkejte na dokončení (5–10 minut).
4. **Spusťte Raspberry Pi**:
   - Vložte SD kartu do Raspberry Pi.
   - Připojte periferie (klávesnici, myš, monitor) a napájení.
5. **Dokončete nastavení**:
   - Povolte automatické přihlášení do desktopového režimu.
   - Aktualizujte systém:
     ```bash
     sudo apt update && sudo apt upgrade -y
     ```

---

## Instalace programu a konfigurace

### 1. Povolte GPIO a SPI/I2C
1. Spusťte konfigurační nástroj Raspberry Pi:
   ```bash
   sudo raspi-config

    V menu postupujte:

        Interface Options → SPI → Enable

        Interface Options → I2C → Enable

2. Připravte Raspberry Pi

    Ujistěte se, že máte aktualizovaný systém:
    bash

    sudo apt update && sudo apt upgrade -y

3. Nainstalujte závislosti
bash

sudo apt install python3 python3-pip python3-venv git

4. Naklonujte repozitář
bash

git clone https://github.com/Sans-coding-the-skeleton/UltrasonicMotionDetectionSystem.git
cd UltrasonicMotionDetectionSystem

5. Připojte HC-SR04 k Raspberry Pi
Senzor HC-SR04	Raspberry Pi GPIO
VCC	5V (Pin 2 nebo 4)
Trig	GPIO23 (Pin 16)
Echo	→ Odporový dělič → GPIO24
GND	GND (Pin 6 nebo 9)

📝 Schéma zapojení:
Zapojení HC-SR04
viz. docs
6. Vytvořte virtuální prostředí Pythonu
bash

python3 -m venv venv           # Vytvoření virtuálního prostředí
source venv/bin/activate       # Aktivace prostředí
pip install -r requirements.txt # Instalace potřebných knihoven
