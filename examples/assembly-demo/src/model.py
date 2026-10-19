"""Generic calibration blocks for assembly and clearance validation."""
from build123d import Align, Box


def build(params):
    p = params['demo']
    return {
        'datum_block': Box(*p['block_mm'], align=(Align.CENTER, Align.CENTER, Align.CENTER)),
        'slider': Box(*p['slider_mm'], align=(Align.CENTER, Align.CENTER, Align.CENTER)),
    }
