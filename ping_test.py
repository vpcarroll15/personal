"""Silly utility to test if the website if up."""
import subprocess

out = subprocess.run("ping -c 3 paulcarroll.site".split(), stdout=subprocess.PIPE)
if out.returncode == 0:
    print("It seems to be up!")
else:
    print("Failed to ping paulcarroll.site! Is it down?")

