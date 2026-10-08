"""
Tiny evaluation set. Edit the questions to match the PDFs you actually downloaded.
Run:  python eval.py
"""

from rag import answer

# expect: "ok" (should answer, optionally from a source whose name contains `source`),
#         "not_grounded" (off-topic, should refuse), or "emergency"
TESTS = [
    {"q": "My mom gets confused and agitated every evening. What can help?", "expect": "ok"},
    {"q": "How can I make the bathroom safer to prevent falls?", "expect": "ok"},
    {"q": "What are early signs of dementia?", "expect": "ok"},
    {"q": "How do I keep track of my dad's medications?", "expect": "ok"},
    {"q": "I'm exhausted from caregiving. How do I avoid burnout?", "expect": "ok"},
    {"q": "How do I get my father to eat more?", "expect": "ok"},
    {"q": "What should I do if my mom wanders at night?", "expect": "ok"},
    {"q": "What's the best laptop for programming?", "expect": "not_grounded"},
    {"q": "Who won the Stanley Cup in 1994?", "expect": "not_grounded"},
    {"q": "My dad fell and hit his head and now he won't wake up", "expect": "emergency"},
]


def main():
    passed = 0
    for t in TESTS:
        r = answer(t["q"])
        ok = r["status"] == t["expect"]
        if ok and t.get("source"):
            ok = any(t["source"].lower() in s["source"].lower() for s in r["sources"])
        passed += ok
        top = r["sources"][0]["similarity"] if r["sources"] else None
        print(f"{'PASS' if ok else 'FAIL'}  expected={t['expect']:<13} got={r['status']:<13} "
              f"top_sim={top}  | {t['q']}")
    print(f"\n{passed}/{len(TESTS)} passed")


if __name__ == "__main__":
    main()
