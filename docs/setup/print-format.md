# Print Format & Letterhead — Setup Guide

A guide for implementers to the **Zatca Sales Invoice** print format — logo/letterhead specs,
customization, and troubleshooting. For how the print format is installed, see
[install.md](install.md).

## Overview

Optima ZATCA provides a professional, ZATCA-compliant print format for Sales Invoices. This guide explains how to customize the print format and letterhead to match your company's branding while maintaining ZATCA compliance.

---

## Table of Contents

1. [Understanding the Default Print Format](#understanding-the-default-print-format)
2. [Logo Requirements and Specifications](#logo-requirements-and-specifications)
3. [Setting Up Your Letterhead](#setting-up-your-letterhead)
4. [Customizing the Print Format](#customizing-the-print-format)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)

---

## Understanding the Default Print Format

### Zatca Sales Invoice Print Format

The **Zatca Sales Invoice** print format is automatically installed with Optima ZATCA and includes:

✅ **ZATCA-Compliant Layout**
- Bilingual (English/Arabic) invoice headers
- QR code integration for e-invoicing
- VAT breakdown and totals
- Company and customer information sections
- Payment and prepayment details

✅ **Professional Design**
- Clean, modern layout
- Optimized for A4 paper
- Print-friendly styling
- Responsive table layouts

✅ **Key Features**
- Letterhead integration
- Multiple currency support
- Automatic VAT calculations
- Payment information display
- Bank details section
- Signature blocks

### Accessing the Print Format

1. Go to **Home → Printing → Print Format**
2. Search for **"Zatca Sales Invoice"**
3. Click to view the print format details

> **Note:** The print format is marked as "Standard: Yes", which means it's a system template. To customize it, you'll need to create a duplicate (see [Customizing the Print Format](#customizing-the-print-format)).

---

## Logo Requirements and Specifications

### Recommended Logo Dimensions

For optimal display in the ZATCA Sales Invoice print format, your logo should match these specifications:

#### **Display Dimensions**
- **Width:** 160 pixels
- **Height:** 120 pixels
- **Aspect Ratio:** 4:3 (portrait orientation)

> These dimensions are specifically designed for the Zatca Sales Invoice layout and provide the best balance between visibility and page space utilization.

#### **Source File Specifications**

**File Format**
- **Primary:** PNG (with transparent background recommended)
- **Alternative:** JPG (with white or light background)
- **Professional:** SVG (vector format, scales perfectly)

**File Size**
- **Maximum:** 500 KB
- **Recommended:** 50-200 KB (for fast loading and optimal performance)

**Resolution**
- **Minimum:** 72 DPI (adequate for screen display)
- **Recommended:** 150-300 DPI (better quality for printing)

**Color Space**
- **RGB:** For digital display and PDF generation
- **CMYK:** If you print physical invoices professionally

### Design Guidelines

#### **Visual Balance**
```
┌─────────────┐
│             │ 
│    LOGO     │ ← 120px height
│             │
│             │
└─────────────┘
  ← 160px width
```

#### **Safe Area**
- Keep important logo elements within 110px × 150px
- Leave 5-10px padding on all sides for visual breathing room
- Avoid placing critical text or details at the edges

#### **Brand Consistency**
1. **Use Official Assets**
   - Use your company's official logo file
   - Maintain brand colors accurately
   - Ensure trademark symbols are visible if required

2. **Background Considerations**
   - Transparent background works best
   - If using solid background, ensure it matches the print format
   - White or light backgrounds recommended

3. **Legibility**
   - Logo should be readable at 120×160px
   - Test on both screen and print
   - Avoid overly intricate details that become blurry

### Creating Your Logo

#### **Option 1: Using Existing Logo**

If your logo is larger than 120×160px:

1. **Resize Using Image Editor**
   - Use Photoshop, GIMP, or online tools
   - Set canvas to 120×160px
   - Maintain aspect ratio
   - Center your logo
   - Add transparent/white padding if needed

2. **Save Optimized Version**
   ```
   Original: company-logo.png (2000×2000px, 5MB)
   Optimized: company-logo-invoice.png (160×120px, 50KB)
   ```

#### **Option 2: Creating from Scratch**

1. **Canvas Setup**
   - Width: 160px
   - Height: 120px
   - Resolution: 150 DPI
   - Color mode: RGB
   - Background: Transparent

2. **Design Placement**
   - Center logo elements
   - Use readable fonts (min 8pt at 150 DPI)
   - Ensure sufficient contrast

### Example Dimensions in Print Format

The current CSS implementation:

```css
.letterhead-table img {
    height: 120px;
    width: 160px;
}
```

This ensures your logo displays consistently across all invoices.

---

## Setting Up Your Letterhead

### Step 1: Prepare Your Logo

Before creating a letterhead:
1. ✅ Resize logo to 160×120px
2. ✅ Save as PNG (preferred) or JPG
3. ✅ Optimize file size (under 500KB)
4. ✅ Test image opens correctly

### Step 2: Create a New Letterhead

1. **Navigate to Letterhead**
   ```
   Home → Printing → Letter Head → New
   ```

2. **Fill in Basic Details**
   - **Letter Head Name:** Your company name (e.g., "ABC Trading Co. Letterhead")
   - **Disabled:** Leave unchecked
   - **Is Default:** Check if this should be the default for all documents

### Step 3: Upload Your Logo

1. **Set Letter Head Based On**
   - Select **"Image"** from the **Letter Head Based On** dropdown
   - This option allows you to upload an image file

2. **Upload Your Logo**
   - Click the **Attach** button
   - Select your prepared logo file (120×160px)
   - Wait for upload completion
   - The image URL will populate automatically in the **Image** field

> **Note:** If you select "HTML" instead, you can paste HTML/CSS code directly. However, for simple logo display, **"Image"** is recommended.

### Step 4: Add Additional Content (Optional)

You can add company information below the logo:

```html
<div style="text-align: center; margin-top: 10px;">
    <p style="margin: 0; font-size: 10px; color: #333;">
        <strong>ABC Trading Company</strong><br>
        Building No. 1234, King Fahd Road<br>
        Riyadh 11564, Saudi Arabia<br>
        Tel: +966 11 234 5678 | Email: info@abc.com<br>
        VAT No: 300000000000003 | CR: 1234567890
    </p>
</div>
```

### Step 5: Preview and Test

1. Click **Save**
2. Open any Sales Invoice
3. Click **Print** dropdown
4. Select **"Zatca Sales Invoice"**
5. Verify:
   - ✅ Logo displays correctly
   - ✅ Logo is clear and readable
   - ✅ Dimensions look proportional
   - ✅ No distortion or stretching

### Step 6: Set as Default (Optional)

To use this letterhead for all Sales Invoices:

1. Go to **Customize Form**
   ```
   Home → Customization → Customize Form
   ```
2. Enter **"Sales Invoice"**
3. Scroll to **Print Settings** section
4. Set **Letter Head** to your letterhead name
5. Click **Update**

---

## Customizing the Print Format

### ⚠️ Important: Never Edit the Standard Format

The "Zatca Sales Invoice" print format is a system template that may be updated by Optima ZATCA. Always create a custom copy for your modifications.

### Step 1: Duplicate the Print Format

1. **Open Standard Format**
   ```
   Home → Printing → Print Format → "Zatca Sales Invoice"
   ```

2. **Create Duplicate**
   - Click **Menu (⋮)** → **Duplicate**
   - Rename: `"[Your Company] - Sales Invoice"` (e.g., "ABC Trading - Sales Invoice")
   - Click **Save**

3. **Uncheck Standard**
   - In your new copy, uncheck **Standard** if it was copied
   - This allows you to edit freely

### Step 2: Common Customizations

#### **A. Adjust Logo Dimensions**

If your logo has different proportions, modify the CSS:

**Example: Square Logo (1:1 ratio)**
```css
.letterhead-table img {
    height: 140px;
    width: 140px;
}
```

**Example: Wider Logo (16:9 ratio)**
```css
.letterhead-table img {
    height: 90px;
    width: 160px;
}
```

**Example: Maintain Aspect Ratio**
```css
.letterhead-table img {
    max-height: 120px;
    max-width: 160px;
    height: auto;
    width: auto;
}
```

#### **B. Change Brand Colors**

Find CSS variables in the CSS field:

```css
:root {
    /* Change these to your brand colors */
    --color-primary: #1976D2;        /* Main brand color */
    --color-primary-dark: #1565C0;   /* Darker shade */
}
```

Common brand color examples:
```css
/* Professional Blue */
--color-primary: #2C3E50;

/* Corporate Green */
--color-primary: #27AE60;

/* Modern Purple */
--color-primary: #8E44AD;

/* Classic Red */
--color-primary: #C0392B;
```

#### **C. Add Company Tagline**

In the HTML field, locate the letterhead section and add:

```html
<table class="letterhead-table">
    <tr>
        <td>
            {% if letter_head %}
                {{ letter_head }}
                <!-- Add tagline below logo -->
                <div style="text-align: center; margin-top: 8px;">
                    <p style="font-size: 9px; color: #666; font-style: italic; margin: 0;">
                        Your Trusted Partner in Excellence
                    </p>
                </div>
            {% endif %}
        </td>
    </tr>
</table>
```

#### **D. Adjust Header Layout**

To give more space to the company info table:

```css
.letterhead-table {
    width: 25%;  /* Change from 29% */
}

.header_table {
    width: 75%;  /* Change from 70% */
}
```

### Step 3: Set Custom Format as Default

1. **Via Customize Form**
   ```
   Home → Customization → Customize Form → Sales Invoice
   ```
   - Set **Default Print Format** to your custom format
   - Click **Update**

2. **Per User Preference**
   Users can select their preferred format from the Print dropdown

---

## Best Practices

### 1. Logo Preparation Checklist

Before implementing your logo:
- [ ] Dimensions are 120×160px (or proportional)
- [ ] File size is under 500KB
- [ ] Format is PNG or JPG
- [ ] Background is transparent or white
- [ ] Image is clear and crisp
- [ ] Colors match brand guidelines
- [ ] File is uploaded and accessible

### 2. Testing Checklist

After setting up letterhead and print format:
- [ ] Print preview looks correct
- [ ] Logo is not pixelated or blurry
- [ ] Test with different invoice amounts
- [ ] Verify QR code displays
- [ ] Check Arabic text renders properly
- [ ] Print physical sample (if applicable)
- [ ] Test on different browsers
- [ ] Verify PDF generation works

### 3. ZATCA Compliance Requirements

**DO NOT remove or modify these sections:**
- ❌ QR Code section (required for e-invoicing)
- ❌ VAT breakdown table
- ❌ Company VAT number display
- ❌ Customer VAT number display
- ❌ Invoice number and date
- ❌ Tax totals section
- ❌ Payment reference section

**Safe to customize:**
- ✅ Colors and fonts
- ✅ Logo and letterhead
- ✅ Spacing and margins
- ✅ Additional company information
- ✅ Signature blocks

### 4. Version Control

Keep track of your customizations:

```
Format Name: ABC Trading - Sales Invoice v1.0
Date: 2025-12-25
Changes:
- Added company logo (120×160px)
- Changed primary color to #1976D2
- Added company tagline
```

### 5. Backup Your Customizations

**Export Your Custom Format:**
1. Open your custom print format
2. Click **Menu (⋮)** → **Export**
3. Save the JSON file in a safe location
4. Document any manual changes

**Create Multiple Versions:**
- Keep "v1.0" as stable backup
- Work on "v2.0 - Draft" for new changes
- Promote to production when tested

---

## Troubleshooting

### Logo Issues

#### **Problem: Logo Not Displaying**

**Possible Causes & Solutions:**

1. **Image URL Not Accessible**
   ```
   Solution:
   - Test URL directly in browser
   - Ensure image is in /public/files/ not /private/files/
   - Check file permissions
   ```

2. **Letterhead Not Selected**
   ```
   Solution:
   - Check letterhead is set in Sales Invoice
   - Set as default in Customize Form
   - Clear cache: bench clear-cache
   ```

3. **Image File Corrupted**
   ```
   Solution:
   - Re-upload the logo
   - Try different file format (PNG → JPG)
   - Optimize and re-export image
   ```

#### **Problem: Logo Appears Distorted or Stretched**

**Solutions:**

1. **Check Source Image Dimensions**
   ```
   If your logo is not 3:4 ratio:
   - Resize to 120×160px with padding
   - Or adjust CSS to maintain aspect ratio
   ```

2. **Use Aspect-Ratio CSS**
   ```css
   .letterhead-table img {
       max-height: 120px;
       max-width: 160px;
       height: auto;
       width: auto;
       object-fit: contain;
   }
   ```

#### **Problem: Logo Too Small or Too Large**

**Solutions:**

1. **Adjust CSS Dimensions**
   ```css
   /* Make larger */
   .letterhead-table img {
       height: 200px;
       width: 150px;
   }
   
   /* Make smaller */
   .letterhead-table img {
       height: 120px;
       width: 90px;
   }
   ```

2. **Modify Container Width**
   ```css
   .letterhead-table {
       width: 35%;  /* Increase from 29% */
   }
   ```

#### **Problem: Logo Quality Poor When Printed**

**Solutions:**

1. **Use Higher Resolution Image**
   - Export logo at 300 DPI
   - Scale up source image: 240×320px (2x)
   - Use SVG format if possible

2. **Check PDF Settings**
   ```
   Print Settings → PDF Settings:
   - Resolution: 300 DPI
   - Image Quality: High
   ```

### Print Format Issues

#### **Problem: Custom Format Not Available**

**Solutions:**

1. **Refresh Format List**
   ```bash
   bench migrate
   bench clear-cache
   ```

2. **Check DocType Assignment**
   - Ensure "Doc Type" = "Sales Invoice"
   - Verify format is not disabled

#### **Problem: Changes Not Reflecting**

**Solutions:**

1. **Clear All Caches**
   ```bash
   bench clear-cache
   bench clear-website-cache
   bench restart
   ```

2. **Hard Refresh Browser**
   - Chrome/Firefox: Ctrl + Shift + R
   - Safari: Cmd + Option + R

#### **Problem: Arabic Text Shows as Boxes**

**Solutions:**

1. **Install Arabic Fonts**
   ```bash
   # On server
   sudo apt-get install fonts-arabeyes
   ```

2. **Add Font Fallbacks in CSS**
   ```css
   body {
       font-family: 'Segoe UI', 'Arial', 'Tahoma', 'Traditional Arabic', sans-serif;
   }
   ```

### QR Code Issues

#### **Problem: QR Code Not Generating**

**Solutions:**

1. **Check ZATCA Configuration**
   - Ensure company is ZATCA-registered
   - Verify certificate is active
   - Check invoice is submitted

2. **Regenerate QR Code**
   - Cancel invoice
   - Resubmit invoice
   - Check error logs

3. **Verify Field Mapping**
   ```python
   # In console
   doc = frappe.get_doc("Sales Invoice", "INV-0001")
   print(doc.ksa_einv_qr or doc.ksa_einv2_qr)
   ```

---

## Quick Reference

### Logo Specifications Summary

| Specification | Value |
|--------------|-------|
| Width | 160px |
| Height | 120px |
| Aspect Ratio | 4:3 (portrait) |
| File Format | PNG (preferred), JPG, SVG |
| Max File Size | 500 KB |
| Recommended Size | 50-200 KB |
| Resolution | 150-300 DPI |
| Background | Transparent or white |

### CSS Locations

| Element | CSS Class | Purpose |
|---------|-----------|---------|
| Logo Container | `.letterhead-table` | Controls logo area |
| Logo Image | `.letterhead-table img` | Sets logo dimensions |
| Primary Color | `--color-primary` | Main brand color |
| Header Table | `.header_table` | Invoice info section |
| Info Tables | `.info-table` | Seller/Client info |

### Key Files

```
optima_zatca/
└── optima_zatca/
    └── print_format/
        └── zatca_sales_invoice/
            ├── zatca_sales_invoice.html    ← Template
            ├── zatca_sales_invoice.css     ← Styles
            └── zatca_sales_invoice.json    ← Metadata (auto-generated)
```

---

## Additional Resources

### Related Documentation
- [PDF/A-3 Invoice — User Guide](../pdfa3/user-guide.md) — the archival PDF uses a different
  rendering engine than the print preview; fonts and the letterhead footer behave differently there
- [ZATCA Concepts & Glossary](../concepts.md)
- [Onboarding — User Guide](../onboarding/user-guide.md)
- [Certificate Management (Onboarding reference)](../onboarding/reference.md)
- [Configuration](configuration.md)

### ERPNext Official Docs
- [Print Format Guide](https://docs.erpnext.com/docs/user/manual/en/setting-up/print/custom-print-format)
- [Letter Head Setup](https://docs.erpnext.com/docs/user/manual/en/setting-up/print/letter-head)
- [Jinja Templates Reference](https://jinja.palletsprojects.com/en/3.0.x/templates/)

### Design Resources
- **Logo Optimization:** [TinyPNG](https://tinypng.com/)
- **Image Editing:** [Photopea (Free)](https://www.photopea.com/)
- **Format Conversion:** [CloudConvert](https://cloudconvert.com/)

### Community Support
- **ERPNext Forum:** [discuss.erpnext.com](https://discuss.erpnext.com/)
- **Frappe Framework:** [frappe.io/docs](https://frappe.io/docs)

---

## Support

### Need Help?

1. **Check This Documentation** - Most common issues are covered above
2. **Search Forum** - Check ERPNext Discuss for similar issues
3. **Review Logs** - Check ERPNext error logs for specific errors
4. **Contact Support** - Reach out to IT Systematic for professional assistance

### Professional Services

IT Systematic offers:
- Custom print format design
- Logo preparation and optimization
- ZATCA compliance consulting
- Training and onboarding

Contact: sales@itsystematic.com

---

**Document Version:** 1.0  
**Last Updated:** December 25, 2025  
**Maintained by:** IT Systematic - Optima ZATCA Team  
**License:** MIT
