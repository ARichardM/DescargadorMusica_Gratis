package cl.arichard.descargador.util;

import android.content.Context;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.ViewConfiguration;
import android.widget.HorizontalScrollView;

/** A carousel owns horizontal drags, including at its edges, and yields vertical drags. */
public class AxisHorizontalScrollView extends HorizontalScrollView {
    private float downX, downY;
    private int axis;
    private final int slop;
    public AxisHorizontalScrollView(Context context, AttributeSet attrs) {
        super(context, attrs); slop = ViewConfiguration.get(context).getScaledTouchSlop();
    }
    @Override public boolean dispatchTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                downX = event.getX(); downY = event.getY(); axis = 0;
                getParent().requestDisallowInterceptTouchEvent(true); break;
            case MotionEvent.ACTION_MOVE:
                if (axis == 0) {
                    float dx = Math.abs(event.getX() - downX), dy = Math.abs(event.getY() - downY);
                    if (Math.max(dx, dy) > slop) axis = dx > dy ? 1 : 2;
                }
                getParent().requestDisallowInterceptTouchEvent(axis != 2); break;
            case MotionEvent.ACTION_UP:
            case MotionEvent.ACTION_CANCEL:
                getParent().requestDisallowInterceptTouchEvent(false); axis = 0; break;
        }
        return super.dispatchTouchEvent(event);
    }
}
