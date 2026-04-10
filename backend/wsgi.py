from gunicorn.app.base import BaseApplication

class StandaloneApplication(BaseApplication):
    def __init__(self, app, options=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application

if __name__ == "__main__":
    options = {
        'bind': '0.0.0.0:' + str(os.environ.get('PORT', 5000)),
        'workers': 1,
        'threads': 2,
        'timeout': 120,
    }
    StandaloneApplication(app, options).run()
