# CI/CD Deployment

Workflow: `.github/workflows/ci-cd.yml`

## CI

Setiap push dan pull request menjalankan:

1. `python -m compileall -q app`
2. `pytest tests -q`
3. MariaDB 10.11 service container
4. Database `sentiment_freeport` dan `sentiment_freeport_test`

## CD

Push ke branch `main` setelah CI lulus akan menjalankan:

```text
GitHub Actions -> SSH deploy-analisis@43.173.40.198
  -> sudo /usr/local/sbin/deploy-analisis-sentimen <sha>
  -> clone release baru
  -> install dependency
  -> flask db upgrade
  -> switch symlink current
  -> restart analisis-sentimen.service
  -> health check /health/db
  -> rollback jika health check gagal
```

## GitHub Secrets

Tambahkan di repository Settings -> Secrets and variables -> Actions:

| Secret | Nilai |
|---|---|
| `VPS_HOST` | `43.173.40.198` |
| `VPS_USER` | `deploy-analisis` |
| `VPS_SSH_KEY` | isi private key `github_deploy_analisis_ed25519` |
| `VPS_KNOWN_HOSTS` | output `ssh-keyscan -t ed25519 43.173.40.198` |

Jangan commit private key.

## VPS setup

User `deploy-analisis` hanya boleh menjalankan:

```text
sudo /usr/local/sbin/deploy-analisis-sentimen <sha>
```

Script ada di `deploy/deploy-analisis-sentimen`. Service systemd ada di `deploy/analisis-sentimen.service`.

Health check production:

```bash
curl -fsS https://minesentiment.web.id/health/db
```

## Rollback

Deploy script menyimpan release sebelumnya. Jika health check gagal, script otomatis mengembalikan symlink `current` ke release sebelumnya dan restart service.
