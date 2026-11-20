from django.apps import AppConfig


class AdministrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administration'

    def ready(self):
        from django.db.models.signals import post_save

        from administration.models import SiteSettings

        def clear_cached_settings(sender, **kwargs):
            from referrals.services import clear_site_settings_cache
            clear_site_settings_cache()

        post_save.connect(clear_cached_settings, sender=SiteSettings, dispatch_uid='instova_clear_site_settings')
