from __future__ import annotations

import frappe


APP_NAME = "CoreAxis Solutions"
APP_LOGO = "/assets/coreaxis/images/coreaxis-favicon.png"
APP_SPLASH = "/assets/coreaxis/images/coreaxis-splash.png"

BRAND_PRIMARY = "#111820"
BRAND_DARK = "#05070A"
BRAND_ACCENT = "#9AA3AD"
BRAND_TEXT = "#151A20"
BRAND_BG = "#F5F7FA"
BRAND_LIGHT = "#E6EAEE"
BRAND_BORDER = "#C8CDD3"


def after_install() -> None:
	"""Apply CoreAxis Solutions branding on install or manual setup."""
	setup_navbar_branding()
	setup_website_settings()
	setup_website_theme()
	setup_letter_head()
	setup_system_settings()
	frappe.db.commit()


def after_uninstall() -> None:
	"""Revert CoreAxis Solutions branding owned by this app."""
	revert_navbar_branding()
	revert_website_settings()
	revert_website_theme()
	revert_letter_head()
	revert_system_settings()
	frappe.db.commit()


def setup_navbar_branding() -> None:
	"""Set the Desk navbar logo."""
	navbar = frappe.get_single("Navbar Settings")
	navbar.app_logo = APP_LOGO
	navbar.save()


def revert_navbar_branding() -> None:
	"""Clear the Desk navbar logo only when owned by this app."""
	navbar = frappe.get_single("Navbar Settings")
	if navbar.app_logo == APP_LOGO:
		navbar.app_logo = ""
		navbar.save()


def setup_website_settings() -> None:
	"""Set website favicon, splash, app name, title, brand HTML, and footer."""
	settings = frappe.get_single("Website Settings")
	settings.favicon = APP_LOGO
	settings.splash_image = APP_SPLASH
	settings.app_name = APP_NAME
	settings.title_prefix = APP_NAME
	settings.brand_html = f"""<div style="display:flex;align-items:center;gap:8px;">
<img src="{APP_LOGO}" style="height:24px;width:24px;object-fit:contain;" alt="{APP_NAME}">
<span style="font-weight:700;font-size:15px;color:{BRAND_TEXT};">{APP_NAME}</span>
</div>"""
	settings.footer_powered = f'Powered by <a href="#" style="color:{BRAND_TEXT};">{APP_NAME}</a>'
	settings.save()


def revert_website_settings() -> None:
	"""Clear website settings only when they match CoreAxis-owned values."""
	settings = frappe.get_single("Website Settings")
	if settings.favicon == APP_LOGO:
		settings.favicon = ""
	if settings.splash_image == APP_SPLASH:
		settings.splash_image = ""
	if settings.app_name == APP_NAME:
		settings.app_name = ""
	if settings.title_prefix == APP_NAME:
		settings.title_prefix = ""
	if APP_NAME in (settings.brand_html or ""):
		settings.brand_html = ""
	if APP_NAME in (settings.footer_powered or ""):
		settings.footer_powered = ""
	settings.save()


def _get_or_create_color(hex_value: str) -> str:
	"""Get or create a Color document for a brand color."""
	color_name = hex_value.upper()
	if not frappe.db.exists("Color", color_name):
		color = frappe.get_doc({"doctype": "Color", "color": hex_value})
		color.name = color_name
		color.insert(ignore_permissions=True)
	return color_name


def setup_website_theme() -> None:
	"""Create and activate the CoreAxis Solutions website theme."""
	theme_name = APP_NAME

	if frappe.db.exists("Website Theme", theme_name):
		theme = frappe.get_doc("Website Theme", theme_name)
	else:
		theme = frappe.new_doc("Website Theme")
		theme.theme = theme_name

	theme.custom = 1
	theme.primary_color = _get_or_create_color(BRAND_PRIMARY)
	theme.text_color = _get_or_create_color(BRAND_TEXT)
	theme.dark_color = _get_or_create_color(BRAND_DARK)
	theme.background_color = _get_or_create_color(BRAND_BG)
	theme.light_color = _get_or_create_color(BRAND_LIGHT)
	theme.google_font = "Inter"
	theme.font_properties = "wght@400;500;600;700;800"
	theme.button_rounded_corners = 1
	theme.button_shadows = 0
	theme.custom_overrides = f"""
// CoreAxis Solutions brand overrides
$primary: {BRAND_PRIMARY};
$body-color: {BRAND_TEXT};

.navbar {{
	box-shadow: 0 1px 2px rgba(5, 7, 10, 0.08);
}}

.page-container {{
	font-family: "Inter", "Segoe UI", sans-serif;
}}
"""
	theme.save(ignore_permissions=True)

	frappe.db.set_single_value("Website Settings", "website_theme", theme_name)


def revert_website_theme() -> None:
	"""Deactivate and remove the CoreAxis Solutions website theme."""
	theme_name = APP_NAME
	settings = frappe.get_single("Website Settings")
	if settings.website_theme == theme_name:
		settings.website_theme = "Standard"
		settings.save()

	if frappe.db.exists("Website Theme", theme_name):
		frappe.delete_doc("Website Theme", theme_name, ignore_permissions=True)


def setup_letter_head() -> None:
	"""Create a default branded letter head for print documents."""
	if frappe.db.exists("Letter Head", APP_NAME):
		letter_head = frappe.get_doc("Letter Head", APP_NAME)
	else:
		letter_head = frappe.new_doc("Letter Head")
		letter_head.letter_head_name = APP_NAME

	letter_head.source = "HTML"
	letter_head.is_default = 1
	letter_head.content = f"""<div style="display:flex;align-items:center;gap:14px;padding:10px 0;border-bottom:2px solid {BRAND_PRIMARY};">
<img src="{APP_LOGO}" style="height:44px;width:44px;object-fit:contain;" alt="{APP_NAME}">
<div>
<div style="font-size:20px;font-weight:800;color:{BRAND_DARK};">{APP_NAME}</div>
<div style="font-size:11px;color:{BRAND_ACCENT};letter-spacing:0.08em;text-transform:uppercase;">Business Systems and ERP</div>
</div>
</div>"""
	letter_head.footer_source = "HTML"
	letter_head.footer = f"""<div style="border-top:1px solid {BRAND_BORDER};padding:8px 0;text-align:center;font-size:10px;color:{BRAND_ACCENT};">
{APP_NAME}
</div>"""
	letter_head.save(ignore_permissions=True)


def revert_letter_head() -> None:
	"""Remove the CoreAxis Solutions letter head."""
	if frappe.db.exists("Letter Head", APP_NAME):
		frappe.delete_doc("Letter Head", APP_NAME, ignore_permissions=True)


def setup_system_settings() -> None:
	"""Set the email footer address when it is not already customized."""
	settings = frappe.get_single("System Settings")
	if not settings.email_footer_address or APP_NAME in settings.email_footer_address:
		frappe.db.set_single_value("System Settings", "email_footer_address", APP_NAME)


def revert_system_settings() -> None:
	"""Clear the email footer address only when owned by this app."""
	settings = frappe.get_single("System Settings")
	if settings.email_footer_address == APP_NAME:
		frappe.db.set_single_value("System Settings", "email_footer_address", "")
