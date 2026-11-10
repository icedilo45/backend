import os
import logging
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication

User = get_user_model()
logger = logging.getLogger(__name__)

_firebase_app = None


def get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not cred_path or not os.path.exists(cred_path):
        logger.warning(
            "Firebase credentials not found at %s — token auth disabled.",
            cred_path,
        )
        return None

    cred = credentials.Certificate(cred_path)
    try:
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


class FirebaseAuthentication(authentication.BaseAuthentication):
    """
    Authorization: Bearer <Firebase ID token>

    - No header → anonymous (None) so public routes (catalog) work.
    - Invalid/expired token → anonymous (None), not 403 on public routes.
      Protected views still return 403 via IsAuthenticated.
    - Valid token → local User (created on first login).
    """

    def authenticate(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        id_token = auth_header.split("Bearer ", 1)[1].strip()
        if not id_token:
            return None

        app = get_firebase_app()
        if app is None:
            # Don't hard-fail public endpoints when Admin SDK isn't configured
            logger.warning("Bearer token present but Firebase Admin not configured.")
            return None

        try:
            decoded = auth.verify_id_token(id_token)
        except Exception as exc:
            logger.warning("Firebase token verification failed: %s", exc)
            return None

        uid = decoded.get("uid")
        if not uid:
            return None

        email = decoded.get("email", "") or ""
        name = decoded.get("name", "") or ""

        user, _created = User.objects.get_or_create(
            firebase_uid=uid,
            defaults={
                "username": uid,
                "email": email or f"{uid}@firebase.local",
                "first_name": (name.split(" ")[0] if name else ""),
                "last_name": (
                    " ".join(name.split(" ")[1:]) if name and " " in name else ""
                ),
            },
        )

        if email and user.email != email:
            user.email = email
            user.save(update_fields=["email"])

        return (user, None)
