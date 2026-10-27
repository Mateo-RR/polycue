from manim import *
from studio.theme import *
from studio.i18n import S
from studio.sync import SyncedScene

from common import N_RUN, running_estimate

LOG_START, LOG_END = 1.0, np.log10(N_RUN)  # trace from 10 dots to N_RUN dots
Y_MIN, Y_MAX = 2.8, 3.8


class Scene04(SyncedScene):
    scene_id = "scene_04"

    def construct(self):
        left, right, top, bottom = content_box()
        est = running_estimate(N_RUN)
        axes = Axes(
            x_range=[1, 4.5, 1], y_range=[Y_MIN, Y_MAX, 0.2],
            x_length=right - left - 2.6, y_length=top - bottom - 1.8,
            axis_config={"color": TEXT_MUTED, "stroke_width": 3, "include_tip": False,
                         "font_size": type_size("caption") * 1.7},
            x_axis_config={"scaling": LogBase(custom_labels=True), "include_numbers": True},
        ).move_to([(left + right) / 2 + 0.4, (top + bottom) / 2, 0])
        # y labels built here, so the decimal separator follows the language (strings.json).
        sep = "{" + S("scene_04.decimal") + "}"
        axes.y_axis.add_labels({y: MathTex(f"{y:.1f}".replace(".", sep), font_size=type_size("caption") * 1.7)
                                for y in np.arange(Y_MIN, Y_MAX + 1e-9, 0.2)})
        x_label = Text(S("scene_04.axis_x"), font=FONT_SANS, font_size=type_size("caption"), color=TEXT_MUTED)
        x_label.next_to(axes.x_axis, DOWN, buff=0.15).align_to(axes.x_axis, RIGHT)
        y_label = Text(S("scene_04.axis_y"), font=FONT_SANS, font_size=type_size("caption"), color=TEXT_MUTED)
        y_label.next_to(axes.y_axis, UP, buff=0.15).align_to(axes.y_axis, LEFT)

        # The running estimate, sampled on a log grid and traced up to the tracker.
        grid = np.unique(np.logspace(LOG_START, LOG_END, 700).astype(int))
        values = np.clip(est[grid - 1], Y_MIN, Y_MAX)
        reach = ValueTracker(LOG_START)

        def trace():
            k = max(2, int(np.searchsorted(grid, 10 ** reach.get_value(), side="right")))
            pts = [axes.c2p(g, v) for g, v in zip(grid[:k], values[:k])]
            return VMobject(stroke_color=PRIMARY, stroke_width=4).set_points_as_corners(pts)

        def tip():
            k = max(1, int(np.searchsorted(grid, 10 ** reach.get_value(), side="right")))
            return Dot(axes.c2p(grid[k - 1], values[k - 1]), radius=0.08, color=ACCENT)

        pi_line = DashedLine(axes.c2p(10, PI), axes.c2p(10 ** 4.5, PI), color=SUCCESS, stroke_width=4, dash_length=0.15)
        pi_label = Text(S("scene_04.pi"), font=FONT_SANS, weight=BOLD, font_size=type_size("body"), color=SUCCESS)
        pi_label.next_to(pi_line, RIGHT, buff=0.2)

        self.fade_in(axes, x_label, y_label)
        curve, dot = always_redraw(trace), always_redraw(tip)
        self.add(curve, dot)
        self.wait_until("few")
        # A few dots first (slow, the estimate jumps), then many more (fast, it settles).
        self.play(reach.animate.set_value(2.0), run_time=self.until("more", min=0.5), rate_func=linear)
        self.play(reach.animate.set_value(3.5), run_time=self.until("converge", min=0.5), rate_func=linear)
        # The true value appears with the voice while the last dots settle on it.
        self.play(reach.animate.set_value(LOG_END), Create(pi_line), FadeIn(pi_label), run_time=self.frames(1.2),
                  rate_func=smooth)
        self.finish()
