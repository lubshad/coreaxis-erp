from __future__ import annotations

import re
from typing import TypedDict

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import strip_html_tags


class ContactInquiryResponse(TypedDict):
	ok: bool
	lead_id: str


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SERVICE_OPTIONS = {
	"ERPNext / Frappe implementation",
	"Custom business system",
	"Web or mobile application",
	"Integration and automation",
	"Cloud hosting and support",
}


@frappe.whitelist(methods=["POST"], allow_guest=True)
@rate_limit(key="contact_inquiry", limit=8, seconds=3600)
def submit_contact_inquiry(
	name: str,
	company: str,
	email: str,
	phone: str,
	service_interest: str,
	message: str,
	budget_timeline: str | None = None,
	website: str | None = None,
) -> ContactInquiryResponse:
	"""Create a CRM Lead from the public CoreAxis website contact form."""
	values = _validate_contact_inquiry(
		name=name,
		company=company,
		email=email,
		phone=phone,
		service_interest=service_interest,
		message=message,
		budget_timeline=budget_timeline,
		website=website,
	)

	if values["website"]:
		return {"ok": True, "lead_id": ""}

	_ensure_crm_defaults()

	first_name, last_name = _split_name(values["name"])
	lead = frappe.new_doc("CRM Lead")
	lead.first_name = first_name
	lead.lead_name = values["name"]
	lead.organization = values["company"]
	lead.email = values["email"]
	lead.mobile_no = values["phone"]
	lead.status = "New"
	lead.source = "Website"
	if last_name:
		lead.last_name = last_name

	lead.insert(ignore_permissions=True)
	_add_inquiry_comment(lead.name, values)
	frappe.db.commit()

	return {"ok": True, "lead_id": lead.name}


def _validate_contact_inquiry(
	name: str,
	company: str,
	email: str,
	phone: str,
	service_interest: str,
	message: str,
	budget_timeline: str | None = None,
	website: str | None = None,
) -> dict[str, str]:
	values = {
		"name": _clean(name),
		"company": _clean(company),
		"email": _clean(email).lower(),
		"phone": _clean(phone),
		"service_interest": _clean(service_interest),
		"message": _clean(message),
		"budget_timeline": _clean(budget_timeline or ""),
		"website": _clean(website or ""),
	}

	if values["website"]:
		return values

	if not values["name"]:
		frappe.throw(_("Name is required."))
	if not values["company"]:
		frappe.throw(_("Company is required."))
	if not EMAIL_PATTERN.match(values["email"]):
		frappe.throw(_("A valid email address is required."))
	phone_digits = re.sub(r"\D", "", values["phone"])
	if len(phone_digits) < 7 or len(phone_digits) > 15:
		frappe.throw(_("A valid phone number is required."))
	if values["service_interest"] not in SERVICE_OPTIONS:
		frappe.throw(_("Choose a valid service interest."))
	if len(values["message"]) < 20:
		frappe.throw(_("Project details must be at least 20 characters."))

	return values


def _clean(value: str) -> str:
	return strip_html_tags(str(value or "")).strip()


def _split_name(full_name: str) -> tuple[str, str]:
	parts = [part for part in full_name.split() if part]
	first_name = parts[0] if parts else full_name
	last_name = " ".join(parts[1:])
	return first_name, last_name


def _ensure_crm_defaults() -> None:
	if not frappe.db.exists("CRM Lead Status", "New"):
		try:
			status = frappe.new_doc("CRM Lead Status")
			status.lead_status = "New"
			status.color = "gray"
			status.type = "Open"
			status.position = 1
			status.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			pass

	if not frappe.db.exists("CRM Lead Source", "Website"):
		try:
			source = frappe.new_doc("CRM Lead Source")
			source.source_name = "Website"
			source.details = "CoreAxis Solutions website contact form"
			source.insert(ignore_permissions=True)
		except frappe.DuplicateEntryError:
			pass


def _add_inquiry_comment(lead_name: str, values: dict[str, str]) -> None:
	content = f"""
<p><strong>Website inquiry from CoreAxis Solutions site</strong></p>
<ul>
	<li><strong>Service interest:</strong> {frappe.utils.escape_html(values["service_interest"])}</li>
	<li><strong>Budget / timeline:</strong> {frappe.utils.escape_html(values["budget_timeline"] or "Not provided")}</li>
	<li><strong>Message:</strong> {frappe.utils.escape_html(values["message"])}</li>
</ul>
"""

	try:
		comment = frappe.new_doc("Comment")
		comment.comment_type = "Comment"
		comment.reference_doctype = "CRM Lead"
		comment.reference_name = lead_name
		comment.comment_email = values["email"]
		comment.comment_by = values["name"]
		comment.content = content
		comment.insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(
			title="CoreAxis contact inquiry comment failed",
			message=frappe.get_traceback(),
		)
