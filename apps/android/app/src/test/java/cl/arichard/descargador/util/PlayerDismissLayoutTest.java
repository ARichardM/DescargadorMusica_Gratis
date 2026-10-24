package cl.arichard.descargador.util;

import android.app.Activity;
import android.app.Application;
import android.os.Looper;
import android.view.MotionEvent;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.SeekBar;
import cl.arichard.descargador.R;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.Shadows;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import java.time.Duration;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28, application = Application.class)
public class PlayerDismissLayoutTest {
    @Test public void onlyDownwardArtworkDragDismissesAndCancellationNeverDismisses() {
        ActivityController<Activity> controller = Robolectric.buildActivity(Activity.class).setup().visible();
        PlayerDismissLayout root = new PlayerDismissLayout(controller.get(), null);
        root.setOrientation(android.widget.LinearLayout.VERTICAL);
        FrameLayout art = new FrameLayout(controller.get()); art.setId(R.id.playerArtworkArea);
        SeekBar seek = new SeekBar(controller.get());
        root.addView(art, new android.widget.LinearLayout.LayoutParams(800, 300));
        root.addView(seek, new android.widget.LinearLayout.LayoutParams(800, 100));
        controller.get().setContentView(root);
        root.layout(0, 0, 800, 500); art.layout(0, 0, 800, 300); seek.layout(0, 300, 800, 400);
        int[] closed = {0}; root.setDismissAction(() -> closed[0]++);
        drag(root, 50, 50, 300, 250, MotionEvent.ACTION_UP); assertEquals(0, closed[0]);
        drag(root, 150, 350, 150, 490, MotionEvent.ACTION_UP); assertEquals(0, closed[0]);
        drag(root, 150, 50, 150, 290, MotionEvent.ACTION_CANCEL); assertEquals(0, closed[0]);
        Shadows.shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMillis(200));
        // Keep the deterministic layout after animation traversal.
        root.layout(0, 0, 800, 500); art.layout(0, 0, 800, 300);
        drag(root, 150, 50, 150, 290, MotionEvent.ACTION_UP); assertEquals(1, closed[0]);
        controller.pause().stop().destroy();
    }
    private void drag(View view, float x1, float y1, float x2, float y2, int end) {
        long now = android.os.SystemClock.uptimeMillis(); int step = 0;
        for (int action : new int[]{MotionEvent.ACTION_DOWN, MotionEvent.ACTION_MOVE, end}) {
            MotionEvent event = MotionEvent.obtain(now, now + step++ * 100, action,
                    action == MotionEvent.ACTION_DOWN ? x1 : x2, action == MotionEvent.ACTION_DOWN ? y1 : y2, 0);
            view.dispatchTouchEvent(event); event.recycle();
        }
    }
}
