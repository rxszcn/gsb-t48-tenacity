import pickle
import re

import tenacity
from tenacity import retry_if_exception_message as msg_is
from tenacity import retry_if_not_exception_message as msg_not


def st(exc):
    rs = tenacity.RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
    rs.outcome = tenacity.Future.construct(1, exc, True)
    return rs


print("=== 1) match= 的命中位置语义（每行都是「用户直觉上想重试」的写法）")
table = [
    ("match='timeout'", msg_is(match="timeout"), "timeout"),
    ("match='timeout'", msg_is(match="timeout"), "timeout occurred"),
    ("match='timeout'", msg_is(match="timeout"), "Connection timeout occurred"),
    ("match=r'\\btimeout\\b'", msg_is(match=r"\btimeout\b"), "Connection timeout occurred"),
    ("match=r'.*timeout'", msg_is(match=r".*timeout"), "Connection timeout occurred"),
    ("match=re.compile('timeout')", msg_is(match=re.compile("timeout")), "Connection timeout"),
    (
        "match=re.compile('timeout', re.I)",
        msg_is(match=re.compile("timeout", re.IGNORECASE)),
        "Connection TIMEOUT",
    ),
    (
        "match=re.compile('^timeout$')",
        msg_is(match=re.compile("^timeout$")),
        "timeout",
    ),
    (
        "match=re.compile('^timeout$')",
        msg_is(match=re.compile("^timeout$")),
        "timeout now",
    ),
    ("message='Connection timeout'", msg_is(message="Connection timeout"), "Connection timeout"),
    ("message='timeout'", msg_is(message="timeout"), "Connection timeout occurred"),
]
for label, strat, text in table:
    print("  %-34s 文本=%-30r -> %s" % (label, text, strat(st(ValueError(text)))))

print()
print("=== 2) 端到端：文案含 timeout，重试次数")


def run(strategy):
    n = {"c": 0}

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        retry=strategy,
        sleep=lambda s: None,
        reraise=True,
    )
    def f():
        n["c"] += 1
        raise ValueError("Connection TIMEOUT occurred")

    try:
        f()
    except BaseException as e:  # noqa: BLE001
        return n["c"], type(e).__name__


print("  match='timeout'                  -> 尝试=%d 抛出=%s" % run(msg_is(match="timeout")))
print("  match=re.compile('timeout', re.I)-> 尝试=%d 抛出=%s"
      % run(msg_is(match=re.compile("timeout", re.IGNORECASE))))
print("  match=re.compile('.*TIMEOUT')    -> 尝试=%d 抛出=%s"
      % run(msg_is(match=re.compile(".*TIMEOUT"))))

print()
print("=== 3) not_ 版与正版的对称性")
ok = tenacity.RetryCallState(retry_object=None, fn=None, args=(), kwargs={})
ok.outcome = tenacity.Future.construct(1, 42, False)
print("  正版  成功结果 ->", msg_is(match="timeout")(ok))
print("  not版 成功结果 ->", msg_not(match="timeout")(ok))
print("  not版 文本命中 ->", msg_not(match="timeout")(st(ValueError("timeout x"))))
print("  not版 文本未命中 ->", msg_not(match="timeout")(st(ValueError("boom"))))

print()
print("=== 4) pickle 往返")
for label, obj in [
    ("message=", msg_is(message="fail")),
    ("match=str", msg_is(match="fail.*")),
    ("match=Pattern", msg_is(match=re.compile("fail", re.I))),
    ("not_ message=", msg_not(message="fail")),
]:
    back = pickle.loads(pickle.dumps(obj))
    s = st(ValueError("xxfail yy"))
    print("  %-16s 往返前=%s 往返后=%s match类型=%s"
          % (label, obj(s), back(s), type(back.match).__name__))
