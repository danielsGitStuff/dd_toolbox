import sys
EXPECTED_RECURSION: int = 20000
CURRENT_RECURSION: int = sys.getrecursionlimit()
print(f"Current recursion limit = {CURRENT_RECURSION}.")
if EXPECTED_RECURSION > CURRENT_RECURSION:
    print(f"Setting recursion limit to {EXPECTED_RECURSION}.")
    sys.setrecursionlimit(EXPECTED_RECURSION)


