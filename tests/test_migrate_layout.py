from migrate_layout import rewrite_manim, rewrite_remotion


def test_rewrite_manim_drops_the_old_package_prefix():
    src = "from manim import *\nfrom scenes.my_video.common import *\nimport scenes.my_video.signals as sig\n"
    assert rewrite_manim(src, "my_video") == "from manim import *\nfrom common import *\nimport signals as sig\n"


def test_rewrite_manim_only_touches_its_own_slug():
    src = "from scenes.other_video.common import *\n"
    assert rewrite_manim(src, "my_video") == src


def test_rewrite_remotion_uses_the_studio_alias_at_any_depth():
    src = 'import { Fade } from "../../studio/Fade";\nimport type { SceneProps } from \'../../../studio/types\';\n'
    assert rewrite_remotion(src) == 'import { Fade } from "@studio/Fade";\nimport type { SceneProps } from \'@studio/types\';\n'


def test_rewrite_remotion_keeps_local_imports():
    src = 'import { Card } from "./ui";\nimport { colors } from "@studio/theme";\n'
    assert rewrite_remotion(src) == src
