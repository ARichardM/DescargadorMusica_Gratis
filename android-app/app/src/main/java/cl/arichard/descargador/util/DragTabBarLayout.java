package cl.arichard.descargador.util;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.drawable.Drawable;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.widget.LinearLayout;
import androidx.core.content.ContextCompat;
import cl.arichard.descargador.R;

/** Taps stay on the two buttons; dragging moves the selector and page continuously. */
public class DragTabBarLayout extends LinearLayout {
    public interface Listener { void onProgress(float progress); void onSelected(boolean search); }
    private Listener listener;
    private final Drawable indicator;
    private final int slop;
    private float progress, downX, downY, initialProgress;
    private boolean dragging, rejected;
    private ValueAnimator animation;
    public DragTabBarLayout(Context context, AttributeSet attrs) {
        super(context, attrs); setWillNotDraw(false); setClickable(true);
        slop = ViewConfiguration.get(context).getScaledTouchSlop();
        indicator = ContextCompat.getDrawable(context, R.drawable.bg_nav_tab_indicator).mutate();
    }
    public void setListener(Listener listener) { this.listener = listener; }
    public void setProgress(float value) { progress = Math.max(0, Math.min(1, value)); invalidate(); }
    public void select(boolean search, boolean animate) {
        if (animation != null) animation.cancel();
        float target = search ? 0 : 1;
        if (!animate) { setProgress(target); return; }
        animation = ValueAnimator.ofFloat(progress, target); animation.setDuration(250);
        animation.setInterpolator(new android.view.animation.DecelerateInterpolator());
        animation.addUpdateListener(a -> setProgress((float) a.getAnimatedValue())); animation.start();
    }
    @Override protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (getChildCount() < 2) return;
        View a = getChildAt(0), b = getChildAt(1);
        int left = Math.round(a.getLeft() + (b.getLeft() - a.getLeft()) * progress);
        int width = Math.round(a.getWidth() + (b.getWidth() - a.getWidth()) * progress);
        indicator.setBounds(left, a.getTop(), left + width, a.getBottom()); indicator.draw(canvas);
    }
    private void begin(MotionEvent e) {
        if (animation != null) animation.cancel();
        downX = e.getX(); downY = e.getY(); initialProgress = progress; dragging = false; rejected = false;
    }
    private boolean claim(MotionEvent e) {
        if (e.getPointerCount() != 1) rejected = true;
        if (rejected) return false;
        float dx = e.getX() - downX, dy = e.getY() - downY;
        if (!dragging && Math.max(Math.abs(dx), Math.abs(dy)) > slop) {
            if (Math.abs(dx) <= Math.abs(dy)) { rejected = true; return false; }
            dragging = true; getParent().requestDisallowInterceptTouchEvent(true);
        }
        return dragging;
    }
    @Override public boolean onInterceptTouchEvent(MotionEvent e) {
        if (e.getActionMasked() == MotionEvent.ACTION_DOWN) begin(e);
        else if (e.getActionMasked() == MotionEvent.ACTION_MOVE) return claim(e);
        return false;
    }
    @Override public boolean onTouchEvent(MotionEvent e) {
        switch (e.getActionMasked()) {
            case MotionEvent.ACTION_MOVE:
                if (claim(e)) {
                    float centers = getChildCount() >= 2 ? getChildAt(1).getX() - getChildAt(0).getX() : getWidth() / 2f;
                    setProgress(initialProgress + (e.getX() - downX) / Math.max(1, centers));
                    if (listener != null) listener.onProgress(progress);
                    return true;
                }
                break;
            case MotionEvent.ACTION_UP:
                if (dragging) {
                    dragging = false; getParent().requestDisallowInterceptTouchEvent(false);
                    if (listener != null) listener.onSelected(progress < .5f);
                    return true;
                }
                break;
            case MotionEvent.ACTION_CANCEL:
                dragging = false; getParent().requestDisallowInterceptTouchEvent(false);
                if (listener != null) listener.onSelected(initialProgress < .5f);
                return true;
        }
        return super.onTouchEvent(e);
    }
}
