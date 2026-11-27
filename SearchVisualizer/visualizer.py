# Phím tắt:
#   Space      : Phát / Tạm dừng
#   ← / →      : Lùi / Tiến 1 bước
#   Home / End : Về đầu / Đến cuối
#   Enter      : Giải
#   T          : Chuyển giữa tab "Lời giải" và "Trace code"

import keyword
import random
import re
import threading
import time
from types import SimpleNamespace

import pygame

import bfs
import dfs
import ucs
import problems as P
import scaling as gfx
import tracer

W, H = 1200, 740
SIDEBAR_W = 300
LIST_W = 320
TRACE_LIST_W = 270
FPS = 60
SPEEDS = [0.5, 1, 2, 4, 8, 16, 32, 64, 128]

DFS_MAX_DEPTH = {"puzzle": 31, "vacuum": 3}
ALGOS = ("BFS", "DFS", "UCS")
MODULES = {"BFS": bfs, "DFS": dfs, "UCS": ucs}
FRONTIER_KIND = {"BFS": "(Queue)", "DFS": "(Stack)", "UCS": "(PQ)"}

C = SimpleNamespace(
    BG=(8, 8, 8), PANEL=(18, 18, 18), BORDER=(48, 48, 48), TEXT=(240, 240, 240),
    MUTED=(150, 150, 150), ACCENT=(34, 197, 94), ACCENT_LIGHT=(14, 46, 26),
    ACCENT_TEXT=(0, 0, 0), PRIMARY_HOVER=(74, 222, 128),
    GREEN=(74, 222, 128), RED=(248, 113, 113), ORANGE=(251, 191, 36),
    TILE=(72, 72, 72), TILE_OK=(22, 163, 74), TILE_TEXT=(255, 255, 255),
    TILE_SHADOW=(0, 0, 0), BOARD=(26, 26, 26), CELL=(14, 14, 14),
    BTN_HOVER=(30, 30, 30), DISABLED_BG=(20, 20, 20), DISABLED_FG=(80, 80, 80),
    BOX=(22, 22, 22), SCROLL=(70, 70, 70),
    FLOOR=(24, 24, 24), FLOOR_LINE=(36, 36, 36), WALL=(110, 110, 110),
    DIRT=(176, 126, 78), BADGE=(18, 18, 18),
    ROBOT_BODY=(220, 220, 220), ROBOT_RING=(60, 60, 60), ROBOT_SHADOW=(0, 0, 0),
    WAVE=(34, 197, 94), PUPIL=(10, 10, 10),
)


class Cancelled(Exception):
    pass


def font(size, bold=False):
    return gfx.SFont("segoeui,arial,tahoma", size, bold=bold)


_mono_cache = {}


def mono(size):
    if size not in _mono_cache:
        _mono_cache[size] = gfx.SFont("consolas,couriernew,dejavusansmono", size)
    return _mono_cache[size]


def compact_state(s):
    """Viết state 8-puzzle gọn trên 1 dòng: 1 2 3 | 4 _ 6 | 7 5 8"""
    if isinstance(s[0], tuple):
        return " | ".join(" ".join(str(v) if v else "_" for v in row) for row in s)
    return str(s)


_scope_cache = {}


def trace_scopes(src):
    """Từ mã nguồn [(số dòng, nội dung)], trả về 2 tập số dòng:
    - loop: thân vòng "for action in ..." (nơi action/child là của node hiện tại)
    - d   : từ sau dòng "d = ..." tới hết thân vòng while (nơi d là của node hiện tại)"""
    key = tuple(src)
    if key in _scope_cache:
        return _scope_cache[key]

    def indent(t):
        return len(t) - len(t.lstrip())

    def body_after(i):
        """Các dòng nằm sau dòng i và thụt vào sâu hơn dòng i."""
        lines, base = set(), indent(src[i][1])
        for ln, t in src[i + 1:]:
            if t.strip() and indent(t) <= base:
                break
            lines.add(ln)
        return lines

    loop, d = set(), set()
    for i, (ln, t) in enumerate(src):
        s = t.strip()
        if s.startswith("for action in"):
            loop = body_after(i)
        elif s.startswith("d =") or s.startswith("d="):
            parent = max(j for j in range(i) if src[j][1].strip()
                         and indent(src[j][1]) < indent(t))
            d = {l for l in body_after(parent) if l > ln}
    _scope_cache[key] = (loop, d)
    return loop, d


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    return t * t * (3 - 2 * t)


class Button:
    def __init__(self, rect, label, on_click, kind="normal", small=False):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.kind = kind
        self.small = small
        self.active = False
        self.enabled = True
        self.visible = True

    def draw(self, surf, f, mouse, f_small=None):
        if not self.visible:
            return
        hover = self.rect.collidepoint(mouse) and self.enabled
        if not self.enabled:
            bg, fg, bd = C.DISABLED_BG, C.DISABLED_FG, C.BORDER
        elif self.kind == "primary":
            bg = C.PRIMARY_HOVER if hover else C.ACCENT
            fg, bd = C.ACCENT_TEXT, bg
        elif self.active:
            bg, fg, bd = C.ACCENT_LIGHT, C.ACCENT, C.ACCENT
        else:
            bg = C.BTN_HOVER if hover else C.PANEL
            fg, bd = C.TEXT, C.BORDER
        gfx.rect(surf, bg, self.rect, border_radius=8)
        gfx.rect(surf, bd, self.rect, 1, border_radius=8)
        txt = (f_small if self.small and f_small else f).render(self.label, True, fg)
        surf.blit(txt, txt.get_rect(center=self.rect.center))

    def handle(self, pos):
        if self.visible and self.enabled and self.rect.collidepoint(pos):
            self.on_click()
            return True
        return False


class App:
    def __init__(self):
        gfx.enable_dpi_awareness()
        pygame.init()
        pygame.display.set_caption("BFS / DFS / UCS Visualizer -8-Puzzle & Vacuum Robot")
        gfx.set_scale(gfx.choose_scale(W, H))
        self.screen = gfx.Canvas(pygame.display.set_mode((gfx.sc(W), gfx.sc(H))))
        self.clock = pygame.time.Clock()

        self.f_title = font(24, True)
        self.f_h = font(17, True)
        self.f = font(16)
        self.f_small = font(14)
        self.f_tile = font(50, True)
        self.f_tile_small = font(20, True)
        self.f_tile_tiny = font(15, True)
        self.f_mono = mono(13)
        self.code_cache = {}          # (cỡ chữ, dòng code) -> surface đã tô màu cú pháp

        self.mode = "puzzle"          # "puzzle" | "vacuum"
        self.algo = "BFS"             # "BFS" | "DFS" | "UCS"
        self.puzzle_init = P.PUZZLE_INITIAL
        self.puzzle_goal = P.PUZZLE_GOAL
        self.vacuum_init = P.VACUUM_INITIAL

        self.result = None            
        self.history = {}             
        self.step = 0
        self.anim_t = 0.0
        self.playing = False
        self.speed_idx = 2
        self.list_scroll = 0
        self.follow = True
        self.view = "solution"        # "solution" | "trace"
        self.tstep = 0                # vị trí hiện tại trong trace

        self.searching = False
        self.search_start = 0
        self.cancel_flag = False
        self.search_thread = None
        self.pending = None
        self.message = ""

        self._build_buttons()

    def _build_buttons(self):
        x, w = 20, SIDEBAR_W - 40
        half = (w - 10) // 2
        self.btn_puzzle = Button((x, 80, half, 38), "8-Puzzle", lambda: self.set_mode("puzzle"))
        self.btn_vacuum = Button((x + half + 10, 80, half, 38), "Vacuum", lambda: self.set_mode("vacuum"))
        third = (w - 12) // 3
        self.btn_bfs = Button((x, 160, third, 38), "BFS (Queue)", lambda: self.set_algo("BFS"), small=True)
        self.btn_dfs = Button((x + third + 6, 160, third, 38), "DFS (Stack)", lambda: self.set_algo("DFS"),
                              small=True)
        self.btn_ucs = Button((x + w - third, 160, third, 38), "UCS (PQ)", lambda: self.set_algo("UCS"),
                              small=True)
        self.btn_solve = Button((x, 215, w, 44), "Giải", self.solve, kind="primary")
        self.btn_shuffle = Button((x, 268, half, 36), "Xáo trộn", self.shuffle)
        self.btn_reset = Button((x + half + 10, 268, half, 36), "Mặc định", self.reset_initial)

        bw = (w - 4 * 6) // 5
        y = 350
        self.btn_first = Button((x, y, bw, 38), "|<", self.go_first)
        self.btn_prev = Button((x + (bw + 6), y, bw, 38), "<", self.go_prev)
        self.btn_play = Button((x + 2 * (bw + 6), y, bw, 38), "Chạy", self.toggle_play)
        self.btn_next = Button((x + 3 * (bw + 6), y, bw, 38), ">", self.go_next)
        self.btn_last = Button((x + 4 * (bw + 6), y, bw, 38), ">|", self.go_last)
        self.btn_slower = Button((x, y + 48, 40, 32), "-", lambda: self.change_speed(-1))
        self.btn_faster = Button((x + w - 40, y + 48, 40, 32), "+", lambda: self.change_speed(1))

        self.buttons = [self.btn_puzzle, self.btn_vacuum, self.btn_bfs, self.btn_dfs, self.btn_ucs,
                        self.btn_solve, self.btn_shuffle, self.btn_reset,
                        self.btn_first, self.btn_prev, self.btn_play, self.btn_next,
                        self.btn_last, self.btn_slower, self.btn_faster]

        # Tab chuyển chế độ xem, nằm ở góc phải tiêu đề khung chính
        self.btn_tab_sol = Button((0, 0, 96, 30), "Lời giải", lambda: self.set_view("solution"))
        self.btn_tab_trace = Button((0, 0, 110, 30), "Trace code", lambda: self.set_view("trace"))
        self.tabs = [self.btn_tab_sol, self.btn_tab_trace]

    def _refresh_buttons(self):
        m = self.main_rect()
        self.btn_tab_trace.rect.topright = (m.right - 16, m.y + 16)
        self.btn_tab_sol.rect.topright = (self.btn_tab_trace.rect.x - 8, m.y + 16)
        tracing = self.in_trace()
        self.btn_tab_sol.active = not tracing
        self.btn_tab_trace.active = tracing
        for b in self.tabs:
            b.visible = self.result is not None and not self.searching
        self.btn_tab_trace.enabled = bool(self.result and self.result.get("trace"))

        self.btn_puzzle.active = self.mode == "puzzle"
        self.btn_vacuum.active = self.mode == "vacuum"
        self.btn_bfs.active = self.algo == "BFS"
        self.btn_dfs.active = self.algo == "DFS"
        self.btn_ucs.active = self.algo == "UCS"
        self.btn_solve.label = "Hủy tìm kiếm" if self.searching else f"Giải bằng {self.algo}"
        self.btn_play.label = "Dừng" if self.playing else "Chạy"
        has = self.result is not None and not self.searching
        for b in (self.btn_first, self.btn_prev, self.btn_play, self.btn_next, self.btn_last):
            b.enabled = has
        for b in (self.btn_puzzle, self.btn_vacuum, self.btn_bfs, self.btn_dfs, self.btn_ucs,
                  self.btn_shuffle, self.btn_reset):
            b.enabled = not self.searching
        self.btn_shuffle.label = "Xáo trộn" if self.mode == "puzzle" else "Ngẫu nhiên"


    def set_mode(self, m):
        if m != self.mode:
            self.mode = m
            self.clear_result()

    def set_algo(self, a):
        if a != self.algo:
            self.algo = a
            key = (self.mode, a)
            if key in self.history:
                self.load_result(self.history[key])
            else:
                self.clear_result(keep_history=True)

    def clear_result(self, keep_history=False):
        self.result = None
        self.step = 0
        self.tstep = 0
        self.anim_t = 0
        self.playing = False
        self.list_scroll = 0
        self.message = ""
        if not keep_history:
            self.history = {}

    def initial_state(self):
        return self.puzzle_init if self.mode == "puzzle" else self.vacuum_init

    def shuffle(self):
        if self.mode == "puzzle":
            s = self.puzzle_goal
            prev = None
            for _ in range(random.randint(8, 16)):
                acts = P.get_actions_8puzzle(s)
                nxt = [P.get_result_8puzzle(s, a) for a in acts]
                nxt = [n for n in nxt if n != prev] or nxt
                prev = s
                s = random.choice(nxt)
            self.puzzle_init = s
        else:
            self.vacuum_init = (random.choice("AB"), random.choice("CD"), random.choice("CD"))
        self.clear_result()

    def reset_initial(self):
        if self.mode == "puzzle":
            self.puzzle_init = P.PUZZLE_INITIAL
        else:
            self.vacuum_init = P.VACUUM_INITIAL
        self.clear_result()

    def change_speed(self, d):
        self.speed_idx = max(0, min(len(SPEEDS) - 1, self.speed_idx + d))

    # ---- Xem lời giải / trace code: dùng chung các nút điều khiển ----
    def in_trace(self):
        return self.view == "trace" and bool(self.result and self.result.get("trace"))

    def set_view(self, v):
        if v != self.view:
            self.view = v
            self.playing, self.anim_t, self.follow = False, 0, True

    def _seq_len(self):
        if not self.result:
            return 1
        return len(self.result["trace"]) if self.in_trace() else len(self.result["path"])

    def _pos(self):
        return self.tstep if self.in_trace() else self.step

    def _set_pos(self, v):
        if self.in_trace():
            self.tstep = v
        else:
            self.step = v

    def toggle_play(self):
        if not self.result:
            return
        if self._pos() >= self._seq_len() - 1:
            self._set_pos(0)
            self.anim_t = 0
        self.playing = not self.playing
        self.follow = True

    def go_first(self):
        self._set_pos(0)
        self.anim_t, self.playing, self.follow = 0, False, True

    def go_last(self):
        if self.result:
            self._set_pos(self._seq_len() - 1)
            self.anim_t, self.playing, self.follow = 0, False, True

    def go_prev(self):
        self.playing, self.follow = False, True
        if self.anim_t > 0:
            self.anim_t = 0
        else:
            self._set_pos(max(0, self._pos() - 1))

    def go_next(self):
        if self.result:
            self.playing, self.follow = False, True
            self.anim_t = 0
            self._set_pos(min(self._seq_len() - 1, self._pos() + 1))


    def solve(self):
        if self.searching:
            self.cancel_flag = True
            return
        self.clear_result(keep_history=True)
        self.searching = True
        self.cancel_flag = False
        self.search_start = time.perf_counter()
        goal = self.puzzle_goal if self.mode == "puzzle" else P.is_goal_vacuum
        args = (self.mode, self.algo, self.initial_state(), goal)
        self.search_thread = threading.Thread(target=self._worker, args=args, daemon=True)
        self.search_thread.start()

    def _worker(self, mode, algo, init, goal):
        module = MODULES[algo]
        func = getattr(module, algo)
        kwargs = {"max_depth": DFS_MAX_DEPTH[mode]} if algo == "DFS" else {}
        expanded = [0]

        if mode == "puzzle":
            base_actions, result_fn = P.get_actions_8puzzle, P.get_result_8puzzle
            cost_fn = P.get_cost_8puzzle
        else:
            base_actions, result_fn = P.get_actions_vacuum, P.get_result_vacuum
            cost_fn = P.get_cost_vacuum
        extra = {"action_cost": cost_fn} if algo == "UCS" else {}

        def actions_fn(state):
            if self.cancel_flag:
                raise Cancelled()
            expanded[0] += 1
            return base_actions(state)

        problem = module.Problem(
            initial_state=init,
            goal_condition=goal,
            actions=actions_fn,
            result=result_fn,
            **extra,
        )
        t0 = time.perf_counter()
        try:
            res = func(problem, **kwargs)
        except Cancelled:
            self.pending = {"cancelled": True}
            return
        elapsed = time.perf_counter() - t0

        if res is None:
            self.pending = {"mode": mode, "algo": algo, "found": False,
                            "expanded": expanded[0], "time": elapsed}
            return

        acts = []
        node = res["goal_node"]
        while node.parent is not None:
            acts.append(node.action)
            node = node.parent
        acts.reverse()
        path = res["path"]
        costs = [cost_fn(path[i], a, path[i + 1]) for i, a in enumerate(acts)]

        # Chạy lại chính hàm BFS/DFS/UCS dưới sys.settrace để ghi lại từng dòng code
        # (chạy riêng, sau khi đã đo thời gian, nên không ảnh hưởng số liệu ở trên)
        def trace_actions(state):
            if self.cancel_flag:
                raise Cancelled()
            return base_actions(state)

        trace_problem = module.Problem(initial_state=init, goal_condition=goal,
                                       actions=trace_actions, result=result_fn, **extra)
        try:
            events, truncated = tracer.run_traced(func, (trace_problem,), kwargs,
                                                  priority=algo == "UCS")
        except Cancelled:
            self.pending = {"cancelled": True}
            return

        self.pending = {"mode": mode, "algo": algo, "found": True, "path": path,
                        "actions": acts, "costs": costs, "cost": sum(costs),
                        "expanded": expanded[0], "time": elapsed,
                        "trace": events, "trace_src": tracer.source_lines(func),
                        "trace_truncated": truncated}

    def _poll_search(self):
        if self.searching and self.pending is not None:
            r, self.pending = self.pending, None
            self.searching = False
            if r.get("cancelled"):
                self.message = "Đã hủy tìm kiếm."
                return
            self.history[(r["mode"], r["algo"])] = r
            if r["mode"] == self.mode and r["algo"] == self.algo:
                self.load_result(r)

    def load_result(self, r):
        self.clear_result(keep_history=True)
        if r["found"]:
            self.result = r
            self.message = ""
        else:
            self.message = "Không tìm thấy lời giải!"


    def puzzle_cell_at(self, pos):
        ox, oy, s, g = self.board_geom()
        for r in range(3):
            for c in range(3):
                if pygame.Rect(ox + c * (s + g), oy + r * (s + g), s, s).collidepoint(pos):
                    return r, c
        return None

    def handle_board_click(self, pos, button):
        if self.searching or self.in_trace():
            return
        if self.mode == "puzzle":
            cell = self.puzzle_cell_at(pos)
            if cell is None:
                return
            if self.result is not None:
                self.clear_result(keep_history=True)
                return
            r, c = cell
            br, bc = P.find_blank(self.puzzle_init)
            if abs(r - br) + abs(c - bc) != 1:
                return
            g = [list(row) for row in self.puzzle_init]
            g[br][bc], g[r][c] = g[r][c], 0
            self.puzzle_init = tuple(tuple(row) for row in g)
            self.clear_result()
        else:
            if self.result is not None:
                return
            rooms = self.room_rects()
            for i, rect in enumerate(rooms):
                if rect.collidepoint(pos):
                    pos_r, a, b = self.vacuum_init
                    name = "AB"[i]
                    if button == 3:
                        pos_r = name
                    else:
                        if name == "A":
                            a = "C" if a == "D" else "D"
                        else:
                            b = "C" if b == "D" else "D"
                    self.vacuum_init = (pos_r, a, b)
                    self.clear_result()
                    return

    def update(self, dt):
        self._poll_search()
        if self.playing and self.result:
            last = self._seq_len() - 1
            self.anim_t += dt * SPEEDS[self.speed_idx]
            while self.anim_t >= 1:
                self.anim_t -= 1
                self._set_pos(self._pos() + 1)
                if self._pos() >= last:
                    self._set_pos(last)
                    self.anim_t, self.playing = 0, False
                    break
        self._refresh_buttons()

    def main_rect(self):
        lw = TRACE_LIST_W if self.in_trace() else LIST_W
        return pygame.Rect(SIDEBAR_W + 20, 20, W - SIDEBAR_W - lw - 40, H - 40)

    def list_rect(self):
        lw = TRACE_LIST_W if self.in_trace() else LIST_W
        return pygame.Rect(W - lw, 20, lw - 20, H - 40)

    def board_geom(self):
        m = self.main_rect()
        size, gap = 112, 8
        total = 3 * size + 2 * gap
        ox = m.centerx - total // 2
        oy = m.y + 100
        return ox, oy, size, gap

    def goal_geom(self):
        m = self.main_rect()
        gs, gg = 44, 5
        return m.x + 36, m.y + 512, gs, gg

    def room_rects(self):
        m = self.main_rect()
        rw, rh = 250, 280
        ox = m.centerx - rw
        oy = m.y + 120
        return [pygame.Rect(ox, oy, rw, rh), pygame.Rect(ox + rw, oy, rw, rh)]

    def panel(self, rect):
        gfx.rect(self.screen, C.PANEL, rect, border_radius=12)
        gfx.rect(self.screen, C.BORDER, rect, 1, border_radius=12)

    def text(self, s, pos, f=None, color=None, center=False, right=False):
        f = f or self.f
        img = f.render(s, True, color or C.TEXT)
        r = img.get_rect()
        if center:
            r.center = pos
        elif right:
            r.topright = pos
        else:
            r.topleft = pos
        self.screen.blit(img, r)
        return r

    def draw_mini_grid(self, state, x, y, s, g, highlight=None, fnt=None):
        fnt = fnt or self.f_tile_small
        for r in range(3):
            for c in range(3):
                v = state[r][c]
                rect = pygame.Rect(x + c * (s + g), y + r * (s + g), s, s)
                gfx.rect(self.screen, C.TILE_OK if v else C.CELL, rect, border_radius=6)
                if v:
                    self.text(str(v), rect.center, fnt, C.TILE_TEXT, center=True)
                if highlight == (r, c):
                    gfx.rect(self.screen, C.ORANGE, rect.inflate(6, 6), 3, border_radius=8)

    def draw(self):
        self.screen.fill(C.BG)
        self.draw_sidebar()
        self.draw_main()
        self.draw_list()
        pygame.display.flip()

    def draw_sidebar(self):
        sb = pygame.Rect(0, 0, SIDEBAR_W, H)
        gfx.rect(self.screen, C.PANEL, sb)
        gfx.line(self.screen, C.BORDER, (SIDEBAR_W, 0), (SIDEBAR_W, H))
        self.text("Search Visualizer", (20, 20), self.f_title)
        self.text("Bài toán", (20, 58), self.f_small, C.MUTED)
        self.text("Thuật toán", (20, 138), self.f_small, C.MUTED)
        self.text("Điều khiển lời giải", (20, 326), self.f_small, C.MUTED)

        sp = SPEEDS[self.speed_idx]
        unit = "dòng/giây" if self.in_trace() else "bước/giây"
        self.text(f"Tốc độ: {sp:g} {unit}", (SIDEBAR_W // 2, 414), self.f, center=True)

        mouse = gfx.mouse_pos()
        for b in self.buttons:
            b.draw(self.screen, self.f, mouse, self.f_small)

        # Thông tin kết quả
        y = 452
        gfx.line(self.screen, C.BORDER, (20, y), (SIDEBAR_W - 20, y))
        y += 12
        self.text("Kết quả", (20, y), self.f_h)
        y += 30
        if self.searching:
            el = time.perf_counter() - self.search_start
            dots = "." * (int(el * 3) % 4)
            self.text(f"Đang tìm kiếm{dots}", (20, y), self.f, C.ORANGE)
            self.text(f"{el:.1f}s", (SIDEBAR_W - 20, y), self.f, C.MUTED, right=True)
            y += 26
        elif self.message:
            self.text(self.message, (20, y), self.f, C.RED)
            y += 26

        for algo in ALGOS:
            r = self.history.get((self.mode, algo))
            box = pygame.Rect(20, y, SIDEBAR_W - 40, 68)
            sel = algo == self.algo
            gfx.rect(self.screen, C.ACCENT_LIGHT if sel else C.BOX, box, border_radius=8)
            gfx.rect(self.screen, C.ACCENT if sel else C.BORDER, box, 1, border_radius=8)
            self.text(algo, (box.x + 12, box.y + 5), self.f_h, C.ACCENT if sel else C.TEXT)
            if r is None:
                self.text("Chưa chạy", (box.x + 12, box.y + 32), self.f_small, C.MUTED)
            elif not r["found"]:
                self.text("Không tìm thấy lời giải", (box.x + 12, box.y + 32), self.f_small, C.RED)
            else:
                self.text(f"{r['time'] * 1000:.1f} ms", (box.right - 12, box.y + 8), self.f_small,
                          C.MUTED, right=True)
                line = f"Số bước: {len(r['actions'])}"
                if algo == "UCS":
                    line += f"   •   Chi phí: {r['cost']}"
                self.text(line, (box.x + 12, box.y + 28), self.f_small)
                self.text(f"Số node mở rộng: {r['expanded']}", (box.x + 12, box.y + 46), self.f_small)
            y += 74


    def current_states(self):
        if self.result:
            path = self.result["path"]
            s0 = path[self.step]
            if self.anim_t > 0 and self.step < len(path) - 1:
                t = self.anim_t if SPEEDS[self.speed_idx] <= 16 else 1.0
                return s0, path[self.step + 1], ease(min(1.0, t))
            return s0, None, 0
        return self.initial_state(), None, 0

    def draw_main(self):
        m = self.main_rect()
        self.panel(m)
        title = "8-Puzzle (ma trận 3x3)" if self.mode == "puzzle" else "Vacuum Robot (1x2)"
        self.text(title, (m.x + 20, m.y + 16), self.f_title)

        mouse = gfx.mouse_pos()
        for b in self.tabs:
            b.draw(self.screen, self.f_small, mouse)

        if self.in_trace():
            self.draw_trace_main(m)
            return

        if self.result:
            n = len(self.result["path"]) - 1
            act = self.result["actions"][self.step - 1] if self.step > 0 else "Bắt đầu"
            sub = f"{self.algo}  •  Bước {self.step}/{n}  •  Hành động: {act}"
            if self.algo == "UCS":
                sub += f"  •  g = {sum(self.result['costs'][:self.step])}"
            if self.step == n:
                sub += "  •  ĐẠT ĐÍCH"
            self.text(sub, (m.x + 20, m.y + 54), self.f, C.ACCENT)
        else:
            hint = ("Trạng thái đầu  —  click ô kề ô trống để trượt" if self.mode == "puzzle"
                    else "Click trái: đổi Sạch/Bẩn  •  Click phải: đặt robot")
            self.text(hint, (m.x + 20, m.y + 54), self.f, C.MUTED)

        if self.mode == "puzzle":
            self.draw_puzzle()
        else:
            self.draw_vacuum()

    def draw_puzzle(self):
        s0, s1, t = self.current_states()
        goal = self.puzzle_goal
        ox, oy, size, gap = self.board_geom()
        total = 3 * size + 2 * gap
        board = pygame.Rect(ox - 12, oy - 12, total + 24, total + 24)
        gfx.rect(self.screen, C.BOARD, board, border_radius=14)

        for r in range(3):
            for c in range(3):
                cell = pygame.Rect(ox + c * (size + gap), oy + r * (size + gap), size, size)
                gfx.rect(self.screen, C.CELL, cell, border_radius=10)

        moving_val, frm, to = None, None, None
        if s1 is not None:
            br0 = P.find_blank(s0)
            br1 = P.find_blank(s1)
            moving_val = s0[br1[0]][br1[1]]
            frm, to = br1, br0

        for r in range(3):
            for c in range(3):
                v = s0[r][c]
                x = ox + c * (size + gap)
                y = oy + r * (size + gap)
                if v != 0:
                    if v == moving_val:
                        x = lerp(ox + frm[1] * (size + gap), ox + to[1] * (size + gap), t)
                        y = lerp(oy + frm[0] * (size + gap), oy + to[0] * (size + gap), t)
                    ok = goal[r][c] == v and v != moving_val
                    rect = pygame.Rect(int(x), int(y), size, size)
                    gfx.rect(self.screen, C.TILE_SHADOW, rect.move(0, 4), border_radius=10)
                    gfx.rect(self.screen, C.TILE_OK if ok else C.TILE, rect, border_radius=10)
                    self.text(str(v), rect.center, self.f_tile, C.TILE_TEXT, center=True)

        gx, gy, gs, gg = self.goal_geom()
        self.text("Trạng thái đích", (gx, gy - 30), self.f_h)
        self.draw_mini_grid(goal, gx, gy, gs, gg)

        lx = gx + 3 * (gs + gg) + 34
        ly = gy - 28
        gfx.rect(self.screen, C.TILE_OK, (lx, ly + 2, 16, 16), border_radius=4)
        self.text("Ô đúng vị trí đích", (lx + 24, ly), self.f_small, C.MUTED)
        gfx.rect(self.screen, C.TILE, (lx, ly + 26, 16, 16), border_radius=4)
        self.text("Ô chưa đúng vị trí", (lx + 24, ly + 24), self.f_small, C.MUTED)
        self.text("Hành động = hướng di chuyển của ô trống", (lx, ly + 52), self.f_small, C.MUTED)
        if self.algo == "UCS":
            self.text("Chi phí: Up/Down = 1, Left/Right = 2", (lx, ly + 74), self.f_small, C.MUTED)
    def draw_vacuum(self):
        s0, s1, t = self.current_states()
        rooms = self.room_rects()
        pos0, a0, b0 = s0
        dirt0 = {"A": a0, "B": b0}
        dirt1 = dirt0 if s1 is None else {"A": s1[1], "B": s1[2]}

        for i, rect in enumerate(rooms):
            name = "AB"[i]
            gfx.rect(self.screen, C.FLOOR, rect)
            for k in range(1, 7):
                yy = rect.y + 60 + k * 30
                if yy < rect.bottom:
                    gfx.line(self.screen, C.FLOOR_LINE, (rect.x, yy), (rect.right, yy))
            gfx.rect(self.screen, C.WALL, rect, 4)
            self.text(f"Phòng {name}", (rect.centerx, rect.y + 24), self.f_title, center=True)

            alpha = 1.0
            if dirt0[name] == "D" and dirt1[name] == "C":
                alpha = 1 - t
            elif dirt0[name] == "C":
                alpha = 0
            if alpha > 0:
                rnd = random.Random(i * 97 + 13)
                dust = pygame.Surface(rect.size, pygame.SRCALPHA)
                for _ in range(26):
                    dx = rnd.randint(25, rect.w - 25)
                    dy = rnd.randint(90, rect.h - 25)
                    rad = rnd.randint(4, 9)
                    gfx.circle(dust, (*C.DIRT, int(230 * alpha)), (dx, dy),
                                       int(rad * (0.4 + 0.6 * alpha)))
                self.screen.blit(dust, rect.topleft)

            st = dirt1[name] if t >= 1 else dirt0[name]
            label = "Bẩn (D)" if st == "D" else "Sạch (C)"
            col = C.DIRT if st == "D" else C.GREEN
            badge = pygame.Rect(0, 0, 110, 28)
            badge.center = (rect.centerx, rect.y + 58)
            gfx.rect(self.screen, C.BADGE, badge, border_radius=14)
            gfx.rect(self.screen, col, badge, 2, border_radius=14)
            self.text(label, badge.center, self.f, col, center=True)

        cx_a, cx_b = rooms[0].centerx, rooms[1].centerx
        x0 = cx_a if pos0 == "A" else cx_b
        x = x0
        sucking = False
        if s1 is not None:
            x1 = cx_a if s1[0] == "A" else cx_b
            x = lerp(x0, x1, t)
            sucking = s1[0] == pos0 and (s1[1] != a0 or s1[2] != b0)
        self.draw_robot(int(x), rooms[0].y + 200, sucking)

        m = self.main_rect()
        st = s1 if (s1 is not None and t >= 1) else s0
        ty = rooms[0].bottom + 40
        self.text(f"Trạng thái: {st}", (m.centerx, ty), self.f_h, center=True)
        self.text("Đích: ('A','C','C') hoặc ('B','C','C')", (m.centerx, ty + 30), self.f, C.MUTED, center=True)
        self.text("Mỗi lượt robot làm 1 trong 3 hành động: Left, Right, Suck", (m.centerx, ty + 56),
                  self.f, C.MUTED, center=True)
        if self.algo == "UCS":
            self.text("Chi phí: Suck = 1, Left/Right = 2", (m.centerx, ty + 82), self.f, C.MUTED, center=True)

    def draw_robot(self, x, y, sucking):
        tt = pygame.time.get_ticks() / 1000
        if sucking:
            for k in range(3):
                r = 40 + ((tt * 60 + k * 15) % 45)
                gfx.circle(self.screen, C.WAVE, (x, y + 10), int(r), 2)
        gfx.ellipse(self.screen, C.ROBOT_SHADOW, (x - 46, y + 34, 92, 16))
        gfx.circle(self.screen, C.ROBOT_RING, (x, y), 44)
        gfx.circle(self.screen, C.ROBOT_BODY, (x, y), 38)
        gfx.circle(self.screen, C.ACCENT, (x, y), 20)
        for ex in (x - 7, x + 7):
            gfx.circle(self.screen, (255, 255, 255), (ex, y - 4), 5)
            gfx.circle(self.screen, C.PUPIL, (ex, y - 4), 2)
        gfx.circle(self.screen, C.ORANGE if sucking else C.GREEN, (x, y - 30), 4)

    # =========================== TRACE CODE ===========================
    def code_line_surface(self, f, size, text):
        """Render 1 dòng code có tô màu cú pháp đơn giản (có cache)."""
        key = (size, text)
        surf = self.code_cache.get(key)
        if surf is None:
            # Render ở độ phân giải thật (f.raw) để chữ code không bị mờ
            raw = f.raw
            surf = pygame.Surface(raw.size(text or " "), pygame.SRCALPHA)
            x = 0
            for tok in re.findall(r"\w+|\s+|[^\w\s]", text):
                if keyword.iskeyword(tok):
                    col = C.GREEN
                elif tok.isdigit():
                    col = C.ORANGE
                elif tok in ("Node", "Queue", "Stack", "enqueue", "dequeue", "push", "pop",
                             "is_empty", "child_node", "solution", "depth", "set", "len",
                             "PriorityQueue", "find_in_frontier", "heapq", "heapify"):
                    col = (125, 200, 255)
                else:
                    col = C.TEXT
                if not tok.isspace():
                    surf.blit(raw.render(tok, True, col), (x, 0))
                x += raw.size(tok)[0]
            surf = gfx.HiSurf(surf)
            self.code_cache[key] = surf
        return surf

    def draw_trace_main(self, m):
        r = self.result
        events, src = r["trace"], r["trace_src"]
        ev = events[self.tstep]

        sub = f"Trace {r['algo']}  •  Dòng {ev.line}  •  {self.tstep + 1}/{len(events)}"
        if ev.ret:
            sub += "  •  return " + ("lời giải" if ev.found else "None")
        self.text(sub, (m.x + 20, m.y + 54), self.f, C.ACCENT)

        # --- Khung mã nguồn, tô sáng dòng sắp thực thi ---
        box = pygame.Rect(m.x + 16, m.y + 84, m.w - 32, 0)
        gutter = 34
        widest = max((t for _, t in src), key=len)
        size = 14
        while size > 10 and mono(size).size(widest)[0] > box.w - gutter - 20:
            size -= 1
        f = mono(size)
        lh = f.get_linesize() + 1
        box.h = len(src) * lh + 14
        gfx.rect(self.screen, C.CELL, box, border_radius=10)
        gfx.rect(self.screen, C.BORDER, box, 1, border_radius=10)
        for i, (ln, text) in enumerate(src):
            y = box.y + 7 + i * lh
            cur = ln == ev.line
            if cur:
                row = pygame.Rect(box.x + 4, y - 1, box.w - 8, lh)
                gfx.rect(self.screen, C.ACCENT_LIGHT, row, border_radius=4)
                gfx.rect(self.screen, C.ACCENT, (row.x, row.y, 3, row.h))
            num = f.render(str(ln), True, C.ACCENT if cur else C.DISABLED_FG)
            self.screen.blit(num, num.get_rect(topright=(box.x + gutter, y)))
            self.screen.blit(self.code_line_surface(f, size, text), (box.x + gutter + 12, y))

        # --- Giá trị các biến tại thời điểm này ---
        # action/child chỉ có nghĩa bên trong vòng "for action in ...", d chỉ có nghĩa
        # sau dòng "d = depth(node)". Ngoài đó biến vẫn giữ giá trị cũ của node
        # trước -> ẩn đi để không bị hiểu nhầm (vd: child cũ hiện ra lúc tìm thấy đích).
        loop_lines, d_lines = trace_scopes(src)
        action = ev.action if ev.line in loop_lines else None
        child = ev.child if ev.line in loop_lines else None
        d = ev.d if ev.line in d_lines else None

        y0 = box.bottom + 14
        x = m.x + 20
        self.trace_state_cell("node.state", ev.node, x, y0)
        x += 150
        self.text("action", (x, y0), self.f_mono, C.MUTED)
        self.text(repr(action) if action is not None else "—", (x, y0 + 24), self.f_h)
        if r["algo"] == "DFS":
            self.text("d", (x, y0 + 56), self.f_mono, C.MUTED)
            self.text(str(d) if d is not None else "—", (x + 20, y0 + 52), self.f_h)
        elif r["algo"] == "UCS":
            self.text("node.g", (x, y0 + 56), self.f_mono, C.MUTED)
            self.text(str(ev.ng) if ev.node is not None else "—", (x + 56, y0 + 52), self.f_h)
            self.text("child.g", (x, y0 + 84), self.f_mono, C.MUTED)
            self.text(str(ev.cg) if child is not None else "—", (x + 64, y0 + 80), self.f_h)
        x += 120
        self.trace_state_cell("child.state", child, x, y0)
        if ev.ret:
            msg, col = ("Tìm thấy đích!", C.GREEN) if ev.found else ("Không có lời giải", C.RED)
            self.text(msg, (m.right - 20, y0 + 30), self.f_h, col, right=True)

    def trace_state_cell(self, label, state, x, y):
        self.text(label, (x, y), self.f_mono, C.MUTED)
        if state is None:
            self.text("—", (x, y + 24), self.f_h)
        elif self.mode == "puzzle":
            self.draw_state_grid(state, x, y + 22, 26, 3)
        else:
            self.draw_mini_vacuum(state, x, y + 24)

    def draw_state_grid(self, state, x, y, s, g):
        goal = self.puzzle_goal
        for r in range(3):
            for c in range(3):
                v = state[r][c]
                rect = pygame.Rect(x + c * (s + g), y + r * (s + g), s, s)
                if v:
                    col = C.TILE_OK if goal[r][c] == v else C.TILE
                    gfx.rect(self.screen, col, rect, border_radius=5)
                    self.text(str(v), rect.center, self.f_tile_tiny, C.TILE_TEXT, center=True)
                else:
                    gfx.rect(self.screen, C.CELL, rect, border_radius=5)
                    gfx.rect(self.screen, C.BORDER, rect, 1, border_radius=5)

    def draw_mini_vacuum(self, state, x, y):
        pos, a, b = state
        for i, (name, st) in enumerate((("A", a), ("B", b))):
            rect = pygame.Rect(x + i * 56, y, 56, 44)
            gfx.rect(self.screen, C.FLOOR, rect)
            gfx.rect(self.screen, C.WALL, rect, 2)
            self.text(name, (rect.x + 6, rect.y + 3), self.f_small, C.MUTED)
            if st == "D":
                for dx, dy in ((14, 30), (26, 22), (38, 32), (44, 18)):
                    gfx.circle(self.screen, C.DIRT, (rect.x + dx, rect.y + dy), 4)
            if pos == name:
                gfx.circle(self.screen, C.ROBOT_BODY, (rect.centerx + 8, rect.centery + 4), 11)
                gfx.circle(self.screen, C.ACCENT, (rect.centerx + 8, rect.centery + 4), 5)
        self.text(str(state), (x, y + 50), self.f_small, C.MUTED)

    def draw_trace_list(self):
        lr = self.list_rect()
        self.panel(lr)
        r = self.result
        ev = r["trace"][self.tstep]
        is_queue = r["algo"] != "DFS"
        is_pq = r["algo"] == "UCS"
        x, y = lr.x + 14, lr.y + 14
        row_h = 21

        # --- frontier ---
        self.text("frontier", (x, y), self.f_h)
        self.text(FRONTIER_KIND[r["algo"]], (x + 76, y + 2), self.f_small, C.MUTED)
        self.text(f"{ev.flen} phần tử", (lr.right - 14, y + 2), self.f_small, C.ACCENT, right=True)
        y += 24
        if is_pq:
            hint = "↑ g nhỏ nhất (dequeue), xếp theo g"
        elif is_queue:
            hint = "↑ đầu hàng đợi (dequeue)"
        else:
            hint = "↑ đỉnh stack (pop)"
        self.text(hint, (x, y), self.f_small, C.MUTED)
        y += 24

        n = ev.flen
        if ev.ftail:
            head = list(enumerate(ev.fhead))
            tail = [(n - len(ev.ftail) + i, s) for i, s in enumerate(ev.ftail)]
            hidden = n - len(head) - len(tail)
            rows = head + [None] + tail if is_queue else tail[::-1] + [None] + head[::-1]
        else:
            hidden = 0
            rows = list(enumerate(ev.fhead))
            if not is_queue:
                rows.reverse()
        if not rows:
            self.text("(rỗng)", (x, y), self.f_mono, C.MUTED)
            y += row_h
        for item in rows:
            if item is None:
                self.text(f"… {hidden} phần tử nữa …", (x + 34, y), self.f_small, C.MUTED)
            else:
                i, (s, g) = item
                self.text(f"[{i}]", (x, y), self.f_mono, C.DISABLED_FG)
                self.text(compact_state(s), (x + (34 if is_pq else 48), y), self.f_mono, C.TEXT)
                if is_pq:
                    self.text(f"g={g}", (lr.right - 14, y), self.f_mono, C.MUTED, right=True)
            y += row_h

        # --- explored ---
        y += 14
        gfx.line(self.screen, C.BORDER, (x, y), (lr.right - 14, y))
        y += 12
        self.text("explored", (x, y), self.f_h)
        self.text("(dict)" if r["algo"] == "DFS" else "(set)", (x + 82, y + 2), self.f_small, C.MUTED)
        self.text(f"{ev.elen} trạng thái", (lr.right - 14, y + 2), self.f_small, C.ACCENT, right=True)
        y += 24
        self.text("mới thêm gần nhất ở trên", (x, y), self.f_small, C.MUTED)
        y += 24
        if not ev.erecent:
            self.text("(rỗng)", (x, y), self.f_mono, C.MUTED)
        for s, d in reversed(ev.erecent):
            self.text(compact_state(s), (x, y), self.f_mono, C.TEXT)
            if d is not None:
                self.text(f"d={d}", (lr.right - 14, y), self.f_mono, C.MUTED, right=True)
            y += row_h

        if r.get("trace_truncated"):
            self.text(f"Chỉ ghi lại {tracer.MAX_EVENTS} dòng", (x, lr.bottom - 48), self.f_small, C.ORANGE)
            self.text("thực thi đầu tiên.", (x, lr.bottom - 28), self.f_small, C.ORANGE)

    def draw_list(self):
        if self.in_trace():
            self.draw_trace_list()
            return
        lr = self.list_rect()
        self.panel(lr)
        self.text("Chuỗi hành động", (lr.x + 16, lr.y + 14), self.f_h)
        inner = pygame.Rect(lr.x + 8, lr.y + 48, lr.w - 16, lr.h - 56)
        if not self.result:
            self.text("Bấm \"Giải\" để chạy thuật toán", (lr.centerx, lr.centery), self.f_small, C.MUTED,
                      center=True)
            return
        path, acts = self.result["path"], self.result["actions"]
        self.text(f"{len(acts)} bước", (lr.right - 16, lr.y + 16), self.f_small, C.MUTED, right=True)
        row_h = 26
        visible = inner.h // row_h
        n = len(path)
        if self.follow:
            if self.step < self.list_scroll:
                self.list_scroll = self.step
            elif self.step >= self.list_scroll + visible:
                self.list_scroll = self.step - visible + 1
        self.list_scroll = max(0, min(self.list_scroll, max(0, n - visible)))

        self.screen.set_clip(inner)
        for i in range(self.list_scroll, min(n, self.list_scroll + visible + 1)):
            ry = inner.y + (i - self.list_scroll) * row_h
            row = pygame.Rect(inner.x, ry, inner.w, row_h - 2)
            if i == self.step:
                gfx.rect(self.screen, C.ACCENT_LIGHT, row, border_radius=6)
            label = "Bắt đầu" if i == 0 else acts[i - 1]
            col = C.ACCENT if i == self.step else (C.MUTED if i < self.step else C.TEXT)
            self.text(f"{i:>4}", (row.x + 8, row.y + 3), self.f_small, C.MUTED)
            self.text(label, (row.x + 56, row.y + 3), self.f_small, col)
            if self.mode == "vacuum":
                self.text(str(path[i]), (row.right - 8, row.y + 3), self.f_small, C.MUTED, right=True)
            if i == n - 1:
                self.text("ĐÍCH", (row.right - 8 if self.mode == "puzzle" else row.x + 120, row.y + 3),
                          self.f_small, C.GREEN, right=self.mode == "puzzle")
        self.screen.set_clip(None)

        if n > visible:
            bar_h = max(30, inner.h * visible // n)
            bar_y = inner.y + (inner.h - bar_h) * self.list_scroll // max(1, n - visible)
            gfx.rect(self.screen, C.SCROLL, (lr.right - 6, bar_y, 3, bar_h), border_radius=2)

    def list_click(self, pos):
        if not self.result or self.in_trace():
            return
        lr = self.list_rect()
        inner = pygame.Rect(lr.x + 8, lr.y + 48, lr.w - 16, lr.h - 56)
        if inner.collidepoint(pos):
            i = self.list_scroll + (pos[1] - inner.y) // 26
            if 0 <= i < len(self.result["path"]):
                self.step, self.anim_t, self.playing = i, 0, False

    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button in (1, 3):
            pos = gfx.unscale_pos(e.pos)
            if e.button == 1 and any(b.handle(pos) for b in self.buttons + self.tabs):
                return
            if self.list_rect().collidepoint(pos):
                if e.button == 1:
                    self.list_click(pos)
            elif self.main_rect().collidepoint(pos):
                self.handle_board_click(pos, e.button)
        elif e.type == pygame.MOUSEWHEEL:
            if self.list_rect().collidepoint(gfx.mouse_pos()):
                self.follow = False
                self.list_scroll -= e.y * 3
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                self.toggle_play()
            elif e.key == pygame.K_RIGHT:
                self.go_next()
            elif e.key == pygame.K_LEFT:
                self.go_prev()
            elif e.key == pygame.K_HOME:
                self.go_first()
            elif e.key == pygame.K_END:
                self.go_last()
            elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.solve()
            elif e.key == pygame.K_t and self.result:
                self.set_view("solution" if self.in_trace() else "trace")
            elif e.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                self.change_speed(1)
            elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.change_speed(-1)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(e)
            self.update(dt)
            self.draw()
        self.cancel_flag = True
        pygame.quit()


if __name__ == "__main__":
    App().run()
