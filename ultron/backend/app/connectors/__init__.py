"""Connector stub'ları ve ortak hata sınıfı."""


class ConnectorError(Exception):
    """Tüm connector hatalarının temel sınıfı."""
    pass


class _BaseConnector:
    def health(self) -> dict:
        return {"ok": False, "error": f"{self.__class__.__name__} not configured"}


class WeatherConnector(_BaseConnector):
    """Hava durumu connector (stub)."""
    pass


class CalendarConnector(_BaseConnector):
    """Takvim connector (stub)."""
    pass
