"""从平台 SVG 生成居中的桌面图标（macOS，需 Pillow）。"""

from pathlib import Path
import subprocess
import tempfile

from PIL import Image


def main():
    actuator = Path(__file__).resolve().parents[1]
    source = actuator.parent / "mango-console" / "src" / "assets" / "logo.svg"
    with tempfile.TemporaryDirectory(prefix="mango-icons-") as temporary:
        rendered = Path(temporary) / "logo.png"
        subprocess.run(["sips", "-s", "format", "png", "-z", "2048", "2048",
                        str(source), "--out", str(rendered)], check=True, capture_output=True)
        image = Image.open(rendered).convert("RGBA")
        bounds = image.getchannel("A").getbbox()
        if bounds is None:
            raise RuntimeError("平台 Logo 为空")
        # 按实际图形边界居中，避免 SVG 画布留白继续传播到各尺寸图标。
        logo = image.crop(bounds)
        logo.thumbnail((768, 768), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (1024, 1024), "white")
        offset = ((1024 - logo.width) // 2, (1024 - logo.height) // 2)
        canvas.alpha_composite(logo, offset)
        canvas.save(actuator / "assets" / "app_icon.icns", format="ICNS")
        canvas.save(actuator / "assets" / "app_icon.ico", format="ICO",
                    sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
        ui_logo = Image.new("RGBA", (256, 256))
        logo.thumbnail((224, 224), Image.Resampling.LANCZOS)
        ui_logo.alpha_composite(logo, ((256 - logo.width) // 2, (256 - logo.height) // 2))
        ui_logo.save(actuator / "assets" / "platform_logo.png")
        print("桌面图标与透明背景的平台 Logo 已更新")


if __name__ == "__main__":
    main()
