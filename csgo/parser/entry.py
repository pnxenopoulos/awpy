from ctypes import *
import os


lib = PyDLL('parse_demo_go')

__go_parse_demo = lib.parse_demo
__go_parse_demo.argtypes = [
    c_char_p, # char* demPath
    POINTER(c_int), # GoInt* parseRate
    POINTER(c_uint8), # GoUint8* parseFrames
    POINTER(c_int64), # GoInt64* tradeTime
    c_char_p, # char* roundBuy
    POINTER(c_bool), # GoUint8* damgesRolled
    c_char_p, # char* demoID
    POINTER(c_bool), # GoUint8* jsonIndentation
    c_char_p # char* outpath
]
__go_parse_demo.restype = None


def parse_demo(
    demo_path,
    parse_rate,
    parse_frames,
    trade_time,
    round_buy,
    damages_rolled,
    demo_id,
    json_indentation,
    outpath
):
    __go_parse_demo(
        c_char_p(demo_path.encode()),
        byref(c_int(parse_rate)),
        byref(c_uint8(parse_frames)),
        byref(c_long(trade_time)),
        c_char_p(round_buy.encode()),
        byref(c_bool(damages_rolled)),
        c_char_p(demo_id.encode()),
        byref(c_bool(json_indentation)),
        c_char_p(outpath.encode())
    )

    return

# ./parse_demo -demo /mnt/workspace/csgo:scrim:a5ten9mb.dem -parserate 16 -tradetime 5 -buystyle csgo -demoid csgo:scrim:a5ten9mb -out /mnt/workspace --parseframes

if __name__ == "__main__":
    parse_demo(
        '../../test1eg.dem',
        16,
        True,
        5,
        "csgo",
        False,
        "csgo:scrim:a5ten9mb",
        False,
        "../../"
    )
