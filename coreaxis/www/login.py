# Re-export Frappe's login page handlers while replacing only the page chrome.
from __future__ import annotations

from frappe.www.login import *  # noqa: F401, F403
from frappe.www.login import get_context as _get_context, no_cache  # noqa: F401


def get_context(context: dict) -> dict:
	_get_context(context)
	context.no_header = True
	context.no_footer = True
	context.logo = "/assets/coreaxis/images/coreaxis-favicon.png"
	context.app_name = "CoreAxis Solutions"
	return context
