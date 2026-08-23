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
    │   ├── <placeholder substitution>          # fonts, logo, QR, footer images
    │   └── _inject_letterhead_footer()         # opt-in, see below
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
`@font-face { src: url('__FONT_REG_MARAI_PATH__') }` in a print format's CSS field work. In
the wkhtmltopdf path the token is never replaced, the `url()` is invalid, and the browser
discards that one rule; the rest of the stylesheet is unaffected. The same print format
therefore serves both renderers.

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

## The Letter Head footer band

### Why it has to be re-attached

The footer never reaches this module's HTML, for two compounding reasons:

1. `_generate_visual_pdf` calls `frappe.get_print(..., no_letterhead=1)`. In
   `frappe/www/printview.py`, `get_letter_head` returns `{}` on that flag, so `footer` is
   empty and `templates/print_formats/standard.html` skips its
   `{% if not no_letterhead and footer %}` block entirely.
2. Clearing the flag would not be enough. With Print Settings **Repeat Header Footer** on, the
   footer is emitted inside `<div id="footer-html" class="visible-pdf">`, and
   `templates/styles/standard.css` declares `.visible-pdf { display: none !important }`.
   wkhtmltopdf still shows it only because `prepare_header_footer` in `frappe/utils/pdf.py`
   *extracts* that div out of the body and passes it as `--footer-html`. WeasyPrint has no
   equivalent step, so the div would render hidden and the footer would still be invisible.

`_inject_letterhead_footer` therefore fetches the Letter Head's `footer` field directly,
renders it through `frappe.render_template` with `{"doc": …}` (matching printview's own
handling, so Jinja in a letterhead footer keeps working), and appends it before `</body>`.

### How it repeats

WeasyPrint repeats `position: fixed` boxes on every page. The injected block pairs that with
an `@page { margin-bottom }` reserving the strip, so body content cannot flow underneath:

```css
@page { margin-bottom: 30mm; }
#pdfa3-letterhead-footer { position: fixed; left: 0; right: 0; bottom: 0; }
```

`ZatcaPDFA3Generator.FOOTER_BAND_HEIGHT_MM` drives both numbers. Raise it if a deployment's
footer is taller than the reserved strip.

The wrapper carries `class="print-format"` so the footer inherits the same fonts and table
styling as the body — including any `.print-format *` font rule.

### Enabling the footer on a new site

The feature is gated on `pdfa3_show_letterhead_footer` (`LETTERHEAD_FOOTER_FIELD`) on
**Zatca Main Settings**. The field is *not* shipped with the app:
`zatca_settings.get(...)` returns `None` where it is absent, so a site that has never asked
for the footer produces byte-identical PDFs to before.

Creating it is a patch that is **deliberately absent from `patches.txt`**:

```
patches/v15/create_pdfa3_letterhead_footer_field.py
```

Leaving it out of `patches.txt` is the whole design. Enabling the footer reserves a strip on
every page and reflows the invoice body — that is not something a deployment should inherit
from an app update, so the patch is run by hand on the sites that want it:

```bash
bench --site <site> execute optima_zatca.patches.v15.create_pdfa3_letterhead_footer_field.execute
```

It is idempotent (`create_custom_fields(..., update=True)`), so re-running is harmless. Then
tick **Show Letter Head Footer in PDF/A-3** on Zatca Main Settings and regenerate.

> **Do not "fix" the missing `patches.txt` entry.** Registering it there would create the field
> on every site on the next `bench migrate`. That alone would not change any PDF — the field
> still defaults to unticked — but it puts a switch in front of every operator for a layout
> decision only some deployments have made, and turns a per-site opt-in into an app-wide one.

Adding the field by hand works equally well where a patch run is awkward: **Customize Form →
Zatca Main Settings → new field**, type **Check**, fieldname `pdfa3_show_letterhead_footer`,
inserted after `letter_head`. Because a Custom Field is site data either way, it never
propagates to other deployments.

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
