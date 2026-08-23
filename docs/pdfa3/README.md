# PDF/A-3 Invoice — Docs

The archival invoice PDF: the visual print format rendered by WeasyPrint, with the signed
UBL XML embedded inside it as an attachment, so one file satisfies both the human reader
and a machine validator.

| Document | For | What it covers |
|----------|-----|----------------|
| [user-guide.md](user-guide.md) | Accountants & implementers | Generating the PDF, where it is stored, enabling the letterhead footer band, and what to check when Arabic or the riyal sign renders wrong |
| [reference.md](reference.md) | Developers | The `ZatcaPDFA3Generator` pipeline, the print-format placeholder contract, the PikePDF embedding and XMP metadata, and why the letterhead footer needs re-attaching |

Code lives in `zatca/pdfa3.py`. The XML it embeds is whatever the most recent successful
[submission](../submission/) wrote to **Optima Zatca Logs** — the PDF is a packaging step,
never a submission step. Print format and letterhead setup is covered in
[setup/print-format.md](../setup/print-format.md).
