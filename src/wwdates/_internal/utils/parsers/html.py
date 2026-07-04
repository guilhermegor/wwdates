"""Minimal HTML helpers used by the US calendar providers.

Exposes only ``lxml_parser`` / ``lxml_xpath``, which the US calendars use to XPath-scrape
holiday tables.
"""

from lxml import html
from requests import Response

from wwdates._internal.utils.typing import TypeChecker


class HtmlHandler(metaclass=TypeChecker):
	"""Small lxml-based HTML helpers for the calendar providers."""

	def lxml_parser(self, resp_req: Response) -> html.HtmlElement:
		"""Parse an HTTP response body into an lxml element tree.

		Parameters
		----------
		resp_req : Response
			HTTP response object containing HTML content.

		Returns
		-------
		html.HtmlElement
			Parsed HTML element tree.
		"""
		page = resp_req.content
		return html.fromstring(page)

	def lxml_xpath(self, html_content: html.HtmlElement, str_xpath: str) -> list:
		"""Evaluate an XPath expression against a parsed HTML tree.

		Parameters
		----------
		html_content : html.HtmlElement
			Parsed HTML element tree.
		str_xpath : str
			XPath expression to evaluate.

		Returns
		-------
		list
			Elements (or values) matching the XPath query.
		"""
		return html_content.xpath(str_xpath)
