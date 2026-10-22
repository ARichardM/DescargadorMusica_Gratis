package cl.arichard.descargador.util;

import android.content.Context;
import android.util.AttributeSet;
import android.view.MotionEvent;
import android.view.ViewConfiguration;
import android.widget.LinearLayout;
import cl.arichard.descargador.R;

/** Entire action strip is reserved for deliberate taps; vertical scrolling still belongs to its list. */
public class GuardedActionsLayout extends LinearLayout {
    private float downX, downY; private boolean dragged;
    private final int slop;
    public GuardedActionsLayout(Context context, AttributeSet attrs) {
        super(context, attrs); slop = ViewConfiguration.get(context).getScaledTouchSlop();
        setTag(R.id.protectedAction, true);
    }
    @Override public boolean dispatchTouchEvent(MotionEvent event) {
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
            downX = event.getRawX(); downY = event.getRawY(); dragged = false;
        } else if (event.getActionMasked() == MotionEvent.ACTION_MOVE && !dragged
                && Math.hypot(event.getRawX() - downX, event.getRawY() - downY) > slop) {
            dragged = true;
            MotionEvent cancel = MotionEvent.obtain(event); cancel.setAction(MotionEvent.ACTION_CANCEL);
            super.dispatchTouchEvent(cancel); cancel.recycle(); return true;
        }
        if (dragged && event.getActionMasked() != MotionEvent.ACTION_CANCEL) return true;
        return super.dispatchTouchEvent(event);
    }
}
