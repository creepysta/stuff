def compute(ldg: list[list], splits: int | None = None, ratio: float | None = None):
    ratio = ratio or 1.0; assert 0 < ratio <= 1.0, f"ratio must be between 0 and 1"
    splits = splits or len(ldg); assert splits <= len(ldg), f"splits cannot be more than known people"
    total_ph, total_all, mean = (
            [sum(l) for l in ldg],
            sum(sum(l) for l in ldg),
            (sum(sum(l) for l in ldg) / splits) * ratio,
        )
    diff = [mean - x for x in total_ph]
    pos, neg = (
            sorted([list(x) for x in enumerate(diff) if x[1] > 0], key=lambda x: x[1], reverse=True),
            sorted([list(x) for x in enumerate(diff) if x[1] < 0], key=lambda x: x[1], reverse=True),
        )
    print("[debug] givers, takers: ", pos, neg)
    # ?? give the biggest pos to lowest neg (greedy) 
    i, j, ans = 0, 0, []
    while i < len(pos):
        p, n = pos[i], neg[j]; diff = p[1] - abs(n[1])
        ans.append((p[0], n[0], abs(n[1]) if diff >= 0.0 else p[1] ))
        i, j = i + 1 if diff < 0.0 else i, j + 1 if diff >= 0.0 else j
        p[1] = max(p[1] - abs(n[1]), 0)

    return ans



ledger = [[21, 10], [31, 41, 11], [47], [31, 33]]
# ledger = [[21, 10], [31, 41, 11], [47]]
print(compute(ledger))
