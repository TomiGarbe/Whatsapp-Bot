"""Database-backed human support workflow service."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.interfaces.messaging_provider import MessagingProvider
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.user import User
from app.services.message_router import HumanSupportServiceProtocol

logger = logging.getLogger(__name__)


class HumanSupportService(HumanSupportServiceProtocol):
    """Human-support behavior backed by persistent conversation state."""

    def __init__(self, messaging_provider: MessagingProvider):
        self.messaging_provider = messaging_provider

    def _resolve_agent(self, db: Session, phone: str) -> Agent | None:
        query = select(Agent).where(
            Agent.email == phone,
            Agent.is_active.is_(True),
        )
        return db.execute(query).scalars().first()

    def _resolve_active_agent_for_business(self, *, db: Session, business_id: UUID) -> Agent | None:
        query = (
            select(Agent)
            .where(
                Agent.business_id == business_id,
                Agent.is_active.is_(True),
            )
            .order_by(Agent.created_at.asc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _get_active_human_conversation(self, *, db: Session, business_id: UUID) -> Conversation | None:
        query = (
            select(Conversation)
            .where(
                Conversation.business_id == business_id,
                Conversation.control_mode == "human",
                Conversation.human_status == "active",
                Conversation.status == "active",
            )
            .order_by(Conversation.started_at.asc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _get_active_conversation_for_agent(
        self,
        *,
        db: Session,
        agent: Agent,
    ) -> Conversation | None:
        query = (
            select(Conversation)
            .where(
                Conversation.business_id == agent.business_id,
                Conversation.assigned_agent_id == agent.id,
                Conversation.control_mode == "human",
                Conversation.human_status == "active",
                Conversation.status == "active",
            )
            .order_by(Conversation.started_at.asc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _get_next_waiting_conversation(self, *, db: Session, business_id: UUID) -> Conversation | None:
        query = (
            select(Conversation)
            .where(
                Conversation.business_id == business_id,
                Conversation.control_mode == "human",
                Conversation.human_status == "waiting",
                Conversation.status == "active",
            )
            .order_by(Conversation.started_at.asc())
            .limit(1)
        )
        return db.execute(query).scalars().first()

    def _close_conversation(self, conversation: Conversation) -> None:
        conversation.control_mode = "ai"
        conversation.human_status = None
        conversation.assigned_agent_id = None

    def _activate_conversation(self, *, conversation: Conversation, agent: Agent) -> None:
        conversation.control_mode = "human"
        conversation.human_status = "active"
        conversation.assigned_agent_id = agent.id

    async def request_human_support(
        self,
        *,
        db: Session,
        conversation: Conversation,
    ) -> None:
        agent = self._resolve_active_agent_for_business(db=db, business_id=conversation.business_id)
        if agent is None:
            raise RuntimeError(f"No active agent configured for business {conversation.business_id}.")

        active_conversation = self._get_active_human_conversation(
            db=db,
            business_id=conversation.business_id,
        )

        if active_conversation is None:
            conversation.control_mode = "human"
            conversation.human_status = "active"
            conversation.assigned_agent_id = agent.id
            db.commit()

            await self._send_conversation_context_to_agent(
                db=db,
                conversation=conversation,
                agent=agent,
            )
            await self._send_to_user(
                db=db,
                conversation=conversation,
                message="Un asesor está tomando tu conversación.",
            )
            return

        conversation.control_mode = "human"
        conversation.human_status = "waiting"
        conversation.assigned_agent_id = None
        db.commit()

        await self._send_to_user(
            db=db,
            conversation=conversation,
            message="Todos nuestros asesores están ocupados. Estás en la cola de espera.",
        )

    async def handle_user_human_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
        conversation: Conversation,
    ) -> None:
        if conversation.human_status == "waiting":
            logger.info(
                "User %s sent message while waiting for human support in conversation %s.",
                phone,
                conversation.id,
            )
            return

        if conversation.human_status == "active":
            if conversation.assigned_agent_id is None:
                logger.warning(
                    "Conversation %s is active in human mode without assigned agent.",
                    conversation.id,
                )
                return

            agent_query = select(Agent).where(
                Agent.id == conversation.assigned_agent_id,
                Agent.is_active.is_(True),
            )
            agent = db.execute(agent_query).scalars().first()
            if agent is None:
                logger.warning(
                    "Assigned agent %s not found or inactive for conversation %s.",
                    conversation.assigned_agent_id,
                    conversation.id,
                )
                return

            if not agent.email:
                logger.warning(
                    "Assigned agent %s has no email destination for conversation %s.",
                    agent.id,
                    conversation.id,
                )
                return

            message_text = self._extract_message_text(incoming_message=incoming_message)
            await self.messaging_provider.send_message(
                user=self._agent_destination(agent=agent, fallback=phone),
                message=message_text,
            )
            logger.info(
                "Forwarded user %s message to agent %s for conversation %s.",
                phone,
                agent.id,
                conversation.id,
            )
            return

        logger.warning(
            "Conversation %s in human mode has unsupported human_status=%s.",
            conversation.id,
            conversation.human_status,
        )

    async def handle_agent_message(
        self,
        *,
        db: Session,
        phone: str,
        incoming_message: dict[str, Any],
    ) -> None:
        agent = self._resolve_agent(db=db, phone=phone)
        if agent is None:
            logger.info("Ignoring agent message from unknown or inactive phone %s.", phone)
            return

        message_text = self._extract_message_text(incoming_message=incoming_message)
        if message_text.strip().lower() == "/cerrar":
            conversation = self._get_active_conversation_for_agent(db=db, agent=agent)
            if conversation is None:
                logger.info("Agent %s tried to close conversation but none is active.", agent.id)
                return

            self._close_conversation(conversation)
            db.commit()
            logger.info("Closed conversation %s by agent %s.", conversation.id, agent.id)

            next_conversation = self._get_next_waiting_conversation(
                db=db,
                business_id=agent.business_id,
            )
            if next_conversation is not None:
                self._activate_conversation(conversation=next_conversation, agent=agent)
                db.commit()
                await self._send_conversation_context_to_agent(
                    db=db,
                    conversation=next_conversation,
                    agent=agent,
                )
                logger.info(
                    "Activated waiting conversation %s for agent %s.",
                    next_conversation.id,
                    agent.id,
                )
            else:
                await self.messaging_provider.send_message(
                    user=self._agent_destination(agent=agent, fallback=phone),
                    message="No hay más clientes en espera.",
                )
            return

        conversation = self._get_active_conversation_for_agent(db=db, agent=agent)
        if conversation is None:
            logger.info("No active human conversation assigned to agent %s.", agent.id)
            await self.messaging_provider.send_message(
                user=self._agent_destination(agent=agent, fallback=phone),
                message="No hay clientes activos.",
            )
            return

        user_phone = self._resolve_user_phone(db=db, conversation=conversation)
        if not user_phone:
            logger.warning(
                "Could not resolve user phone for conversation %s.",
                conversation.id,
            )
            return

        await self.messaging_provider.send_message(user=user_phone, message=message_text)
        logger.info(
            "Forwarded agent %s message to user %s for conversation %s.",
            agent.id,
            user_phone,
            conversation.id,
        )

    async def _send_conversation_context_to_agent(
        self,
        *,
        db: Session,
        conversation: Conversation,
        agent: Agent,
    ) -> None:
        if not agent.email:
            raise ValueError(f"Agent {agent.id} has no email destination.")

        user_name, user_phone = self._resolve_user_identity(db=db, conversation=conversation)
        recent_messages = self._format_last_messages(conversation=conversation)
        context_message = (
            "Nuevo cliente asignado:\n"
            f"Nombre: {user_name}\n"
            f"Teléfono: {user_phone}\n"
            "Últimos mensajes (últimos 5):\n"
            f"{recent_messages}"
        )
        await self.messaging_provider.send_message(
            user=self._agent_destination(agent=agent, fallback=agent.email),
            message=context_message,
        )

    def _resolve_user_phone(self, *, db: Session, conversation: Conversation) -> str | None:
        if conversation.user is not None and conversation.user.phone:
            return conversation.user.phone

        query = select(User.phone).where(User.id == conversation.user_id)
        return db.execute(query).scalar_one_or_none()

    async def _send_to_user(self, *, db: Session, conversation: Conversation, message: str) -> None:
        user_phone = self._resolve_user_phone(db=db, conversation=conversation)
        if not user_phone:
            logger.warning("Could not resolve user phone for conversation %s.", conversation.id)
            return
        await self.messaging_provider.send_message(user=user_phone, message=message)

    def _resolve_user_identity(self, *, db: Session, conversation: Conversation) -> tuple[str, str]:
        user_name = "Sin nombre"
        user_phone = "Sin teléfono"

        user = conversation.user
        if user is None:
            user = db.execute(select(User).where(User.id == conversation.user_id)).scalars().first()

        if user is not None:
            if user.name:
                user_name = user.name
            if user.phone:
                user_phone = user.phone

        return user_name, user_phone

    def _format_last_messages(self, *, conversation: Conversation) -> str:
        messages = sorted(
            conversation.messages,
            key=lambda msg: msg.created_at,
            reverse=True,
        )[:5]
        if not messages:
            return "- Sin mensajes previos."

        ordered_messages = list(reversed(messages))
        lines = []
        for message in ordered_messages:
            sender = message.sender_type.capitalize()
            content = message.content.strip()
            lines.append(f"- {sender}: {content}")
        return "\n".join(lines)

    def _agent_destination(self, *, agent: Agent, fallback: str) -> str:
        if agent.email and agent.email.strip():
            return agent.email.strip()
        return fallback

    def _extract_message_text(self, *, incoming_message: dict[str, Any]) -> str:
        for key in ("message", "text", "body"):
            value = incoming_message.get(key)
            if value is not None:
                text = str(value).strip()
                if text:
                    return text
        raise ValueError("Incoming message is missing message content.")
