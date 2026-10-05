import pytest
from django.core.exceptions import ValidationError

from .models import User
from .phone import normalize_whatsapp


@pytest.mark.parametrize(
    "raw, esperado",
    [
        ("55 1234 5678", "+525512345678"),
        ("(55) 1234-5678", "+525512345678"),
        ("+52 55 1234 5678", "+525512345678"),
        ("525512345678", "+525512345678"),
        ("+1 415 555 2671", "+14155552671"),
    ],
)
def test_normaliza_whatsapp(raw, esperado):
    assert normalize_whatsapp(raw) == esperado


@pytest.mark.parametrize("raw", ["", "123", "abc", "+1234567890123456"])
def test_whatsapp_invalido(raw):
    with pytest.raises(ValidationError):
        normalize_whatsapp(raw)


@pytest.mark.django_db
def test_el_pin_se_guarda_con_argon2():
    user = User.objects.create_user("55 1234 5678", pin="123456", nombre="Laura")
    assert user.whatsapp == "+525512345678"
    assert user.password.startswith("argon2$")
    assert user.check_password("123456")
    assert not user.check_password("654321")


@pytest.mark.django_db
def test_mismo_whatsapp_no_se_duplica():
    User.objects.create_user("5512345678", nombre="Ana")
    with pytest.raises(Exception):  # noqa: B017 - IntegrityError según el motor
        User.objects.create_user("+52 55 1234 5678", nombre="Otra Ana")
