import pathlib
import sys
from PIL import Image

sys.path.insert(0, r"d:\code\translate\tools")
import psb
import tlg

EXT_UIPSD = pathlib.Path(r"d:\code\translate\build\extracted\data\uipsd")
OUT_DIR = pathlib.Path(r"d:\code\translate\work\ui_previews")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def composite_pimg(pimg_path: pathlib.Path, out_png: pathlib.Path, save_layers_dir: pathlib.Path | None = None):
    p = psb.PsbFile.parse(pimg_path.read_bytes())
    w = p.root.get("width", 1280)
    h = p.root.get("height", 720)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layers = p.root.get("layers", [])
    # PSB layers are listed top-to-bottom or bottom-to-top? Let's draw in reverse AND check.
    # Actually let's sort/paste in reverse order (bottom to top) or check layer_id order; also save individual layers if requested.
    for lay in reversed(layers):
        lid = lay.get("layer_id", -1)
        if lid < 0:
            continue
        key = f"{lid}.tlg"
        res = p.root.get(key)
        if not isinstance(res, psb.PsbResource):
            continue
        im = tlg.decode_tlg5(p.chunks[res.index])
        if save_layers_dir is not None:
            save_layers_dir.mkdir(parents=True, exist_ok=True)
            safe_name = lay.get("name", str(lid)).replace("/", "_").replace(":", "_").replace("*", "_")
            im.save(save_layers_dir / f"{lid:03d}_{safe_name}.png")
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        # Composite onto canvas even if visible==0? Wait: only visible==1 for composite, or draw onto checkerboard
        if lay.get("visible", 1):
            x = int(lay.get("left", 0))
            y = int(lay.get("top", 0))
            op = int(lay.get("opacity", 255))
            if op < 255:
                r, g, b, a = im.split()
                a = a.point(lambda v: (v * op) // 255)
                im = Image.merge("RGBA", (r, g, b, a))
            canvas.alpha_composite(im, (x, y))
    canvas.save(out_png)
    return p


def main():
    # 1. Test TLG5 encode->decode roundtrip on conf_lang.pimg chunks
    p_cl = psb.PsbFile.parse((EXT_UIPSD / "conf_lang.pimg").read_bytes())
    rt_ok = 0
    for c in p_cl.chunks:
        im1 = tlg.decode_tlg5(c)
        enc = tlg.encode_tlg5(im1)
        im2 = tlg.decode_tlg5(enc)
        assert im1.mode == im2.mode and im1.size == im2.size and im1.tobytes() == im2.tobytes()
        rt_ok += 1
    print(f"conf_lang.pimg TLG5 encode->decode pixel-exact roundtrip: {rt_ok}/{len(p_cl.chunks)}")

    # 2. Export all conf_lang, cn/*.pimg, and key root *.pimg composites + conf_lang & dialog_cn individual layers
    targets = [EXT_UIPSD / "conf_lang.pimg"] + sorted((EXT_UIPSD / "cn").glob("*.pimg")) + [
        EXT_UIPSD / "title.pimg",
        EXT_UIPSD / "extra.pimg",
        EXT_UIPSD / "file.pimg",
        EXT_UIPSD / "file_load.pimg",
        EXT_UIPSD / "file_save.pimg",
        EXT_UIPSD / "conf.pimg",
        EXT_UIPSD / "conf_mask.pimg",
        EXT_UIPSD / "dialog.pimg",
        EXT_UIPSD / "ezsave.pimg",
        EXT_UIPSD / "bgmtitle.pimg",
        EXT_UIPSD / "qlpopup.pimg",
        EXT_UIPSD / "backlog.pimg",
        EXT_UIPSD / "message.pimg",
    ]
    for pimg in targets:
        rel = pimg.relative_to(EXT_UIPSD)
        out_png = OUT_DIR / f"{str(rel).replace('\\', '_').replace('/', '_')}.png"
        layers_dir = None
        if rel.name in ("conf_lang.pimg", "dialog_cn.pimg", "9_voicedialog_cn.pimg", "conf_cn.pimg"):
            layers_dir = OUT_DIR / "layers" / rel.stem
        composite_pimg(pimg, out_png, layers_dir)
    print(f"Exported {len(targets)} UI composite PNGs to {OUT_DIR}")


if __name__ == "__main__":
    main()
