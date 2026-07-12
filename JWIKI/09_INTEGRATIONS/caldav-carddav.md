# CalDAV / CardDAV — Calendar y Contacts genéricos

## Resumen

**CalDAV** (Calendar) y **CardDAV** (Contacts) son standards abiertos basados en WebDAV. Permiten interoperabilidad con cualquier provider (Apple iCloud, Nextcloud, Yahoo, etc.). **NO integrado en Aithera V0.7.3** (usa Google Calendar API).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## CalDAV (Calendar)

```python
from caldav import DAVClient

client = DAVClient(url="https://caldav.icloud.com", username="user@icloud.com", password="app-password")
principal = client.principal()
calendars = principal.calendars()

for cal in calendars:
    events = cal.date_search(start=datetime.now(), end=datetime.now() + timedelta(days=30))
    for event in events:
        print(event.vobject_instance.vevent.summary.value)
```

## CardDAV (Contacts)

```python
import vobject

# Read vCard
vcard_data = """BEGIN:VCARD
VERSION:3.0
FN:John Doe
TEL:+1234567890
EMAIL:john@example.com
END:VCARD
"""

card = vobject.readOne(vcard_data)
print(card.fn.value)  # John Doe
print(card.tel.value)  # +1234567890
```

## Servers CalDAV populares

- **Apple iCloud**: `https://caldav.icloud.com`
- **Nextcloud**: `https://nextcloud.example.com/remote.php/dav`
- **Yahoo**: `https://caldav.calendar.yahoo.com`
- **Fastmail**: `https://caldav.fastmail.com`
- **Radicale** (self-hosted): cualquier URL

## CalDAV vs Google Calendar API

| Aspecto | CalDAV | Google Calendar API |
|---|---|---|
| Standard | ✅ IETF RFC 4791 | ❌ Google-specific |
| Multi-provider | ✅ | ❌ |
| Search/filter | limitada | ✅ full search |
| Free/busy | partial | ✅ full |
| Push notifications | webhooks | Pub/Sub |
| Color/category | limited | ✅ |

## Aithera V1.0+ plan

CalDAV/CardDAV para:
- ✅ Apple iCloud users.
- ✅ Self-hosted Nextcloud.
- ✅ Multi-provider sync.

## Referencias cruzadas

- [JWIKI-154 google-calendar-api.md](./google-calendar-api.md)

## Fuentes

1. https://datatracker.ietf.org/doc/html/rfc4791 (CalDAV)
2. https://datatracker.ietf.org/doc/html/rfc6352 (CardDAV)
3. https://github.com/python-caldav/caldav

## Nivel de confianza

**85%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified