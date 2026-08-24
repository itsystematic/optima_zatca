# Authoring a PDF/A-3 Print Format

Developer reference for writing print formats that render correctly under **WeasyPrint**.
For the generator pipeline itself, see [reference.md](reference.md); for the click-by-click
guide, see [user-guide.md](user-guide.md).

The worked examples are the shipped **PDFA3** format
(`optima_zatca/print_format/pdfa3/pdfa3.json`, context from
`print_format/sales_invoice_controller.py`) and the site-local client formats, which build
their context inline so they need no app release to change.

---

## Why a separate convention

The ordinary Print button renders through **wkhtmltopdf**, a full browser with a request
context, cookies, and a base URL. The PDF/A-3 button renders through **WeasyPrint**, which
`pdfa3.py` calls as `HTML(string=…)` — no base URL, no network, no request. Three things
that "just work" in the browser therefore fail silently:

| Works in wkhtmltopdf | Under WeasyPrint |
|---|---|
| `<img src="/files/x.png">` | dropped — `Relative URI reference without a base URI` |
| `<link href="/assets/…/print.bundle.css">` | dropped — Frappe's ~250 KB print stylesheet never loads |
| the printview toolbar, stripped automatically | rendered into the PDF |

Nothing raises. You get a PDF that is missing pieces.

---

## The rules

### 1. Never reference a URL the renderer has to fetch

Images must arrive as `data:` URIs. `pdfa3.py` substitutes these tokens across the whole
document, `<style>` blocks included:

| Token | Becomes |
|---|---|
| `__ZATCA_QR_SRC__` | `data:image/png;base64,…` |
| `__LETTERHEAD_LOGO_PATH__` | `data:` URI from the Letter Head **Image** field |
| `__FOOTER_IMG_1/2/3__` | `data:` URIs |
| `__FONT_REG_MARAI_PATH__`, `__FONT_BOLD_MARAI_PATH__`, `__FONT_REG_CLAUDION_PATH__` | `file://` font paths |

```html
<img class="qr" src="__ZATCA_QR_SRC__" alt="ZATCA QR Code">   <!-- yes -->
<img src="{{ doc.ksa_einv_qr }}">                              <!-- no: a /files/ URL -->
```

> **A format containing any of these tokens is PDF/A-3 only.** They are not substituted on
> the ordinary Print button, and an unresolved `url()` makes wkhtmltopdf abort the whole
> render with *"PDF generation failed because of broken image links"*. Name such formats so
> nobody reaches for them from the Print menu.

### 2. Make the CSS self-contained

`print.bundle.css` never loads, so Bootstrap's grid (`col-xs-*`, `row`) and Frappe's utility
classes (`text-right`, `pull-left`, `print-hide`) do nothing. Declare every class the format
uses in its own **CSS** field — borders, padding, alignment, font sizes. Treat the absence of
that stylesheet as normal rather than something to restore.

### 3. Hide the printview chrome yourself

wkhtmltopdf strips the toolbar; WeasyPrint renders it, so "Print" and "Get PDF" appear as the
first line of the PDF. Every format needs:

```css
.print-heading-template, .print-toolbar, .action-banner,
.page-header, a[href*="get_pdf"] { display: none !important; }
```

### 4. Build layout from tables, not flex or floats

Use `display: table` / `table-cell` for columns (the shipped format's `.layout-grid` /
`.layout-col`), or real `<table>` markup. Both renderers agree on tables; float and flex
behaviour differs between them.

### 5. Set direction explicitly

`pdfa3.py` does not pass a print language, so WeasyPrint always sees `<html dir="ltr">` even
when the format declares `default_print_language: "ar"`. A format authored RTL-first mirrors
correctly on the Print button and comes out backwards in the PDF/A-3.

Set it on your own root element and never depend on the ambient value:

```css
.akt { direction: rtl; }
.akt .ltr { direction: ltr; unicode-bidi: embed; }   /* amounts, IBANs, invoice ids */
```

### 6. Size images in CSS, not HTML attributes

`width="100mm"` is not a valid HTML `width` attribute. Browsers salvage it; WeasyPrint drops
it and the image collapses. Put real units in the stylesheet: `.qr { width: 26mm; }`.

### 7. Fonts need `!important` on descendants

Elements inside a print format carry their own `font-family`, so a rule on the container
alone never reaches the text. Per-glyph fallback also stops at the first family that *has*
the glyph — so list the Arabic family first, or a Latin font with Arabic coverage will serve
Arabic instead.

```css
html, body, .akt, .akt *,
.print-format, .print-format * { font-family: 'Almarai', sans-serif !important; }
.akt .riyal { font-family: 'Claudion', 'Almarai', sans-serif !important; }
```

WeasyPrint logs `.notdef glyph rendered for Unicode string unsupported by fonts` on the
`weasyprint` logger when a glyph is missing — the quickest way to confirm a font problem.
Do **not** judge Arabic coverage from the PDF's `/ToUnicode` maps: Arabic shapes to
positional-form glyph ids that do not reverse-map to base codepoints, so a correct PDF looks
empty by that measure.

---

## Structure

### One context block, at the top

Keep lookups out of the markup. Whether the data comes from the app or from the template
itself, resolve it **once, in one labelled block**, and let the body read only from it. That
is the structural win — a reader can see every query the format makes without scrolling, and
the query count stays flat as the layout grows.

For a **site-local format** (a client format that must not depend on an app release), build
the context in the template. Everything below the block reads `ctx.*` and touches no
database:

```jinja
{# ==================== CONTEXT ==================== #}
{% set address = frappe.get_doc('Address', doc.customer_address) if doc.customer_address else {} %}
{% set ctx = {
    'customer_tax_id': frappe.db.get_value('Customer', doc.customer, 'tax_id') or '',
    'address_ar':      address.get('address_in_arabic') or '',
    'address_en':      address.get('address_line1') or '',
    'phone':           address.get('phone') or ''
} %}
```

`.get()` is the important detail: it reads the same way on a Frappe Document and on the `{}`
fallback, so a missing Address degrades to blanks instead of raising.

For a **shipped format**, put the logic in a controller module next to the format
(`print_format/sales_invoice_controller.py` is the worked example, unit-tested in
`test_sales_invoice_controller.py`) and expose it as a Jinja global through
`hooks.jinja.methods`. The template then keeps the same one-line shape.

> **Avoid `frappe.call(...)` in a template.** It routes through `execute_cmd`, which requires
> an HTTP request: it works from the desk button but raises `AttributeError: request` in a
> background job, a scheduled run, or a test. A Jinja hook method — or an inline block — is a
> plain call and works in every context.

### Macros for repeated rows

Bilingual layouts repeat the same three-cell shape dozens of times. Declare it once:

```jinja
{% macro pair(label_ar, value, label_en, value_class='mid') %}
<tr>
    <td class="start">{{ label_ar }}</td>
    <td class="{{ value_class }}">{{ value or '' }}</td>
    <td class="end">{{ label_en }}</td>
</tr>
{% endmacro %}

{{ pair('رقم الفاتورة', doc.name, 'Invoice Number', 'mid ltr') }}
```

### No inline styles

Every `style="…"` is invisible to the next reader and unreachable from the CSS field. Give
the element a class instead. Name classes by role — `.start` / `.end` rather than
`.text-right` / `.text-left`, so an RTL flip does not turn the names into lies.

### File shape

```
{# header comment: what renders this, and which rules it follows #}

{# ==================== CONTEXT ==================== #}   every lookup, once
{# ==================== MACROS ==================== #}
{# ==================== DOCUMENT ==================== #}
<div class="akt">
    {# ---------- TITLE ---------- #}
    {# ---------- ITEMS ---------- #}
    ...
</div>
```

Wrap blocks that must not split across pages in `page-break-inside: avoid`.

---

## Checking your work

Render through the generator and inspect, rather than trusting the on-screen preview:

```python
import io, logging, pypdf, frappe
import optima_zatca.zatca.pdfa3 as m

logging.getLogger("weasyprint").setLevel(logging.DEBUG)   # unresolved URLs, notdef glyphs
pdf = m.ZatcaPDFA3Generator("<invoice>")._generate_visual_pdf()
r = pypdf.PdfReader(io.BytesIO(pdf))
print(sum(len(p["/Resources"].get("/XObject", {})) for p in r.pages))   # images embedded
print({str(v.get("/BaseFont")) for p in r.pages for v in p["/Resources"]["/Font"].values()})
print(r.pages[0].extract_text()[:80])                     # should start at your title
```

A healthy render has every expected image present, only the intended fonts embedded, no
`.notdef` warnings, and no toolbar text at the start of the extracted text. One unresolved
URL for `print.bundle.css` is expected and harmless once rule 2 is followed.

---

## Related

- [reference.md](reference.md) — the generator pipeline and placeholder contract
- [Print Format & Letterhead — Setup Guide](../setup/print-format.md)
