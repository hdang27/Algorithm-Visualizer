import inspect
import sys
from collections import namedtuple

MAX_EVENTS = 100000
SHOW = 6

Event = namedtuple("Event", "line node action child d flen fhead ftail elen erecent ret found")


class TraceLimit(Exception):
    pass


def source_lines(func):
    src, start = inspect.getsourcelines(func)
    out = []
    for i, line in enumerate(src):
        text = line.rstrip()
        if text.lstrip().startswith("#"):
            continue
        if "#" in text:
            text = text[:text.index("#")].rstrip()
        out.append((start + i, text))
    return out


def run_traced(func, args=(), kwargs=None, max_events=MAX_EVENTS):
    kwargs = kwargs or {}
    code = func.__code__
    events = []
    ex_order = []
    last_len = [0]

    def snapshot(frame, line, ret=False, found=False):
        L = frame.f_locals
        node, child = L.get("node"), L.get("child")
        frontier, explored = L.get("frontier"), L.get("explored")

        flen, fhead, ftail = 0, (), ()
        if frontier is not None:
            flen = len(frontier)
            if flen <= 2 * SHOW:
                fhead = tuple(n.state for n in frontier)
            else:
                fhead = tuple(n.state for n in frontier[:SHOW])
                ftail = tuple(n.state for n in frontier[-SHOW:])

        elen, erecent = 0, ()
        if explored is not None:
            elen = len(explored)
            if elen > last_len[0] and node is not None:
                ex_order.append(node.state)
            last_len[0] = elen
            if isinstance(explored, dict):
                erecent = tuple((s, explored.get(s)) for s in ex_order[-SHOW:])
            else:
                erecent = tuple((s, None) for s in ex_order[-SHOW:])

        if events:
            prev = events[-1]
            if fhead == prev.fhead:
                fhead = prev.fhead
            if ftail == prev.ftail:
                ftail = prev.ftail
            if erecent == prev.erecent:
                erecent = prev.erecent

        return Event(line=line,
                     node=node.state if node is not None else None,
                     action=L.get("action"),
                     child=child.state if child is not None else None,
                     d=L.get("d"),
                     flen=flen, fhead=fhead, ftail=ftail,
                     elen=elen, erecent=erecent,
                     ret=ret, found=found)

    def local_trace(frame, event, arg):
        if event == "line":
            if len(events) >= max_events:
                raise TraceLimit()
            events.append(snapshot(frame, frame.f_lineno))
        elif event == "return":
            events.append(snapshot(frame, frame.f_lineno, ret=True, found=arg is not None))
        return local_trace

    def global_trace(frame, event, arg):
        return local_trace if frame.f_code is code else None

    truncated = False
    sys.settrace(global_trace)
    try:
        func(*args, **kwargs)
    except TraceLimit:
        truncated = True
    finally:
        sys.settrace(None)

    if truncated and events and events[-1].ret:
        events.pop()
    return events, truncated
