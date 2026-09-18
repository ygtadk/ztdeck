"""Translation helpers.

Every user-visible string goes through :func:`_`.

The catalogue directory has to be passed explicitly. ``gettext.translation()``
defaults to ``sys.prefix + "/share/locale"`` -- ``/usr/share/locale`` for the
interpreter inside the runtime -- while Meson installs ZTDeck's catalogues
under the app prefix, ``/app/share/locale`` in a Flatpak. Relying on the
default silently yields untranslated English no matter how complete the .po
files are, so the launcher exports ZTDECK_LOCALE_DIR and this module honours it.

Running uninstalled (from the source tree, as the tests do) there is no
catalogue at all; gettext then falls back to the original English, which is
exactly what we want.
"""

import gettext
import os

DOMAIN = "ztdeck"

#: Set by the Meson-generated launcher to the configured localedir.
LOCALE_DIR = os.environ.get("ZTDECK_LOCALE_DIR") or None

_translation = gettext.translation(DOMAIN, localedir=LOCALE_DIR, fallback=True)

#: Mark a string for translation and return its translation.
_ = _translation.gettext

#: Plural-aware variant: ngettext("%d peer", "%d peers", n) % n
ngettext = _translation.ngettext


def pgettext(context, message):
    """Disambiguate identical strings used in different contexts."""
    return _translation.pgettext(context, message)


def is_active():
    """True when a real catalogue was loaded rather than the English fallback."""
    return not isinstance(_translation, gettext.NullTranslations) or hasattr(
        _translation, "_catalog"
    )
