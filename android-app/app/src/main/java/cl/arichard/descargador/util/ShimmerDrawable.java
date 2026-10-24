package cl.arichard.descargador.util;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.PixelFormat;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;
import android.os.SystemClock;
import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import cl.arichard.descargador.R;

/** Lightweight animated placeholder used while artwork is being decoded or downloaded. */
public final class ShimmerDrawable extends Drawable implements Runnable {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final int baseColor;
    private final int highlightColor;
    private final long startedAt = SystemClock.uptimeMillis();

    public ShimmerDrawable(Context context) {
        baseColor = ContextCompat.getColor(context, R.color.skeleton_base);
        highlightColor = ContextCompat.getColor(context, R.color.skeleton_highlight);
    }

    @Override public void draw(@NonNull Canvas canvas) {
        float width = Math.max(1, getBounds().width());
        float phase = (SystemClock.uptimeMillis() - startedAt) % 1250L / 1250f;
        float center = -width + phase * width * 3f;
        paint.setShader(new LinearGradient(center - width, 0, center + width, 0,
                new int[]{baseColor, baseColor, highlightColor, baseColor, baseColor},
                new float[]{0f, .28f, .5f, .72f, 1f}, Shader.TileMode.CLAMP));
        canvas.drawRect(getBounds(), paint);
        scheduleSelf(this, SystemClock.uptimeMillis() + 16L);
    }

    @Override public void run() { invalidateSelf(); }
    @Override public void setAlpha(int alpha) { paint.setAlpha(alpha); }
    @Override public void setColorFilter(android.graphics.ColorFilter filter) { paint.setColorFilter(filter); }
    @Override public int getOpacity() { return PixelFormat.OPAQUE; }
}
