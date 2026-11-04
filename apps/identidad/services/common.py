"""Reglas de dominio independientes de HTTP/DRF."""
from django.core.exceptions import ValidationError as DjangoValidationError


class ReglaNegocioError(ValueError):
    """La solicitud incumple una regla de negocio de Vita Suite."""


def validar_modelo(objeto):
    try:
        objeto.full_clean()
    except DjangoValidationError as exc:
        raise ReglaNegocioError('; '.join(exc.messages)) from exc
