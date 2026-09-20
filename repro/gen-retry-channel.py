import asyncio
import inspect

import tenacity
from tenacity import retry, stop_after_attempt

print("=== 1) 同步生成器：创建期失败应被重试")
n1 = {"calls": 0}


@retry(stop=stop_after_attempt(4))
def head_flaky():
    n1["calls"] += 1
    if n1["calls"] < 3:
        raise RuntimeError("head boom %d" % n1["calls"])
    yield 10
    yield 20


try:
    print("   values:", list(head_flaky()), "| calls:", n1["calls"])
except Exception as e:
    print("   RAISES:", type(e).__name__, str(e)[:60], "| calls:", n1["calls"])

print("=== 2) 同步生成器：交付首值后再失败，不重试、原样抛")
n2 = {"calls": 0}


@retry(stop=stop_after_attempt(4))
def mid_flaky():
    n2["calls"] += 1
    yield "a"
    raise RuntimeError("mid boom")


got = []
try:
    for v in mid_flaky():
        got.append(v)
except Exception as e:
    print("   got:", got, "| then", type(e).__name__, str(e)[:40], "| calls:", n2["calls"])
else:
    print("   NO RAISE got:", got, "| calls:", n2["calls"])

print("=== 3) 异步生成器：创建期失败应被重试，且不阻塞事件循环")
n3 = {"calls": 0}
ticks = {"n": 0}


@retry(stop=stop_after_attempt(4), wait=tenacity.wait_fixed(0.05))
async def ahead_flaky():
    n3["calls"] += 1
    if n3["calls"] < 3:
        raise RuntimeError("ahead boom")
    yield 1
    yield 2


async def ticker():
    for _ in range(10):
        await asyncio.sleep(0.01)
        ticks["n"] += 1


async def main():
    vals = []
    t = asyncio.create_task(ticker())
    try:
        async for v in ahead_flaky():
            vals.append(v)
    except Exception as e:
        print("   RAISES:", type(e).__name__, str(e)[:40], "| calls:", n3["calls"])
    await t
    print("   values:", vals, "| calls:", n3["calls"], "| ticker ticks:", ticks["n"])

    print("=== 4) 异步生成器：交付首值后再失败，不重试、原样抛")

    async def amid_flaky():
        yield "x"
        raise RuntimeError("amid boom")

    wrapped = retry(stop=stop_after_attempt(4))(amid_flaky)
    got4 = []
    try:
        async for v in wrapped():
            got4.append(v)
    except Exception as e:
        print("   got:", got4, "| then", type(e).__name__, str(e)[:40])
    else:
        print("   NO RAISE got:", got4)

    print("=== 5) 空生成器与元数据")
    e5 = {"calls": 0}

    @retry(stop=stop_after_attempt(3))
    def empty_gen():
        e5["calls"] += 1
        if e5["calls"] < 2:
            raise RuntimeError("empty boom")
        return iter(())
        yield  # pragma: no cover

    @retry(stop=stop_after_attempt(3))
    async def empty_agen():
        return
        yield  # pragma: no cover

    try:
        es = list(empty_gen())
    except Exception as e:
        es = f"{type(e).__name__}:{str(e)[:20]}"
    try:
        ea = [v async for v in empty_agen()]
    except Exception as e:
        ea = f"{type(e).__name__}:{str(e)[:20]}"
    print("   empty sync:", es, "calls:", e5["calls"])
    print("   empty async:", ea)
    print("   metadata:", empty_gen.__name__, ahead_flaky.__name__)

    print("=== 6) 耗尽后的错误形态")
    n6 = {"calls": 0}

    @retry(stop=stop_after_attempt(2))
    def always_boom():
        n6["calls"] += 1
        raise RuntimeError("nope")
        yield  # pragma: no cover

    try:
        list(always_boom())
    except Exception as e:
        print("   exhausted:", type(e).__name__, "| calls:", n6["calls"])


asyncio.run(main())
print("done")
