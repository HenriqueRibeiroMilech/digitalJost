def register_modules(app):
    from .events import events_bp, events_shell_bp
    app.register_blueprint(events_bp)
    app.register_blueprint(events_shell_bp)
