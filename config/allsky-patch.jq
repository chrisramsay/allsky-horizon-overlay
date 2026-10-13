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

# --- Camera / INDI -----------------------------------------------------------
# Driver resets bandwidth to AUTO (80) on connect; pin it.
| .INDI_CONFIG_DEFAULTS.PROPERTIES.CCD_CONTROLS.BandWidth = 40

# --- Text labels ---------------------------------------------------------------
| .TEXT_PROPERTIES.PIL_FONT_CUSTOM = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# --- Exposure targets ---------------------------------------------------------
| .TARGET_ADU         = 70
| .TARGET_ADU_DAY     = 80
| .TARGET_ADU_DEV     = 10
| .TARGET_ADU_DEV_DAY = 10

# --- White balance --------------------------------------------------------------
| .WBR_FACTOR     = 1.16 | .WBG_FACTOR     = 1.0 | .WBB_FACTOR     = 1.15
| .WBR_FACTOR_DAY = 1.28 | .WBG_FACTOR_DAY = 1.0 | .WBB_FACTOR_DAY = 0.98
| .WBR_MTF_MIDTONES     = 0.5 | .WBG_MTF_MIDTONES     = 0.51 | .WBB_MTF_MIDTONES     = 0.5
| .WBR_MTF_MIDTONES_DAY = 0.5 | .WBG_MTF_MIDTONES_DAY = 0.5  | .WBB_MTF_MIDTONES_DAY = 0.5
| .AUTO_WB = false | .AUTO_WB_DAY = false
| .SCNR_ALGORITHM = "" | .SCNR_ALGORITHM_DAY = ""

# --- Stretch: MTF mode 2, day and night ---------------------------------------
| .IMAGE_STRETCH.CLASSNAME        = "mode2_mtf"
| .IMAGE_STRETCH.MODE2_SHADOWS    = 0.03
| .IMAGE_STRETCH.MODE2_MIDTONES   = 0.4
| .IMAGE_STRETCH.MODE2_HIGHLIGHTS = 1.0
| .IMAGE_STRETCH.DAYTIME          = true

# --- Contrast: CLAHE at night only ----------------------------------------------
| .NIGHT_CONTRAST_ENHANCE   = true
| .DAYTIME_CONTRAST_ENHANCE = false
| .CLAHE_CLIPLIMIT          = 0.5
| .CLAHE_GRIDSIZE           = 8

# --- Tone, colour, sharpness ------------------------------------------------------
| .GAMMA_CORRECTION  = 0.87 | .GAMMA_CORRECTION_DAY  = 1.565
| .SATURATION_FACTOR = 1.1  | .SATURATION_FACTOR_DAY = 1.3
| .SHARPEN_AMOUNT    = 0.2  | .SHARPEN_AMOUNT_DAY    = 0.75

# --- Noise reduction: wavelet at night (slow - watch "Image processed in") --------
| .IMAGE_DENOISE          = "wavelet"
| .IMAGE_DENOISE_STRENGTH = 2
| .IMAGE_DENOISE_DAY      = ""


# --- Detection / brightness mask (from detection_mask.py) ----------------------
# Uncomment after copying detection_mask.png into place:
# | .DETECT_MASK = "/var/lib/indi-allsky/detection_mask.png"
| .DETECT_MASK = "/var/lib/indi-allsky/detection_mask.png"

