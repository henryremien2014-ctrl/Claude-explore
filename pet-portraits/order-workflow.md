# Order workflow

Target: about 10–15 minutes of your time per order.

## Getting photos to Claude

This cloud environment can't reach Google Drive or Higgsfield files directly,
but Claude can use anything uploaded to your Higgsfield account.

1. Save the buyer's photo, or your own sample photos.
2. Upload it to your Higgsfield account (web or app, in your uploads/assets).
   Name it with the order number and pet name if you can, e.g. `1234-bella`.
3. Tell Claude: *"New order 1234: Bella, dog, Royal style, Living Portrait, send 2 drafts."*

Backup: share the photo from Google Drive as "Anyone with the link", paste the
link, and Claude will import it into Higgsfield.

## Steps

| # | Who | Step |
|---|---|---|
| 1 | Etsy | Order arrives as an open made-to-order digital order |
| 2 | You | Send message template A (if the buyer hasn't already sent photos) |
| 3 | You | Upload the buyer's photos to Higgsfield and tell Claude the order details |
| 4 | Claude | Generate 2 drafts at 2k in the chosen style |
| 5 | You | Pick the best draft using the checklist in `styles.md` (2 min) |
| 6 | Claude | Render the final 4:5 at 4k plus the 9:16 wallpaper; for Living Portrait orders, animate the 9:16 |
| 7 | You | Download the files from Higgsfield, open the order in Etsy → *Complete order* → upload the files |
| 8 | You | Send message template C (delivery + ask to share on TikTok) |
| 9 | Claude | Log the order, style and credits used in `orders.csv` |

## Message templates

**A — After purchase (ask for photos)**

```
Hi {name}! Thank you so much for your order. 🐾 I can't wait to create
{pet}'s portrait.

Please reply with 1–3 clear photos of {pet}: bright light, face clearly
visible, and showing their markings. If there's anything special about their
look (a floppy ear, a white patch), let me know!

I'll have it ready within {1–3 business days | 24 hours}.
```

**B — Revision received**

```
Thanks for letting me know! I'll fix that and send the updated portrait
within 24 hours.
```

**C — Delivery**

```
{pet}'s portrait is ready! 🎉 You'll find your files in your Etsy account
under Purchases. Includes a print-ready file (fits 8×10, 11×14 and 16×20
frames) and a phone wallpaper{, plus your Living Portrait video}.

If anything doesn't look quite like {pet}, just reply and I'll fix it.

One small question: would you be OK with me sharing {pet}'s portrait on my
TikTok? Totally fine to say no!
```

Etsy does not allow asking for reviews in exchange for anything (discounts,
freebies). Leave it to Etsy's own automatic review request.

## Sample photos checklist (for your first samples)

- 5–10 photos of the same pet; 2–3 different pets is even better
- At least one clear, front-facing shot in daylight
- One shot that shows the markings clearly
- Permission from the owner if the pet isn't yours

## Later automation (week 3+)

Once orders are regular, Claude can check Higgsfield on a schedule for new
uploads named with an order number, generate the drafts automatically, and
have them waiting for your review. That leaves you only steps 5, 7 and 8.
