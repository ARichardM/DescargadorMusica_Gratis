package cl.arichard.descargador.util;

import android.content.Context;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.ViewConfiguration;
import android.widget.LinearLayout;

/** Intercepts drags over child buttons without stealing ordinary taps. */
public class SwipeActionsLayout extends LinearLayout {
    private float downX, downY;
    private int axis;
    private boolean rejected;
    private final int slop;
    private Runnable next, previous, expand;
    public interface HorizontalDragListener {
        void onDrag(float distance);
        void onEnd(boolean committed);
    }
    private HorizontalDragListener dragListener;
    public interface VerticalDragListener { void onDrag(float distance); void onEnd(float distance, boolean cancelled); }
    private VerticalDragListener verticalListener;
    public void setVerticalDragListener(VerticalDragListener listener) { verticalListener = listener; }
    public void setHorizontalDragListener(HorizontalDragListener listener) { dragListener = listener; }

    public SwipeActionsLayout(Context context, AttributeSet attrs) {
        super(context, attrs);
        slop = ViewConfiguration.get(context).getScaledTouchSlop();
        setClickable(true);
    }

    public void setSwipeActions(Runnable next, Runnable previous, Runnable expand) {
        this.next = next; this.previous = previous; this.expand = expand;
    }

    private void begin(MotionEvent event) {
        downX = event.getX(); downY = event.getY(); axis = 0; rejected = false;
    }
    private boolean claim(MotionEvent event) {
        if (event.getPointerCount() != 1) { rejected = true; axis = 0; return false; }
        if (!rejected && axis == 0) {
            float dx = event.getX() - downX, dy = event.getY() - downY;
            if (Math.abs(dx) > slop * 2 && Math.abs(dx) > Math.abs(dy) * 1.5f) axis = 1;
            else if (expand != null && dy < -slop * 2 && Math.abs(dy) > Math.abs(dx) * 1.5f) axis = 2;
            else if (Math.max(Math.abs(dx), Math.abs(dy)) > slop * 2) rejected = true;
        }
        if (axis != 0) getParent().requestDisallowInterceptTouchEvent(true);
        return axis != 0;
    }
    @Override public boolean onInterceptTouchEvent(MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) begin(event);
        else if (event.getActionMasked() == MotionEvent.ACTION_MOVE) return claim(event);
        return false;
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        float dx = event.getX() - downX, dy = event.getY() - downY;
        if (event.getActionMasked() == MotionEvent.ACTION_MOVE && claim(event)) {
            if (axis == 1 && dragListener != null) dragListener.onDrag(dx);
            if (axis == 2 && verticalListener != null) verticalListener.onDrag(dy);
            return true;
        }
        if (event.getActionMasked() == MotionEvent.ACTION_UP && axis != 0) {
            getParent().requestDisallowInterceptTouchEvent(false);
            float threshold = 48 * getResources().getDisplayMetrics().density;
            if (axis == 1 && dragListener != null) dragListener.onEnd(Math.abs(dx) > threshold);
            if (axis == 1 && Math.abs(dx) > threshold) {
                Runnable action = dx < 0 ? next : previous;
                if (action != null) action.run();
            } else if (axis == 2) {
                if (verticalListener != null) verticalListener.onEnd(dy, false);
                else if (dy < -threshold && expand != null) expand.run();
            }
            axis = 0; return true;
        }
        if (event.getActionMasked() == MotionEvent.ACTION_CANCEL) {
            if (dragListener != null) dragListener.onEnd(false);
            if (verticalListener != null) verticalListener.onEnd(dy, true);
            getParent().requestDisallowInterceptTouchEvent(false); axis = 0; rejected = true; setPressed(false); return true;
        }
        if (event.getActionMasked() == MotionEvent.ACTION_UP && rejected) { setPressed(false); return true; }
        return super.onTouchEvent(event);
    }
}
