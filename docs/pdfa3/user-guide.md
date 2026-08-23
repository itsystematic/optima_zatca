# PDF/A-3 Invoice — User Guide

A plain-language guide for accountants and implementers to producing the archival invoice
PDF and tuning how it looks. For the technical model, see [reference.md](reference.md).

---

## What a PDF/A-3 invoice is

A normal invoice PDF is a picture of the invoice. A **PDF/A-3** invoice is the same picture
with the signed e-invoice XML tucked inside it as an attachment. Anyone can open it and read
it; a tax authority's validator can open the same file and pull out the exact XML that was
cleared. One file, one archive, no pairing of a PDF with a loose `.xml` alongside it.

---

## Generating one

1. Open a Sales Invoice that has been **successfully sent to ZATCA**.
2. Click **Generate PDF/A-3**.
3. The finished file is attached to the invoice and linked from its **PDF/A-3** field.

Re-running replaces the previous attachment rather than piling up copies.

> **The invoice must have cleared first.** The generator embeds the signed XML recorded by
> the last successful submission. On an invoice that has never been sent — or whose every
> attempt failed — it stops with *ZATCA XML not found in logs*. Send the invoice first, then
> generate.

---

## Where the layout comes from

Two settings on **Zatca Main Settings** decide what the PDF looks like:

| Setting | Effect |
|---------|--------|
| **Print Format** | The layout used. Falls back to the Sales Invoice default, then to *Standard* |
| **Letter Head** | The letterhead the logo and footer are taken from. Falls back to the invoice's own letterhead |

Because these live on Zatca Main Settings, each site chooses its own layout without any
change to the app.

---

## Showing the letterhead footer

By default the PDF/A-3 carries **no letterhead footer** — the address / phone / email band
you see at the bottom of a normal printed invoice is missing. This is deliberate on the
framework's side, not a fault in your letterhead, and it needs to be switched on:

1. Go to **Zatca Main Settings**.
2. Tick **Show Letter Head Footer in PDF/A-3**.
3. Regenerate the PDF.

The footer is then drawn at the bottom of **every** page, and a strip of the page is reserved
for it so invoice lines never run underneath it.

> **If the tick box isn't there**, the field has not been added on this site yet — it is
> opt-in precisely so existing PDFs never change shape without someone asking. See
> [reference.md](reference.md#enabling-the-footer-on-a-new-site) for the one-time setup an
> administrator runs.

Nothing else needs configuring: the content is whatever is already in the **Footer** field of
the letterhead chosen above. Edit the letterhead, regenerate, and the PDF follows.

---

## Fonts: Arabic text or the riyal sign looks wrong

The PDF/A-3 is rendered by a different engine than the ordinary print preview, and it does
**not** inherit the fonts your browser has. If Arabic comes out in the wrong typeface, or the
riyal sign appears as an empty box, the fix is in your print format's **CSS** field, not in
the letterhead.

Two things have to be true:

1. **The font has to be loaded.** The generator makes the bundled Arabic and riyal fonts
   available to your print format through three placeholders. Declare them in the CSS field:

   ```css
   @font-face { font-family: 'Almarai'; src: url('__FONT_REG_MARAI_PATH__'); }
   @font-face { font-family: 'Almarai'; src: url('__FONT_BOLD_MARAI_PATH__'); font-weight: bold; }
   @font-face { font-family: 'Claudion'; src: url('__FONT_REG_CLAUDION_PATH__'); }
   ```

   In the ordinary print preview these placeholders are left alone, the rules are ignored, and
   nothing breaks — so the same print format serves both.

2. **The font has to actually reach the text.** Elements inside a print format usually carry
   their own font, so setting a font on the outer container alone quietly does nothing. Target
   the descendants, and mark it important:

   ```css
   html, body,
   .print-format, .print-format * { font-family: 'Almarai', sans-serif !important; }

   /* The riyal sign exists only in Claudion. Keep this rule last so it wins. */
   .print-format .new-riyal { font-family: 'Claudion', 'Almarai', sans-serif !important; }
   ```

> **Order matters more than it looks.** If you list a general-purpose font before the Arabic
> one, Arabic silently renders in the general-purpose font — the browser stops at the first
> font that happens to have the letter. Put the Arabic font first.

> **This also changes your ordinary printed invoice**, since the CSS field is shared by both.
> That is usually what you want — the two outputs then match — but preview a normal print
> before rolling it out.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| *ZATCA XML not found in logs* | Invoice never cleared successfully | Send it to ZATCA first |
| *ZATCA XML content is empty* | The log row exists but carries no XML | Re-send the invoice; check the log record |
| No footer at the bottom | **Show Letter Head Footer in PDF/A-3** is off, or the letterhead's Footer field is empty | Tick the box; fill in the letterhead footer |
| Footer overlaps the invoice lines | Footer is taller than the reserved strip | Shorten it, or ask a developer to raise the reserved height |
| Arabic in the wrong typeface | Font not declared, or listed after a font that also has Arabic | See [Fonts](#fonts-arabic-text-or-the-riyal-sign-looks-wrong) above |
| Riyal sign is an empty box | Claudion never loaded | Add its `@font-face` rule |
| Logo missing | The letterhead stores its logo as HTML rather than in the **Image** field | Set the letterhead's Image field, or embed the logo via the print format |

---

## Related

- [Print Format & Letterhead — Setup Guide](../setup/print-format.md)
- [Submission — User Guide](../submission/user-guide.md) — getting the invoice cleared first
- [Configuration](../setup/configuration.md)
