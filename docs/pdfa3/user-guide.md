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

## The letterhead footer

The address / phone / email band at the bottom of the page does **not** come from the
letterhead automatically the way it does on the ordinary Print button — the PDF/A-3 renderer
has no equivalent of the mechanism Frappe uses there.

Instead, the **print format draws it**. A format built for PDF/A-3 pulls the content from the
**Footer** field of the letterhead it names, so you still edit the text in one place: change
the Letter Head record, regenerate, and every invoice follows.

If no footer appears, check in this order:

1. The letterhead's **Footer** field actually has content.
2. The invoice (or Zatca Main Settings) names that letterhead.
3. The print format in use was built to draw a footer — not every format is.

Adding footer support to a format is a developer task; see
[print-format-authoring.md](print-format-authoring.md).

---

## Fonts: Arabic text or the riyal sign looks wrong

The PDF/A-3 is rendered by a different engine than the ordinary print preview, and it does
**not** inherit the fonts your browser has. If Arabic comes out in the wrong typeface, or the
riyal sign appears as an empty box, the fix is in your print format's **CSS** field, not in
the letterhead.

Two things have to be true:

1. **The font has to be loaded.** The best way is to have your administrator install the font
   on the server, where **both** the ordinary print and the PDF/A-3 pick it up by name. Nothing
   goes in the CSS field for this — you just name the family in step 2.

   > **Do not add `@font-face` rules that point at `__FONT_..._PATH__` placeholders.** They work
   > in the PDF/A-3 but **break the ordinary Print button**: nothing fills the placeholder in
   > that path, so the PDF fails outright with *"PDF generation failed because of broken image
   > links"*. The same warning covers a `__ZATCA_QR_SRC__` image. A print format that uses any
   > of these placeholders can only be printed through **Generate PDF/A-3** — never the normal
   > Print button.

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
> That is usually what you want — the two outputs then match — but always download a normal PDF
> before rolling it out, not just a screen preview. The preview renders in your browser and will
> look fine even when the server-side PDF fails.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| *ZATCA XML not found in logs* | Invoice never cleared successfully | Send it to ZATCA first |
| *ZATCA XML content is empty* | The log row exists but carries no XML | Re-send the invoice; check the log record |
| No footer at the bottom | The letterhead's Footer field is empty, or the print format does not draw one | Fill in the letterhead footer; otherwise see the authoring guide |
| Footer overlaps the invoice lines | The format's reserved bottom margin is smaller than the footer | Shorten the footer, or ask a developer to raise the page's bottom margin |
| Arabic in the wrong typeface | Font not declared, or listed after a font that also has Arabic | See [Fonts](#fonts-arabic-text-or-the-riyal-sign-looks-wrong) above |
| Riyal sign is an empty box | The riyal font is not installed on the server | Have an administrator install it system-wide |
| *PDF generation failed because of broken image links* on the **normal Print button** | The print format contains an unsubstituted `__…__` placeholder, which only the PDF/A-3 path fills in | Remove the placeholder from that print format, or print it only through **Generate PDF/A-3** |
| Logo missing | The letterhead stores its logo as HTML rather than in the **Image** field | Set the letterhead's Image field, or embed the logo via the print format |

---

## Related

- [Print Format & Letterhead — Setup Guide](../setup/print-format.md)
- [Submission — User Guide](../submission/user-guide.md) — getting the invoice cleared first
- [Configuration](../setup/configuration.md)
