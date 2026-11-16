import json
import pathlib
import re
from collections import Counter

CORPUS_DIR = pathlib.Path(r"d:\code\translate\work\scn_corpus")
TR_DIR = pathlib.Path(r"d:\code\translate\work\scn_translated")
UI_DIR = pathlib.Path(r"d:\code\translate\work\ui_texts")
DEC_MAIN = pathlib.Path(r"d:\code\translate\build\decoded\data\main")

TAG_RE = re.compile(r"%[^;]*;")
TC_STRICT = set(
    "這為說裡個們會來時學問國動無應將總覺聲聽話經讓該請識變過進連還選錯鏡難離頭顏風飛飯館點開關門體廣張寫對愛認氣場機歡樂從條與畫書見現觀視電腦網線結統給紅綠藍黃嗎"
    "麼誰語謝課讀維絕繼續練緣織繪藥蘇處號虧觸設計討論試詩誠詳調談謀證議護譯負責財貧貨販貫貴買費貼賀資質賴賺購賽贈贊贏趕跡車軍輕輪輸轉輝載輩辭農週進遊運達違遙遠適遲遺邊邏鄰醫釋銀銅錯錢錦鎖鎮鐘鐵長閃閉閒間陽陰陣階際隨險隱雙雖靈靜響頁頂項順須領題額願類顧顯飄飲飾餅養馬駐駕驗驚髮鬧魚鳥鳳鳴麗麥黨齊齒龍龜"
)
TW_BAD_WORDS = ["葛格", "香阪", "的說", "妳", "牠", "啥咪", "歐尼醬", "歐尼", "[CN-STUB]", "（CN）", "(CN)"]
KATAKANA_RE = re.compile(r"[\u30a1-\u30f6\u30fc]{2,}")
HIRAGANA_RE = re.compile(r"[\u3041-\u3096]{2,}")
SINGLE_KANA_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30fa]")


def extract_tags(s: str) -> list[str]:
    return TAG_RE.findall(s or "")


def check_balance(s: str) -> list[str]:
    issues = []
    pairs = [("「", "」"), ("『", "』"), ("（", "）")]
    for op, cl in pairs:
        if s.count(op) != s.count(cl):
            issues.append(f"unbalanced {op}{cl} ({s.count(op)} vs {s.count(cl)})")
    return issues


def check_scenarios():
    corpus_files = sorted(p for p in CORPUS_DIR.glob("*.json") if p.name != "_summary.json")
    print(f"=== SCENARIO QA ({len(corpus_files)} corpus files) ===")

    missing_files = []
    hard_errors = []
    warnings = []
    total_lines = 0
    total_selects = 0
    key_samples = {}

    for cpath in corpus_files:
        tpath = TR_DIR / cpath.name
        if not tpath.exists():
            missing_files.append(cpath.name)
            continue

        cobj = json.loads(cpath.read_text(encoding="utf-8"))
        tobj = json.loads(tpath.read_text(encoding="utf-8"))
        t_items = tobj.get("items", {})
        t_selects = tobj.get("selects", {})
        ret_scenes = set(tobj.get("retained_r18_scenes", []))
        ret_keys = set(tobj.get("retained_r18_keys", []))

        exp_keys = set()
        exp_sel_keys = set()

        for sc in cobj["scenes"]:
            s_idx = sc["scene_idx"]
            for it in sc["texts"]:
                key = f"{s_idx}:{it['i']}"
                exp_keys.add(key)
                total_lines += 1
                is_retained_r18 = (s_idx in ret_scenes) or (key in ret_keys)

                jp_disp = it["jp"][1] if it.get("jp") else ""
                en_disp = it["en"][1] if it.get("en") else ""
                tc_disp = it["cn"][1] if it.get("cn") else ""

                if key not in t_items:
                    hard_errors.append(f"{cpath.name} {key}: missing line")
                    continue

                tr = t_items[key]
                if not tr or not tr.strip():
                    hard_errors.append(f"{cpath.name} {key}: empty translation")
                    continue

                if "\n" in tr or "\r" in tr:
                    hard_errors.append(f"{cpath.name} {key}: contains raw newline byte")
                if "\\\\n" in tr:
                    hard_errors.append(f"{cpath.name} {key}: contains double-escaped \\\\n")

                # Tag parity against jp_disp (or tc_disp if jp had none / retained r18)
                jp_tags = extract_tags(jp_disp)
                tc_tags = extract_tags(tc_disp)
                exp_tags = tc_tags if is_retained_r18 else (jp_tags if jp_tags else tc_tags)
                got_tags = extract_tags(tr)
                if Counter(exp_tags) != Counter(got_tags):
                    hard_errors.append(
                        f"{cpath.name} {key}: tag mismatch exp={exp_tags} got={got_tags} | tr={tr!r}"
                    )

                if not is_retained_r18:
                    clean_tr = TAG_RE.sub("", tr)
                    # Strict TC characters
                    tc_hits = sorted(set(clean_tr) & TC_STRICT)
                    if tc_hits:
                        hard_errors.append(
                            f"{cpath.name} {key}: TC_STRICT chars {''.join(tc_hits)} | tr={tr!r}"
                        )

                    # Bad TW words / stubs
                    for bw in TW_BAD_WORDS:
                        if bw in clean_tr:
                            hard_errors.append(f"{cpath.name} {key}: forbidden term {bw!r} | tr={tr!r}")

                    # Any single hiragana/katakana leak
                    kana_m = SINGLE_KANA_RE.findall(clean_tr)
                    if kana_m:
                        hard_errors.append(
                            f"{cpath.name} {key}: kana leak {''.join(kana_m)} | tr={tr!r}"
                        )

                    # Unbalanced quotes
                    bal = check_balance(clean_tr)
                    if bal:
                        warnings.append(f"{cpath.name} {key}: {'; '.join(bal)} | tr={tr!r} | jp={jp_disp!r}")

                # Capture spot checks
                if cpath.name == "b18_2a.txt.json" and key == "10:90":
                    key_samples["b18_2a 10:90"] = (jp_disp, tc_disp, tr)
                if cpath.name == "b14.txt.json" and "できない" in jp_disp:
                    key_samples[f"b14 {key}"] = (jp_disp, tc_disp, tr)
                if cpath.name == "b02.txt.json" and "そうなの" in jp_disp and "？" not in jp_disp:
                    key_samples[f"b02 {key}"] = (jp_disp, tc_disp, tr)
                if cpath.name == "b10a.txt.json" and "打工" in tc_disp:
                    key_samples[f"b10a {key}"] = (jp_disp, tc_disp, tr)
                if cpath.name == "b01.txt.json" and key in ("0:0", "0:1", "1:301", "1:401"):
                    key_samples[f"b01 {key}"] = (jp_disp, tc_disp, tr)

            for sel in sc["selects"]:
                skey = f"{s_idx}:{sel['i']}"
                exp_sel_keys.add(skey)
                total_selects += 1
                if skey not in t_selects or not t_selects[skey].strip():
                    hard_errors.append(f"{cpath.name} select {skey}: missing/empty")
                else:
                    stxt = t_selects[skey]
                    tc_hits = sorted(set(stxt) & TC_STRICT)
                    if tc_hits:
                        hard_errors.append(f"{cpath.name} select {skey}: TC_STRICT {tc_hits} | {stxt!r}")
                    key_samples[f"SEL {cpath.name} {skey}"] = (
                        sel["data"].get("text", ""),
                        "",
                        stxt,
                    )

        extra_keys = set(t_items.keys()) - exp_keys
        if extra_keys:
            hard_errors.append(f"{cpath.name}: {len(extra_keys)} extra item keys")
        extra_sels = set(t_selects.keys()) - exp_sel_keys
        if extra_sels:
            hard_errors.append(f"{cpath.name}: {len(extra_sels)} extra select keys")

    print(f"Translated files present: {len(corpus_files) - len(missing_files)}/{len(corpus_files)}")
    if missing_files:
        print(f"Missing files ({len(missing_files)}): {missing_files}")
    print(f"Checked lines: {total_lines}, selects: {total_selects}")
    print(f"Hard errors: {len(hard_errors)}")
    for e in hard_errors[:60]:
        print("  [ERR]", e)
    if len(hard_errors) > 60:
        print(f"  ... and {len(hard_errors) - 60} more hard errors")

    print(f"Warnings: {len(warnings)}")
    for w in warnings[:40]:
        print("  [WARN]", w)
    if len(warnings) > 40:
        print(f"  ... and {len(warnings) - 40} more warnings")

    print("=== SPOT CHECKS ===")
    for k, (jp, tc, tr) in sorted(key_samples.items()):
        print(f"  {k}:")
        print(f"    JP: {jp}")
        if tc:
            print(f"    TC: {tc}")
        print(f"    SC: {tr}")

    return len(missing_files) == 0 and len(hard_errors) == 0


def parse_ini_keys(text: str) -> list[str]:
    keys = []
    sec = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            sec = line[1:-1].strip()
        elif "=" in line:
            k = line.split("=", 1)[0].strip()
            keys.append(f"{sec}.{k}")
    return keys


def check_ui_texts():
    print("\n=== UI TEXTS QA ===")
    expected = [
        "syslangtext_cn.ini",
        "syslangtext_jp.ini",
        "syslangtext_en.ini",
        "help_conf_cn.txt",
        "help_exch_cn.txt",
    ]
    ok = True
    for fn in expected:
        p = UI_DIR / fn
        if not p.exists():
            print(f"  [MISSING] {p}")
            ok = False
            continue
        txt = p.read_text(encoding="utf-8")
        stubs = [m for m in ("[CN-STUB]", "（CN）", "(CN)", "（JP）", "(EN)") if m in txt]
        if stubs:
            print(f"  [ERR] {fn}: contains stub markers {stubs}")
            ok = False
        if fn.endswith(".ini"):
            orig_path = DEC_MAIN / fn
            orig_keys = parse_ini_keys(orig_path.read_text(encoding="utf-8"))
            new_keys = parse_ini_keys(txt)
            if set(orig_keys) != set(new_keys):
                print(
                    f"  [ERR] {fn}: key mismatch missing={sorted(set(orig_keys)-set(new_keys))} extra={sorted(set(new_keys)-set(orig_keys))}"
                )
                ok = False
            else:
                print(f"  [OK] {fn}: {len(new_keys)} INI keys match original")
        else:
            print(f"  [OK] {fn}: {len(txt.splitlines())} lines")

        if fn.endswith("_cn.ini") or fn.endswith("_cn.txt"):
            hits = []
            for ln_no, line in enumerate(txt.splitlines(), 1):
                s = line.strip()
                if not s or s.startswith("#") or s.startswith(";") or s.startswith("!section"):
                    continue
                if line.startswith("textLanguageMenuItem_jp") or line.startswith("subLanguageMenuItem_jp"):
                    continue
                if fn.endswith(".ini"):
                    parts = re.split(r"\t+|=", s, maxsplit=1)
                    val = parts[1].strip() if len(parts) > 1 else ""
                else:
                    if not line[0].isspace():
                        # Key header line in help_*.txt
                        continue
                    val = s
                tc_hits = sorted(set(val) & TC_STRICT)
                if tc_hits:
                    hits.append((ln_no, "".join(tc_hits), line))
            if hits:
                print(f"  [ERR/TC] {fn}: {len(hits)} value lines with TC_STRICT chars:")
                for ln_no, chars, line in hits[:20]:
                    print(f"    L{ln_no} [{chars}]: {line}")
                ok = False
            else:
                print(f"  [OK] {fn}: 0 TC_STRICT chars in values")
    return ok


if __name__ == "__main__":
    scn_ok = check_scenarios()
    ui_ok = check_ui_texts()
    print(f"\nQA SUMMARY: scn_ok={scn_ok}, ui_ok={ui_ok}")
