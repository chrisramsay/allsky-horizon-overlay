# indi-allsky config changes - edit values here, then run ./apply_config.sh
# Each line sets one key; nested keys use dots. Keys not listed are untouched.
# Re-applying is safe: lines that already match produce no change.

# --- Image geometry ---------------------------------------------------------
# Crop is in final (already flipped) image coordinates; all values must be even.
# Circle centre in the uncropped frame ~ (1732, 1824), diameter ~3316.
  .IMAGE_CROP_ROI         = [4, 96, 3460, 3552]
| .IMAGE_BORDER.TOP       = 80
| .IMAGE_BORDER.LEFT      = 80
| .IMAGE_BORDER.RIGHT     = 80
| .IMAGE_BORDER.BOTTOM    = 80
| .LENS_IMAGE_CIRCLE      = 3316
| .LENS_OFFSET_X          = 0
| .LENS_OFFSET_Y          = 0
| .CARDINAL_DIRS.DIAMETER = 3316

# --- Black out the unlit sensor corners to match the border -----------------
| .IMAGE_CIRCLE_MASK.ENABLE   = true
| .IMAGE_CIRCLE_MASK.DIAMETER = 3330
| .IMAGE_CIRCLE_MASK.OFFSET_X = 0
| .IMAGE_CIRCLE_MASK.OFFSET_Y = 0
| .IMAGE_CIRCLE_MASK.BLUR     = 35

# --- Horizon overlay ---------------------------------------------------------
| .LOGO_OVERLAY = "/var/lib/indi-allsky/horizon_overlay.png"
