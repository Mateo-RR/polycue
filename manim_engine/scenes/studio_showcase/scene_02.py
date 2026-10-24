from manim import *
from studio.theme import *
from studio.i18n import S
from studio.sync import SyncedScene

TILE_W, TILE_H, GAP = 5.8, 2.7, 0.3
PAD = 0.3  # inner padding of a tile
REVEAL = 0.5  # seconds a tile takes to light up

# Simulation tile: samples of a standard normal, revealed progressively.
N_SAMPLES = 800
BINS = 17
HIST_RANGE = 3.0
PEAK_SHARE = (2 * HIST_RANGE / BINS) * 0.3989  # expected share of samples in the central bin

WORD_PERIOD = 0.55  # seconds per greeting
SUB_PERIOD = 2.4  # seconds per karaoke pass


class Scene02(SyncedScene):
    scene_id = "scene_02"

    def construct(self):
        left, right, top, bottom = content_box()
        cx, cy = (left + right) / 2, (top + bottom) / 2
        centers = [np.array([cx + dx * (TILE_W + GAP) / 2, cy + dy * (TILE_H + GAP) / 2, 0])
                   for dy in (1, -1) for dx in (-1, 1)]
        specs = [("math", PRIMARY), ("sims", SECONDARY), ("languages", SUCCESS), ("subs", ACCENT)]

        frames, labels = [], []
        for (key, color), c in zip(specs, centers):
            frame = RoundedRectangle(corner_radius=0.25, width=TILE_W, height=TILE_H, stroke_color=BORDER,
                                     stroke_width=4, fill_color=SURFACE, fill_opacity=1).move_to(c)
            label = Text(S(f"scene_02.{key}"), font=FONT_SANS, weight=SEMIBOLD, font_size=type_size("caption"),
                         color=color)
            label.move_to(frame.get_corner(UL) + np.array([PAD + label.width / 2, -PAD - label.height / 2, 0]))
            frames.append(frame)
            labels.append(label)
        stages = [c + DOWN * 0.22 for c in centers]

        builders = [self.math_tile, self.sims_tile, self.languages_tile, self.subs_tile]
        self.fade_in(*frames)

        for i, ((key, color), build) in enumerate(zip(specs, builders)):
            self.wait_until(key)
            content, start = build(stages[i], frames[i], labels[i])
            self.play(frames[i].animate.set_stroke(color), FadeIn(labels[i]), FadeIn(content),
                      run_time=self.frames(REVEAL))
            start()

        # Closing title over the still-moving grid, dimmed by a veil of background color.
        self.wait_until("title")
        grid = VGroup(*frames)
        veil = Rectangle(width=grid.width + 0.2, height=grid.height + 0.2, stroke_width=0,
                         fill_color=BG, fill_opacity=0.92).move_to(grid)
        title = Text(S("scene_02.title"), font=FONT_SANS, weight=BOLD, font_size=type_size("title"), color=TEXT)
        chips = VGroup()
        for i, (key, color) in enumerate([("manim", SECONDARY), ("remotion", PRIMARY), ("agent", ACCENT)]):
            if i:
                chips.add(Text("+", font=FONT_SANS, weight=BOLD, font_size=type_size("body"), color=TEXT_MUTED))
            name = Text(S(f"scene_02.{key}"), font=FONT_SANS, weight=SEMIBOLD, font_size=type_size("body"), color=color)
            pill = RoundedRectangle(corner_radius=0.3, width=name.width + 0.6, height=name.height + 0.4,
                                    stroke_color=color, stroke_width=4, fill_color=SURFACE, fill_opacity=1)
            chips.add(VGroup(pill, name.move_to(pill)))
        chips.arrange(RIGHT, buff=0.3)
        closing = VGroup(title, chips).arrange(DOWN, buff=0.55).move_to(content_center())
        fit_in_content(closing)
        self.play(FadeIn(veil), FadeIn(title, shift=UP * 0.2), FadeIn(chips, shift=UP * 0.2),
                  run_time=self.frames(0.6))
        self.finish()

    # ---- tiles: each returns (content, start) where start() attaches the motion updaters ----

    def clock(self):
        t = ValueTracker(0.0)
        self.add(t)
        return t, lambda: t.add_updater(lambda m, dt: m.increment_value(dt))

    def math_tile(self, stage, frame, label):
        """A rotating phasor tracing a sine wave, with Euler's formula."""
        t, start = self.clock()
        r, k = 0.62, 2.4
        center = stage + LEFT * 1.75
        x0, x1 = center[0] + 1.05, frame.get_right()[0] - PAD
        ring = Circle(radius=r, color=BORDER, stroke_width=3).move_to(center)

        def tip():
            a = 2.4 * t.get_value()
            return center + r * np.array([np.cos(a), np.sin(a), 0])

        def wave():
            a = 2.4 * t.get_value()
            xs = np.linspace(x0, x1, 120)
            pts = [np.array([x, center[1] + r * np.sin(a - k * (x - x0)), 0]) for x in xs]
            return VMobject(stroke_color=PRIMARY, stroke_width=5).set_points_smoothly(pts)

        arm = always_redraw(lambda: Line(center, tip(), color=TEXT, stroke_width=5))
        dot = always_redraw(lambda: Dot(tip(), radius=0.08, color=PRIMARY))
        link = always_redraw(lambda: DashedLine(tip(), np.array([x0, tip()[1], 0]), color=TEXT_MUTED,
                                                stroke_width=2, dash_length=0.06))
        curve = always_redraw(wave)
        formula = MathTex(r"e^{i\theta} = \cos\theta + i\sin\theta", color=TEXT, font_size=type_size("body") * 1.4)
        formula.scale_to_fit_width(min(formula.width, TILE_W - label.width - 3 * PAD))
        formula.move_to(np.array([frame.get_right()[0] - PAD - formula.width / 2, label.get_center()[1], 0]))
        return VGroup(ring, link, curve, arm, dot, formula), start

    def sims_tile(self, stage, frame, label):
        """A histogram of normal samples converging to the bell curve."""
        rng = np.random.default_rng(7)
        idx = np.clip(((rng.normal(size=N_SAMPLES) + HIST_RANGE) / (2 * HIST_RANGE) * BINS).astype(int), 0, BINS - 1)
        n = ValueTracker(1.0)
        self.add(n)
        rate = N_SAMPLES / max(1.0, self.cue("title") - self.cue("sims"))
        hist_w, hist_h = TILE_W - 2 * PAD - 0.4, 1.55
        base = stage + DOWN * 0.78
        bin_w = hist_w / BINS
        scale = hist_h / (N_SAMPLES * PEAK_SHARE * 1.3)

        def bars():
            counts = np.bincount(idx[: int(n.get_value())], minlength=BINS)
            group = VGroup()
            for b, c in enumerate(counts):
                h = max(c * scale, 0.02)
                x = base[0] - hist_w / 2 + (b + 0.5) * bin_w
                group.add(Rectangle(width=bin_w * 0.82, height=h, stroke_width=0, fill_color=SECONDARY,
                                    fill_opacity=0.9).move_to([x, base[1] + h / 2, 0]))
            return group

        def bell():
            share = n.get_value() * (2 * HIST_RANGE / BINS) * scale
            xs = np.linspace(-HIST_RANGE, HIST_RANGE, 90)
            pts = [np.array([base[0] + x / (2 * HIST_RANGE) * hist_w,
                             base[1] + share * np.exp(-x * x / 2) / np.sqrt(2 * PI), 0]) for x in xs]
            return VMobject(stroke_color=TEXT, stroke_width=4).set_points_smoothly(pts)

        def counter():
            text = Text(S("scene_02.samples").format(n=int(n.get_value())), font=FONT_MONO,
                        font_size=type_size("caption"), color=TEXT_MUTED)
            return text.move_to(np.array([frame.get_right()[0] - PAD - text.width / 2, label.get_center()[1], 0]))

        axis = Line(base + LEFT * hist_w / 2, base + RIGHT * hist_w / 2, color=BORDER, stroke_width=3)
        content = VGroup(axis, always_redraw(bars), always_redraw(bell), always_redraw(counter))
        return content, lambda: n.add_updater(lambda m, dt: m.set_value(min(N_SAMPLES, m.get_value() + rate * dt)))

    def languages_tile(self, stage, frame, label):
        """The same greeting cycling through languages, with the active locale lit."""
        t, start = self.clock()
        greetings = S("scene_02.greetings").split("|")
        codes = S("scene_02.locales").split("|")
        words = VGroup(*[Text(g, font=FONT_SANS, weight=BOLD, font_size=type_size("title"), color=TEXT)
                         .move_to(stage + UP * 0.3) for g in greetings])
        chips = VGroup(*[Text(c, font=FONT_MONO, font_size=type_size("caption"), color=TEXT_MUTED) for c in codes])
        chips.arrange(RIGHT, buff=0.3).scale_to_fit_width(min(chips.width, TILE_W - 2 * PAD)).move_to(stage + DOWN * 0.7)

        def show(group):
            # Each period: the previous greeting fades out, then the next one fades in.
            step = t.get_value() / WORD_PERIOD
            phase = step % 1
            active = int(step) % len(greetings)
            previous = (active - 1) % len(greetings)
            if step >= 1 and phase < 0.15:
                shown, opacity = previous, 1 - phase / 0.15
            else:
                shown, opacity = active, 1.0 if step < 1 else min(1.0, (phase - 0.15) / 0.2)
            for i, w in enumerate(words):
                w.set_opacity(opacity if i == shown else 0)
            for i, c in enumerate(chips):
                c.set_color(SUCCESS if i == shown else TEXT_MUTED)

        content = VGroup(words, chips)
        show(content)
        return content, lambda: (start(), content.add_updater(show))

    def subs_tile(self, stage, frame, label):
        """A karaoke subtitle line driven by a playhead over the word timeline."""
        t, start = self.clock()
        # One Text for the whole line keeps a common baseline; glyphs are then grouped per word.
        line = S("scene_02.sub_line")
        full = Text(line, font=FONT_SANS, weight=BOLD, font_size=type_size("body"), color=TEXT_MUTED)
        words, i = VGroup(), 0
        for w in line.split():
            n = len(w.replace(" ", ""))
            words.add(VGroup(*full[i:i + n]))
            i += n
        words.scale_to_fit_width(min(words.width, TILE_W - 2 * PAD)).move_to(stage + UP * 0.25)
        y = words.get_bottom()[1] - 0.55
        x_left, x_right = words.get_left()[0], words.get_right()[0]
        track = Line([x_left, y, 0], [x_right, y, 0], color=BORDER, stroke_width=4)
        ticks = VGroup(*[Line([w.get_left()[0], y - 0.12, 0], [w.get_left()[0], y + 0.12, 0], color=TEXT_MUTED,
                              stroke_width=3) for w in words])

        def head_x():
            return x_left + (t.get_value() % SUB_PERIOD) / SUB_PERIOD * (x_right - x_left)

        def paint(group):
            x = head_x()
            for w in words:
                w.set_color(ACCENT if w.get_left()[0] <= x <= w.get_right()[0] + 0.16
                            else TEXT if w.get_right()[0] < x else TEXT_MUTED)

        played = always_redraw(lambda: Line([x_left, y, 0], [max(head_x(), x_left + 1e-3), y, 0], color=ACCENT,
                                            stroke_width=4))
        head = always_redraw(lambda: Dot([head_x(), y, 0], radius=0.09, color=ACCENT))
        content = VGroup(words, track, ticks, played, head)
        paint(content)
        return content, lambda: (start(), words.add_updater(paint))
