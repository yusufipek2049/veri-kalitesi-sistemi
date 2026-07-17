"""Guvenilir kimlik ve yetkilendirme hata turleri."""


class IdentityError(Exception):
    """Kimlik ve yetkilendirme hatalarinin taban sinifi."""


class ActorContextValidationError(IdentityError):
    """Guvenilir aktor baglami uretilemedi."""


class AuthorizationDeniedError(IdentityError):
    """Yetkilendirme karari varsayilan olarak reddedildi."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__("Authorization denied.")
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class AuthorizationUnavailableError(IdentityError):
    """Yetkilendirme veya karar audit siniri kullanilamiyor."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__("Authorization could not be established.")
        self.correlation_id = correlation_id


class LdapCredentialsRejectedError(IdentityError):
    """LDAP adaptoru kimlik bilgisini genel bir ret olarak siniflandirdi."""


class LdapAdapterTechnicalError(IdentityError):
    """LDAP adaptoru teknik olarak kimlik dogrulayamadi."""


class AuthenticationThrottleTechnicalError(IdentityError):
    """Basarisiz giris sinirlandirma deposuna erisilemedi."""


class SessionTechnicalError(IdentityError):
    """Oturum deposuna erisilemedi veya kalici kayit bozuk."""


class SessionDeniedError(IdentityError):
    """Oturum gecersiz, suresi dolmus veya iptal edilmis."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__("Session denied.")
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class SessionUnavailableError(IdentityError):
    """Oturum veya audit siniri kullanilamadigi icin context kurulamadi."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__("Session could not be established.")
        self.correlation_id = correlation_id


class AuthenticationDeniedError(IdentityError):
    """LDAP kimligi veya yerel yetki eslemesi fail-closed reddedildi."""

    def __init__(self, reason_code: str, correlation_id: str) -> None:
        super().__init__("Authentication denied.")
        self.reason_code = reason_code
        self.correlation_id = correlation_id


class AuthenticationUnavailableError(IdentityError):
    """LDAP veya kimlik audit siniri kullanilamadigi icin giris kurulamadi."""

    def __init__(self, correlation_id: str) -> None:
        super().__init__("Authentication could not be established.")
        self.correlation_id = correlation_id
