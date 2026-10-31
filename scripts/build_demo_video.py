"""Build a silent walkthrough from screenshots of verified live interactions."""

from __future__ import annotations

import subprocess
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FRAMES = ASSETS / "video_frames"
SIZE = (1280, 720)
FONT_FILE = Path("C:/Windows/Fonts/msyh.ttc")


def font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_FILE), size=size)


def base(slide: int, title: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", SIZE, "#f6f8fc")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1280, 62), fill="#16253d")
    draw.text((34, 16), title, fill="white", font=font(26))
    draw.text((1194, 20), f"{slide}/8", fill="#c7d7f0", font=font(20))
    return image, draw


def title_card(slide: int, title: str, lines: list[str]) -> Image.Image:
    image, draw = base(slide, "个人收支管理 Agent · 演示")
    draw.text((78, 160), title, fill="#17243c", font=font(52))
    for index, line in enumerate(lines):
        draw.text((82, 270 + index * 76), line, fill="#344a67", font=font(29))
    draw.rounded_rectangle((82, 603, 1198, 650), radius=12, fill="#dce9fa")
    draw.text((102, 610), "虚构人民币消费数据 · 本机 DeepSeek 工具调用", fill="#245488", font=font(23))
    return image


def screenshot_card(slide: int, filename: str, caption: str) -> Image.Image:
    image, draw = base(slide, "个人收支管理 Agent · 真实在线交互截图")
    source = Image.open(ASSETS / filename).convert("RGB")
    source = source.crop((300, 100, 1600, 760))
    source.thumbnail((1240, 555), Image.Resampling.LANCZOS)
    x = (1280 - source.width) // 2
    y = 70 + (555 - source.height) // 2
    image.paste(source, (x, y))
    draw.rectangle((0, 634, 1280, 720), fill="#183457")
    draw.text((40, 654), caption, fill="white", font=font(26))
    return image


def main() -> None:
    FRAMES.mkdir(parents=True, exist_ok=True)
    cards = [
        (title_card(1, "用中文提问，查账与预算", ["DeepSeek 理解问题并选择工具", "Python 计算金额，页面展示依据", "模拟日期：2026-10-31"]), 12),
        (screenshot_card(2, "demo-query.png", "① 10 月餐饮支出：280.00 元；可展开计算依据"), 18),
        (screenshot_card(3, "demo-budget.png", "② 餐饮预算 250.00 元，已用 280.00 元，超支 30.00 元"), 18),
        (screenshot_card(4, "demo-clarify.png", "③ 没有指定月份：先追问，避免猜测"), 16),
        (screenshot_card(5, "demo-followup.png", "④ 补充“10 月”后继续对话，返回 280.00 元"), 18),
        (title_card(6, "如何验证", ["九条 DeepSeek 在线问答：9/9 通过", "本地自动测试：12/12 通过", "跨月差额由 Python 工具计算"]), 20),
        (title_card(7, "错误处理", ["无记录月份：明确说明无法推断", "缺少月份：追问用户", "API 故障：给出安全提示，不泄露密钥"]), 12),
        (title_card(8, "项目代码与记录", ["github.com/hwy77-h/budget-agent-demo", "含虚构 CSV、测试、需求与验收记录", "视频由真实交互截图制作，静音字幕演示"]), 12),
    ]
    playlist = []
    for index, (card, duration) in enumerate(cards):
        path = FRAMES / f"slide_{index:02d}.png"
        card.save(path, optimize=True)
        playlist.extend([f"file '{path.name}'", f"duration {duration}"])
    playlist.append(f"file 'slide_{len(cards)-1:02d}.png'")
    (FRAMES / "timeline.txt").write_text("\n".join(playlist) + "\n", encoding="utf-8")

    output = ASSETS / "demo-video.mp4"
    subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0",
            "-i", "timeline.txt", "-t", "126", "-r", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(output),
        ],
        cwd=FRAMES,
        check=True,
        capture_output=True,
        text=True,
    )
    print(f"Created {output}")


if __name__ == "__main__":
    main()
