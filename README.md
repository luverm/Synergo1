# Synergo - Lokale, veilige chatbot met kennisbank

Volledig lokaal: Ollama draait het taalmodel, Open WebUI is de
chatinterface met ingebouwde RAG-kennisbank. Geen cloud, geen
telemetrie, alles op je eigen machine.

## Vereisten

- Docker Desktop (Mac/Windows) of Docker Engine (Linux)
- ~5 GB schijfruimte voor de standaardmodellen

## Starten

```bash
docker compose up -d
```

Eerste keer duurt 1-2 minuten (image-download). Daarna open:

**<http://127.0.0.1:3000>**

Op het eerste bezoek maak je een account aan - die wordt direct
admin. Daarna log je in.

## Een model installeren

Klik in Open WebUI op je profiel (links onderin) → **Settings** →
**Models**. Type bijvoorbeeld `llama3.2:3b` en klik op de
download-knop. Wacht tot het klaar is (~2 GB, 2-3 min).

Goede modellen om mee te beginnen:

| Model         | Grootte | Geheugen | Snelheid |
| ------------- | ------- | -------- | -------- |
| `llama3.2:3b` | 2 GB    | 4 GB     | Snel     |
| `llama3.1:8b` | 5 GB    | 8 GB     | Middel   |
| `qwen2.5:7b`  | 4 GB    | 8 GB     | Middel   |

## Kennis toevoegen

In Open WebUI:

1. Klik linksboven op **Workspace** → **Knowledge**.
2. **Create knowledge collection** met een naam, bv. "Bedrijfsbeleid".
3. Sleep `.pdf`, `.txt`, `.md`, `.docx` bestanden in de collection.
4. In een chat: type `#` en kies je collection om hem aan dit gesprek
   te koppelen. De bot gebruikt dan die documenten als bron.

## Beheer

```bash
docker compose stop          # pauze, data blijft
docker compose start         # weer aan
docker compose down          # containers weg, data blijft in volumes
docker compose down -v       # alles wissen (chat, KB, modellen)
docker compose logs -f       # zien wat er gebeurt
```

## Delen met collega's (Tailscale)

De simpelste veilige manier:

1. Installeer Tailscale op deze host:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
2. Lees het Tailscale-IP:
   ```bash
   tailscale ip -4
   ```
3. Maak `.env` op basis van `.env.example` en zet:
   ```
   UI_BIND=100.x.y.z
   ```
4. Herstart:
   ```bash
   docker compose up -d
   ```
5. Collega's installeren Tailscale op hun apparaat, joinen jouw
   tailnet, en openen `http://100.x.y.z:3000`.
6. Ze maken een account. Jij keurt ze goed in Open WebUI:
   **Admin Panel** → **Users** → klik op "pending" naast hun naam.
   Zo bepaal jij wie binnen mag.

Waarom dit veilig is:

- Geen poort open op internet (mesh-VPN, end-to-end versleuteld met WireGuard)
- Toegang per persoon - intrekken via Tailscale of in Open WebUI Admin Panel
- Open WebUI's signup is ingesteld op "pending"; alleen door admin goedgekeurde accounts kunnen chatten

## Beveiligingsmaatregelen

- Default binding op `127.0.0.1` (alleen jouw machine)
- Ollama heeft geen host-poort (alleen binnen docker network bereikbaar)
- Telemetrie uit (`ANONYMIZED_TELEMETRY`, `SCARF_NO_ANALYTICS`, `DO_NOT_TRACK`)
- Container hardening: `no-new-privileges`
- Auth verplicht; nieuwe gebruikers staan op "pending" tot admin goedkeurt
- `.env` staat in `.gitignore`

## Wat is *niet* meegenomen

- HTTPS - niet nodig op loopback; voor Tailscale gebruik
  `tailscale serve --bg --https=443 http://localhost:3000` voor TLS.
- Rate limiting - voeg toe via een reverse proxy als je dat nodig
  hebt.
