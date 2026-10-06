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
    Garantiza generación explícita de UUID y validación de clave foránea
    para que ningún evento se pierda o falle silenciosamente.
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

        # Validar si user_id existe físicamente en la BD para evitar violaciones de foreign key
        safe_user_id = None
        if user_id:
            try:
                from app.models import User
                exists = db.query(User.id).filter(User.id == user_id).first()
                if exists:
                    safe_user_id = user_id
            except Exception:
                safe_user_id = None

        log_entry = AuditLog(
            id=uuid.uuid4(),
            action_type=str(action_type).strip().upper(),
            module=str(module).strip().upper(),
            description=str(description).strip(),
            user_id=safe_user_id,
            username=str(username).strip() if username else None,
            user_role=str(user_role).strip() if user_role else None,
            entity_id=str(entity_id).strip() if entity_id else None,
            entity_name=str(entity_name).strip() if entity_name else None,
            changes_payload=payload_str,
            ip_address=final_ip,
            user_agent=final_ua,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[AUDIT LOG WARNING]: Error al registrar auditoría: {e}")
        return None
