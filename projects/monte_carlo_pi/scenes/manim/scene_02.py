from manim import *
from studio.theme import *
from studio.i18n import S
from studio.sync import SyncedScene

from common import N_DOTS, inside, points

SIDE = 5.2  # square side in frame units
DOT_R = 0.032


class Scene02(SyncedScene):
    scene_id = "scene_02"

    def construct(self):
        left, right, top, bottom = content_box()
        center = np.array([left + SIDE / 2 + 0.6, (top + bottom) / 2, 0])
        square = Square(side_length=SIDE, color=TEXT_MUTED, stroke_width=4).move_to(center)
        circle = Circle(radius=SIDE / 2, color=TEXT, stroke_width=4).move_to(center)

        pts = points(N_DOTS)
        hit = inside(pts)
        dots = [Dot(center + np.array([x, y, 0]) * SIDE / 2, radius=DOT_R, color=TEXT_MUTED) for x, y in pts]
        n = ValueTracker(0.0)
        shown = VGroup()

        # Counters on the right: total while the dots fall, inside/outside once they are sorted.
        def row(key, color):
            label = Text(S(f"scene_02.{key}"), font=FONT_SANS, font_size=type_size("body"), color=TEXT_MUTED)
            swatch = Dot(radius=0.11, color=color)
            return label, swatch

        def number(value, color):
            return Text(str(value), font=FONT_MONO, weight=BOLD, font_size=type_size("title"), color=color)

        x_text = square.get_right()[0] + 1.3
        labels = {}
        for i, (key, color) in enumerate([("inside", PRIMARY), ("outside", SECONDARY), ("total", TEXT)]):
            label, swatch = row(key, color)
            y = center[1] + 1.4 - i * 1.4
            swatch.move_to([x_text, y + 0.35, 0])
            label.next_to(swatch, RIGHT, buff=0.25)
            labels[key] = (VGroup(swatch, label), y - 0.3)

        def total_counter():
            group, y = labels["total"]
            text = number(int(n.get_value()), TEXT)
            return text.move_to([x_text + text.width / 2 - 0.11, y, 0])

        self.wait_until("square")
        self.play(Create(square), run_time=self.frames(0.6))
        self.play(Create(circle), run_time=self.frames(0.6))

        self.wait_until("dots")
        rate = N_DOTS / max(0.5, self.cue("inside") - self.cue("dots") - 0.3)
        shown.add_updater(lambda m: m.add(*dots[len(m.submobjects):int(n.get_value())]))
        n.add_updater(lambda m, dt: m.set_value(min(N_DOTS, m.get_value() + rate * dt)))
        # The counter changes its glyph count every frame, so it appears directly instead of fading in.
        counter = always_redraw(total_counter)
        self.add(n, shown, counter)
        self.play(FadeIn(labels["total"][0]), run_time=self.frames(0.3))

        self.wait_until("inside")
        n.clear_updaters()
        n.set_value(N_DOTS)
        shown.clear_updaters()
        shown.add(*dots[len(shown.submobjects):])
        counter.clear_updaters()
        ins = VGroup(*[d for d, h in zip(dots, hit) if h])
        out = VGroup(*[d for d, h in zip(dots, hit) if not h])
        counts = []
        for key, color, value in [("inside", PRIMARY, len(ins)), ("outside", SECONDARY, len(out))]:
            group, y = labels[key]
            text = number(value, color)
            counts.append(VGroup(group, text.move_to([x_text + text.width / 2 - 0.11, y, 0])))
        self.play(ins.animate.set_color(PRIMARY), out.animate.set_color(SECONDARY),
                  circle.animate.set_color(PRIMARY), *[FadeIn(c, shift=RIGHT * 0.2) for c in counts],
                  run_time=self.frames(0.6))
        self.finish()
