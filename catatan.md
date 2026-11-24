# Catatan Persiapan & Menjalankan Automasi Teams

## 1. Uji Coba Manual di Laptop (Wajib Sebelum Dijadwalkan)

1. Pastikan isi [`.env`](.env) sudah sesuai:
   - `MEET_URL`: link meeting Microsoft Teams
   - `MEET_USERNAME`: nama peserta saat join
   - `DURATION_MINUTES`: `100`
   - `HEADLESS`: `false` (untuk uji coba di laptop agar layar terlihat)
   - `END_DATE`: `2026-12-30` (setelah tanggal ini script otomatis tidak berjalan)
2. Jalankan manual:
   ```bash
   .venv/bin/python main.py
   ```
3. Pastikan alur klik (launcher browser, popup *Continue without audio or video*, isi nama, matikan mic/kamera, dan tombol *Join now*) berjalan sampai masuk meeting.

---

## 2. Pasang Jadwal Otomatis di Laptop (`systemd --user`)

File template sudah tersedia di folder `systemd/`:
- `systemd/teams-automation.service`
- `systemd/teams-automation.timer` (Senin–Jumat jam `18:55:00`)

Jika ingin mengaktifkan di laptop nanti:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/teams-automation.service systemd/teams-automation.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now teams-automation.timer
```

Cek status & log:
```bash
systemctl --user list-timers teams-automation.timer
journalctl --user -u teams-automation -f
```

Menonaktifkan / menghapus:
```bash
systemctl --user disable --now teams-automation.timer
rm -f ~/.config/systemd/user/teams-automation.service ~/.config/systemd/user/teams-automation.timer
systemctl --user daemon-reload
```

---

## 3. Tata Cara Instalasi & Deploy di Linux Server (Homeserver)

### A. Persiapan Server & Instalasi Docker (Ubuntu/Debian)

Jika Docker & Docker Compose belum terpasang di Linux server Anda:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```
> Logout lalu login kembali ke SSH agar grup `docker` aktif tanpa `sudo`.

Pastikan timezone server sesuai WIB (`Asia/Jakarta`) agar jadwal `crontab` jam `18:55` tepat:
```bash
sudo timedatectl set-timezone Asia/Jakarta
timedatectl
```

### B. Salin Project ke Linux Server

Dari laptop Anda, salin folder project ke server (kecuali `.venv/` dan `__pycache__/`):
```bash
rsync -avz --exclude '.venv' --exclude '__pycache__' \
  "/home/azhar-fakhri/Documents/python/automasi meet aws/" \
  user@IP_SERVER:~/automasi-meet-aws/
```

### C. Build & Uji Coba di Server

Masuk ke server via SSH, lalu masuk ke folder project:
```bash
cd ~/automasi-meet-aws
```

Pastikan `.env` ada dan sesuai (di Docker, `HEADLESS=true` sudah otomatis di-override oleh `docker-compose.yml`, tapi boleh juga diubah di `.env`):
```bash
cat .env
```

Build image Docker (berisi Python 3.12 + Chromium + ChromeDriver):
```bash
docker compose build
```

Uji coba jalankan sekali secara manual (tekan `Ctrl+C` setelah terlihat berhasil masuk/jalan):
```bash
docker compose run --rm teams-bot
```

### D. Pasang Jadwal Otomatis di Server (`crontab`)

Buka crontab:
```bash
crontab -e
```

Tambahkan baris berikut untuk menjalankan setiap **Senin–Jumat jam 18:55**:
```cron
55 18 * * 1-5 cd /home/USER_SERVER/automasi-meet-aws && /usr/bin/docker compose run --rm teams-bot >> /home/USER_SERVER/automasi-meet-aws/teams-bot.log 2>&1
```
> Ganti `USER_SERVER` dengan username Linux di homeserver Anda (cek dengan perintah `whoami`), dan pastikan path `docker` sesuai (`which docker`).

### E. Monitoring & Pemeliharaan di Server

- **Lihat log eksekusi:**
  ```bash
  tail -f ~/automasi-meet-aws/teams-bot.log
  ```
- **Ubah link meeting / durasi / tanggal berakhir:** edit `.env` di server (tidak perlu rebuild Docker image):
  ```bash
  nano ~/automasi-meet-aws/.env
  ```
- **Hentikan container yang sedang berjalan (jika perlu):**
  ```bash
  docker ps
  docker stop teams-automation
  ```
- **Catatan tanggal berakhir:** selama `END_DATE=2026-12-30` ada di `.env`, mulai `2026-12-31` script otomatis langsung keluar tanpa membuka browser.

---

### Opsi Alternatif: Deploy di Linux Server Tanpa Docker (Langsung Python + Chromium)

Jika server tidak memakai Docker:
```bash
sudo apt update
sudo apt install -y python3 python3-venv chromium chromium-driver
cd ~/automasi-meet-aws
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```
Set `HEADLESS=true`, `CHROME_BINARY=/usr/bin/chromium`, dan `CHROMEDRIVER_PATH=/usr/bin/chromedriver` di `.env`, lalu pasang di `crontab -e`:
```cron
55 18 * * 1-5 cd /home/USER_SERVER/automasi-meet-aws && /home/USER_SERVER/automasi-meet-aws/.venv/bin/python main.py >> /home/USER_SERVER/automasi-meet-aws/teams-bot.log 2>&1
```
