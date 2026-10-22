package cl.arichard.descargador.player;

import android.content.Context;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.util.Log;
import android.view.SurfaceHolder;
import android.view.SurfaceView;
import android.view.ViewGroup;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.Toast;
import cl.arichard.descargador.DescargadorApp;
import cl.arichard.descargador.model.Song;
import cl.arichard.descargador.service.MusicService;
import com.yausername.youtubedl_android.YoutubeDL;
import com.yausername.youtubedl_android.YoutubeDLRequest;
import org.json.JSONObject;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

/** Single native player shared by the full screen and mini player. */
public class PlayerManager {
    private static PlayerManager instance;
    public static final int REPEAT_OFF = 0, REPEAT_ALL = 1, REPEAT_ONE = 2;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private final List<PlaybackListener> listeners = new ArrayList<>();
    private Context context;
    private MediaPlayer mediaPlayer;
    private boolean prepared, playWhenReady = true, online, shuffle, loading;
    private int repeatMode = REPEAT_ALL, currentIndex = -1, generation;
    private List<Song> queue = new ArrayList<>(), originalQueue = new ArrayList<>();
    private Song currentSong;
    private String currentOnlineVideoId, currentOnlineUrl;
    private SurfaceView videoView;

    public interface PlaybackListener {
        void onTrackChanged(Song song);
        void onPlaybackStateChanged(boolean playing);
        void onProgressUpdate(int position, int duration);
        default void onPlaybackError(String message) {}
        default void onPlaybackLoading(boolean loading) {}
    }

    private final Runnable progressUpdater = new Runnable() {
        @Override public void run() {
            if (!prepared || mediaPlayer == null) return;
            for (PlaybackListener l : new ArrayList<>(listeners))
                l.onProgressUpdate(getCurrentPosition(), getDuration());
            handler.postDelayed(this, 350);
        }
    };

    public static synchronized PlayerManager getInstance() {
        if (instance == null) instance = new PlayerManager();
        return instance;
    }
    public void init(Context ctx) { context = ctx.getApplicationContext(); }
    public void setMainActivityHost(ViewGroup host) { /* Native audio needs no hidden WebView. */ }

    // Activity compatibility: these methods now attach a native video surface.
    public void attachOnlineWebView(ViewGroup host) {
        detachOnlineWebView();
        if (host == null) return;
        videoView = new SurfaceView(host.getContext());
        host.addView(videoView, new FrameLayout.LayoutParams(-1, -1));
        videoView.getHolder().addCallback(new SurfaceHolder.Callback() {
            @Override public void surfaceCreated(SurfaceHolder holder) {
                if (mediaPlayer != null) mediaPlayer.setDisplay(holder);
            }
            @Override public void surfaceChanged(SurfaceHolder holder, int format, int width, int height) {
                if (mediaPlayer != null) mediaPlayer.setDisplay(holder);
            }
            @Override public void surfaceDestroyed(SurfaceHolder holder) {
                if (mediaPlayer != null) mediaPlayer.setDisplay(null);
            }
        });
        videoView.post(this::fitVideo);
    }
    public void detachOnlineWebView() {
        if (mediaPlayer != null) mediaPlayer.setDisplay(null);
        if (videoView != null && videoView.getParent() instanceof ViewGroup)
            ((ViewGroup) videoView.getParent()).removeView(videoView);
        videoView = null;
    }

    private void fitVideo() {
        if (videoView == null || !prepared || mediaPlayer == null) return;
        ViewGroup host = (ViewGroup) videoView.getParent();
        int width = mediaPlayer.getVideoWidth(), height = mediaPlayer.getVideoHeight();
        if (host == null || width <= 0 || height <= 0 || host.getWidth() <= 0 || host.getHeight() <= 0) return;
        float scale = Math.min((float) host.getWidth() / width, (float) host.getHeight() / height);
        videoView.setLayoutParams(new FrameLayout.LayoutParams(Math.round(width * scale), Math.round(height * scale), Gravity.CENTER));
    }

    public void playSong(Song song, List<Song> newQueue) {
        online = false;
        if (newQueue != null && !newQueue.isEmpty()) {
            originalQueue = new ArrayList<>(newQueue);
            queue = new ArrayList<>(newQueue);
            if (shuffle) Collections.shuffle(queue);
        }
        currentSong = song;
        currentIndex = queue.indexOf(song);
        if (currentIndex < 0 && song != null) { queue.add(0, song); currentIndex = 0; }
        startLocal();
    }

    private void startLocal() {
        if (currentSong == null) return;
        releasePlayer();
        playWhenReady = true;
        notifyTrack();
        try { prepareSource(currentSong.getPath(), Collections.emptyMap()); }
        catch (Exception e) { fail(e); }
    }

    public void playOnline(String videoId, String title, String channel, String thumbnail, String url) {
        releasePlayer();
        final int requestGeneration = generation;
        online = true;
        playWhenReady = true;
        currentOnlineVideoId = videoId;
        currentOnlineUrl = "https://www.youtube.com/watch?v=" + videoId;
        currentSong = new Song(System.currentTimeMillis(), title, channel, "YouTube", 0,
                thumbnail != null ? thumbnail : "https://i.ytimg.com/vi/" + videoId + "/hqdefault.jpg",
                "YouTube", System.currentTimeMillis());
        notifyTrack();
        notifyState();
        loading(true);
        final String target = currentOnlineUrl;
        DescargadorApp.IO.execute(() -> {
            try {
                YoutubeDLRequest request = new YoutubeDLRequest(target);
                request.addOption("--no-playlist");
                request.addOption("--dump-single-json");
                request.addOption("--skip-download");
                request.addOption("--socket-timeout", "15");
                request.addOption("-f", "best[ext=mp4]/best");
                JSONObject info = new JSONObject(YoutubeDL.getInstance().execute(request).getOut());
                String stream = info.getString("url");
                Map<String, String> headers = new HashMap<>();
                JSONObject http = info.optJSONObject("http_headers");
                if (http != null) {
                    Iterator<String> keys = http.keys();
                    while (keys.hasNext()) { String key = keys.next(); headers.put(key, http.getString(key)); }
                }
                handler.post(() -> {
                    if (generation != requestGeneration) return;
                    try { prepareSource(stream, headers); } catch (Exception e) { fail(e); }
                });
            } catch (Exception e) {
                handler.post(() -> { if (generation == requestGeneration) fail(e); });
            }
        });
    }

    private void prepareSource(String source, Map<String, String> headers) throws Exception {
        MediaPlayer player = new MediaPlayer();
        mediaPlayer = player;
        player.setWakeMode(context, PowerManager.PARTIAL_WAKE_LOCK);
        player.setAudioAttributes(new AudioAttributes.Builder().setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                .setUsage(AudioAttributes.USAGE_MEDIA).build());
        player.setOnPreparedListener(mp -> {
            if (mp != mediaPlayer) return;
            prepared = true;
            fitVideo();
            loading(false);
            if (playWhenReady) mp.start();
            notifyState();
            handler.post(progressUpdater);
            Log.i("MusicBoxPlayer", "Prepared: duration=" + mp.getDuration() + " video=" + mp.getVideoWidth() + "x" + mp.getVideoHeight());
        });
        player.setOnErrorListener((mp, what, extra) -> {
            if (mp == mediaPlayer) fail(new IllegalStateException("Error del reproductor " + what + "/" + extra));
            return true;
        });
        player.setOnVideoSizeChangedListener((mp, width, height) -> fitVideo());
        player.setOnCompletionListener(mp -> {
            if (repeatMode == REPEAT_ONE) { mp.seekTo(0); mp.start(); }
            else if (online) { playWhenReady = false; notifyState(); }
            else playNext();
        });
        if (videoView != null && videoView.getHolder().getSurface().isValid()) player.setDisplay(videoView.getHolder());
        if (source.startsWith("http")) player.setDataSource(context, Uri.parse(source), headers);
        else player.setDataSource(source);
        loading(true);
        player.prepareAsync();
    }

    private void fail(Exception error) {
        Log.e("MusicBoxPlayer", "Playback failed", error);
        releasePlayer();
        loading(false);
        String message = online ? "No se pudo reproducir. Revisa la conexión o prueba otro resultado." : "No se pudo abrir el archivo de música.";
        for (PlaybackListener l : new ArrayList<>(listeners)) l.onPlaybackError(message);
        Toast.makeText(context, message, Toast.LENGTH_LONG).show();
        notifyState();
    }
    public void togglePlayPause() {
        if (!prepared) {
            if (loading) playWhenReady = !playWhenReady;
            else if (online) playOnline(currentOnlineVideoId, currentSong.getTitle(), currentSong.getArtist(), currentSong.getPath(), currentOnlineUrl);
            else startLocal();
            return;
        }
        if (mediaPlayer.isPlaying()) { playWhenReady = false; mediaPlayer.pause(); }
        else { playWhenReady = true; mediaPlayer.start(); }
        notifyState();
    }
    public void playNext() {
        if (online || queue.isEmpty()) return;
        if (repeatMode != REPEAT_ONE) currentIndex++;
        if (currentIndex >= queue.size()) {
            if (repeatMode != REPEAT_ALL) { releasePlayer(); notifyState(); return; }
            currentIndex = 0;
        }
        currentSong = queue.get(Math.max(0, currentIndex));
        startLocal();
    }
    public void playPrevious() {
        if (online || getCurrentPosition() > 3000) { seekTo(0); return; }
        if (queue.isEmpty()) return;
        currentIndex = currentIndex > 0 ? currentIndex - 1 : (repeatMode == REPEAT_ALL ? queue.size() - 1 : 0);
        currentSong = queue.get(currentIndex); startLocal();
    }
    public void seekTo(int ms) { if (prepared && mediaPlayer != null) mediaPlayer.seekTo(ms); }
    public boolean toggleShuffle() {
        shuffle = !shuffle;
        queue = new ArrayList<>(originalQueue);
        if (shuffle) Collections.shuffle(queue);
        currentIndex = queue.indexOf(currentSong);
        return shuffle;
    }
    public int toggleRepeat() { return repeatMode = (repeatMode + 1) % 3; }
    public boolean isPlaying() { return prepared && mediaPlayer != null && mediaPlayer.isPlaying(); }
    public boolean isLoading() { return loading; }
    public int getCurrentPosition() { return prepared && mediaPlayer != null ? mediaPlayer.getCurrentPosition() : 0; }
    public int getDuration() { return prepared && mediaPlayer != null ? mediaPlayer.getDuration() : 0; }
    public Song getCurrentSong() { return currentSong; }
    public boolean isOnlineTrack() { return online; }
    public String getCurrentOnlineVideoId() { return currentOnlineVideoId; }
    public String getCurrentOnlineUrl() { return currentOnlineUrl; }
    public boolean isShuffle() { return shuffle; }
    public int getRepeatMode() { return repeatMode; }
    public void addListener(PlaybackListener l) { if (l != null && !listeners.contains(l)) listeners.add(l); }
    public void removeListener(PlaybackListener l) { listeners.remove(l); }
    private void notifyTrack() { for (PlaybackListener l : new ArrayList<>(listeners)) l.onTrackChanged(currentSong); }
    private void notifyState() {
        boolean playing = isPlaying();
        for (PlaybackListener l : new ArrayList<>(listeners)) l.onPlaybackStateChanged(playing);
        if (currentSong != null) MusicService.updateNotification(context, currentSong, playing);
    }
    private void loading(boolean value) { loading = value; for (PlaybackListener l : new ArrayList<>(listeners)) l.onPlaybackLoading(value); }
    private void releasePlayer() {
        generation++;
        prepared = false;
        handler.removeCallbacks(progressUpdater);
        if (mediaPlayer != null) { mediaPlayer.release(); mediaPlayer = null; }
    }
}
