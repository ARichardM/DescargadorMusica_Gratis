package cl.arichard.descargador;

import android.app.Application;
import android.content.SharedPreferences;
import androidx.appcompat.app.AppCompatDelegate;
import com.yausername.ffmpeg.FFmpeg;
import com.yausername.youtubedl_android.YoutubeDL;
import cl.arichard.descargador.data.PlaylistManager;
import cl.arichard.descargador.player.PlayerManager;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class DescargadorApp extends Application {
    public static final ExecutorService IO = Executors.newSingleThreadExecutor();
    private volatile boolean ready;
    private volatile String initError;

    @Override public void onCreate() {
        super.onCreate();
        // Immediately enforce saved theme before any activity or layout inflater runs
        SharedPreferences prefs = getSharedPreferences("musicbox_prefs", MODE_PRIVATE);
        boolean isDark = prefs.getBoolean("dark_mode", true);
        AppCompatDelegate.setDefaultNightMode(isDark ? AppCompatDelegate.MODE_NIGHT_YES : AppCompatDelegate.MODE_NIGHT_NO);

        PlayerManager.getInstance().init(this);
        PlaylistManager.getInstance(this);

        IO.execute(() -> {
            try {
                YoutubeDL.getInstance().init(this);
                FFmpeg.getInstance().init(this);
                ready = true;
            } catch (Exception e) {
                initError = e.getLocalizedMessage();
            }
        });
    }

    public boolean isReady() { return ready; }
    public String getInitError() { return initError; }
}
