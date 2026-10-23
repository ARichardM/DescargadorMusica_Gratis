package cl.arichard.descargador.util;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.view.View;
import android.view.ViewGroup;
import android.view.animation.DecelerateInterpolator;

import cl.arichard.descargador.R;

/** Minimal splash that animates the original MusicBox artwork as one piece. */
public final class AnimatedSplashView extends View {
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Bitmap cube;
    private final Path wavePath = new Path();
    private ValueAnimator animator;
    private ValueAnimator introAnimator;
    private float phase;
    private float intro;

    public AnimatedSplashView(Context context) {
        super(context);
        setBackgroundColor(Color.rgb(17, 22, 28));
        cube = BitmapFactory.decodeResource(getResources(), R.drawable.logo_cube);
        paint.setFilterBitmap(true);
        paint.setDither(true);
        setLayerType(View.LAYER_TYPE_SOFTWARE, null);
    }

    public void start() {
        animator = ValueAnimator.ofFloat(0f, 1f);
        animator.setDuration(1650);
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.setInterpolator(new DecelerateInterpolator());
        animator.addUpdateListener(value -> { phase = (float) value.getAnimatedValue(); invalidate(); });
        animator.start();
        introAnimator = ValueAnimator.ofFloat(0f, 1f);
        introAnimator.setDuration(650);
        introAnimator.setInterpolator(new DecelerateInterpolator(1.8f));
        introAnimator.addUpdateListener(value -> { intro = (float) value.getAnimatedValue(); invalidate(); });
        introAnimator.start();
        postDelayed(() -> animate().alpha(0f).setDuration(360).withEndAction(() -> {
            if (animator != null) animator.cancel();
            if (introAnimator != null) introAnimator.cancel();
            ViewGroup parent = (ViewGroup) getParent();
            if (parent != null) parent.removeView(this);
        }).start(), 2100);
    }

    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (cube == null) return;
        float cycle = (float) Math.sin(phase * Math.PI * 2);
        float size = Math.min(dp(250), Math.min(getWidth(), getHeight()) * .42f);
        float maxSide = Math.max(cube.getWidth(), cube.getHeight());
        float drawWidth = size * cube.getWidth() / maxSide;
        float drawHeight = size * cube.getHeight() / maxSide;
        float left = (getWidth() - drawWidth) / 2f;
        float top = (getHeight() - drawHeight) / 2f - dp(5) * Math.abs(cycle);
        android.graphics.RectF target = new android.graphics.RectF(left, top, left + drawWidth, top + drawHeight);
        paint.setAlpha(Math.round(255f * intro));
        canvas.drawBitmap(cube, null, target, paint);
        drawWave(canvas, left, top, drawWidth, drawHeight);
    }

    private void drawWave(Canvas canvas, float left, float top, float width, float height) {
        final float[][] raw = {
                {18,238},{32,245},{43,238},{56,192},{67,190},{83,282},{94,295},
                {120,122},{130,128},{148,361},{158,364},{177,244},{187,242},{201,302},{220,312}
        };
        float[] xs = new float[raw.length];
        float[] ys = new float[raw.length];
        for (int i = 0; i < raw.length; i++) {
            float t = i / (float) (raw.length - 1);
            float travel = (float) Math.sin(phase * Math.PI * 2 - raw[i][0] / 446f * Math.PI * 4);
            float anchor = (float) Math.sin(t * Math.PI);
            xs[i] = left + raw[i][0] / 446f * width;
            ys[i] = top + (raw[i][1] + 15f * travel * anchor) / 488f * height;
        }
        wavePath.reset();
        wavePath.moveTo(xs[0], ys[0]);
        for (int i = 1; i < raw.length - 1; i++) {
            wavePath.quadTo(xs[i], ys[i], (xs[i] + xs[i + 1]) / 2f, (ys[i] + ys[i + 1]) / 2f);
        }
        wavePath.lineTo(xs[xs.length - 1], ys[ys.length - 1]);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setStrokeWidth(9f / 446f * width);
        paint.setColor(Color.rgb(80, 233, 255));
        paint.setAlpha(Math.round(255f * intro));
        paint.setShadowLayer(12f / 446f * width, 0, 0, Color.rgb(32, 191, 255));
        canvas.drawPath(wavePath, paint);
        paint.clearShadowLayer();
        paint.setStyle(Paint.Style.FILL);
    }

    private float dp(float value) { return value * getResources().getDisplayMetrics().density; }
}
