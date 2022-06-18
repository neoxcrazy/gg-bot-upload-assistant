raw_name= "Evangelion.2.0.You.Can.(Not).Advance.2009.1080p.BluRay.Dual-Audio.Do-Vi.TrueHD.6.1.10bit.x265-RG.mkv"


hdr_hybrid_remux_keyword_search = str(raw_name).lower().replace(" ", ".").replace("-", ".").split(".")

print(hdr_hybrid_remux_keyword_search)

for word in hdr_hybrid_remux_keyword_search:
    if any(x == str(word) for x in ['dv', 'dovi', 'do-vi']):
        print(word)

    if any(x == str(word) for x in ['dv', 'dovi']) or all(x == str(word) for x in ['do', 'vi']):
        print("new" + word)

if 'do'in hdr_hybrid_remux_keyword_search and 'vi' in hdr_hybrid_remux_keyword_search:
    print("Do-Vi Matched")