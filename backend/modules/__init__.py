def register_modules(app):
    from .events import events_bp, events_shell_bp
    from .demands import demands_bp, demands_shell_bp, management_bp
    app.register_blueprint(events_bp)
    app.register_blueprint(events_shell_bp)
    app.register_blueprint(demands_bp)
    app.register_blueprint(demands_shell_bp)
    app.register_blueprint(management_bp)
