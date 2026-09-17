import base64

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une paire de clés VAPID pour les notifications push (à lancer UNE SEULE FOIS)."

    def handle(self, *args, **options):
        try:
            from py_vapid import Vapid01
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "Il manque des dépendances. Lance d'abord : pip install py-vapid pywebpush"
            ))
            return

        vapid = Vapid01()
        vapid.generate_keys()

        private_path = 'vapid_private.pem'
        public_path = 'vapid_public.pem'
        vapid.save_key(private_path)
        vapid.save_public_key(public_path)

        raw_public = vapid.public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        public_b64 = base64.urlsafe_b64encode(raw_public).rstrip(b'=').decode()

        self.stdout.write(self.style.SUCCESS("Clés VAPID générées avec succès."))
        self.stdout.write(f"  - Clé privée (PEM)  : ./{private_path}  (à GARDER SECRÈTE, ne jamais commit)")
        self.stdout.write(f"  - Clé publique (PEM): ./{public_path}")
        self.stdout.write("")
        self.stdout.write("Variables d'environnement à définir :")
        self.stdout.write(f"  VAPID_PRIVATE_KEY_PATH={private_path}")
        self.stdout.write(f"  VAPID_PUBLIC_KEY={public_b64}")
        self.stdout.write(f"  VAPID_CLAIMS_EMAIL=<ton_email_de_contact>")