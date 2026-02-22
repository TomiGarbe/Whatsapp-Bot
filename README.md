# 🤖 WhatsApp Bot AI (SaaS Ready)

Plataforma de bot de WhatsApp con inteligencia artificial orientada a pequeñas y medianas empresas.

Este proyecto permite automatizar la atención al cliente, responder consultas frecuentes, gestionar pedidos/reservas y acceder a información del negocio (productos, stock, servicios), todo mediante WhatsApp.

Diseñado con una arquitectura desacoplada que permite cambiar fácilmente:

* Proveedor de IA (OpenAI, Azure, local)
* Fuente de datos (PostgreSQL, Google Sheets, APIs)
* Proveedor de mensajería (Twilio, Meta WhatsApp API)

---

## 🚀 Features principales

* 💬 Atención automática por WhatsApp
* 🧠 Integración con IA (respuestas inteligentes)
* 📦 Consulta de productos y stock
* 🔄 Sugerencias de productos similares
* 🛒 Toma de pedidos y reservas
* 👤 Derivación a humano
* 🧾 Historial de conversaciones (memoria)
* 🔌 Conexión a múltiples fuentes de datos
* 🏢 Multiempresa (multi-tenant)
* ⚙️ Configuración dinámica por negocio

---

## 🏗️ Arquitectura

El sistema está basado en una arquitectura desacoplada usando interfaces:

* `AIProvider` → Motor de IA
* `DataSource` → Fuente de datos
* `MessagingProvider` → WhatsApp

El bot funciona mediante un orquestador central que decide cómo responder cada mensaje.

---

## 🧩 Stack tecnológico

* **Backend:** FastAPI (Python)
* **Base de datos:** PostgreSQL
* **IA:** Azure (inicialmente)
* **Mensajería:** Twilio (MVP) → Meta API (producción)
* **Integraciones:** Google Sheets API

---

## 📂 Estructura del proyecto (propuesta)

```
app/
│
├── core/              # Configuración, settings
├── providers/         # Implementaciones (AI, DB, Messaging)
├── interfaces/        # Interfaces base (AIProvider, DataSource, etc.)
├── services/          # Lógica del bot (orquestador)
├── models/            # Modelos DB
├── api/               # Endpoints (webhooks)
├── utils/             # Helpers
│
└── main.py            # Entry point
```

---

## 🧠 Filosofía del proyecto

Este proyecto no es solo un bot, sino una **plataforma adaptable**:

> Un mismo sistema puede servir para múltiples negocios cambiando únicamente la configuración.

---

## ⚙️ Configuración futura

Cada empresa podrá definir:

* Tipo de negocio (productos / servicios)
* Fuente de datos
* Prompt del bot
* Reglas de atención

---

## 🤝 Contribuciones

Proyecto en desarrollo personal con enfoque profesional.

---

## 📌 Autor

Tomás Garbellotto
