# Devpost submission packet — Sentinel (Kiroween 2026, Frankenstein)

> Draft siap isi. JANGAN submit tanpa konfirmasi parent.
> Deadline: **5 Des 2026 05:00 WIB** (Dec 4 14:00 PT). Jangan submit di jam terakhir.

## Form fields (copy-paste ready)

- **Project name:** Sentinel — the agent that says NO
- **Category:** Frankenstein
- **Tagline:** An autonomous safety agent for free crypto mints that protects your wallet by refusing — and proves every refusal.
- **Description (Devpost, singkat):** Sentinel scans free-mint candidates and verifies each one against live on-chain data through a deterministic gate pipeline (verified contract, free phase open, zero cost, value signal, clean preview). The LLM is advisory only — no model output can authorise a transaction. Every run leaves an append-only audit trace, a Markdown report, and a live dashboard. A kill switch halts a run within one tick, and a hostile-input firewall blocks injected instructions from project pages. Built with Kiro (specs, steering, hooks, MCP).
- **GitHub repo (public, MIT):** https://github.com/JohnyKucel/sentinel-kiroween
- **How to run (working app / instructions):**
  ```bash
  git clone https://github.com/JohnyKucel/sentinel-kiroween.git
  cd sentinel-kiroween
  python3 -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  python3 -m sentinel.cli run --candidates fixtures/candidates.json
  python3 -m sentinel.cli trap-test
  python3 -m sentinel.cli verify-trace
  python3 -m sentinel.cli dashboard   # http://127.0.0.1:8787
  python3 -m pytest -q                # 95 tests
  ```
  Live reads (optional): `python3 -m sentinel.cli run --candidates fixtures/live-demo.json --live-reads --wallet 0x000000000000000000000000000000000000dEaD`
- **Demo video:** ⏳ MENUNGGU Grey upload `demo/demo.mp4` (46 detik, 1280x720, 662 KB) ke YouTube sebagai Public → tempel URL di sini.
- **How Kiro was used:** paste dari `KIRO_USAGE.md` (spec-driven development, steering, save-hooks, MCP read-only, Kiro CLI v3.1.0 — login 13 Nov + 1 chat turn terverifikasi; MCP live + credits belum diklaim, dinyatakan jujur).
- **Built with:** Kiro, Python 3.12 (stdlib-first), BSC RPC + Sourcify, pytest.
- **Team:** solo — JohnyKucel (Rosy Maulana).

## Bukti verifikasi (13 Nov 2026, semua dicek ulang)

| Item | Hasil |
|---|---|
| pytest | 95 passed in 2.01 s |
| Demo end-to-end (`bash demo/run_demo.sh`) | exit 0; 1 WOULD_MINT + 4 SKIP; verify-trace PASS; dashboard `/health` OK, title "Sentinel — live run" |
| demo.mp4 | h264 1280x720, 45.67 s, 662.675 byte |
| Kiro CLI login | `whoami` = Logged in with Builder ID, sandijohan113@gmail.com |
| Kiro CLI chat (1 turn) | pytest 95 passed in 2.31 s + ffprobe 45.67 s + CHECKLIST read — semua terverifikasi sendiri oleh turn itu |
| Repo GitHub | PUBLIC, MIT terdeteksi, `.kiro/` di root, commit 5c37490 |
| Devpost Kiroween | TERDAFTAR (JohnyKucel, "Thanks for registering!") |

## Masih butuh Grey (tidak bisa diwakilkan)

1. **Upload video demo ke YouTube (Public)** — file `demo/demo.mp4` siap; butuh akun YouTube Grey. Setelah upload, isi URL video di atas.
2. **Klaim 4.000 kredit Kiro (opsional, sebelum 2 Des 03:00 WIB)** — form Resources tab + Didit ID check (foto KTP/paspor + selfie). Data form siap:
   - First/Last name: Rosy Maulana
   - Devpost email: darmih8@gmail.com
   - URL profil Devpost: https://devpost.com/JohnyKucel
   - Kiro User ID: `d-9067c98495.04a874c8-20c1-7000-ea62-d1058ad6c3c9`
   - Kategori: Frankenstein
   - Tentang proyek: `Sentinel — safety agent for free mints`
   - Catatan: build TIDAK butuh credits ini (Free plan 50 kredit cukup; tidak ada kartu yang diminta — tolak penawaran "Kiro Pro free month" yang minta kartu).
3. **Tekan submit di Devpost** — setelah URL video terisi; butuh konfirmasi parent.
