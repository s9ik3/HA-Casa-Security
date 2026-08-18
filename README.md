# Casa Security

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Integrazione custom per Home Assistant che permette di definire, interamente
da interfaccia utente (nessun YAML manuale), N **livelli di sicurezza** (es.
"Sicurezza Perimetro", "Sicurezza Interna"), ognuno associato a una o più
telecamere/sensori di movimento. Per ogni livello, l'integrazione genera e
mantiene automaticamente:

- **Un'automazione per ogni telecamera del livello**, che alla rilevazione di
  movimento scatta uno snapshot e registra un video, inviando entrambi su
  Telegram (foto immediatamente, video al termine della registrazione).
- **Uno script di attivazione/disattivazione per livello**, che con un solo
  tap abilita/disabilita tutte le automazioni del livello (tramite label).
- **Un sensore di stato per livello** (`binary_sensor.<slug>_attivo`), `on`
  solo se **tutte** le automazioni del livello sono attive.
- **Una dashboard dedicata**, con una card per livello, che si aggiorna da
  sola quando aggiungi, modifichi o rimuovi un livello.

Nessun file YAML viene scritto su disco: tutto vive come entità gestite dal
ciclo di vita della configurazione, coerentemente creato, aggiornato e
rimosso quando modifichi i livelli dalle opzioni dell'integrazione.

## Screenshot

> _Sostituisci questi placeholder con screenshot reali del tuo setup._

![Dashboard](docs/screenshot-dashboard.png)
![Opzioni](docs/screenshot-options.png)

## Prerequisiti

- Home Assistant **2024.6.0** o superiore.
- L'integrazione [`telegram_bot`](https://www.home-assistant.io/integrations/telegram_bot/)
  già configurata e funzionante nella tua istanza. **Casa Security non
  configura Telegram**: si limita a chiamare `telegram_bot.send_photo` e
  `telegram_bot.send_video` usando il bot/chat di default già impostato.
- [HACS](https://hacs.xyz/) installato (per l'installazione via custom
  repository) oppure copia manuale dei file.
- La card [`custom:button-card`](https://github.com/custom-cards/button-card)
  installata (necessaria per il rendering della dashboard generata).

## Installazione

### Tramite HACS (custom repository)

1. Apri HACS → menu (⋮) in alto a destra → **Repository personalizzati**.
2. Aggiungi l'URL di questo repository, categoria **Integrazione**.
3. Cerca "Casa Security" in HACS e installa.
4. Riavvia Home Assistant.

### Manuale

1. Copia la cartella `custom_components/casa_security` nella cartella
   `custom_components` della tua configurazione Home Assistant.
2. Riavvia Home Assistant.

## Configurazione

### 1. Aggiungi l'integrazione

**Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Dynamic
Security**. Al primo avvio ti verrà chiesto solo il **percorso base** dove
salvare snapshot e video (default:
`/media/VideoTelecamere/Volume/HAOS/SORVEGLIANZA`).

### 2. Configura i livelli di sicurezza

Dalla card dell'integrazione, clicca **Configura** per aprire le opzioni:

- **Aggiungi livello di sicurezza**: dai un nome (es. "Sicurezza Perimetro"),
  scegli una **label** (creata automaticamente se non esiste), le icone per
  lo stato attivo/non attivo e, opzionalmente, da quale altro livello dipende
  (per abilitare/disabilitare la card in dashboard solo se il livello da cui
  dipende è attivo).
- Subito dopo aver salvato i dati del livello, ti viene mostrato un
  sotto-menu per **aggiungere le telecamere** del livello: per ciascuna
  specifichi il sensore di movimento/presenza che fa da trigger, la
  telecamera, un nome descrittivo e (opzionalmente) durata e lookback del
  video registrato.
- Puoi tornare in qualsiasi momento su **Modifica livello di sicurezza** o
  **Rimuovi livello di sicurezza** per gestire i livelli esistenti.

### Esempio: livello con 2 telecamere

| Campo | Valore |
|---|---|
| Nome livello | Sicurezza Perimetro |
| Label | `sicurezza_perimetro` |
| Telecamera 1 – sensore | `binary_sensor.cancello_movimento` |
| Telecamera 1 – camera | `camera.cancello` |
| Telecamera 1 – nome | Cancello |
| Telecamera 2 – sensore | `binary_sensor.giardino_movimento` |
| Telecamera 2 – camera | `camera.giardino` |
| Telecamera 2 – nome | Giardino |

Al salvataggio, l'integrazione genera automaticamente:

- `automation.sicurezza_perimetro_cancello`
- `automation.sicurezza_perimetro_giardino`
- `script.sicurezza_perimetro`
- `binary_sensor.sicurezza_perimetro_attivo`
- una card nella dashboard **Casa Security**

### 3. Dashboard

L'integrazione crea (o aggiorna) una dashboard dedicata, visibile nella
barra laterale, con una view a griglia contenente una card per livello. Le
card mostrano lo stato corrente del livello, e al tap eseguono lo script di
toggle corrispondente (rispettando l'eventuale dipendenza da un altro
livello).

## Note operative

- Il binary_sensor di un livello è `on` **solo se tutte** le automazioni del
  livello sono abilitate: se anche una sola telecamera del livello è
  disattivata, il sensore passa a `off`.
- Rimuovendo un livello (o l'intera integrazione), tutte le entità generate e
  la relativa card in dashboard vengono rimosse in modo pulito.
- Il bot/chat Telegram usato è sempre quello di default configurato nella tua
  istanza; non è possibile specificare bot o chat_id diversi per livello.

## Sviluppo e test

```bash
pip install -r requirements_test.txt
pytest tests/
```

## Licenza

[MIT](LICENSE)
