import json
import uuid
from typing import Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import Request

from app.models import AuditLog


def get_client_ip(request: Optional[Request]) -> Optional[str]:
    """Obtiene la IP del cliente considerando proxies y encabezados X-Forwarded-For."""
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def get_user_agent(request: Optional[Request]) -> Optional[str]:
    """Obtiene el User-Agent (navegador/dispositivo) de la petición."""
    if not request:
        return None
    return request.headers.get("user-agent")


def record_audit(
    db: Session,
    action_type: str,
    module: str,
    description: str,
    user_id: Optional[uuid.UUID] = None,
    username: Optional[str] = None,
    user_role: Optional[str] = None,
    entity_id: Optional[str] = None,
    entity_name: Optional[str] = None,
    changes_payload: Optional[Any] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request: Optional[Request] = None
) -> Optional[AuditLog]:
    """
    Registra un evento de auditoría en la base de datos de forma segura.
    Captura accesos, inicios de sesión, creaciones, modificaciones y eliminaciones.
    """
    try:
        final_ip = ip_address or get_client_ip(request)
        final_ua = user_agent or get_user_agent(request)
        
        # Serializar payload si es diccionario o lista
        payload_str = None
        if changes_payload is not None:
            if isinstance(changes_payload, (dict, list)):
                try:
                    payload_str = json.dumps(changes_payload, ensure_ascii=False, default=str)
                except Exception:
                    payload_str = str(changes_payload)
            else:
                payload_str = str(changes_payload)

        log_entry = AuditLog(
            action_type=action_type,
            module=module,
            description=description,
            user_id=user_id,
            username=username,
            user_role=user_role,
            entity_id=str(entity_id) if entity_id else None,
            entity_name=str(entity_name) if entity_name else None,
            changes_payload=payload_str,
            ip_address=final_ip,
            user_agent=final_ua
        )
        db.add(log_entry)
        db.commit()
        return log_entry
    except Exception as e:
        db.rollback()
        print(f"[AUDIT LOG WARNING]: Error al registrar auditoría: {e}")
        return None
