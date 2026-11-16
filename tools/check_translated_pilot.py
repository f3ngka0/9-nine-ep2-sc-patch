import json, pathlib

TC_ONLY = set(
    "這為說裡個們會來時學問國動無應將總覺聲聽話經讓該請識變過進連還選錯鏡難離頭顏風飛飯館點開關門體廣東張實寫對愛認氣場機歡樂從條與畫書見現觀視電腦網線結統給紅綠藍數據報紙讀語言詞義際專業產品品質問題解決設計製造驗證測試區別狀態勢號碼標準確遺留殘餘譯繁簡嗎"
)
# Exclude '黑' (shared SC/TC!), '黃' (TC only, '黄' is SC)
TC_ONLY.discard("黑")
TC_ONLY.add("黃")

tr_dir = pathlib.Path(r"d:\code\translate\work\scn_translated")
for p in sorted(tr_dir.glob("*.json")):
    obj = json.loads(p.read_text(encoding="utf-8"))
    fixed = 0
    tc_hits = []
    unbal = []
    for k, v in list(obj["items"].items()):
        orig = v
        v = v.replace("\r\n", "\n").replace("\n", "\\n")
        while "\\\\n" in v:
            v = v.replace("\\\\n", "\\n")
        if v != orig:
            obj["items"][k] = v
            fixed += 1
        # Check unambiguous TC chars (outside %...; tags)
        clean = v
        found = [c for c in clean if c in TC_ONLY]
        if found:
            tc_hits.append((k, "".join(found), v))
        if clean.count("「") != clean.count("」"):
            unbal.append((k, v))
    if fixed:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{p.name}: total={len(obj['items'])}, fixed_escapes={fixed}, tc_hits={len(tc_hits)}, unbal_quotes={len(unbal)}")
    for h in tc_hits[:5]:
        print("  TC HIT:", h)
    for u in unbal[:5]:
        print("  UNBAL:", u)
