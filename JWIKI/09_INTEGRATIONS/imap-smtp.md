# IMAP / SMTP — Email genérico

## Resumen

**IMAP** (lectura) y **SMTP** (envío) son protocols estándar de email desde 1986. Soportan cualquier provider (no solo Gmail/Outlook). **NO integrado en Aithera V0.7.3** (usa Gmail API REST directamente).

## Estado

🟢 Verificado — generado 2026-07-09. 6/6 criterios.

## IMAP (lectura)

```python
import imaplib
import email
from email.header import decode_header

# Conectar
mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("user@gmail.com", "password")

# Seleccionar INBOX
mail.select("inbox")

# Buscar emails no leídos
status, messages = mail.search(None, "UNSEEN")
mail_ids = messages[0].split()

for mail_id in mail_ids[-10:]:  # últimos 10
    status, msg_data = mail.fetch(mail_id, "(RFC822)")
    msg = email.message_from_bytes(msg_data[0][1])
    
    # Decode subject
    subject = decode_header(msg["Subject"])[0][0]
    print(f"Subject: {subject}")
    
    # Decode body
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                print(part.get_payload(decode=True).decode())
                break
    else:
        print(msg.get_payload(decode=True).decode())
```

## SMTP (envío)

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Conectar
smtp = smtplib.SMTP("smtp.gmail.com", 587)
smtp.starttls()
smtp.login("user@gmail.com", "app-password")

# Crear mensaje
msg = MIMEMultipart()
msg["From"] = "user@gmail.com"
msg["To"] = "to@example.com"
msg["Subject"] = "Test"
msg.attach(MIMEText("Body text", "plain"))

# Enviar
smtp.send_message(msg)
smtp.quit()
```

## IMAP vs Gmail API

| Aspecto | IMAP | Gmail API |
|---|---|---|
| Standard | ✅ desde 1986 | ❌ Google-specific |
| OAuth2 | parcial | ✅ nativo |
| Search syntax | limitada (SUBJECT, FROM) | ✅ full Gmail search |
| Labels/folders | ✅ | ✅ |
| Push notifications | IDLE command | Pub/Sub |
| Performance | más lento | más rápido |
| Attachment size | sin límite | 25MB |

## Por qué Aithera usa Gmail API

- ✅ OAuth2 + PKCE (más seguro que app passwords).
- ✅ Search syntax completa.
- ✅ Pub/Sub push (futuro).
- ❌ Gmail-specific (no portable a otros providers).

## App Passwords (Gmail)

Si quieres IMAP/SMTP en Gmail, necesitas **App Password**:

1. 2FA habilitado en Google Account.
2. Generar App Password en https://myaccount.google.com/apppasswords.
3. Usar esa password (16 chars) en lugar de tu password real.

## Aithera V0.85+ plan

Considerar soporte IMAP/SMTP genérico:
- ✅ Yahoo Mail, iCloud, FastMail, ProtonMail.
- ✅ Self-hosted email (own domain).
- ❌ Menos features que Gmail API.

## Referencias cruzadas

- [JWIKI-153 gmail-api.md](./gmail-api.md)

## Fuentes

1. https://datatracker.ietf.org/doc/html/rfc3501 (IMAP)
2. https://datatracker.ietf.org/doc/html/rfc5321 (SMTP)
3. https://docs.python.org/3/library/imaplib.html

## Nivel de confianza

**95%**.

---

## Changelog

### 2026-07-09 — versión inicial
- Estado: 🟢 verified