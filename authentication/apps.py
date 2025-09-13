from django.apps import AppConfig
// hadi juste fonction t3ayat lel signals
class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):

        import authentication.signals
