"""Regenerate the balitech provider models block in kilo.jsonc.

Pricing comes from /v3/catalog's `multiplier`, not `price_per_1m`: the
quota drain measured against /v3/balance is

    drain = (prompt_tokens / 2 + completion_tokens) * multiplier

so input is half-weight. That maps 1:1 onto Kilo's cost.input/cost.output.
Model metadata (limits, modalities, reasoning efforts) comes from models.dev,
resolved by catalog `family` -> owning provider.

Usage: resolve_balitech.py [--write] [--no-probe] [model-id ...]
  --write     patch ~/.config/kilo/kilo.jsonc in place
  --no-probe  skip the 403 availability probe (keeps gated models)
  model-id... restrict output to these ids (default: all resolvable)
"""
import json, os, re, sys, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

HOME = os.path.expanduser('~')
CONFIG = f'{HOME}/.config/kilo/kilo.jsonc'
AUTH = f'{HOME}/.local/share/kilo/auth.json'
BASE = 'https://balitechsolution.com/v3'
MD_URL = 'https://models.dev/api.json'

# Rp 3,500 / 12M credits = cheapest published a-la-carte rate; volume tiers run
# ~8x cheaper, so absolute USD here is order-of-magnitude only. Rank order is
# exact. ponytail: pin the tier you are actually billed at if it starts to matter.
K_IDR = 3500 / 12e6
FX_IDR_USD = float(os.environ.get('BT_FX', 18090.29))

FAMILY = {
    'anthropic': ['anthropic'], 'deepseek': ['deepseek', 'azure-cognitive-services'],
    'glm': ['zhipuai'], 'google': ['google'], 'openai': ['openai'], 'xai': ['xai'],
    'kimi': ['moonshotai'], 'minimax': ['minimax'], 'qwen': ['alibaba', 'hyper'],
    'mimo': ['xiaomi'],
}
REASONING_OK = ('none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max')

# models.dev entries for these disagree with balitech's own published spec
# (site + /v3/catalog), usually because the only resolvable entry is a reseller's.
LIMIT_OVERRIDE = {
    'bt/deepseek-v4.1-flash': {'context': 1048576, 'output': 393216},  # 1.05M / 393K per balitech
}


def get(url, key=None, timeout=90):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {key}'} if key else {
        'User-Agent': 'Mozilla/5.0'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def probe(model, key):
    """Only 403 (model_not_allowed) excludes a model.

    503 is transient upstream noise and a timeout means the model is reachable but
    slow, so neither retries nor counts against it; retrying turned a 30-model run
    into 5+ minutes for no extra signal.
    """
    req = urllib.request.Request(
        f'{BASE}/chat/completions',
        data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'hi'}],
                         'max_tokens': 1}).encode(),
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    try:
        urllib.request.urlopen(req, timeout=20).read()
        return 200
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 503


def probe_all(models, key):
    """Probe concurrently: upstream latency dominates (~20s/call), not retries."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(models, pool.map(lambda m: probe(m, key), models)))


def norm(s):
    return re.sub(r'[^a-z0-9.]', '', s.lower())


def loose(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def build_index(md):
    idx = []
    for pid, p in md.items():
        for mid, m in p.get('models', {}).items():
            idx.append((pid, mid, m))
    return idx


def resolve(idx, slug, family):
    """Rank: exact id > owner's own canonical > foreign canonical > substring.

    Resellers republish the owner's canonical_model_id, so the owner's entry must
    beat a reseller's identical metadata; and an exact id must beat a variant whose
    canonical merely points at it (glm-5.3-flashx -> zhipuai/glm-5.3-flash).
    """
    provs = FAMILY.get(family, [])
    base = loose(slug)
    best, best_key = None, (-1, -1)
    for pid, mid, m in idx:
        if pid not in provs:
            continue
        cid = m.get('canonical_model_id', '')
        canon_prov, canon = cid.split('/')[0], loose(cid.split('/')[-1])
        if loose(mid.split('/')[-1]) == base:
            tier = 4
        elif canon == base and canon_prov == pid:
            tier = 3
        elif canon_prov == pid and canon.startswith(base):  # owner's dated revision
            tier = 2
        elif canon == base:
            tier = 1
        elif base and base in loose(mid):
            tier = 0
        else:
            continue
        key = (tier, 1 if pid == provs[0] else 0)
        if key > best_key:
            best, best_key = (pid, mid, m), key
    if best:
        return best
    # canonical id may live under a provider not in FAMILY (e.g. anthropic/claude-opus-5-5)
    for pid, mid, m in idx:
        cid = m.get('canonical_model_id', '')
        if cid and loose(cid.split('/')[-1]) == base and loose(cid.split('/')[0]) == loose(pid):
            return (pid, mid, m)
    return None


def entry(model, meta):
    x = float(model['multiplier'])
    cfg = {
        'name': model['id'],
        'tool_call': meta.get('tool_call', True),
        'reasoning': bool(meta.get('reasoning')),
        'temperature': meta.get('temperature', True),
        'cost': {'output': round(x * K_IDR / FX_IDR_USD * 1e6, 6)},
    }
    lim = {k: v for k, v in (('context', meta.get('limit', {}).get('context')),
                             ('input', meta.get('limit', {}).get('input')),
                             ('output', meta.get('limit', {}).get('output'))) if v}
    lim.update(LIMIT_OVERRIDE.get(model['id'], {}))
    lim = {k: lim[k] for k in ('context', 'input', 'output') if k in lim}
    if lim:
        cfg['limit'] = lim
    mod = meta.get('modalities') or {}
    cfg['modalities'] = {'input': mod.get('input') or ['text'],
                         'output': mod.get('output') or ['text']}
    if meta.get('attachment') and any(m in cfg['modalities']['input'] for m in
                                      ('image', 'audio', 'video', 'pdf')):
        cfg['attachment'] = True
    efforts = next((o['values'] for o in (meta.get('reasoning_options') or [])
                    if o.get('type') == 'effort'), None)
    if efforts:
        cfg['variants'] = {e: {'reasoningEffort': e} for e in efforts if e in REASONING_OK}
    return cfg


def render(out):
    """Emit the models block in the same compact style as the rest of kilo.jsonc."""
    lines = ['      "models": {']
    for bid, cfg in out.items():
        lines.append(f'        {json.dumps(bid)}: {{')
        lines.append(f'          "name": {json.dumps(cfg["name"])},')
        lines.append(f'          "tool_call": {json.dumps(cfg["tool_call"])},')
        lines.append(f'          "reasoning": {json.dumps(cfg["reasoning"])},')
        lines.append(f'          "temperature": {json.dumps(cfg["temperature"])},')
        if cfg.get('cost'):
            c = cfg['cost']
            lines.append(f'          "cost": {{ "input": {round(c["output"] / 2, 6)}, '
                         f'"output": {c["output"]} }},')
        lim = ', '.join(f'"{k}": {v}' for k, v in cfg['limit'].items())
        lines.append(f'          "limit": {{ {lim} }},')
        mods = ', '.join(json.dumps(m) for m in cfg['modalities']['input'])
        outs = ', '.join(json.dumps(m) for m in cfg['modalities']['output'])
        lines.append('          "modalities": {')
        lines.append(f'            "input": [{mods}],')
        lines.append(f'            "output": [{outs}],')
        lines.append('          },')
        if cfg.get('attachment'):
            lines.append('          "attachment": true,')
        if cfg.get('variants'):
            lines.append('          "variants": {')
            for e in cfg['variants']:
                lines.append(f'            {json.dumps(e)}: {{ "reasoningEffort": {json.dumps(e)} }},')
            lines.append('          },')
        lines.append('        },')
    lines.append('      },')
    return '\n'.join(lines)


def read_models():
    """Parse the current models block out of kilo.jsonc (JSONC: strip comments)."""
    txt = open(CONFIG).read()
    body = re.search(r'      "models": \{(.*?)\n      \},', txt, re.S)
    if not body:
        return {}
    raw = re.sub(r'(?m)^\s*//.*$', '', body.group(1))
    text = '{' + raw + '}'
    return json.loads(re.sub(r',(\s*[}\]])', r'\1', text))


def patch_config(out):
    txt = open(CONFIG).read()
    block = render(out)
    patched, n = re.subn(r'      "models": \{.*?\n      \},', lambda _: block, txt, count=1, flags=re.S)
    if n != 1:
        sys.exit('could not locate the balitech models block in kilo.jsonc')
    # keep one generation back so a bad catalog read is recoverable; kept outside
    # ~/.config/kilo so chezmoi (which manages this dir) does not sweep it up
    with open('/tmp/kilo.jsonc.bak', 'w') as f:
        f.write(txt)
    open(CONFIG, 'w').write(patched)


def diff_report(before, after, reasons=None):
    """What changed in the block, so a run needs no eyeballing.

    `reasons` maps a removed id to why, which separates real upstream deprecation
    from a metadata miss on our side.
    """
    reasons = reasons or {}
    added = sorted(set(after) - set(before))
    removed = [f'{bid}  ({reasons[bid]})' if bid in reasons else bid
               for bid in sorted(set(before) - set(after))]
    changed = []
    for bid in sorted(set(before) & set(after)):
        old, new = before[bid], after[bid]
        fields = []
        for key in ('limit', 'variants', 'modalities', 'temperature', 'reasoning'):
            if old.get(key) != new.get(key):
                fields.append(key)
        # cost is stored as input+output but generated as output only
        if old.get('cost', {}).get('output') != new.get('cost', {}).get('output'):
            fields.append('cost')
        if fields:
            detail = ''
            if 'cost' in fields:
                detail = (f' ({old["cost"]["output"]:.4f} -> {new["cost"]["output"]:.4f})'
                          if old.get('cost') and new.get('cost') else '')
            changed.append(f'{bid}: {", ".join(fields)}{detail}')
    for label, rows in (('ADDED', added), ('REMOVED', removed), ('CHANGED', changed)):
        for row in rows:
            print(f'  {label:<7} {row}')


def main():
    args = sys.argv[1:]
    write = '--write' in args
    do_probe = '--no-probe' not in args
    only = [a for a in args if not a.startswith('--')]

    key = json.load(open(AUTH))['balitech']['key']
    catalog = get(f'{BASE}/catalog', key)['data']
    md = get(MD_URL)
    idx = build_index(md)

    out, skipped, reasons = {}, [], {}
    resolved = {}
    for model in sorted(catalog, key=lambda m: float(m['multiplier'])):
        if only and model['id'] not in only:
            continue
        r = resolve(idx, model['slug'], model['family'])
        if r:
            resolved[model['id']] = (model, r[2])
        else:
            skipped.append((model['id'], 'no models.dev metadata'))
            reasons[model['id']] = 'no models.dev metadata'

    gate = probe_all(list(resolved), key) if do_probe else {}
    for bid, (model, meta) in resolved.items():
        if gate.get(bid) == 403:
            skipped.append((bid, '403 model_not_allowed'))
            reasons[bid] = '403 model_not_allowed'
            continue
        out[bid] = entry(model, meta)

    json.dump(out, open('/tmp/bt_config.json', 'w'), indent=1)
    print(f'{len(out)} models')
    for bid, why in skipped:
        print(f'  skipped {bid}: {why}')

    before = read_models()
    if only:
        # refresh the named entries; a 403 or a vanished catalog id is an explicit
        # drop, since the user named it, not a reason to keep a stale entry
        in_catalog = {m['id'] for m in catalog}
        for bid in only:
            if bid not in in_catalog:
                reasons[bid] = 'not in /v3/catalog'
        merged = {k: v for k, v in before.items() if not (k in only and k in reasons)}
        merged.update(out)
        for bid in before:
            if bid not in merged:
                reasons.setdefault(bid, 'deprecated upstream')
    else:
        merged = out
        known = {m['id'] for m in catalog}
        for bid in before:
            reasons.setdefault(bid, 'deprecated upstream' if bid not in known
                               else 'excluded on this run')
    diff_report(before, merged, reasons)
    if write:
        patch_config(merged)
        print(f'patched {CONFIG} ({len(merged)} models)')
    else:
        print('(dry run; pass --write to apply)')


if __name__ == '__main__':
    main()