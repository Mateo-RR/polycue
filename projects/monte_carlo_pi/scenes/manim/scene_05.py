from manim import *
from studio.theme import *
from studio.i18n import S
from studio.sync import SyncedScene

COL_X = 2.6  # column centers at ±COL_X
ROW_GAP = 1.7


class Scene05(SyncedScene):
    scene_id = "scene_05"

    def construct(self):
        left, right, top, bottom = content_box()
        cx = (left + right) / 2
        formula = MathTex(rf"\text{{{S('scene_05.error')}}}", r"\propto", r"\frac{1}{\sqrt{n}}",
                          font_size=type_size("title") * 1.4, color=TEXT)
        formula.move_to([cx, top - formula.height / 2 - 0.35, 0])

        # Two-column comparison: dots on the left, error on the right.
        head_y = formula.get_bottom()[1] - 0.75
        heads = VGroup(*[Text(S(f"scene_05.{key}"), font=FONT_SANS, font_size=type_size("body"), color=TEXT_MUTED)
                         .move_to([cx + side * COL_X, head_y, 0]) for key, side in (("dots", -1), ("error", 1))])
        rule = Line([cx - COL_X - 1.6, head_y - 0.4, 0], [cx + COL_X + 1.6, head_y - 0.4, 0], color=BORDER, stroke_width=3)

        def cell(text, side, row, color):
            return Text(text, font=FONT_MONO, weight=BOLD, font_size=type_size("title"), color=color).move_to(
                [cx + side * COL_X, head_y - 1.15 - row * ROW_GAP, 0])

        counts = S("scene_05.counts").split("|")
        errors = S("scene_05.errors").split("|")
        rows = [VGroup(cell(counts[r], -1, r, TEXT), cell(errors[r], 1, r, TEXT)) for r in range(2)]

        def step(column, label_key, side, color):
            a, b = rows[0][column], rows[1][column]
            arrow = Arrow(a.get_bottom() + DOWN * 0.1, b.get_top() + UP * 0.1, buff=0, color=color, stroke_width=5,
                          max_tip_length_to_length_ratio=0.25)
            label = Text(S(f"scene_05.{label_key}"), font=FONT_MONO, weight=BOLD, font_size=type_size("body"), color=color)
            label.next_to(arrow, side * RIGHT, buff=0.25)
            return VGroup(arrow, label)

        more = step(0, "more", -1, ACCENT)
        less = step(1, "less", 1, SUCCESS)

        self.fade_in(heads, rule)
        self.wait_until("error")
        self.play(Write(formula), run_time=self.until("hundred", gap=0.3, cap=1.4))

        self.wait_until("hundred")
        self.play(FadeIn(rows[0], shift=UP * 0.2), run_time=self.frames(0.4))
        self.play(GrowArrow(more[0]), FadeIn(more[1]), FadeIn(rows[1][0], shift=DOWN * 0.2),
                  run_time=self.until("digit", gap=0.3, cap=1.0))

        self.wait_until("digit")
        new_digit = rows[1][1][-1]  # the extra significant digit of the smaller error
        self.play(GrowArrow(less[0]), FadeIn(less[1]), FadeIn(rows[1][1], shift=DOWN * 0.2), run_time=self.frames(0.5))
        self.play(new_digit.animate.set_color(SUCCESS).scale(1.25), run_time=self.frames(0.4))
        self.finish()
