"""Attach the single ULTRON dashboard and its specialist hologram tool."""
def attach(ui):
    from .hologram_panel import attach as attach_hologram
    from .web_panel import attach as attach_dashboard
    attach_hologram(ui)
    attach_dashboard(ui)
