# app/gateway/adapters/ — implementaciones concretas de ChannelAdapter (V0.8).
#
# Cada adapter es una pieza FINA: traduce el formato nativo de su canal al
# MessageEnvelope y de vuelta. Cero logica de negocio (esa vive detras del
# Gateway). Guia: PLAN_MAESTRO_2026/06_GATEWAY_V08_DISENO.md
#
# NOTA: no importamos los adapters aqui para no forzar sus dependencias
# (p.ej. python-telegram-bot) en entornos que no las necesiten. El lifespan
# de main.py importa el adapter concreto solo si el canal esta configurado.
