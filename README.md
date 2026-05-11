# Synergo - Lokale, veilige chatbot met kennisbank

Een volledig lokaal gehoste chatbot met RAG-kennisbank. Geen cloud, geen
telemetrie, geen data die je machine verlaat. Alles draait in Docker
containers achter een loopback-binding.

## Architectuur

```
+----------------------+
|  Streamlit UI        |   127.0.0.1:8501  (alleen loopback)
|  (frontend)          |
+----------+-----------+
           |  X-API-Key
           v
+----------------------+
|  FastAPI backend     |   geen host-poort
|  - /api/chat (RAG)   |
|  - /api/kb/*         |
+----+-------------+---+
     |             |
     v             v
+---------+   +-------------+
| Ollama  |   |  ChromaDB   |   geen host-poort
| (LLM +  |   |  (lokaal,   |
| embed)  |   |   persist.) |
+---------+   +-------------+
```

Alle services praten over een privé Docker bridge-netwerk. Enkel de
Streamlit UI is op `127.0.0.1:8501` bereikbaar - niet op `0.0.0.0`,
dus niet vanaf het netwerk.

## Beveiligingsmaatregelen

- **Loopback-only**: enkel `127.0.0.1:8501` is bereikbaar; backend en
  Ollama zijn nooit van buiten het docker-netwerk te benaderen.
- **API key auth**: frontend en backend delen een `API_KEY`
  (constant-time vergelijking). Backend weigert requests zonder key.
- **Geen telemetrie**: ChromaDB anonymized telemetry uit, Streamlit
  usage stats uit.
- **Geen externe calls op runtime**: na het eenmalig pullen van de
  Ollama-modellen praat het systeem nergens meer naar buiten.
- **Container-hardening**: `no-new-privileges`, non-root user in
  backend en frontend.
- **Strikte CORS**: enkel de geconfigureerde UI origin mag de backend
  aanspreken.
- **Input-validatie**: bestandsnaam wordt gesaneerd, extensie en grootte
  worden gevalideerd, document-id wordt gevalideerd als hex-uuid.
- **XSRF**: ingeschakeld in Streamlit; CORS uit op de UI.
- **Secrets**: `.env` staat in `.gitignore`; backend faalt bewust als er
  geen `API_KEY` is gezet.

## Vereisten

- Docker en Docker Compose
- ~5 GB schijfruimte voor de standaardmodellen
- Optioneel: NVIDIA GPU met `nvidia-container-toolkit` voor snellere
  inferentie

## Setup

1. Kopieer en vul de env-file:

   ```bash
   cp .env.example .env
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

   Plak de output in `.env` bij `API_KEY=`.

2. Start de stack (eerste keer duurt langer, modellen worden gepulld):

   ```bash
   docker compose up -d --build
   ```

3. Open de UI op <http://127.0.0.1:8501>.

4. (Optioneel) Volg de logs:

   ```bash
   docker compose logs -f backend
   ```

## Gebruik

- Stel vragen in het chatvenster.
- Upload `.pdf`, `.txt` of `.md` documenten in de zijbalk en klik op
  **Indexeren** om ze aan de kennisbank toe te voegen.
- De toggle **Gebruik kennisbank bij beantwoorden** bepaalt of de
  context wordt opgehaald.
- Documenten kunnen weer worden verwijderd via de zijbalk.

## Delen met collega's (Tailscale)

De simpelste veilige manier om de chatbot met collega's te delen is via
[Tailscale](https://tailscale.com), een mesh-VPN met end-to-end
WireGuard-encryptie. Geen poort open op internet, toegang per identiteit,
gratis voor kleine teams.

1. Installeer Tailscale op de host die de chatbot draait:

   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. Lees het Tailscale-IP van deze machine:

   ```bash
   tailscale ip -4
   ```

3. Zet dat IP in `.env`:

   ```
   UI_BIND=100.x.y.z
   ```

4. Herstart de stack:

   ```bash
   docker compose up -d
   ```

5. Iedere collega installeert Tailscale op zijn eigen apparaat en logt in
   met hetzelfde tailnet. Daarna openen ze `http://100.x.y.z:8501`.

6. Toegang beheren (uitnodigen, intrekken, ACLs) doe je in de Tailscale
   admin: <https://login.tailscale.com/admin/machines>.

Waarom dit veilig is:

- Geen enkele poort staat open op internet.
- Verkeer is end-to-end versleuteld (WireGuard).
- Toegang per gebruiker via Google/Microsoft/etc.-login; intrekken is
  één klik.
- De UI bindt enkel aan het Tailscale-interface; vanaf het reguliere
  LAN is hij niet bereikbaar.

Optioneel HTTPS in plaats van HTTP:

```bash
sudo tailscale serve --bg --https=443 http://localhost:8501
```

De UI is dan bereikbaar op `https://<machine>.<tailnet>.ts.net`.

## Andere modellen

Pas in `.env` aan, bijvoorbeeld:

```
LLM_MODEL=llama3.1:8b
EMBEDDING_MODEL=nomic-embed-text
```

Daarna `docker compose restart backend`. Op de eerste request worden
ontbrekende modellen automatisch gepulld door Ollama.

Voor GPU-acceleratie kun je deze sectie aan de `ollama`-service in
`docker-compose.yml` toevoegen:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

## Data wissen

Alle persistente data zit in named Docker volumes:

```bash
docker compose down -v
```

verwijdert chat-state, kennisbank, en gedownloade modellen.

## API endpoints (backend, intern)

| Methode | Pad                      | Beschrijving                   |
| ------- | ------------------------ | ------------------------------ |
| GET     | `/health`                | Liveness check                 |
| POST    | `/api/chat`              | Chat-stream (NDJSON, RAG)      |
| POST    | `/api/kb/upload`         | Upload document (multipart)    |
| GET     | `/api/kb/documents`      | Lijst geindexeerde documenten  |
| DELETE  | `/api/kb/documents/{id}` | Verwijder document uit KB      |

Alle endpoints behalve `/health` vereisen header `X-API-Key`.

## Wat is *niet* meegenomen

- Multi-user accounts of rollen - toegang gaat via de identity van
  Tailscale (of single-user op loopback).
- Rate limiting - voeg toe via een reverse proxy als je dat nodig hebt.
- Audit-log per gebruiker - eventueel toe te voegen als FastAPI
  middleware.
