package cl.arichard.descargador.util;

import android.app.Application;
import android.view.MotionEvent;
import android.widget.FrameLayout;
import android.widget.TextView;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28, application = Application.class)
public class SwipeMiniPlayerLayoutTest {
    @Test public void swipesOnPlayerBackgroundWorkAndCancelledOrDiagonalDragsDoNothing() {
        org.robolectric.android.controller.ActivityController<android.app.Activity> controller =
                org.robolectric.Robolectric.buildActivity(android.app.Activity.class).setup().visible();
        SwipeActionsLayout layout = new SwipeActionsLayout(controller.get(), null);
        FrameLayout parent = new FrameLayout(controller.get()); parent.addView(layout);
        controller.get().setContentView(parent); layout.layout(0, 0, 800, 500);
        int[] actions = {0}; layout.setSwipeActions(() -> actions[0]++, () -> actions[0]++, () -> actions[0]++);
        gesture(layout, 600, 50, 100, 50); assertEquals(1, actions[0]);
        gesture(layout, 100, 50, 300, 250); assertEquals(1, actions[0]);
        long now = android.os.SystemClock.uptimeMillis();
        for (int action : new int[]{MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE, MotionEvent.ACTION_CANCEL}) {
            MotionEvent event = MotionEvent.obtain(now, now + 20, action, action == MotionEvent.ACTION_DOWN ? 600 : 100, 50, 0);
            layout.dispatchTouchEvent(event); event.recycle();
        }
        assertEquals(1, actions[0]); controller.pause().stop().destroy();
    }
    @Test public void swipesOverChildButtonsChangeTracksWithoutTriggeringTheirClicks() {
        org.robolectric.android.controller.ActivityController<android.app.Activity> controller =
                org.robolectric.Robolectric.buildActivity(android.app.Activity.class).setup().visible();
        SwipeActionsLayout layout = new SwipeActionsLayout(controller.get(), null);
        FrameLayout parent = new FrameLayout(layout.getContext()); parent.addView(layout);
        controller.get().setContentView(parent);
        TextView button = new TextView(layout.getContext());
        int[] next = {0}, previous = {0}, expand = {0}, taps = {0};
        button.setOnClickListener(v -> taps[0]++);
        layout.addView(button, new android.widget.LinearLayout.LayoutParams(800, 100));
        layout.layout(0, 0, 800, 100); button.layout(0, 0, 800, 100);
        layout.setSwipeActions(() -> next[0]++, () -> previous[0]++, () -> expand[0]++);
        gesture(layout, 600, 50, 100, 50);
        assertEquals(1, next[0]); assertEquals(0, taps[0]);
        gesture(layout, 100, 50, 600, 50);
        assertEquals(1, previous[0]); assertEquals(0, expand[0]);
        gesture(layout, 100, 50, 100, 50);
        org.robolectric.Shadows.shadowOf(android.os.Looper.getMainLooper()).idle();
        assertEquals(1, taps[0]);
        controller.pause().stop().destroy();
    }
    private void gesture(SwipeActionsLayout layout, float x1, float y1, float x2, float y2) {
        long now = android.os.SystemClock.uptimeMillis();
        int step = 0;
        for (int action : new int[]{MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE, MotionEvent.ACTION_UP}) {
            MotionEvent event = MotionEvent.obtain(now, now + step++ * 20, action,
                    action == MotionEvent.ACTION_DOWN ? x1 : x2, action == MotionEvent.ACTION_DOWN ? y1 : y2, 0);
            layout.dispatchTouchEvent(event); event.recycle();
        }
    }
}
