def register_modules(app):
    from .events import events_bp
    app.register_blueprint(events_bp)