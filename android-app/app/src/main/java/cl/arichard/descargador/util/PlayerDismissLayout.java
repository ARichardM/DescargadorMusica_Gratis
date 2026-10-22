package cl.arichard.descargador.util;

import android.content.Context;
import android.graphics.Rect;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewConfiguration;
import android.widget.LinearLayout;
import cl.arichard.descargador.R;

/** Only a downward drag beginning on the artwork can dismiss the full player. */
public class PlayerDismissLayout extends LinearLayout {
    private float downX, downY;
    private long downTime;
    private boolean eligible, dragging, rejected;
    private final int slop;
    private Runnable dismiss;

    public PlayerDismissLayout(Context context, AttributeSet attrs) {
        super(context, attrs); slop = ViewConfiguration.get(context).getScaledTouchSlop();
    }
    public void setDismissAction(Runnable action) { dismiss = action; }
    private void begin(MotionEvent event) {
        downX = event.getRawX(); downY = event.getRawY(); downTime = event.getEventTime();
        dragging = false; rejected = false;
        View artwork = findViewById(R.id.playerArtworkArea);
        Rect rect = new Rect();
        eligible = artwork != null && artwork.getGlobalVisibleRect(rect) && rect.contains((int) downX, (int) downY);
    }
    private boolean claim(MotionEvent event) {
        if (!eligible || rejected) return false;
        if (event.getPointerCount() != 1) { rejected = true; reset(); return false; }
        float dx = event.getRawX() - downX, dy = event.getRawY() - downY;
        if (!dragging && (Math.abs(dx) > slop * 2 || Math.abs(dy) > slop * 2)) {
            // Lock out horizontal, upward and diagonal movement for the rest of this gesture.
            if (dy < 0 || dy <= Math.abs(dx) * 1.5f) { rejected = true; return false; }
            dragging = true;
            getParent().requestDisallowInterceptTouchEvent(true);
        }
        return dragging;
    }
    @Override public boolean onInterceptTouchEvent(MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) begin(event);
        if (event.getActionMasked() == MotionEvent.ACTION_MOVE) return claim(event);
        return false;
    }
    @Override public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN: begin(event); return eligible || super.onTouchEvent(event);
            case MotionEvent.ACTION_MOVE:
                if (claim(event)) {
                    float dy = Math.max(0, event.getRawY() - downY);
                    setTranslationY(dy * .8f);
                    setAlpha(1f - Math.min(.35f, dy / Math.max(1, getHeight())));
                }
                return eligible;
            case MotionEvent.ACTION_UP:
                float distance = event.getRawY() - downY;
                float density = getResources().getDisplayMetrics().density;
                float speed = distance * 1000 / Math.max(1, event.getEventTime() - downTime);
                boolean close = dragging && !rejected && (distance > 120 * density
                        || (distance > 56 * density && speed > 900 * density));
                boolean handled = eligible;
                dragging = false; eligible = false;
                getParent().requestDisallowInterceptTouchEvent(false);
                if (close && dismiss != null) dismiss.run(); else reset();
                return handled;
            case MotionEvent.ACTION_POINTER_DOWN:
            case MotionEvent.ACTION_CANCEL:
                eligible = false; rejected = true; dragging = false;
                getParent().requestDisallowInterceptTouchEvent(false); reset(); return true;
        }
        return super.onTouchEvent(event);
    }
    private void reset() { animate().translationY(0).alpha(1f).setDuration(180).start(); }
}
