# PDF/A-3 Invoice

Developer + power-user reference for **`zatca/pdfa3.py`** — rendering the invoice PDF and
embedding the signed UBL XML inside it. For a click-by-click guide aimed at accountants, see
[user-guide.md](user-guide.md).

---

## Entry point

`generate_pdfa3_for_invoice(sales_invoice_name)` is the only `@frappe.whitelist()` in the
module; the desk button in `public/js/sales_invoice/zatca_buttons.js` calls it by dotted path.
Its signature is public — keep new helpers private (`_` prefix). Everything it does is
delegated to `ZatcaPDFA3Generator`, and any exception is funnelled through
`log_and_throw_error`.

```
generate_pdfa3_for_invoice(name)
└── ZatcaPDFA3Generator(name).generate_and_save()
    ├── _generate_visual_pdf()      # print format → HTML → WeasyPrint → bytes
    │   ├── frappe.get_print(no_letterhead=1)
    │   └── <placeholder substitution>          # fonts, logo, QR, footer images
    ├── _get_zatca_xml()            # signed XML from Optima Zatca Logs
    ├── _embed_xml_file()           # PikePDF: /EmbeddedFiles + /AF + XMP
    │   └── _inject_xmp_metadata()  # pdfaid:part 3, conformance B
    └── _save_file()                # File doctype, attached to ksa_einv_pdfa3
```

**Two renderers, one print format.** The ordinary desk print runs through wkhtmltopdf; this
module runs WeasyPrint. They do not share behaviour, and most surprises in this module trace
back to that split.

---

## Settings resolution

`_get_print_settings()` resolves three values, each with a fallback chain:

| Key | Chain |
|-----|-------|
| `print_format` | Zatca Main Settings `print_format` → Sales Invoice `default_print_format` → `"Standard"` |
| `letterhead` | Zatca Main Settings `letter_head` → the invoice's own `letter_head` |
| `language` | Zatca Main Settings `language` → `frappe.local.lang` → `"en"` |

Zatca Main Settings is a Single doctype, so every one of these is **per-site data**. Layout
differences between deployments belong here, not in the module.

---

## The placeholder contract

WeasyPrint has no Frappe request context and cannot fetch `/files/…` or `/assets/…` URLs, so
the module resolves those assets itself and substitutes them into the rendered HTML as
`file://` URLs or `data:` URIs. A print format opts in by writing the placeholder token; a
print format that omits it renders unchanged.

| Placeholder | Substituted with | Source |
|-------------|------------------|--------|
| `__FONT_REG_CLAUDION_PATH__` | `file://…/public/fonts/Claudion.ttf` | bundled |
| `__FONT_REG_MARAI_PATH__` | `file://…/public/fonts/Almarai-Regular.ttf` | bundled |
| `__FONT_BOLD_MARAI_PATH__` | `file://…/public/fonts/Almarai-Bold.ttf` | bundled |
| `__LETTERHEAD_LOGO_PATH__` | `data:` URI | Letter Head `image` field |
| `__ZATCA_QR_SRC__` | `data:image/png` | `ksa_einv2_qr` / `ksa_einv_qr`, re-encoded by `_generate_qr_code` |
| `__FOOTER_IMG_1/2/3__` | `data:` URI | fixed filenames in the site's Files |

Substitution runs over the **whole document**, `<style>` blocks included — which is what makes
`@font-face { src: url('__FONT_REG_MARAI_PATH__') }` in a print format's CSS field work here.

> **A print format carrying these tokens is valid *only* through the PDF/A-3 path.** Nothing
> substitutes them in the ordinary desk print, and an unsubstituted token is not inert: it stays
> in the markup as a relative URL, wkhtmltopdf requests it, gets a 404, and **aborts the whole
> PDF**. Frappe surfaces that as `ContentNotFoundError` → *"PDF generation failed because of
> broken image links"*. This is not configurable per call — `frappe/utils/pdf.py` leaves
> `'load-error-handling': 'ignore'` commented out, so wkhtmltopdf runs with its default `abort`.
>
> It applies to every token equally — an `<img src="__ZATCA_QR_SRC__">` breaks the normal Print
> button exactly as an `@font-face` `url()` does.

Consequently the same print format does **not** transparently serve both renderers. Where a
format must work under both, prefer resources neither renderer has to fetch: font families
installed system-wide and resolved by name through fontconfig (no `@font-face` at all), and the
QR taken from the invoice's own field rather than a placeholder.

> **`__LETTERHEAD_LOGO_PATH__` reads the Letter Head `image` field only.** A letterhead whose
> logo lives inside its `content` HTML resolves to an empty string here — the `content` block
> is never rendered, because the print is requested with `no_letterhead=1`.

### Font cascade

Two independent failure modes, both silent:

- **The font is never loaded.** No `@font-face` rule in the print format → the family name
  resolves through fontconfig, or falls back to a system font.
- **The font is loaded but never applied.** A rule on `.print-format` alone does not reach the
  text: elements inside a print format carry their own `font-family`, and the more specific
  declaration wins. `.print-format *` with `!important` is what actually lands.

Per-glyph fallback stops at the first family in the stack that *has* the glyph, so a
general-purpose font listed ahead of the Arabic one will serve Arabic itself. Order the Arabic
family first.

WeasyPrint reports missing glyphs on the `weasyprint` logger
(`.notdef glyph rendered for Unicode string unsupported by fonts: …`) — the fastest way to
confirm a font problem. Note that inspecting the output PDF's `/ToUnicode` maps is **not** a
valid check: Arabic shapes to positional-form glyph IDs that do not reverse-map to the base
codepoints, so a correct PDF looks empty by that measure.

---

## The Letter Head footer

Frappe never puts the Letter Head footer in this module's HTML. `_generate_visual_pdf`
requests `no_letterhead=1`, so `get_letter_head` returns `{}` and `standard.html` skips its
footer block; and with **Repeat Header Footer** on it would land in a `.visible-pdf` div that
the print stylesheet hides, which wkhtmltopdf only survives because `prepare_header_footer`
extracts that div into `--footer-html`. WeasyPrint has no equivalent step.

The generator does **not** compensate for this — a print format that wants a footer draws one
itself. See [print-format-authoring.md](print-format-authoring.md#the-rules) for the working
mechanism (`position: fixed` offset into the page's bottom margin) and the two traps around
it: CSS running elements render on the last page only under WeasyPrint 68, and a margin box
sizes to its content unless given an explicit width.

---

## XML retrieval

`_get_zatca_xml()` reads the most recent **Optima Zatca Logs** row for the invoice with status
`Success` or `Warning`, ordered by `creation desc`, preferring `xml_content` and falling back
to base64-decoding `invoice`. It throws when no such row exists, so the PDF can only ever be
built from an invoice that actually cleared.

---

## Embedding and PDF/A-3 conformance

`_embed_xml_file()` works at the PikePDF object level rather than through a convenience
helper, because PDF/A-3 requires the attachment to be reachable two ways:

| Structure | Purpose |
|-----------|---------|
| `/Names/EmbeddedFiles/Names` | the classic attachment table |
| `/AF` (Associated Files) on the document catalog | the PDF/A-3 association, with `AFRelationship = /Data` |

The file spec carries `Type=/Filespec`, matching `F` and `UF` names
(`<invoice>_zatca.xml`, slashes replaced), and a `/Params` dictionary with `Size` and
`ModDate`. The stream is typed `/EmbeddedFile` with subtype `/text#2Fxml` (the escaped form of
`text/xml`).

`_inject_xmp_metadata()` then overwrites `/Root/Metadata` with an RDF packet declaring
`pdfaid:part 3` and `pdfaid:conformance B`, alongside the `dc:title` / `dc:creator` /
`dc:description` set through `pdf.open_metadata()`.

> **The XMP packet asserts conformance; it does not enforce it.** Nothing in this module
> validates the rendered page content against PDF/A-3 (embedded fonts, colour spaces, no
> transparency). A deployment that must certify conformance should run the output through an
> external validator.

---

## Storage

`_save_file()` deletes any existing File rows for
`(Sales Invoice, <name>, ksa_einv_pdfa3)` before writing, so regeneration replaces rather than
accumulates. The new File is **public** (`is_private: 0`), named `<invoice>_PDFA3.pdf` with
slashes replaced, and the invoice's `ksa_einv_pdfa3` field is updated via `db_set`.

---

## Related

- [Architecture](../reference/architecture.md) — where this module sits
- [Submission — reference](../submission/reference.md) — how the embedded XML got into the logs
- [Print Format & Letterhead — Setup Guide](../setup/print-format.md)
