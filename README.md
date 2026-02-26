# 🤖 WhatsApp Bot AI  
### Modular Conversational Platform for SMEs

**WhatsApp Bot AI** es una plataforma conversacional modular diseñada para automatizar la atención al cliente de pequeñas y medianas empresas mediante inteligencia artificial.

No es un bot rígido ni específico para un único negocio.  
Es un núcleo conversacional desacoplado y configurable que puede adaptarse a distintos tipos de empresas mediante configuración y proveedores intercambiables.

---

## 🎯 Objetivo del Proyecto

Construir una base sólida para un sistema SaaS multi-tenant capaz de:

- Automatizar interacciones por WhatsApp
- Interpretar intención del usuario mediante un sistema de scoring
- Orquestar flujos conversacionales dinámicos
- Integrarse con múltiples fuentes de datos
- Permitir configuración por negocio sin modificar el core

---

## 🏗️ Arquitectura

El sistema está diseñado con principios de:

- Clean Architecture  
- Separación estricta de responsabilidades  
- Inyección real de dependencias  
- Interfaces desacopladas  
- Extensibilidad por proveedor  

### Componentes centrales

**IntentEngine**  
Motor de detección de intención con sistema de scoring configurable.

**FlowManager**  
Orquestador conversacional responsable de decidir cómo responder cada mensaje.

**AIProvider (interface)**  
Permite intercambiar motores de IA sin modificar la lógica del bot.

**DataSource (interface)**  
Abstrae la fuente de datos (PostgreSQL, Google Sheets, APIs externas).

**MessagingProvider (interface)**  
Desacopla la integración con proveedores de WhatsApp.

La lógica del negocio no depende directamente de:

- Proveedor de IA
- Base de datos específica
- Servicio de mensajería

---

## 🧠 Enfoque Conversacional

El sistema no responde únicamente por prompts.

La arquitectura permite:

- Detección estructurada de intención
- Lógica determinística cuando es necesario
- Respuestas asistidas por IA cuando aporta valor
- Derivación a humano
- Escalabilidad hacia memoria conversacional avanzada

---

## 🏢 Orientación SaaS

El proyecto está pensado desde el inicio para:

- Soportar múltiples empresas (multi-tenant)
- Permitir configuración dinámica por negocio
- Adaptarse a distintos rubros (productos, servicios, reservas)
- Escalar hacia una plataforma administrable

---

## 🧩 Stack Tecnológico

- Backend: FastAPI  
- ORM: SQLAlchemy 2.0  
- Migraciones: Alembic  
- Configuración tipada: Pydantic Settings  
- Base de datos: PostgreSQL  

---

## 📌 Visión

Evolucionar desde un bot configurable hacia una **plataforma conversacional empresarial**, donde el núcleo técnico permanezca estable mientras las implementaciones y configuraciones cambian por cliente.