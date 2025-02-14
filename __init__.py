import sys, resource
EXPECTED_RECURSION: int = 2000000
CURRENT_RECURSION: int = sys.getrecursionlimit()
print(f"Current recursion limit = {CURRENT_RECURSION}.")
if EXPECTED_RECURSION > CURRENT_RECURSION:
    print(f"Setting recursion limit to {EXPECTED_RECURSION}.")
    sys.setrecursionlimit(EXPECTED_RECURSION)
    resource.setrlimit(resource.RLIMIT_STACK, (EXPECTED_RECURSION, -1))


