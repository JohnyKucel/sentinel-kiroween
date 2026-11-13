# CHECKLIST — Kiroween 2026: Sentinel (Frankenstein)

> Semua akun/registrasi memakai email **darmih8@gmail.com** (perintah Grey
> 2026-11-10). Jangan pakai email lain.

## Identitas proyek (siap pakai di form)

- **Nama:** Sentinel — the agent that says NO
- **Kategori:** Frankenstein
- **Tagline:** An autonomous safety agent for free crypto mints that
  protects your wallet by refusing — and proves every refusal.
- **Deskripsi singkat (Devpost):** Sentinel scans free-mint candidates and
  verifies each one against live on-chain data through a deterministic
  gate pipeline (verified contract, free phase open, zero cost, value
  signal, clean preview). The LLM is advisory only — no model output can
  authorise a transaction. Every run leaves an append-only audit trace, a
  Markdown report, and a live dashboard. A kill switch halts a run within
  one tick, and a hostile-input firewall blocks injected instructions from
  project pages. Built with Kiro (specs, steering, hooks, MCP).
- **Repo (akan dibuat):** `github.com/JohnyKucel/sentinel-kiroween`
  (public, MIT) — nama final diputuskan saat publish; isi: kode di
  `~/workspace/hackathon-big-prizes/kiroween-sentinel/`
- **Demo video:** <3 menit, YouTube public — direkam dari satu run utuh
  tanpa campur tangan (scan → 1 pass + 4 skip → trap-test → kill switch →
  report). File rekaman SUDAH JADI: `demo/demo.mp4` (46 detik, 1280x720,
  rekaman layar nyata Xvfb + xterm + ffmpeg, tanpa suara) — upload oleh Grey.

## Timeline (WIB)

| Tenggat | Waktu | Keterangan |
|---|---|---|
| Sekarang | 13 Nov 2026 | Devpost Kiroween TERDAFTAR (JohnyKucel); akun Kiro jadi (sandijohan113@gmail.com, Free, UserID didapat); `kiro-cli login` DONE + 1 chat turn terverifikasi; repo GitHub PUBLIC (sentinel-kiroween); 95 test lolos; demo end-to-end terverifikasi ulang 13 Nov |
| Build inti | 10–20 Nov | Live chain reads, dashboard final, video demo — SELESAI 10 Nov, lebih cepat dari jadwal |
| Klaim credits | **sebelum 2 Des 03:00 WIB** | Form Resources tab (Dec 1 12:00 PT); kode tiba ±48 jam kerja; redeem sebelum 4 Des — form BISA diisi sekarang (UserID diketahui), Didit ID check tetap butuh Grey |
| Polish + video | 21 Nov–3 Des | README final, write-up Kiro, video final |
| SUBMIT | **sebelum 5 Des 05:00 WIB** | Dec 4 14:00 PT; jangan submit di jam terakhir |
| Juri | Des 2026 | Pemenang diumumkan per Devpost |

## Rencana build (spesifik)

1. **Fase 1 — selesai (10 Nov):** skeleton repo lengkap: `sentinel/`
   (cli, gates G0–G6, firewall, trace, killswitch, chain, report,
   advisor, executor, dashboard), `.kiro/` (specs, steering, hooks, MCP),
   fixtures (5 kandidat + 4 trap), 24 unit test — semua lolos.
2. **Fase 2 — live reads — SELESAI (10 Nov, lebih cepat dari jadwal 11–15 Nov):** `chain.py` ditulis ulang (BscRpc: Session + retry 4 endpoint; Sourcify `fields=abi` — `stdJson` terbukti 400); `live_facts.py` baru (fail-closed: gagal baca → SKIP); CLI `--live-reads` + `--wallet`; trace `LIVE_FACTS`; 46 test lolos (24 baseline + 22 baru, network di-mock); demo offline tetap 1 WOULD_MINT + 4 SKIP, verify-trace PASS, trap-test 4/4; demo live UnWritten: totalMinted 8822/8888, exact_match, balanceOf live. Sisa dari rencana Fase 2 awal (belum dikerjakan): 2 sumber kandidat (scan list statis + input manual) — pindah ke Fase 3.
3. **Fase 3 — dashboard + demo — SELESAI (10 Nov, lebih cepat dari jadwal 16–20 Nov):** dashboard final (`status.json` + trace tail + gate trail + live facts + kill-switch state, endpoint `/`, `/status.json`, `/health`); 2 sumber kandidat baru (`sentinel/sources.py`: static scan list `fixtures/scan-list.json` + input manual `--manual`, dedupe by contract, 16 test baru); demo end-to-end `demo/run_demo.sh` + video nyata `demo/demo.mp4` (38 detik, 1280x720, Xvfb + xterm + ffmpeg, tanpa suara): offline 1 WOULD_MINT + 4 SKIP, sources 2 + 2, live-reads 0 + 5 fail-closed, trap-test 4/4, kill switch abort mid-run (3 kandidat), verify-trace PASS; Kiro pass: hooks diperluas (sources + dashboard on-save tests, 21 passed) — Kiro CLI chat/mcp TERBUKTI butuh login Grey (`whoami` = "Not logged in", chat gagal OAuth, disarankan `login --use-device-flow`). 67 test lolos total (46 + 21 baru).
4. **Fase 4 — polish + hardening (tanpa login Kiro) — SELESAI (10 Nov):** segmen live-reads di demo diperbaiki — langkah 3/8 tetap fail-closed (sintetis 0 + 5), langkah 4/8 BARU: kontrak nyata UnWritten (`fixtures/live-demo.json`, `0x10e46d53...`) dengan `--live-reads --wallet 0x0000...dEaD` → **1 WOULD_MINT** (live terverifikasi: exact_match, 8822/8888, balanceOf 0); fakta free/market/preview dinyatakan sebagai input demo di banner layar + steering product.md (aturan demo-honesty). Test edge-case baru `tests/test_edge_cases.py` (28 test: koersi bool string `"false"`, validasi sources, partial/wallet/nol live facts, encoding calldata balanceOf, tail trace dashboard max 15, query string, config MCP tanpa kredensial, fixture live-demo ter-pin); perbaikan hardening: `_coerce_facts` kini mem-parsing string `"false"`/`"true"` secara eksplisit (sebelumnya `bool("false")` = True — bisa lolos G2 diam-diam). MCP: server kedua `sequential-thinking` di `.kiro/settings/mcp.json` (no network, no writes). Hooks: +2 (`chain.py` + `live_facts.py` → `test_live_reads.py`, 22 passed). Steering: product (demo-honesty) + tech (MCP) + structure (modul/fixture/test terbaru). Draft write-up Kiro `KIRO_USAGE.md` (paste-ready untuk form Devpost, tabel claim / no-claim + batasan login). Video direkam ulang: `demo/demo.mp4` **46 detik, 1280x720, 662 KB** — frame dicek visual (offline 1 + 4, sources 2 + 2, live fail-closed 0 + 5, live pass 1 + 0, trap-test 4/4, kill switch abort, verify-trace PASS). **95 test lolos** (67 baseline + 28 baru). Catatan infra: `xterm` hilang dari VM (dulu ada di Fase 3) — `apt-get update` macet >13 menit, dibatalkan; xterm 390 + xbitmaps dipasang via .deb langsung dari mirror (SHA256 terverifikasi). Kiro CLI chat/MCP tetap butuh login Grey — tidak dijalankan.
5. **Fase 5 — submit (26 Nov–4 Des):** repo public, README final,
   video YouTube public, isi form Devpost, submit. **13 Nov:
   repo public DONE; `kiro-cli login` + 1 chat turn DONE; submission
   packet drafted (`SUBMISSION.md`); tersisa video YouTube (Grey) +
   submit (butuh konfirmasi parent).**

## Langkah registrasi — siap dieksekusi (urutan)

### A. Akun Devpost — ✅ SELESAI 13 Nov 2026
Terdaftar sebagai JohnyKucel ("Thanks for registering!", halaman
submission terverifikasi, 3.133 peserta saat itu). Langkah 1–5 di bawah
sudah tidak berlaku — dicatat sebagai riwayat.
1. Buka https://devpost.com → Sign up (atau langsung
   https://kiroween.devpost.com → Register).
2. Pilih **Sign up with email** (jangan SSO GitHub/Google — supaya akun
   terikat ke darmih8@gmail.com).
3. Isi: full name `Grey` (nama tampil; nama lengkap resmi diisi saat
   menang/payout saja), username (pilih, mis. `greydarmi` — cek
   ketersediaan saat daftar), email `darmih8@gmail.com`, password
   (Grey yang buat; jangan kirim lewat chat), centang ToS + Privacy.
4. **INBOX — darmih8@gmail.com:** email verifikasi dari Devpost →
   Grey forward link-nya (atau klik sendiri); akun aktif setelah klik.
5. Di halaman Kiroween, klik **Register for this hackathon** (gratis).

### B. Akun Kiro — ✅ SELESAI 13 Nov 2026
Akun dibuat via Google sign-in sandijohan113@gmail.com (Gmail di Box);
Free plan, 50 kredit; **Kiro User ID:
`d-9067c98495.04a874c8-20c1-7000-ea62-d1058ad6c3c9`**; `kiro-cli login`
DONE via device flow + 1 chat turn terverifikasi. Langkah 1–3 di bawah
sudah tidak berlaku — dicatat sebagai riwayat.
1. Buka https://kiro.dev → sign in (pilih **Google** atau **GitHub** —
   pakai akun yang terhubung ke darmih8@gmail.com; JANGAN buat AWS
   account — tidak dibutuhkan).
2. Setelah login, buka usage dashboard (app.kiro.dev) → salin **Kiro
   User ID**.
3. (Opsional, nanti saat build:) install Kiro CLI di mesin kerja:
   `curl -fsSL https://cli.kiro.dev/install | bash` — SUDAH terverifikasi
   instalasinya di VM ini (binary `~/.local/bin/kiro-cli`).

### C. Klaim 4.000 free Kiro credits — [BUTUH GREY: form + ID check]
1. Pastikan A + B selesai (harus sudah terdaftar di hackathon).
2. Di halaman Kiroween, buka tab **Resources** → klik form klaim credits.
3. Isi form: first + last name, Devpost email (`darmih8@gmail.com`),
   URL profil Devpost, Kiro User ID (dari B), kategori `Frankenstein`,
   satu baris tentang proyek (`Sentinel — safety agent for free mints`).
4. **INBOX — darmih8@gmail.com:** email dari Devpost berisi link **Didit
   ID check** → Grey kerjakan sendiri di HP (foto KTP/paspor + selfie;
   ini data identitas Grey — tidak bisa diwakilkan).
5. Kode credits tiba ±48 jam kerja via email → login ke Kiro dulu, lalu
   buka link redeem → cek usage dashboard (saldo ber-prefix `kiroween`).
6. **JANGAN** ambil penawaran "Kiro Pro free month" yang minta kartu —
   itu penawaran TERPISAH (bukan Kiroween) dan mengikat auto-renewal.
   Klaim credits Kiroween TIDAK butuh kartu.

### D. Repo GitHub public — ✅ SELESAI 13 Nov 2026
**https://github.com/JohnyKucel/sentinel-kiroween** (PUBLIC, MIT, commit
`5c37490`, `.kiro/` di root, LICENSE terdeteksi). Dibuat + push via
`gh` CLI (login JohnyKucel, scope `repo`). Langkah 1–3 di bawah sudah
tidak berlaku — dicatat sebagai riwayat.
1. Pax siapkan repo lokal lengkap (sudah ada di
   `~/workspace/hackathon-big-prizes/kiroween-sentinel/`).
2. Grey (akun GitHub `JohnyKucel`): buat repo public baru, push, dan
   pastikan file LICENSE terlihat di About + folder `.kiro/` ada di root.
3. Salin URL repo untuk form Devpost.

### E. Video demo YouTube — [BUTUH GREY: upload]
1. Pax rekam demo (screen capture + caption, <3 menit).
2. Grey upload ke YouTube sebagai **Public** dari akunnya → salin link
   untuk form Devpost.

### F. Submit Devpost — [BUTUH GREY: isi + tekan submit]
Form: pilih kategori `Frankenstein`, tempel URL repo GitHub (public +
LICENSE), URL working app / instruksi run, deskripsi, link video
YouTube, write-up pemakaian Kiro (draft di `README.md` + `.kiro/`).
Submit sebelum 5 Des 05:00 WIB.

## Yang HANYA Grey bisa lakukan (ringkas)

1. Buat password Devpost + klik link verifikasi email di
   darmih8@gmail.com.
2. Sign-in Kiro (Google/GitHub) + salin Kiro User ID.
3. Isi form klaim credits + kerjakan Didit ID check (foto ID + selfie).
4. Tekan publish repo GitHub (`JohnyKucel`).
5. Upload video demo ke YouTube (Public).
6. Tekan submit di Devpost.

Segala selain itu (riset, kode, test, demo run, rekaman video, pengisian
draft form) dikerjakan Pax — Grey hanya menerima link/kode dari inbox
untuk diteruskan.
