# agents/utils.py
import logging
from datetime import datetime, timezone
from dateutil import parser

def parse_datetime_str(datetime_str: str, default_tz=timezone.utc) -> str:
    """
    Parsea una cadena de fecha/hora a formato ISO 8601, agregando la zona horaria si no está presente.
    """
    if not datetime_str:
        return None
    try:
        dt = parser.parse(datetime_str)
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=default_tz)
        return dt.isoformat()
    except (ValueError, OverflowError) as e:
        logging.warning(f"Error al parsear '{datetime_str}': {e}")
        return None

def get_current_datetime() -> dict:
    """
    Retorna la fecha y hora actual en formato ISO 8601 con zona horaria.
    """
    now = datetime.now().astimezone()
    return {"status": "success", "current_datetime_iso": now.isoformat()}
