# Traccia Formazione

Mini web app self-hosted per gestione certificati e scadenze formazione dipendenti con sync automatico da Factorial API.

## Stack

- Backend/UI: FastAPI + Jinja2 + Bootstrap
- DB: PostgreSQL
- Migrazioni: Alembic
- Scheduler: APScheduler (sync Factorial + invio alert)
- Deploy: Docker Compose (app + db)

## Funzionalita principali

- Sync dipendenti da Factorial (`Sync now` + scheduler notturno)
- Gestione certificazioni per dipendente
- Upload multi-file allegati (`PDF/JPG/PNG`) con metadati e checksum
- Dashboard scadenze (30/60/90 giorni)
- Alert configurabili a soglia (90/60/30/14/7/1) con anti-spam (`certificato+soglia`)
- Utenti locali con ruoli: `admin`, `manager`, `viewer`
- Sicurezza: bcrypt, sessioni sicure, CSRF su form, rate-limit login
- Audit log su create/update/delete certificazioni/allegati

## Struttura repository

- `docker-compose.yml`
- `app/` (FastAPI, template, migrazioni, Dockerfile)
- `db/` (placeholder per eventuali init script)
- `.env.example`

## Setup rapido

1. Copia env:

```bash
cp .env.example .env
```

2. Avvia:

```bash
docker compose up -d --build
```

3. Apri app:

- URL: `http://localhost:8080`
- Login iniziale:
  - email: `admin@example.local`
  - password: `admin1234`

4. Cambia subito password admin creando nuovo utente admin e disabilitando quello di default.

## Configurazione Factorial

Da UI (`Impostazioni`) o via env:

- `FACTORIAL_BASE_URL` (esempio: `https://api.factorialhr.com`)
- `FACTORIAL_API_TOKEN` (usato come `x-api-key`)
- `FACTORIAL_COMPANY_ID` (opzionale)

Operazioni:

- Sync manuale: bottone `Sync now (Factorial)` in pagina Dipendenti
- Sync schedulato: variabile `FACTORIAL_SYNC_CRON` (default: `0 2 * * *`)

Regole sync:

- Nuovo dipendente -> creato
- Dipendente esistente -> aggiornato
- Terminated/inactive -> marcato inattivo (non cancellato)
- Se Factorial non raggiungibile -> app continua a usare dati locali

Note implementazione API:
- Endpoint usato: `/api/2026-01-01/resources/employees/employees`
- Header auth: `x-api-key: <FACTORIAL_API_TOKEN>`
- Paginazione cursor (`meta.has_next_page`, `meta.end_cursor`) gestita automaticamente

## Deploy in Portainer

1. Crea Stack in Portainer.
2. Incolla contenuto di `docker-compose.yml`.
3. Carica `.env` con le variabili richieste.
4. Deploy stack.
5. Verifica healthcheck `app` e `db` in stato `healthy`.

La porta esposta di default e `8080` (configurabile con `PORT`).

## Persistenza dati

Volumi docker usati:

- `db_data`: database PostgreSQL
- `attachments_data`: allegati certificazioni

## Backup / Restore

### Backup DB

```bash
docker exec traccia-db pg_dump -U traccia traccia_formazione > backup.sql
```

### Restore DB

```bash
cat backup.sql | docker exec -i traccia-db psql -U traccia -d traccia_formazione
```

### Backup allegati

```bash
docker run --rm -v attachments_data:/data -v $(pwd):/backup alpine tar czf /backup/attachments_backup.tgz -C /data .
```

### Restore allegati

```bash
docker run --rm -v attachments_data:/data -v $(pwd):/backup alpine sh -c "tar xzf /backup/attachments_backup.tgz -C /data"
```

## Endpoint REST principali

- `GET /api/employees`
- `GET /api/employees/{id}/certifications`
- `POST /api/employees/{id}/certifications`
- `POST /api/certifications/{id}/attachments`
- `GET /api/admin/settings`
- `POST /api/admin/settings`
- `POST /api/admin/sync/factorial`

Tutti gli endpoint richiedono sessione autenticata; quelli admin richiedono ruolo `admin`.
