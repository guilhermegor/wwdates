"""Unit tests for the Playwright scraper seam.

Covers the cookie-consent probe only: the branch that decides whether a banner is present
before clicking it. Everything here drives fake locators, so no browser is launched and the
socket guard in ``tests/conftest.py`` stays intact.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest

from wwdates._internal.utils.webdriver_tools.playwright_wd import (
	_COOKIE_ACCEPT_SELECTOR,
	_COOKIE_PROBE_TIMEOUT_MS,
	_DEFAULT_TIMEOUT_MS,
	PlaywrightScraper,
)


class FakeLocator:
	"""Locator stub recording the timeouts it was called with.

	Parameters
	----------
	present : bool
		Whether ``wait_for`` should resolve (banner visible) or raise (no banner).
	click_fails : bool
		Whether ``click`` should raise once the banner is considered present.
	"""

	def __init__(self, present: bool, click_fails: bool = False) -> None:
		self.present = present
		self.click_fails = click_fails
		self.wait_timeouts: list[int] = []
		self.click_timeouts: list[int] = []

	@property
	def first(self) -> FakeLocator:
		"""Mimic Playwright's ``.first`` narrowing, which returns a locator.

		Returns
		-------
		FakeLocator
			This same stub.
		"""
		return self

	def wait_for(self, state: str, timeout: int) -> None:
		"""Record the probe timeout and raise when no banner is present.

		Parameters
		----------
		state : str
			Playwright wait state; unused by the stub.
		timeout : int
			Probe budget in milliseconds.

		Raises
		------
		TimeoutError
			When ``present`` is False, mimicking Playwright's timeout.
		"""
		self.wait_timeouts.append(timeout)
		if not self.present:
			raise TimeoutError(f"Timeout {timeout}ms exceeded waiting for {state}")

	def click(self, timeout: int) -> None:
		"""Record the click timeout and optionally fail.

		Parameters
		----------
		timeout : int
			Click budget in milliseconds.

		Raises
		------
		RuntimeError
			When ``click_fails`` is True.
		"""
		self.click_timeouts.append(timeout)
		if self.click_fails:
			raise RuntimeError("element is not clickable")


class FakePage:
	"""Page stub returning a single pre-built locator.

	Parameters
	----------
	locator_stub : FakeLocator
		The locator every ``locator()`` call resolves to.
	"""

	def __init__(self, locator_stub: FakeLocator) -> None:
		self.locator_stub = locator_stub
		self.selectors: list[str] = []

	def locator(self, selector: str) -> FakeLocator:
		"""Record the selector and hand back the stub.

		Parameters
		----------
		selector : str
			Selector requested by the scraper.

		Returns
		-------
		FakeLocator
			The pre-built locator stub.
		"""
		self.selectors.append(selector)
		return self.locator_stub


def _build_scraper(locator_stub: FakeLocator) -> tuple[PlaywrightScraper, FakePage]:
	"""Build a scraper wired to a fake page, bypassing browser launch.

	A real logger is injected: with ``logger=None`` the scraper's ``CreateLog`` adapter
	prints to stdout instead of emitting records, so ``caplog`` would capture nothing.

	Parameters
	----------
	locator_stub : FakeLocator
		Locator the fake page should return.

	Returns
	-------
	tuple[PlaywrightScraper, FakePage]
		The scraper and the fake page attached to it.
	"""
	cls_scraper = PlaywrightScraper(logger=logging.getLogger("test_playwright_wd"))
	page = FakePage(locator_stub)
	cls_scraper.page = page  # type: ignore[assignment]
	return cls_scraper, page


def _levels(records: list[Any]) -> list[str]:
	"""Extract level names from captured log records.

	Parameters
	----------
	records : list[Any]
		Records captured by ``caplog``.

	Returns
	-------
	list[str]
		Lowercased level names, in order.
	"""
	return [r.levelname.lower() for r in records]


def test_handle_cookie_popup_no_banner_returns_fast_without_clicking() -> None:
	"""An absent banner must cost only the short probe and never attempt a click."""
	locator_stub = FakeLocator(present=False)
	cls_scraper, page = _build_scraper(locator_stub)

	cls_scraper._handle_cookie_popup()

	assert page.selectors == [_COOKIE_ACCEPT_SELECTOR]
	assert locator_stub.wait_timeouts == [_COOKIE_PROBE_TIMEOUT_MS]
	assert locator_stub.click_timeouts == []


def test_handle_cookie_popup_probe_budget_is_far_below_the_page_timeout() -> None:
	"""The probe is paid on every navigation, so it must not use the page-load budget.

	This is the regression the issue was filed for: the probe used to be hard-coded at
	30_000ms, stalling every navigation on a page with no banner.
	"""
	assert _COOKIE_PROBE_TIMEOUT_MS < _DEFAULT_TIMEOUT_MS
	assert _COOKIE_PROBE_TIMEOUT_MS <= 2_000


def test_handle_cookie_popup_absent_banner_is_not_logged_as_an_error(
	caplog: pytest.LogCaptureFixture,
) -> None:
	"""No banner is the normal outcome and must not be reported as a failure."""
	cls_scraper, _ = _build_scraper(FakeLocator(present=False))

	with caplog.at_level("INFO"):
		cls_scraper._handle_cookie_popup()

	assert "error" not in _levels(caplog.records)


def test_handle_cookie_popup_present_banner_is_clicked() -> None:
	"""A visible banner must be clicked with the same bounded budget."""
	locator_stub = FakeLocator(present=True)
	cls_scraper, _ = _build_scraper(locator_stub)

	cls_scraper._handle_cookie_popup()

	assert locator_stub.click_timeouts == [_COOKIE_PROBE_TIMEOUT_MS]


def test_handle_cookie_popup_unclickable_banner_logs_an_error(
	caplog: pytest.LogCaptureFixture,
) -> None:
	"""A banner that is present but refuses the click is a real error, unlike absence."""
	cls_scraper, _ = _build_scraper(FakeLocator(present=True, click_fails=True))

	with caplog.at_level("INFO"):
		cls_scraper._handle_cookie_popup()

	assert "error" in _levels(caplog.records)


def test_handle_cookie_popup_honours_an_explicit_timeout() -> None:
	"""A caller may widen the probe for a source whose banner is injected late."""
	locator_stub = FakeLocator(present=True)
	cls_scraper, _ = _build_scraper(locator_stub)

	cls_scraper._handle_cookie_popup(timeout=250)

	assert locator_stub.wait_timeouts == [250]
	assert locator_stub.click_timeouts == [250]


def test_handle_cookie_popup_rejects_a_negative_timeout() -> None:
	"""The existing timeout guard must still apply to the probe budget."""
	cls_scraper, _ = _build_scraper(FakeLocator(present=False))

	with pytest.raises(ValueError, match="timeout must be a positive integer or None"):
		cls_scraper._handle_cookie_popup(timeout=-1)


def test_default_page_timeout_is_usable() -> None:
	"""``int_default_timeout`` feeds ``page.goto``; the old 10ms default loaded nothing."""
	assert PlaywrightScraper().int_default_timeout == _DEFAULT_TIMEOUT_MS
	assert PlaywrightScraper().int_default_timeout >= 5_000
