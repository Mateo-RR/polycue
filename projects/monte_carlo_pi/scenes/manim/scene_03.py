from manim import *
from studio.theme import *
from studio.i18n import S
from studio.sync import SyncedScene

from common import N_DOTS, inside, points

SIDE = 3.0  # side of the small square that illustrates π/4


class Scene03(SyncedScene):
    scene_id = "scene_03"

    def construct(self):
        left, right, top, bottom = content_box()
        cy = (top + bottom) / 2
        hits = int(inside(points(N_DOTS)).sum())
        estimate = f"{4 * hits / N_DOTS:.3f}".replace(".", S("scene_03.decimal"))
        ratio = rf"\frac{{\text{{{S('scene_03.inside')}}}}}{{\text{{{S('scene_03.total')}}}}}"
        size = type_size("title") * 1.9

        # Left: the circle covers π/4 of the square.
        square = Square(side_length=SIDE, color=TEXT_MUTED, stroke_width=4, fill_color=SURFACE, fill_opacity=1)
        disc = Circle(radius=SIDE / 2, stroke_color=PRIMARY, stroke_width=4, fill_color=PRIMARY, fill_opacity=0.35)
        quarter = MathTex(r"\frac{\pi}{4}", color=TEXT, font_size=size)
        figure = VGroup(square, disc, quarter).move_to([left + SIDE / 2 + 0.4, cy, 0])

        # Right: the formula, rewritten twice.
        steps = [
            MathTex(ratio, r"\approx", r"\frac{\pi}{4}", font_size=size, color=TEXT),
            MathTex(r"\pi", r"\approx", r"4", r"\cdot", ratio, font_size=size, color=TEXT),
            MathTex(r"\pi", r"\approx", r"4", r"\cdot", rf"\frac{{{hits}}}{{{N_DOTS}}}", r"=\,", estimate,
                    font_size=size, color=TEXT),
        ]
        slot_left = square.get_right()[0] + 0.9
        for f in steps:
            f.scale_to_fit_width(min(f.width, right - slot_left))
            f.move_to([(slot_left + right) / 2, cy, 0])

        self.wait_until("ratio")
        self.play(FadeIn(square), GrowFromCenter(disc), run_time=self.frames(0.5))
        self.play(FadeIn(quarter), Write(steps[0]), run_time=self.until("times", gap=0.3, cap=1.4))

        self.wait_until("times")
        steps[1][2].set_color(ACCENT)
        self.play(TransformMatchingTex(steps[0], steps[1]), run_time=self.frames(0.6))

        self.wait_until("estimate")
        result = steps[2][-1].set_color(ACCENT)
        box = SurroundingRectangle(result, color=ACCENT, buff=0.12, corner_radius=0.1, stroke_width=4)
        self.play(TransformMatchingTex(steps[1], steps[2]), run_time=self.frames(0.6))
        self.play(Create(box), run_time=self.frames(0.4))
        self.finish()
