# build_one.py
import importlib, sys, inspect

slug = sys.argv[1] if len(sys.argv) > 1 else None
mode = (sys.argv[2] if len(sys.argv) > 2 else "flashcards").lower()

if not slug:
    print("Usage: python build_one.py <slug> [mode]")
    sys.exit(2)

def log(msg): print(msg, flush=True)

# 0) Prefer the single entry point if available
def try_sets_utils(slug, mode):
    try:
        su = importlib.import_module("app.sets_utils")
    except Exception as e:
        log(f"! import app.sets_utils failed: {e}")
        return False

    regen = getattr(su, "regenerate_set_pages", None)
    if not regen:
        log("! sets_utils.regenerate_set_pages not found")
        return False

    trials = [
        {"modes":[mode], "force": True, "verbose": True},
        {"modes":[mode], "force": True},
        {"force": True, "verbose": True},
        {"force": True},
        {},  # plain (slug)
    ]
    for kwargs in trials:
        try:
            log(f"→ sets_utils.regenerate_set_pages({slug!r}, {kwargs})")
            regen(slug, **kwargs)
            log("✓ sets_utils.regenerate_set_pages OK")
            return True
        except TypeError as e:
            log(f"· signature mismatch: {e}")
            continue
        except Exception as e:
            log(f"! regenerate failed: {e}")
            return False
    return False

def try_module(mod, funcs):
    try:
        m = importlib.import_module(f"app.{mod}")
    except Exception as e:
        log(f"! import app.{mod} failed: {e}")
        return False

    # Helpful: show available callables that look relevant
    cand = [a for a in dir(m) if any(k in a.lower() for k in ("page","gen","build","listen","flash","main"))]
    log(f"• app.{mod} candidates: {cand}")

    for fn in funcs:
        f = getattr(m, fn, None)
        if not f: 
            continue
        # Try simple, then with force=True
        for call in [((), {}), ((slug,), {}), ((slug,), {"force": True})]:
            args, kwargs = call
            if not args:  # first attempt: maybe the fn reads slug globally
                try:
                    log(f"→ {mod}.{fn}()")
                    f()
                    log(f"✓ {mod}.{fn}() OK")
                    return True
                except TypeError:
                    continue
                except Exception as e:
                    log(f"! {mod}.{fn}() failed: {e}")
                    break
            else:
                try:
                    log(f"→ {mod}.{fn}({slug!r}, {kwargs})")
                    f(*args, **kwargs)
                    log(f"✓ {mod}.{fn} OK")
                    return True
                except TypeError:
                    continue
                except Exception as e:
                    log(f"! {mod}.{fn} failed: {e}")
                    # keep trying other funcs
    return False

preferred = {
    "flashcards": [("flashcards", ["generate_set_pages","generate_pages","build_pages","main"])],
    "reading":    [("reading",    ["generate_set_pages","generate_pages","build_pages","main"])],
    "listening":  [("listening",  ["create_listening_set","generate_set_pages","generate_pages","build_pages","main"])],
    "practice":   [("practice",   ["generate_set_pages","generate_pages","build_pages","main"])],
}.get(mode, [])

fallbacks = [
    ("flashcards", ["generate_set_pages","generate_pages","build_pages","main"]),
    ("reading",    ["generate_set_pages","generate_pages","build_pages","main"]),
    ("listening",  ["create_listening_set","generate_set_pages","generate_pages","build_pages","main"]),
    ("practice",   ["generate_set_pages","generate_pages","build_pages","main"]),
]

seen = {mod for mod, _ in preferred}
order = list(preferred) + [(mod, fns) for mod, fns in fallbacks if mod not in seen]

ok = try_sets_utils(slug, mode)
if not ok:
    for mod, funcs in order:
        if try_module(mod, funcs):
            ok = True
            break

print("OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
