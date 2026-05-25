import sys
sys.path.insert(0, '/home/volumio/rpi-rgb-led-matrix/bindings/python')

from rgbmatrix import RGBMatrix, RGBMatrixOptions

opts = RGBMatrixOptions()
opts.rows = 64
opts.cols = 64
opts.gpio_slowdown = 2
opts.hardware_mapping = 'regular'
opts.disable_hardware_pulsing = True
opts.pixel_mapper_config = 'Rotate:270'
# No led_rgb_sequence — seengreat wiring corrects GBR in hardware

matrix = RGBMatrix(options=opts)
canvas = matrix.CreateFrameCanvas()

canvas.SetPixel(0,  0,  255, 0,   0)    # top-left     = RED
canvas.SetPixel(63, 0,  0,   255, 0)    # top-right    = GREEN
canvas.SetPixel(0,  63, 0,   0,   255)  # bottom-left  = BLUE
canvas.SetPixel(63, 63, 255, 255, 0)    # bottom-right = YELLOW

matrix.SwapOnVSync(canvas)
input("Should be: RED top-left, GREEN top-right, BLUE bottom-left, YELLOW bottom-right. Press Enter.")
matrix.Clear()
