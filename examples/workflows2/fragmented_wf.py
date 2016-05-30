from aiida.backends.utils import load_dbenv, is_dbenv_loaded

if not is_dbenv_loaded():
    load_dbenv()

from aiida.workflows2.process import run
from aiida.workflows2.fragmented_wf import FragmentedWorkfunction


class W(FragmentedWorkfunction):
    definition = """
s1
s2
if cond1:
    s3
    s4
elif cond3:
    s11 # <- For Mounet
else:
    s5
    s6

while cond2:
    s7
    s8
s9
"""


    def start(self, ctx):
        print "s1"
        ctx.v = 1

        return 1, 2, 3, 4

    def s2(self, ctx):
        print "s2"
        ctx.v = 2
        ctx.w = 2

    def cond1(self, ctx):
        return ctx.v == 3

    def s3(self, ctx):
        print "s3"

    def s4(self, ctx):
        print "s4"

    def s5(self, ctx):
        print "s5"

    def s6(self, ctx):
        print "s6"

    #        f = async(slow)
    #        return Wait(f)

    def cond2(self, ctx):
        return ctx.w < 10

    def cond3(self, ctx):
        return True

    def s7(self, ctx):
        print " s7"
        ctx.w += 1
        print "w=", ctx.w

    def s8(self, ctx):
        print "s8"

    def s9(self, ctx):
        print "s9, end"

    def s11(self, ctx):
        pass


if __name__ == '__main__':
    run(W)
