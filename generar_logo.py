"""Genera los iconos de la aplicación a partir de geometría vectorial sencilla."""

from pathlib import Path

from PIL import Image, ImageDraw


ASSETS = Path(__file__).resolve().parent / "assets"
SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <title>Descargador</title>
  <rect x="16" y="16" width="224" height="224" rx="60" fill="#6251e8"/>
  <g stroke="white" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <path d="M76 156V88L138 74V142"/>
    <path d="M76 100L138 86"/>
    <path d="M184 122V178M166 160L184 178L202 160M162 199H206"/>
  </g>
  <ellipse cx="66" cy="158" rx="17" ry="13" fill="white" transform="rotate(-20 66 158)"/>
  <ellipse cx="128" cy="144" rx="17" ry="13" fill="white" transform="rotate(-20 128 144)"/>
</svg>
'''


def generate():
    ASSETS.mkdir(exist_ok=True)
    scale = 4
    image = Image.new("RGBA", (256 * scale, 256 * scale))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((64, 64, 960, 960), radius=240, fill="#6251e8")

    def line(points, width=12):
        points = [(x * scale, y * scale) for x, y in points]
        draw.line(points, fill="white", width=width * scale, joint="curve")
        radius = width * scale / 2
        for x, y in points:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="white")

    line([(76, 156), (76, 88), (138, 74), (138, 142)])
    line([(76, 100), (138, 86)])
    line([(184, 122), (184, 178)])
    line([(166, 160), (184, 178), (202, 160)])
    line([(162, 199), (206, 199)])
    for x, y in ((66, 158), (128, 144)):
        note = Image.new("RGBA", image.size)
        ImageDraw.Draw(note).ellipse(((x - 17) * scale, (y - 13) * scale,
                                     (x + 17) * scale, (y + 13) * scale), fill="white")
        note = note.rotate(20, resample=Image.Resampling.BICUBIC, center=(x * scale, y * scale))
        image.alpha_composite(note)
        note.close()
    logo = image.resize((256, 256), Image.Resampling.LANCZOS)
    logo.save(ASSETS / "logo.png")
    logo.resize((48, 48), Image.Resampling.LANCZOS).save(ASSETS / "logo-48.png")
    logo.save(ASSETS / "descargador.ico", sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
    (ASSETS / "logo.svg").write_text(SVG, encoding="utf-8")
    image.close()
    logo.close()


if __name__ == "__main__":
    generate()
