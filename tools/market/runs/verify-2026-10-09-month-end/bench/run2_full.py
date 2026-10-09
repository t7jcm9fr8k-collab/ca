"""SYNTHETIC. The frozen invocation's full path in the mirror: the same command, token for token, except the
two --expect-sha256 values, which name the SYNTHETIC files; the frozen spec is pointed at that copy of the
invocation for this process only. Shows read() end to end. No real bar file is read."""
import hashlib, os, sys, time
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mirror")
os.chdir(M)
sys.path.insert(0, M)
import edgelab as E
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
inv = open("prereg-2026-10-09/invocation.sh").read()
assert inv.count("52a006deec221ab41c869bd25b279203d3f8d9dedad0bb99ea481164a2cd45a0") == 1
assert inv.count("4433bdbc019328196c84e610fe5f834aa72097de70a9d3bc2d499a6dfeae790e") == 1
inv2 = (inv.replace("52a006deec221ab41c869bd25b279203d3f8d9dedad0bb99ea481164a2cd45a0", sha("bars/SPY-1d.csv"))
        .replace("4433bdbc019328196c84e610fe5f834aa72097de70a9d3bc2d499a6dfeae790e", sha("bars/QQQ-1d-long.csv")))
p2 = "prereg-2026-10-09/invocation-synthetic.sh"
open(p2, "w").write(inv2)
E.FROZEN["month_end_overlay"] = dict(E.FROZEN["month_end_overlay"], invocation=p2, invocation_sha256=sha(p2))
argv = E.parse_invocation(p2)
a1 = E.parse_invocation("prereg-2026-10-09/invocation.sh")
print("argv differs from the frozen one only at:", [(i, x, y) for i, (x, y) in enumerate(zip(a1, argv)) if x != y],
      file=sys.stderr)
t0 = time.time()
code = E.main(argv)
print(f"exit {code}; {time.time() - t0:.1f} s", file=sys.stderr)
