from unittest.mock import patch
import models
from services.price_refresh import _check_wishlist_targets
from conftest import make_card


def make_wishlist_entry(db, user, card, target_price, foil=False, notified=False):
    entry = models.WishlistEntry(
        user_id=user.id,
        card_id=card.id,
        target_price=target_price,
        foil=foil,
        notified=notified,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


class TestCheckWishlistTargets:
    def test_fires_once_when_price_drops_to_target(self, db, regular_user):
        card = make_card(db, price_usd=1.00, price_usd_foil=2.00)
        entry = make_wishlist_entry(db, regular_user, card, target_price=1.00)

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 1
        db.refresh(entry)
        assert entry.notified is True

    def test_does_not_refire_on_subsequent_check(self, db, regular_user):
        card = make_card(db, price_usd=1.00)
        make_wishlist_entry(db, regular_user, card, target_price=1.00)

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 1

    def test_no_fire_when_price_above_target(self, db, regular_user):
        card = make_card(db, price_usd=5.00)
        make_wishlist_entry(db, regular_user, card, target_price=1.00)

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 0

    def test_rearms_when_price_rises_back_above_target(self, db, regular_user):
        card = make_card(db, price_usd=1.00)
        entry = make_wishlist_entry(db, regular_user, card, target_price=1.00, notified=True)

        card.price_usd = 5.00
        db.commit()

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 0
        db.refresh(entry)
        assert entry.notified is False

    def test_fires_again_after_rearm_on_next_drop(self, db, regular_user):
        card = make_card(db, price_usd=5.00)
        entry = make_wishlist_entry(db, regular_user, card, target_price=1.00, notified=False)

        card.price_usd = 0.50
        db.commit()
        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 1
        db.refresh(entry)
        assert entry.notified is True

    def test_uses_foil_price_for_foil_entries(self, db, regular_user):
        card = make_card(db, price_usd=10.00, price_usd_foil=1.00)
        make_wishlist_entry(db, regular_user, card, target_price=2.00, foil=True)

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 1
        call_kwargs = mock_notify.call_args[0]
        assert call_kwargs[2] == 1.00

    def test_ignores_entries_without_target_price(self, db, regular_user):
        card = make_card(db, price_usd=0.01)
        make_wishlist_entry(db, regular_user, card, target_price=None)

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 0

    def test_converts_price_for_non_native_preferred_currency(self, db, regular_user):
        regular_user.preferred_currency = "gbp"
        db.add(models.ConvertedCurrency(code="GBP", symbol="£", rate=0.5))
        db.commit()

        card = make_card(db, price_usd=10.00)
        make_wishlist_entry(db, regular_user, card, target_price=6.00)

        with patch("services.webhooks.notify_wishlist_target_met") as mock_notify:
            _check_wishlist_targets(db)
        assert mock_notify.call_count == 1
        current_price = mock_notify.call_args[0][2]
        assert current_price == 5.00
